// ============================================================
// WorkBuddy 每日签到（独立分享版）
//
// 原理：读取 WorkBuddy（腾讯 CodeBuddy 桌面版）本地登录凭证
//       （workbuddy-desktop.info 中 $wbEncrypted 加密信封的 accessToken，
//       AES-256-GCM + AAD；密钥 atRestSecretKey 经 WorkBuddy.exe 内置
//       native 绑定获取，sha256 派生对称密钥），解密后调用签到 API。
//       全程只读本机文件，凭证不离开本机。
//
// 前置条件：
//   1. 已安装 WorkBuddy 客户端并登录（脚本只复用本地登录态；
//      取密钥需要 WorkBuddy.exe 存在，但无需客户端正在运行）
//   2. Node.js 18+（无 Node 时 run_checkin.cmd 会尝试用 WorkBuddy 客户端兜底）
//
// 用法: node workbuddy_checkin.js [--no-delay] [--status]
//   --no-delay  跳过随机延迟（手动测试用）
//   --status    只查询签到状态，不执行签到
// 退出码: 0=成功/已签/查询成功  1=失败
//
// 可选配置：上级目录 config.json，如 {"delayMinSec":30,"delayMaxSec":300}
// ============================================================
'use strict';
const fs = require('fs');
const os = require('os');
const path = require('path');
const crypto = require('crypto');
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

// ============================================================
// 环境探测（全自动，无硬编码）
// ============================================================
const WB_BASE = 'https://copilot.tencent.com';
// 认证数据目录：优先 LOCALAPPDATA，兜底 os.homedir()\AppData\Local
// （auth 不在 .workbuddy 下：客户端 sharedDataPath 指向 CodeBuddyExtension\Data\Public）
const WB_AUTH_DIR = path.join(
  process.env.LOCALAPPDATA || path.join(os.homedir(), 'AppData', 'Local'),
  'CodeBuddyExtension', 'Data', 'Public', 'auth'
);

// ---- 注册表探测：按关键词查客户端安装目录（未安装返回 ''）----
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

// 自动探测 WorkBuddy.exe 安装路径：注册表 -> 常见路径候选
function findWorkBuddyExe() {
  const localAppData = process.env.LOCALAPPDATA || '';
  const candidates = [];
  const installDir = regQueryInstallLocation('WorkBuddy');
  if (installDir) candidates.push(path.join(installDir, 'WorkBuddy.exe'));
  candidates.push(
    path.join(localAppData, 'Programs', 'WorkBuddy', 'WorkBuddy.exe'),
    path.join('C:\\Program Files', 'WorkBuddy', 'WorkBuddy.exe'),
    path.join('C:\\Program Files (x86)', 'WorkBuddy', 'WorkBuddy.exe'),
  );
  for (const p of candidates) {
    if (fs.existsSync(p)) return p;
  }
  return '';
}

// ---- 目录下按修改时间取最新的匹配文件（登录态兜底定位）----
function pickNewestFile(dir, filter) {
  try {
    return fs.readdirSync(dir)
      .filter(filter)
      .map(name => ({ path: path.join(dir, name), mtime: fs.statSync(path.join(dir, name)).mtimeMs }))
      .sort((a, b) => b.mtime - a.mtime)
      .map(x => x.path)[0] || null;
  } catch { return null; }
}

function wbFindAuthFile() {
  const preferred = path.join(WB_AUTH_DIR, 'workbuddy-desktop.info');
  if (fs.existsSync(preferred)) return preferred;
  // 兜底：取目录内最新的非时间戳命名 .info 文件
  return pickNewestFile(WB_AUTH_DIR,
    f => f.endsWith('.info') && f !== 'workbuddy-desktop.info' && !/^\d{4}-\d{2}-\d{2}T/.test(f));
}

// ============================================================
// 凭证提取：$wbEncrypted 信封 -> AES-256-GCM(+AAD) 解密 -> accessToken
// （密钥来自客户端 native 绑定，算法逆向自客户端）
// ============================================================
// 密钥获取三层：①native binding（本进程即 Electron 时）②本地缓存 ③spawn WorkBuddy.exe
// （ELECTRON_RUN_AS_NODE 模式跑内联脚本，只需 exe 存在，无需客户端正在运行，
//  也不触发单实例锁；实测 1 秒内返回）
function wbGetAtRestSecretKey() {
  // 1. native binding（进程自身为 WorkBuddy.exe/Electron 时）
  try {
    const ws = process._linkedBinding('electron_browser_workbuddy_storage');
    const raw = JSON.parse(String(ws.loggerGet()));
    if (typeof raw.atRestSecretKey === 'string' && raw.atRestSecretKey.length === 44) {
      return raw.atRestSecretKey;
    }
  } catch { /* 非 Electron 进程，继续下一层 */ }
  // 2. 上次缓存（客户端卸载时的兜底；两代文件名均尝试）
  for (const f of ['wb_key.json', 'wb_atrest_key.json']) {
    try {
      const cached = JSON.parse(fs.readFileSync(path.join(__dirname, '.temp', f), 'utf8'));
      if (typeof cached.atRestSecretKey === 'string' && cached.atRestSecretKey.length === 44) {
        return cached.atRestSecretKey;
      }
    } catch { /* 无缓存 */ }
  }
  // 3. spawn 兜底：以 WorkBuddy.exe + ELECTRON_RUN_AS_NODE 运行内联脚本
  try {
    const exe = findWorkBuddyExe();
    if (exe) {
      const js = "try{const ws=process._linkedBinding('electron_browser_workbuddy_storage');"
        + "const raw=JSON.parse(String(ws.loggerGet()));"
        + "if(typeof raw.atRestSecretKey==='string'&&raw.atRestSecretKey.length===44)"
        + "{process.stdout.write(raw.atRestSecretKey)}}catch(e){}";
      const out = execFileSync(exe, ['-e', js], {
        encoding: 'utf8',
        timeout: 20000,
        windowsHide: true,
        env: Object.assign({}, process.env, { ELECTRON_RUN_AS_NODE: '1' }),
      }).trim();
      if (out.length === 44) return out;
    }
  } catch { /* spawn 失败 */ }
  return null;
}

// 清除密钥缓存（客户端升级致密钥轮换、解密 authTag 校验失败时调用）
function wbClearKeyCache() {
  for (const f of ['wb_key.json', 'wb_atrest_key.json']) {
    try { fs.rmSync(path.join(__dirname, '.temp', f), { force: true }); } catch { /* 忽略 */ }
  }
}

// AES-GCM 解密信封（sym-v1 field framing）
function wbEncodeLengthPrefixed(str) {
  const b = Buffer.from(str, 'utf8');
  const len = Buffer.alloc(4);
  len.writeUInt32BE(b.length, 0);
  return Buffer.concat([len, b]);
}
function wbEncodeUint32(v) {
  const b = Buffer.alloc(4);
  b.writeUInt32BE(v, 0);
  return b;
}
function wbBuildAad(keyIdHex, suite) {
  const AAD_DOMAIN = Buffer.from('WB-AAD\0', 'ascii');
  return Buffer.concat([
    AAD_DOMAIN,
    Buffer.from([1]),
    wbEncodeLengthPrefixed('WBEV1'),
    wbEncodeLengthPrefixed('sym-v1'),
    wbEncodeUint32(suite),
    wbEncodeLengthPrefixed(keyIdHex),
    Buffer.from([2]),  // FRAMING_CODE.field
    Buffer.from([0]),  // encodeOptionalUint64(undefined) → 1B 0x00
    Buffer.from([0]),  // final undefined → 0
  ]);
}
function wbOpenEnvelope(envelopeB64, key) {
  const env = JSON.parse(Buffer.from(envelopeB64, 'base64').toString('utf8'));
  if (env.suite !== 1) throw new Error(`不支持的 suite: ${env.suite}`);
  const nonce = Buffer.from(env.nonce, 'base64');
  const authTag = Buffer.from(env.authTag, 'base64');
  const ct = Buffer.from(env.ciphertext, 'base64');
  const aad = wbBuildAad(env.keyId, env.suite);
  const d = crypto.createDecipheriv('aes-256-gcm', key, nonce, { authTagLength: 16 });
  d.setAAD(aad);
  d.setAuthTag(authTag);
  return Buffer.concat([d.update(ct), d.final()]);
}

// 主解密流程：返回 { token, uid }
function wbGetToken() {
  const exe = findWorkBuddyExe();
  if (!exe) throw new Error('未找到 WorkBuddy.exe（请确认 WorkBuddy 客户端已安装）');

  const symKeyOf = s => crypto.createHash('sha256').update(s, 'utf8').digest();
  let secret = wbGetAtRestSecretKey();
  if (!secret) throw new Error('无法获取 atRestSecretKey（WorkBuddy.exe 不存在或密钥读取失败）');

  const authFile = wbFindAuthFile();
  if (!authFile) throw new Error('未找到 WorkBuddy 登录态文件');

  let session;
  try {
    session = JSON.parse(fs.readFileSync(authFile, 'utf8'));
  } catch (e) { throw new Error(`读取登录态失败 - ${e.message}`); }

  const env = session?.auth?.accessToken;
  if (!env || typeof env.envelope !== 'string') throw new Error('登录态中无加密 accessToken');
  if (!session?.account?.uid) throw new Error('登录态中无 uid');

  // 解密（缓存密钥可能已随客户端升级轮换而失效：authTag 校验失败时
  // 清缓存并强制重新获取新密钥重试一次）
  let token;
  try {
    token = wbOpenEnvelope(env.envelope, symKeyOf(secret)).toString('utf8');
  } catch (e) {
    wbClearKeyCache();
    const fresh = wbGetAtRestSecretKey();
    if (!fresh || fresh === secret) {
      throw new Error('accessToken 解密失败（密钥与登录态不匹配，请打开 WorkBuddy 客户端重新登录）');
    }
    secret = fresh;
    token = wbOpenEnvelope(env.envelope, symKeyOf(secret)).toString('utf8');
  }

  // 缓存密钥（下次免 spawn；升级轮换时上面会自动刷新）
  try {
    const dir = path.join(__dirname, '.temp');
    fs.mkdirSync(dir, { recursive: true });
    fs.writeFileSync(path.join(dir, 'wb_key.json'), JSON.stringify({ atRestSecretKey: secret }));
  } catch { /* 缓存失败不影响主流程 */ }

  return { token, uid: session.account.uid };
}

// ============================================================
// 签到 API
// ============================================================
function wbBuildHeaders(session) {
  const h = {
    'Accept': 'application/json',
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${session.token}`,
    'X-User-Id': session.uid,
  };
  if (session.domain) h['X-Domain'] = session.domain;
  return h;
}

async function wbApiPost(url, session) {
  const res = await fetch(url, {
    method: 'POST',
    headers: wbBuildHeaders(session),
    body: '{}',
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok || (body.code !== 0 && body.code !== 200)) {
    throw new Error(`HTTP ${res.status}；code=${body.code}；msg=${body.msg || body.message || '未知'}`);
  }
  return body.data;
}

async function main() {
  const args = process.argv.slice(2);
  const statusOnly = args.includes('--status');
  const noDelay = args.includes('--no-delay');

  logSection('WorkBuddy 每日签到');

  // 1) 登录态文件
  if (!wbFindAuthFile()) {
    log('错误：未找到 WorkBuddy 登录态文件（请先安装并登录 WorkBuddy 客户端）');
    process.exitCode = 1; return;
  }

  // 2) 解密登录态
  let session;
  try {
    const t = wbGetToken();
    session = { token: t.token, uid: t.uid, domain: 'www.codebuddy.cn' };
  } catch (e) {
    log(`错误：accessToken 解密失败 - ${e.message}`);
    log('提示：请确认 WorkBuddy 客户端已安装且已登录（脚本会自动以 WorkBuddy.exe 获取密钥，无需客户端正在运行）');
    process.exitCode = 1; return;
  }

  const statusUrl = `${WB_BASE}/billing/meter/checkin-activity-status`;
  const claimUrl = `${WB_BASE}/billing/meter/daily-checkin`;

  // 3) 查状态
  let status;
  try {
    status = await wbApiPost(statusUrl, session);
  } catch (e) {
    if (/401|token|认证|auth/i.test(e.message)) {
      log('错误：登录态已过期，请打开 WorkBuddy 客户端重新登录');
    } else {
      log(`错误：状态接口调用失败 - ${e.message}`);
    }
    process.exitCode = 1; return;
  }
  log(`今日已签：${status.today_checked_in ? '是' : '否'}　连续 ${status.streak_days} 天，今日积分 ${status.today_credit}，每日可领 ${status.daily_credit}`);

  if (statusOnly) return;
  if (status.today_checked_in) { log('今日已签到，跳过'); return; }
  if (!status.active) { log('签到活动未开启'); return; }

  // 4) 随机延迟防检测
  if (!noDelay) {
    const sec = DELAY_MIN + Math.floor(Math.random() * (DELAY_MAX - DELAY_MIN + 1));
    log(`随机延迟 ${sec} 秒...`);
    await sleep(sec);
  }

  // 5) 签到 + 复查
  try {
    try {
      await wbApiPost(claimUrl, session);
    } catch (e) {
      // 云端竞态：状态查询时未签、领取时已签（如客户端 UI 先点过），code=10001 按已签处理
      if (!/10001|已签到/.test(e.message)) throw e;
      log('云端提示今日已签到（领取返回 10001），按已签处理');
    }
    const status2 = await wbApiPost(statusUrl, session).catch(() => null);
    if (status2?.today_checked_in) {
      log(`签到成功！连续 ${status2.streak_days} 天，今日积分 ${status2.today_credit}，每日可领 ${status2.daily_credit}`);
    } else {
      log('领取请求已发送，但复查显示今日仍未签到，请人工确认');
      process.exitCode = 1;
    }
  } catch (e) {
    log(`错误：签到请求异常 - ${e.message}`);
    process.exitCode = 1;
  }
}

function logSection(name) {
  console.log(`\n${'='.repeat(50)}\n[${name}]\n${'='.repeat(50)}`);
}

main().catch(e => { log(`致命错误：${e.message}`); process.exitCode = 1; });
