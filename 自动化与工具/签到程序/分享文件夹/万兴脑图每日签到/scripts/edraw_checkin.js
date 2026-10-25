// ============================================================
// 万兴脑图（MindMaster）每日签到（独立分享版，refresh_token 自续命）
// 平台：userapi.edrawsoft.cn（APP 与网页版共用后端）
//
// 接口（实测验证）：
//   POST goapi.edrawsoft.cn/api/user/ws/account/refresh/token
//        表单 refresh_token -> 换新 token(2h) + 轮换 refresh_token(30d)
//   POST userapi.edrawsoft.cn/api/user/{uid}/clockin       签到
//   GET  userapi.edrawsoft.cn/api/user/{uid}/clockin/list  本周状态
//   GET  userapi.edrawsoft.cn/api/user/{uid}/point         当前积分
//
// 凭证机制（自续命闭环）：
//   1. config/edraw_config.json 存 refresh_token（30 天有效，每次刷新轮换）
//   2. 每次运行：refresh_token 换新 token -> 立即保存轮换后的 refresh_token
//      -> 再签到。只要 30 天内运行过一次即永久续命（每天跑则无风险）
//   3. 兜底：config 缺失/失效时，从夸克浏览器 EDCurrent Cookie 现提取
//      （需用户刚在 mm.edrawsoft.cn/app 退出并重新登录过；该登录流程
//        才会把 refresh_token 写进 Cookie）
//   提取链路（兜底用）：VSS 卷影绕过独占 -> DPAPI 解主密钥 -> AES-GCM 解密
//
// 前置条件：
//   1. 首次使用：在夸克浏览器打开 https://mm.edrawsoft.cn/app
//      退出并重新登录一次（脚本兜底提取一次后自续命）
//   2. Node.js 18+（纯刷新路径）；浏览器兜底提取需 Node 22.5+
//      （node:sqlite）且需管理员权限（VSS）
//
// 用法: node edraw_checkin.js [--no-delay] [--status]
//   --no-delay  跳过随机延迟（手动测试用）
//   --status    只查询签到状态，不执行签到
// 退出码: 0=成功/已签/状态查询成功  1=失败
//
// 可选配置：上级目录 config.json，如 {"delayMinSec":30,"delayMaxSec":300}
// ============================================================
'use strict';
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { execFileSync, execSync } = require('child_process');

// ============================================================
// 公共工具
// ============================================================
function log(msg) {
  console.log(`${new Date().toLocaleString('sv-SE')} ${msg}`);
}

function logSection(name) {
  console.log(`\n${'='.repeat(50)}\n[${name}]\n${'='.repeat(50)}`);
}

function sleep(sec) {
  return new Promise(resolve => setTimeout(resolve, sec * 1000));
}

// ---------- 延迟配置（上级 config.json，缺省 30/300） ----------
const DELAY_CFG = (() => {
  try { return JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'config.json'), 'utf8')); }
  catch { return {}; }
})();
const DELAY_MIN = DELAY_CFG.delayMinSec ?? 30;
const DELAY_MAX = DELAY_CFG.delayMaxSec ?? 300;

function randomDelaySec() {
  return DELAY_MIN + Math.floor(Math.random() * (DELAY_MAX - DELAY_MIN + 1));
}

function jwtExp(jwt) {
  try {
    const p = JSON.parse(Buffer.from(jwt.split('.')[1].replace(/-/g, '+').replace(/_/g, '/'), 'base64').toString());
    return p.exp || 0;
  } catch { return 0; }
}

// ============================================================
// 配置（refresh_token 持久化）
// ============================================================
const CFG_PATH = path.join(__dirname, '..', 'config', 'edraw_config.json');

function loadConfig() {
  try { return JSON.parse(fs.readFileSync(CFG_PATH, 'utf8')); } catch { return null; }
}

function saveConfig(obj) {
  fs.mkdirSync(path.dirname(CFG_PATH), { recursive: true });
  fs.writeFileSync(CFG_PATH, JSON.stringify(obj, null, 2), 'utf8');
}

// ============================================================
// 浏览器凭证提取（兜底路径：VSS + DPAPI + AES-GCM）
// ============================================================
const BROWSER_UD = path.join(process.env.LOCALAPPDATA || '', 'Quark', 'User Data');
const COOKIE_NAME = 'EDCurrent';
const COOKIE_DOMAIN = 'mm.edrawsoft.cn';

function dpapiUnprotect(buf) {
  const payload = Buffer.from(buf).toString('base64');
  const ps = [
    'Add-Type -AssemblyName System.Security;',
    `$src=[Convert]::FromBase64String('${payload}');`,
    "$k=[Security.Cryptography.ProtectedData]::Unprotect($src,$null,'CurrentUser');",
    '[Convert]::ToBase64String($k)'
  ].join('');
  const out = execFileSync('powershell.exe',
    ['-NoProfile', '-NonInteractive', '-Command', ps],
    { encoding: 'utf8' }).trim();
  return Buffer.from(out, 'base64');
}

function vssCopyCookies(workDir) {
  const src = path.join(BROWSER_UD, 'Default', 'Network', 'Cookies');
  const dstFile = path.join(workDir, 'Cookies');
  const vol = src.slice(0, 2);
  execSync(`vssadmin create shadow /for=${vol}`, { stdio: 'pipe' });
  const list = execSync('vssadmin list shadows', { encoding: 'utf8' });
  const matches = [...list.matchAll(/Shadow Copy Volume: (\\\\\?\\GLOBALROOT\\Device\\HarddiskVolumeShadowCopy\d+)/g)];
  if (!matches.length) throw new Error('未找到刚创建的卷影');
  const shadow = matches[matches.length - 1][1];
  const link = path.join(workDir, 'vss_link');
  try { fs.rmSync(link, { recursive: true }); } catch { /* 忽略 */ }
  execSync(`cmd.exe /c mklink /d "${link}" "${shadow}\\"`, { stdio: 'pipe' });
  const rel = src.slice(2);
  fs.copyFileSync(path.join(link, rel), dstFile);
  for (const ext of ['-wal', '-shm']) {
    try { fs.copyFileSync(path.join(link, rel + ext), dstFile + ext); } catch { /* 可缺省 */ }
  }
  try { execSync(`vssadmin delete shadows /for=${vol} /oldest /quiet`, { stdio: 'pipe' }); } catch { /* 清理失败无碍 */ }
  return dstFile;
}

// 从浏览器 EDCurrent 提取 { userId, refreshToken }（兜底，需用户刚登录过）
function extractFromBrowser() {
  const { DatabaseSync } = require('node:sqlite');
  const workDir = path.join(process.env.TEMP, 'edraw_cookie');
  fs.mkdirSync(workDir, { recursive: true });
  const cookiesDb = vssCopyCookies(workDir);
  const localState = JSON.parse(fs.readFileSync(path.join(BROWSER_UD, 'Local State'), 'utf8'));
  const encKeyB64 = localState?.os_crypt?.encrypted_key;
  if (!encKeyB64) throw new Error('Local State 无 os_crypt.encrypted_key');
  const blob = Buffer.from(encKeyB64, 'base64');
  if (blob.slice(0, 5).toString('ascii') !== 'DPAPI') throw new Error('encrypted_key 前缀非 DPAPI');
  const masterKey = dpapiUnprotect(blob.slice(5));

  const db = new DatabaseSync(cookiesDb, { readOnly: true });
  const row = db.prepare('SELECT host_key, encrypted_value FROM cookies WHERE name=? AND host_key LIKE ?').get(COOKIE_NAME, `%${COOKIE_DOMAIN}%`);
  db.close();
  if (!row) throw new Error(`浏览器中未找到 ${COOKIE_DOMAIN} 的 ${COOKIE_NAME}`);

  const b = Buffer.from(row.encrypted_value);
  if (b.slice(0, 3).toString() !== 'v10') throw new Error('EDCurrent 密文前缀非 v10');
  const d = crypto.createDecipheriv('aes-256-gcm', masterKey, b.slice(3, 15));
  d.setAuthTag(b.slice(-16));
  let dec = Buffer.concat([d.update(b.slice(15, -16)), d.final()]);
  const sha = crypto.createHash('sha256').update(row.host_key).digest();
  if (dec.length > 32 && dec.slice(0, 32).equals(sha)) dec = dec.slice(32);

  const ed = JSON.parse(decodeURIComponent(dec.toString('utf8')));
  if (!ed.user_id || !ed.refresh_token) {
    throw new Error('EDCurrent 缺 user_id/refresh_token 字段——请在夸克浏览器退出并重新登录 https://mm.edrawsoft.cn/app（应用内登录流程才会写入 refresh_token）');
  }
  return { userId: String(ed.user_id), refreshToken: ed.refresh_token };
}

// ============================================================
// API 封装
// ============================================================
const API = 'https://userapi.edrawsoft.cn';
const GO_API = 'https://goapi.edrawsoft.cn';
const UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Quark/4.5.5.275 Chrome/112.0.0.0 Safari/537.36';

// 用 refresh_token 换新 token + 轮换 refresh_token
async function refreshTokens(refreshToken) {
  const res = await fetch(`${GO_API}/api/user/ws/account/refresh/token`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded', 'User-Agent': UA },
    body: 'refresh_token=' + encodeURIComponent(refreshToken),
  });
  let json;
  try { json = await res.json(); } catch { throw new Error(`刷新接口 HTTP ${res.status} 响应非 JSON`); }
  if (res.status !== 200 || json?.status !== 'success' || !json?.data?.token) {
    throw new Error(`刷新失败: HTTP ${res.status} ${json?.msg || JSON.stringify(json).slice(0, 120)}`);
  }
  return { token: json.data.token, refreshToken: json.data.refresh_token };
}

async function apiRequest(token, method, apiPath) {
  const res = await fetch(`${API}${apiPath}?lang=cn`, {
    method,
    headers: {
      'Authorization': `Bearer ${token}`,
      'User-Agent': UA,
      'Accept': 'application/json, text/plain, */*',
      'Accept-Language': 'zh-CN',
      'Origin': 'https://mm.edrawsoft.cn',
      'Referer': 'https://mm.edrawsoft.cn/',
      ...(method === 'POST' ? { 'Content-Type': 'application/json' } : {}),
    },
    body: method === 'POST' ? '{}' : undefined,
  });
  let json;
  try { json = await res.json(); } catch { throw new Error(`HTTP ${res.status} 响应非 JSON`); }
  return { status: res.status, json };
}

async function edrawStatus(token, userId) {
  const list = await apiRequest(token, 'GET', `/api/user/${userId}/clockin/list`);
  const point = await apiRequest(token, 'GET', `/api/user/${userId}/point`);
  if (list.status !== 200 || list.json?.status !== 'success') {
    return { ok: false, err: `clockin/list 异常: HTTP ${list.status} ${JSON.stringify(list.json).slice(0, 120)}` };
  }
  const week = Array.isArray(list.json?.data) ? list.json.data : [];
  return {
    ok: true,
    week,
    signedToday: week.length > 0 ? week[week.length - 1] === 1 : false,
    point: point.json?.data?.point ?? '?',
  };
}

async function edrawSign(token, userId) {
  const { status, json } = await apiRequest(token, 'POST', `/api/user/${userId}/clockin`);
  if (status !== 200) return { ok: false, err: `HTTP ${status}` };
  const data = json?.data || {};
  if (json?.status === 'success' && data.signed === true) {
    return { ok: true, already: false, ai: data.total_ai ?? 0, score: data.total_score ?? 0 };
  }
  if (json?.msg === 'already check in') {
    return { ok: true, already: true, msg: data.success_message || '今日已签到' };
  }
  return { ok: false, err: `异常响应: ${JSON.stringify(json).slice(0, 150)}` };
}

// ============================================================
// 主流程
// ============================================================
async function main() {
  const args = process.argv.slice(2);
  const statusOnly = args.includes('--status');
  const noDelay = args.includes('--no-delay');

  logSection('万兴脑图 MindMaster');

  // 1) 取 refresh_token：config 优先，浏览器兜底
  let userId = null;
  let refreshToken = null;
  const cfg = loadConfig();
  const now = Math.floor(Date.now() / 1000);
  if (cfg?.refresh_token && jwtExp(cfg.refresh_token) > now) {
    userId = cfg.user_id;
    refreshToken = cfg.refresh_token;
    log(`使用 config 中的 refresh_token（剩余 ${Math.round((jwtExp(refreshToken) - now) / 8640) / 10} 天）`);
  } else {
    if (cfg?.refresh_token) log('config 中的 refresh_token 已过期，转浏览器提取');
    try {
      ({ userId, refreshToken } = extractFromBrowser());
      log(`浏览器凭证提取成功：user_id=${userId}`);
    } catch (e) {
      log(`错误：凭证获取失败 - ${e.message}`);
      log('处理：在夸克浏览器打开 https://mm.edrawsoft.cn/app 退出并重新登录后重试（兜底提取需管理员权限运行）');
      process.exitCode = 1;
      return;
    }
  }

  // 2) 刷新：换新 token + 轮换 refresh_token（先保存再签到，防凭证丢失）
  let token;
  try {
    const r = await refreshTokens(refreshToken);
    token = r.token;
    saveConfig({ user_id: userId, refresh_token: r.refreshToken, saved_at: new Date().toISOString() });
    log(`token 刷新成功（新 token 2h 有效，refresh_token 已轮换保存）`);
  } catch (e) {
    log(`错误：token 刷新失败 - ${e.message}`);
    // config 的 refresh_token 可能已失效，清除避免下次再用
    if (cfg?.refresh_token === refreshToken) {
      try { fs.unlinkSync(CFG_PATH); log('已清除失效的 config 文件'); } catch { /* 忽略 */ }
    }
    process.exitCode = 1;
    return;
  }

  // 3) 查状态
  let st;
  try {
    st = await edrawStatus(token, userId);
  } catch (e) {
    log(`错误：状态查询失败 - ${e.message}`);
    process.exitCode = 1;
    return;
  }
  if (!st.ok) {
    log(`错误：${st.err}`);
    process.exitCode = 1;
    return;
  }
  log(`本周签到：${st.week.map(x => x ? '[√]' : '[×]').join('')}　当前积分：${st.point}`);

  if (statusOnly) {
    log(`今日状态：${st.signedToday ? '已签到' : '未签到'}（只读模式，未执行签到）`);
    return;
  }

  // 4) 签到
  if (st.signedToday) {
    log('今日已签到，跳过');
    return;
  }
  if (!noDelay) {
    const sec = randomDelaySec();
    log(`随机延时 ${sec} 秒防检测...`);
    await sleep(sec);
  }
  try {
    const r = await edrawSign(token, userId);
    if (!r.ok) {
      log(`错误：签到失败 - ${r.err}`);
      process.exitCode = 1;
      return;
    }
    if (r.already) {
      log(`今日已签到（${r.msg}）`);
    } else {
      log(`签到成功！AI点数 +${r.ai}，积分 +${r.score}`);
    }
    const st2 = await edrawStatus(token, userId);
    if (st2.ok) log(`复查：本周 ${st2.week.map(x => x ? '[√]' : '[×]').join('')}　积分：${st2.point}`);
  } catch (e) {
    log(`错误：签到请求异常 - ${e.message}`);
    process.exitCode = 1;
  }
}

main().catch(e => { log(`致命错误：${e.message}`); process.exitCode = 1; });
