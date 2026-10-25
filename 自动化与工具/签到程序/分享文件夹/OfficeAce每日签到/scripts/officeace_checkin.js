// ============================================================
// OfficeAce（果办）每日签到（独立分享版）
//
// 原理：读取果办客户端本地登录态（session.cookie，DPAPI 加密），
//       通过客户端本地 API（127.0.0.1，HTTPS 自签证书）完成每日签到。
//       全程只读本机文件，凭证不落盘、不上传。
//
// ⚠️ 重要前置：签到时果办客户端必须处于运行状态！
//    签到走客户端本地 API（客户端内嵌服务承载云凭证签名），
//    客户端没启动则必然失败。
//
// 前置条件：
//   1. 已安装 OfficeAce（果办）客户端并登录，且签到时保持运行
//   2. Node.js 18+（无 Node 时 run_checkin.cmd 会尝试用客户端兜底）
//
// 用法: node officeace_checkin.js [--no-delay] [--status]
//   --no-delay  跳过随机延迟（手动测试用）
//   --status    只查询签到状态，不执行领取
// 退出码: 0=成功/已签/查询成功  1=失败
//
// 可选配置：上级目录 config.json，如 {"delayMinSec":30,"delayMaxSec":300}
// ============================================================
'use strict';
const fs = require('fs');
const os = require('os');
const path = require('path');
const https = require('https');
const { execFileSync, execSync } = require('child_process');

// ---------- 配置 ----------
const CFG_PATH = path.join(__dirname, '..', 'config.json');
const CFG = (() => {
  try { return JSON.parse(fs.readFileSync(CFG_PATH, 'utf8')); }
  catch { return {}; }
})();
const DELAY_MIN = CFG.delayMinSec ?? 30;
const DELAY_MAX = CFG.delayMaxSec ?? 300;

// ---------- 工具 ----------
const log = m => console.log(`${new Date().toLocaleString('sv-SE')} ${m}`);
const sleep = s => new Promise(r => setTimeout(r, s * 1000));

function logSection(name) {
  console.log(`\n${'='.repeat(50)}\n[${name}]\n${'='.repeat(50)}`);
}

// ============================================================
// 公共件：注册表安装目录探测 + DPAPI(CurrentUser) 解密
// ============================================================
function regQueryInstallLocation(keyword) {
  try {
    const out = execSync(
      `reg query "HKCU\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall" /s /f "${keyword}" /d`,
      { encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }
    );
    const m = out.match(/InstallLocation\s+REG_SZ\s+(.+)/i);
    if (m) return m[1].trim();
  } catch { /* 注册表查询失败按未安装处理 */ }
  return '';
}

// 入参为密文 Buffer，返回明文 Buffer
function dpapiUnprotect(buf) {
  const payload = Buffer.from(buf).toString('base64');
  const ps = [
    "Add-Type -AssemblyName System.Security;",
    `$src=[Convert]::FromBase64String('${payload}');`,
    "$dst=New-Object byte[] $src.Length;",
    "[array]::Copy($src,0,$dst,0,$src.Length);",
    "$k=[Security.Cryptography.ProtectedData]::Unprotect($dst,$null,'CurrentUser');",
    "[Convert]::ToBase64String($k)"
  ].join('');
  const out = execFileSync('powershell.exe',
    ['-NoProfile', '-NonInteractive', '-Command', ps],
    { encoding: 'utf8' }).trim();
  return Buffer.from(out, 'base64');
}

// ============================================================
// 安装目录探测：注册表 -> 常见路径候选
// ============================================================
function officeaceFindInstallDir() {
  const fromRegistry = regQueryInstallLocation('OfficeAce');
  if (fromRegistry && fs.existsSync(fromRegistry)) return fromRegistry;
  const candidates = [
    path.join(process.env.LOCALAPPDATA || '', 'Programs', 'OfficeAce'),
    path.join(os.homedir(), 'OfficeAce'),
    path.join('C:\\Program Files', 'OfficeAce'),
    path.join('C:\\Program Files (x86)', 'OfficeAce'),
  ];
  for (const p of candidates) {
    if (p && fs.existsSync(p)) return p;
  }
  return '';
}

// ============================================================
// 本地 API 地址弹性发现（四层策略，候选遍历 + 逐个探测判活）
// ============================================================
// 已知默认端口：3004 为当前版本默认（.env API_SERVER_PORT），3002 为代码内另一默认值
const OFFICEACE_DEFAULT_PORTS = [3004, 3002];

// 策略④：轻量枚举本机回环监听端口（netstat 毫秒级、零模块依赖；
// 不用 Get-NetTCPConnection/Get-CimInstance——实测 WMI/模块冷启动超过 20 秒）
function officeaceFindLocalListenPorts() {
  try {
    const out = execFileSync('netstat.exe', ['-ano'],
      { encoding: 'utf8', timeout: 15000, windowsHide: true, maxBuffer: 16 * 1024 * 1024 });
    const ports = new Set();
    for (const line of out.split(/\r?\n/)) {
      if (!/\bLISTENING\b/i.test(line)) continue;
      const m = line.match(/^\s*TCP\s+(?:127\.0\.0\.1|\[::1\]):(\d+)\s/i);
      if (m) ports.add(Number(m[1]));
    }
    return [...ports];
  } catch { return []; }
}

// 策略②：从 .env / .inner.env 读取 API_SERVER_PORT（跳过注释行）
function officeaceReadEnvApiPort(installDir) {
  if (!installDir) return null;
  for (const name of ['.env', '.inner.env']) {
    try {
      const p = path.join(installDir, name);
      if (!fs.existsSync(p)) continue;
      for (const line of fs.readFileSync(p, 'utf8').split(/\r?\n/)) {
        const m = line.match(/^\s*API_SERVER_PORT\s*=\s*(\d+)\s*$/);
        if (m) return Number(m[1]);
      }
    } catch { /* 忽略单个文件读取失败 */ }
  }
  return null;
}

// 判活探测：果办本地 API 无论有无有效会话，/api/subscription/current 均返回
// 200（已鉴权）/ 401 / 403（鉴权中间件），并要求响应体含果办特征，避免误判其他本地服务
async function officeaceProbeApi(origin) {
  try {
    const res = await officeaceHttpJson('GET', `${origin}/api/subscription/current`, { timeoutMs: 6000 });
    if (res.status === 200) {
      return /"bonusSkus"|"planId"|"creditGroups"|"tier"/.test(res.body);
    }
    if (res.status === 401 || res.status === 403) {
      return /"statusCode"|Authentication required/i.test(res.body);
    }
    return false;
  } catch { return false; }
}

// 汇总四层策略候选，去重后逐个探测，返回 { origin, source } 或 null
async function officeaceDiscoverApiOrigin(installDir) {
  const candidates = [];

  // 策略①：运行态快照 runtime-state.json（服务每次启动时写入，快/准/零成本）
  if (installDir) {
    try {
      const p = path.join(installDir, '.office-claw', 'run', 'windows', 'runtime-state.json');
      if (fs.existsSync(p)) {
        const state = JSON.parse(fs.readFileSync(p, 'utf8'));
        if (state.ApiUrl && /^https?:\/\//.test(state.ApiUrl)) {
          candidates.push({ origin: state.ApiUrl.replace(/\/+$/, ''), source: '运行态快照' });
        } else if (state.ApiPort) {
          candidates.push({ origin: `https://127.0.0.1:${state.ApiPort}`, source: '运行态快照' });
          candidates.push({ origin: `http://127.0.0.1:${state.ApiPort}`, source: '运行态快照' });
        }
      }
    } catch { /* 忽略快照读取失败 */ }
  }

  // 策略②：.env / .inner.env 的 API_SERVER_PORT
  const envPort = officeaceReadEnvApiPort(installDir);
  if (envPort) {
    candidates.push({ origin: `https://127.0.0.1:${envPort}`, source: 'env 配置' });
    candidates.push({ origin: `http://127.0.0.1:${envPort}`, source: 'env 配置' });
  }

  // 策略③：已知默认端口兜底
  for (const port of OFFICEACE_DEFAULT_PORTS) {
    candidates.push({ origin: `https://127.0.0.1:${port}`, source: '默认端口' });
    candidates.push({ origin: `http://127.0.0.1:${port}`, source: '默认端口' });
  }

  // 逐个探测前三层候选
  const seen = new Set();
  for (const c of candidates) {
    if (seen.has(c.origin)) continue;
    seen.add(c.origin);
    if (await officeaceProbeApi(c.origin)) return c;
  }

  // 策略④：全量枚举回环监听端口并发探测（客户端换端口/多实例时的终极兜底）
  const ports = officeaceFindLocalListenPorts();
  if (ports.length > 0) {
    log(`前述候选均未命中，改为扫描本机 ${ports.length} 个回环监听端口...`);
    const tasks = [];
    for (const port of ports) {
      for (const scheme of ['https', 'http']) {
        const origin = `${scheme}://127.0.0.1:${port}`;
        if (seen.has(origin)) continue;
        seen.add(origin);
        tasks.push((async () => {
          return (await officeaceProbeApi(origin)) ? { origin, source: '端口扫描' } : null;
        })());
      }
    }
    const results = await Promise.all(tasks);
    const hit = results.find(Boolean);
    if (hit) return hit;
  }

  return null;
}

// ============================================================
// 登录态解密：session.cookie = "OC-DPAPI-1\n" + base64(DPAPI(CurrentUser, JSON))
// 解密得 { value, expires }，value 即签名后的 oc_sid Cookie 值
// ============================================================
const OFFICEACE_SESSION_COOKIE_PATH = path.join(os.homedir(), '.office-claw', 'session.cookie');

function officeaceDecryptSessionCookie() {
  const raw = fs.readFileSync(OFFICEACE_SESSION_COOKIE_PATH, 'utf8');
  if (!raw.startsWith('OC-DPAPI-1')) throw new Error('session.cookie 格式异常（缺少 OC-DPAPI-1 头）');
  const b64 = raw.slice('OC-DPAPI-1\n'.length).trim();
  const session = JSON.parse(dpapiUnprotect(Buffer.from(b64, 'base64')).toString('utf8'));
  if (!session.value) throw new Error('session.cookie 解密结果缺少 value');
  return session;
}

// ============================================================
// TLS 信任：安装目录 .office-claw\certs\root-ca.pem（自签三级 CA 链）
// ============================================================
function officeaceFindRootCaPem(installDir) {
  if (!installDir) return '';
  const p = path.join(installDir, '.office-claw', 'certs', 'root-ca.pem');
  try {
    return fs.existsSync(p) ? fs.readFileSync(p, 'utf8') : '';
  } catch { return ''; }
}

// ============================================================
// 本地 API 请求（HTTPS + CA 信任；无 CA 时退化为跳过证书校验）
// ============================================================
function officeaceHttpJson(method, urlStr, { cookie, caPem, timeoutMs = 20000 } = {}) {
  return new Promise((resolve, reject) => {
    const u = new URL(urlStr);
    const headers = {
      'Accept': 'application/json',
    };
    if (cookie) headers['Cookie'] = cookie; // 探测时无会话，不发送 Cookie 头（undefined 值会被 Node 拒绝）
    let body;
    if (method === 'POST') {
      headers['Content-Type'] = 'application/json'; // 本地服务校验 Content-Type，缺失返回 415
      body = '{}'; // 空对象请求体，与客户端行为一致
    }
    const options = {
      hostname: u.hostname,
      port: u.port || 443,
      path: u.pathname + u.search,
      method,
      headers,
      timeout: timeoutMs,
    };
    if (caPem) {
      options.ca = caPem;
    } else {
      options.rejectUnauthorized = false; // 兜底：找不到 CA 文件时跳过证书校验
    }
    const req = https.request(options, res => {
      let data = '';
      res.on('data', d => { data += d; });
      res.on('end', () => resolve({ status: res.statusCode, body: data }));
    });
    req.on('error', reject);
    req.on('timeout', () => req.destroy(new Error('请求超时')));
    if (body) req.write(body);
    req.end();
  });
}

// ============================================================
// 主流程
// ============================================================
const OFFICEACE_DAILY_ACTIVITY_ID = 'bonus-daily-checkin-2026';

async function main() {
  const args = process.argv.slice(2);
  const statusOnly = args.includes('--status');
  const noDelay = args.includes('--no-delay');

  logSection('OfficeAce（果办）每日签到');

  // 1. 登录态
  if (!fs.existsSync(OFFICEACE_SESSION_COOKIE_PATH)) {
    log('错误：未找到果办登录态文件（请确认已安装并登录 OfficeAce）');
    process.exitCode = 1; return;
  }
  let session;
  try {
    session = officeaceDecryptSessionCookie();
  } catch (e) {
    log(`错误：登录态解密失败 - ${e.message}`);
    log('提示：请打开 OfficeAce 客户端确认已登录');
    process.exitCode = 1; return;
  }
  // Cookie 有效期检查（expires 为 epoch 秒）
  if (typeof session.expires === 'number' && session.expires * 1000 < Date.now()) {
    log('警告：会话 Cookie 已过期，将尝试请求（失败请打开客户端重新登录）');
  }

  // 2. 本地 API 地址弹性发现与 CA
  const installDir = officeaceFindInstallDir();
  const caPem = officeaceFindRootCaPem(installDir);
  const found = await officeaceDiscoverApiOrigin(installDir);
  if (!found) {
    log('错误：未发现 OfficeAce 本地 API（客户端未运行或未按预期监听），请先启动果办客户端');
    process.exitCode = 1; return;
  }
  const origin = found.origin;
  log(`本地 API：${origin}（来源：${found.source}，${caPem ? 'root-ca.pem 信任' : '跳过证书校验'}）`);
  const cookie = `oc_sid=${session.value}`;

  const get = p => officeaceHttpJson('GET', `${origin}${p}`, { cookie, caPem });
  const post = p => officeaceHttpJson('POST', `${origin}${p}`, { cookie, caPem });

  // 3. 查询签到活动
  let status;
  try {
    const res = await get('/api/subscription/current');
    if (res.status === 401 || res.status === 403) {
      log('错误：本地会话已失效，请打开 OfficeAce 客户端重新登录');
      process.exitCode = 1; return;
    }
    if (res.status !== 200) {
      log(`错误：状态接口返回 HTTP ${res.status}`);
      process.exitCode = 1; return;
    }
    status = JSON.parse(res.body);
  } catch (e) {
    const msg = e.cause?.code || e.cause?.message || e.message;
    if (/ECONNREFUSED|ECONNRESET|ENOTFOUND|fetch failed/i.test(msg)) {
      log('错误：OfficeAce 客户端未运行（本地 API 无法连接），请先启动果办客户端');
    } else {
      log(`错误：状态接口调用失败 - ${msg}`);
    }
    process.exitCode = 1; return;
  }

  const bonuses = status.bonusSkus || [];
  // 同一活动可能多条记录短暂并存（昨日记录过期消失前 + 今日新领），取 effectiveTime 最新一条
  const dailies = bonuses
    .filter(b => b.activityId === OFFICEACE_DAILY_ACTIVITY_ID)
    .sort((a, b) => new Date(b.effectiveTime).getTime() - new Date(a.effectiveTime).getTime());
  const daily = dailies[0];

  if (!daily) {
    const other = bonuses.length > 0 ? `（现有活动：${bonuses.map(b => b.activityId).join(', ')}）` : '';
    log(`未找到每日签到活动${other}。活动可能已下线或尚未刷新（每日 00:00 刷新），跳过本次`);
    return; // 跳过不算失败
  }

  // ---- 判定语义 ----
  // currentValue 是已消耗量，不作判定依据；「今日已领」看 effectiveTime 是否落在今日北京时间 00:00 之后
  const now = Date.now();
  const bjTodayStart = (() => {
    const bj = new Date(now + 8 * 3600 * 1000); // 换算到北京日期
    return Date.UTC(bj.getUTCFullYear(), bj.getUTCMonth(), bj.getUTCDate()) - 8 * 3600 * 1000;
  })();
  const effMs = new Date(daily.effectiveTime).getTime();
  const total = Number(daily.points) || 0;

  if (effMs >= bjTodayStart && effMs <= now) {
    log(`今日已签到。${daily.activityName} +${total} 积分已入账（领取时刻 ${daily.effectiveTime}，有效期至 ${daily.expiredTime}）`);
    log(`当前总余额 ${status.totalCredits}（已用 ${status.usedCredits}）`);
    return;
  }

  if (statusOnly) {
    log(`${daily.activityName} 今日可领（+${total} 积分），当前总余额 ${status.totalCredits}（已用 ${status.usedCredits}）`);
    return;
  }

  // 4. 随机延迟防检测
  if (!noDelay) {
    const sec = DELAY_MIN + Math.floor(Math.random() * (DELAY_MAX - DELAY_MIN + 1));
    log(`随机延迟 ${sec} 秒...`);
    await sleep(sec);
  }

  // 5. 今日未领（列表为昨日残留记录或无记录）：发起领取（服务端会领取当天全部可领奖励）
  log(`${daily.activityName} 今日可领（+${total} 积分），领取中...`);
  let claimBody;
  try {
    const res = await post('/api/subscription/claim-bonus');
    const text = res.body || '';
    if (res.status !== 200) {
      log(`领取请求失败 HTTP ${res.status}：${text.slice(0, 200)}`);
      process.exitCode = 1; return;
    }
    claimBody = JSON.parse(text);
  } catch (e) {
    log(`错误：领取请求失败 - ${e.cause?.code || e.cause?.message || e.message}`);
    process.exitCode = 1; return;
  }

  const claimedSkus = claimBody.bonusSkus || [];
  const dailyAfter = claimedSkus.find(b => b.activityId === OFFICEACE_DAILY_ACTIVITY_ID);
  if (dailyAfter) {
    log(`领取成功！${dailyAfter.activityName} +${Number(dailyAfter.points)} 积分已入账（有效期至 ${dailyAfter.expiredTime}）`);
  } else if (claimedSkus.length > 0) {
    // 领到其他活动奖励（如节日翻倍礼）但未含每日签到，仍以复查结果为准
    for (const b of claimedSkus) {
      log(`附带入账：${b.activityName}（${b.activityId}）+${Number(b.points)} 积分`);
    }
  }

  // 6. 复查确认（以最新 effectiveTime 判断今日是否已入账；claim 返回空 = 客户端已代领）
  await sleep(2);
  try {
    const res2 = await get('/api/subscription/current');
    const j2 = res2.status === 200 ? JSON.parse(res2.body) : {};
    const d2 = (j2.bonusSkus || [])
      .filter(b => b.activityId === OFFICEACE_DAILY_ACTIVITY_ID)
      .sort((a, b) => new Date(b.effectiveTime).getTime() - new Date(a.effectiveTime).getTime())[0];
    const eff2 = d2 ? new Date(d2.effectiveTime).getTime() : 0;
    if (d2 && eff2 >= bjTodayStart && eff2 <= Date.now()) {
      const tip = dailyAfter ? '' : '（今日早前已被客户端或其它会话领取）';
      log(`签到完成${tip}！${d2.activityName} +${Number(d2.points)} 积分已入账，当前总余额 ${j2.totalCredits}（已用 ${j2.usedCredits}）`);
      return;
    }
    log('领取请求已发送，但复查未见今日入账记录（疑云端资格判定未通过），请人工确认');
    process.exitCode = 1;
  } catch (e) {
    log(`警告：复查失败（领取请求可能已生效）- ${e.cause?.code || e.cause?.message || e.message}`);
    process.exitCode = 1;
  }
}

main().catch(e => { log(`致命错误：${e.message}`); process.exitCode = 1; });
