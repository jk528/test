// ============================================================
// 统一积分签到脚本（API 直连版，无需客户端窗口）
// 单文件自包含：合并原分散文件（以下原文件已可删除）
//   - common.js             公共工具（日志/随机延时/注册表探测/版本探测/DPAPI/AES-GCM）
//   - workbuddy_get_token.js  WorkBuddy accessToken 解密（已内联为 wbGetToken）
//   - codearts_checkin.js     CodeArts Agent 签到
//   - qoder_checkin.js        Qoder 签到
//   - officeace_checkin.js    果办 OfficeAce 签到
// 共 9 个签到平台，分两组调度（2026-10-25 重构，详见「主流程」注释）：
//   ai 组（凌晨 00:05）：Trae / TeleAgent / WorkBuddy / CodeArts / OfficeAce / 库库AI
//   daily 组（白天 10:35）：Qoder（每日 10:00 才重置）/ 百度网盘 / 天翼云盘
// （2026-10-16：TraeWork 与 TraeCN 客户端已合并为同一客户端/同一账号，两入口合并为单平台 Trae，
//  数据目录保留新旧名候选：Trae CN 新名优先，TRAE SOLO CN 旧名兑底）
// 各平台独立执行，互不阻塞，单平台失败不影响其他平台
// 每个平台签到前随机等待 30~300 秒，打乱固定时间模式（--no-delay 可跳过全部延时）
// 用法: node checkin_all.js [--group=ai|daily] [--no-delay]
// 退出码: 0=全部成功/已签  1=至少一个失败
// ============================================================
'use strict';
const fs = require('fs');
const os = require('os');
const path = require('path');
const crypto = require('crypto');
const https = require('https');
const { execFileSync, execSync, spawnSync } = require('child_process');

// ============================================================
// 公共工具（内联自 common.js，供全文件共享）
//   日志、随机延时、注册表安装目录探测、应用版本探测、
//   DPAPI 解密、AES-256-GCM("v10" 信封) 解密与加密
// ============================================================

// ---- 日志：统一 ISO 风格时间戳，便于排序与解析 ----
function log(msg) {
  console.log(`${new Date().toLocaleString('sv-SE')} ${msg}`);
}

function logSection(name) {
  console.log(`\n${'='.repeat(50)}\n[${name}]\n${'='.repeat(50)}`);
}

// ---- 随机延时（防脚本检测）：每个平台签到前等待 30~300 秒 ----
function sleep(sec) {
  return new Promise(resolve => setTimeout(resolve, sec * 1000));
}

function randomDelaySec() {
  return 30 + Math.floor(Math.random() * 271);
}

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

// ---- 版本探测：从候选 package.json 读取 version，全部失败则返回 fallback ----
function detectAppVersion(candidates, fallback = '') {
  for (const p of candidates) {
    try {
      if (p && fs.existsSync(p)) {
        const v = JSON.parse(fs.readFileSync(p, 'utf8')).version;
        if (v) return v;
      }
    } catch { /* 忽略单个候选读取失败 */ }
  }
  return fallback;
}

// ---- DPAPI(CurrentUser) 解密；入参为去掉前缀后的密文，返回明文 Buffer ----
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

// ---- Chromium 系客户端 AES 主密钥：Local State -> os_crypt.encrypted_key -> DPAPI ----
// TeleAgent / Qoder / CodeArts 客户端均采用此机制，共用一个实现
function readChromiumMasterKey(dataDir) {
  const localState = JSON.parse(fs.readFileSync(path.join(dataDir, 'Local State'), 'utf8'));
  const encKeyB64 = localState?.os_crypt?.encrypted_key;
  if (!encKeyB64) throw new Error('Local State 中未找到 os_crypt.encrypted_key');
  const blob = Buffer.from(encKeyB64, 'base64');
  if (blob.slice(0, 5).toString('ascii') !== 'DPAPI') throw new Error('encrypted_key 前缀非 DPAPI');
  return dpapiUnprotect(blob.slice(5));
}

// ---- 应用版本探测：注册表 InstallLocation + 候选路径 ----
function detectVersionFromInstall(regKeyword, extraCandidates, fallback = '') {
  const candidates = [];
  const installDir = regQueryInstallLocation(regKeyword);
  if (installDir) candidates.push(path.join(installDir, 'resources', 'app', 'package.json'));
  candidates.push(...extraCandidates);
  return detectAppVersion(candidates, fallback);
}

// ---- AES-256-GCM "v10" 信封（3B 前缀 + 12B nonce + 密文 + 16B tag）----
function aesGcmDecryptV10(buf, key) {
  const b = Buffer.from(buf);
  const prefix = b.slice(0, 3).toString('ascii');
  if (prefix !== 'v10') throw new Error(`未知密文前缀: ${prefix}`);
  const nonce = b.slice(3, 15);
  const tag = b.slice(b.length - 16);
  const ct = b.slice(15, b.length - 16);
  const d = crypto.createDecipheriv('aes-256-gcm', key, nonce);
  d.setAuthTag(tag);
  return Buffer.concat([d.update(ct), d.final()]);
}

function aesGcmEncryptV10(plain, key) {
  const nonce = crypto.randomBytes(12);
  const c = crypto.createCipheriv('aes-256-gcm', key, nonce);
  const ct = Buffer.concat([c.update(Buffer.from(plain, 'utf8')), c.final()]);
  return Buffer.concat([Buffer.from('v10', 'ascii'), nonce, ct, c.getAuthTag()]);
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

// ============================================================
// 公共路径自动探测工具（消除硬编码，避免客户端更名/迁移时失效）
// ============================================================

/**
 * 自动探测 Trae 数据目录（%APPDATA%\xxx）。
 * 按 preferred 候选名顺序遍历，返回第一个含 storage.json 的目录。
 * 默认候选：Trae CN（新名）、TRAE SOLO CN（旧名）
 */
function findTraeAppDataRoot(preferred = ['Trae CN', 'TRAE SOLO CN']) {
  const appData = process.env.APPDATA;
  if (!appData) return null;
  for (const name of preferred) {
    const root = path.join(appData, name);
    const storage = path.join(root, 'User', 'globalStorage', 'storage.json');
    if (fs.existsSync(storage)) return root;
  }
  return null;
}

/**
 * 自动探测 Trae 客户端版本号（用于 x-app-version 请求头）。
 * 优先级：注册表 InstallLocation -> 常见安装路径候选。
 */
function findTraeAppVersion() {
  const localAppData = process.env.LOCALAPPDATA || '';
  return detectVersionFromInstall('Trae', [
    path.join(localAppData, 'Programs', 'Trae CN', 'resources', 'app', 'package.json'),
    path.join(localAppData, 'Programs', 'TRAE SOLO CN', 'resources', 'app', 'package.json'),
    path.join('B:\\Trae CN', 'resources', 'app', 'package.json'),
    path.join('B:\\trae work\\TRAE SOLO CN', 'resources', 'app', 'package.json'),
  ]);
}

// ---- AES-128-CBC + SHA-512 解密常量（Trae 平台，原 TraeWork/TraeCN 共用）----
const HP = 16, q8_AES128 = 16, WP = HP, rh = 64, Rv = 32, VP = 64, Em = 6;
const ure = Uint8Array.from([82,9,106,213,48,54,165,56,191,64,163,158,129,243,215,251,124,227,57,130,155,47,255,135,52,142,67,68,196,222,233,203,84,123,148,50,166,194,35,61,238,76,149,11,66,250,195,78,8,46,161,102,40,217,36,178,118,91,162,73,109,139,209,37]);
const dre = Uint8Array.from([31,221,168,51,136,7,199,49,177,18,16,89,39,128,236,95,96,81,127,169,25,181,74,13,45,229,122,159,147,201,156,239,160,224,59,77,174,42,245,176,200,235,187,60,131,83,153,97,23,43,4,126,186,119,214,38,225,105,20,99,85,33,12,125]);

async function sha512(data) {
  const h = await crypto.subtle.digest('SHA-512', data);
  return new Uint8Array(h);
}

async function decryptTrae(b64) {
  const t = new Uint8Array(Buffer.from(b64, 'base64'));
  const key = t.slice(Em, Em + Rv);
  const sha = await sha512(key);
  const xor = new Uint8Array(VP);
  for (let i = 0; i < VP; i++) xor[i] = ure[i] ^ dre[i];
  const comb = new Uint8Array(rh + VP);
  comb.set(sha, 0); comb.set(xor, rh);
  const hash = await sha512(comb);
  const aesKey = hash.slice(0, q8_AES128);
  const iv = hash.slice(q8_AES128, q8_AES128 + WP);
  const ct = t.slice(Rv + Em);
  const ck = await crypto.subtle.importKey('raw', aesKey, { name: 'AES-CBC' }, false, ['decrypt']);
  const dec = new Uint8Array(await crypto.subtle.decrypt({ name: 'AES-CBC', iv }, ck, ct));
  return new TextDecoder().decode(dec.slice(rh));
}

// ============================================================
// 1. Trae 签到（原 TraeWork / TraeCN 两客户端已合并为同一账号，2026-10-16 起单入口）
// ============================================================
async function checkinTrae(platformName, dirCandidates) {
  logSection(platformName);
  // 自动探测数据目录（候选按优先级排列）
  const root = findTraeAppDataRoot(dirCandidates);
  if (!root) { log(`错误：未检测到 ${platformName} 数据目录（请确认已安装并登录 ${dirCandidates.join(' / ')}）`); return false; }
  log(`检测到数据目录：${root}`);
  const storagePath = path.join(root, 'User', 'globalStorage', 'storage.json');

  let auth;
  try {
    const storage = JSON.parse(fs.readFileSync(storagePath, 'utf8'));
    const enc = storage['iCubeAuthInfo://icube.cloudide'];
    if (!enc) { log('错误：未找到登录态数据'); return false; }
    auth = JSON.parse(await decryptTrae(enc));
    if (!auth.token) { log('错误：登录态中没有 token'); return false; }
  } catch (e) {
    log(`错误：登录态读取失败 - ${e.message}`); return false;
  }

  let deviceId = '';
  try {
    const envPath = path.join(root, 'ModularData', 'ckg_server', 'local_env.json');
    deviceId = String(JSON.parse(fs.readFileSync(envPath, 'utf8')).device_id || '');
  } catch {}

  const appVersion = findTraeAppVersion();

  const headers = { 'Authorization': `Cloud-IDE-JWT ${auth.token}`, 'Content-Type': 'application/json' };
  if (auth.userRegion?.region) headers['X-User-Region'] = auth.userRegion.region;
  if (deviceId) {
    headers['x-device-id'] = deviceId;
    headers['x-device-type'] = 'Windows';
    headers['x-os-version'] = os.release();
    if (appVersion) headers['x-app-version'] = appVersion;
  } else {
    log('警告：未找到设备 ID，签到可能被拒绝');
  }

  const body = JSON.stringify({ req_source: 2 });
  const BASE = 'https://api.trae.cn/trae/api/v2/ug/checkin_credits';
  const statusUrl = `${BASE}/status`;
  const claimUrl = `${BASE}/claim`;

  try {
    const statusRes = await fetch(statusUrl, { method: 'POST', headers, body });
    const status = await statusRes.json();
    // extra_credits 为可选的额外奖励字段，仅在存在时附加到日志
    const extraNote = status.extra_credits ? `（含额外 ${status.extra_credits}）` : '';
    if (status.checked_in) {
      log(`今日已签到。积分：${status.credits}${extraNote}`);
      return true;
    }
    if (!status.enable) { log('签到功能未启用'); return true; }
    const claimRes = await fetch(claimUrl, { method: 'POST', headers, body });
    const claim = await claimRes.json();
    if (claim.code === 0) {
      let credits = status.credits || 200;
      try {
        const refreshRes = await fetch(statusUrl, { method: 'POST', headers, body });
        const refresh = await refreshRes.json();
        if (typeof refresh.credits === 'number') credits = refresh.credits;
      } catch {}
      log(`签到成功！积分：${credits}${extraNote}`);
      return true;
    } else {
      log(`签到失败：${claim.message || JSON.stringify(claim)}`);
      return false;
    }
  } catch (e) {
    log(`错误：${e.message}`); return false;
  }
}

// 单平台入口：新目录名优先，旧目录名兑底（客户端合并后同一账号只需签一次；
// 若未来产品再拆分为双客户端双账号，恢复为两个入口并互换候选顺序即可）
const checkinTraeUnified = () => checkinTrae('Trae', ['Trae CN', 'TRAE SOLO CN']);

// ============================================================
// 3. TeleAgent 签到
// ============================================================
const TA_DATA_ROOT = path.join(os.homedir(), '.local', 'share', 'TeleAgent');
const TA_BASE = 'https://agent.teleai.com.cn/superCowork/sapi';
// 自动探测 TeleAgent 客户端版本号，失败时回退到已知版本
const TA_APP_VERSION_FALLBACK = '2.5.2';
let _taAppVersion = '';
function findTeleAgentAppVersion() {
  if (_taAppVersion) return _taAppVersion;
  const localAppData = process.env.LOCALAPPDATA || '';
  _taAppVersion = detectVersionFromInstall('TeleAgent',
    [path.join(localAppData, 'Programs', 'TeleAgent', 'resources', 'app', 'package.json')],
    TA_APP_VERSION_FALLBACK);
  return _taAppVersion;
}

function taFindTokenJson() {
  try {
    const owner = JSON.parse(fs.readFileSync(path.join(TA_DATA_ROOT, 'current-owner.json'), 'utf8'));
    const p = path.join(TA_DATA_ROOT, 'users', owner.ownerDir, 'app-auth', 'token.json');
    if (fs.existsSync(p)) return p;
  } catch {}
  const usersDir = path.join(TA_DATA_ROOT, 'users');
  try {
    for (const d of fs.readdirSync(usersDir)) {
      const p = path.join(usersDir, d, 'app-auth', 'token.json');
      if (fs.existsSync(p)) return p;
    }
  } catch {}
  return null;
}


function taDecryptToken(tokenJsonPath, masterKey) {
  const tj = JSON.parse(fs.readFileSync(tokenJsonPath, 'utf8'));
  const raw = tj.encryptedToken;
  if (!raw) throw new Error('token.json 中无 encryptedToken');
  if (tj.encrypted === false) return raw;
  return aesGcmDecryptV10(Buffer.from(raw, 'base64'), masterKey).toString('utf8');
}

function taReadDeviceId() {
  try {
    return String(JSON.parse(fs.readFileSync(
      path.join(TA_DATA_ROOT, 'app-auth', 'device-meta.json'), 'utf8')).deviceId || '');
  } catch { return ''; }
}

function taBuildHeaders(token) {
  return {
    'Content-Type': 'application/json',
    'X-Timestamp': String(Math.floor(Date.now() / 1000)),
    'X-Nonce': crypto.randomUUID(),
    'X-App-Version': findTeleAgentAppVersion(),
    'X-OS-Type': 'Windows',
    'X-SuperAgent-Device-Id': taReadDeviceId(),
    'X-Token': token,
    'X-Channel-Id': '',
    'X-Runtime-Env': ''
  };
}

async function taApiGet(url, token) {
  const res = await fetch(url, { method: 'GET', headers: taBuildHeaders(token) });
  const body = await res.json().catch(() => ({}));
  if (!res.ok || (body.code !== 200 && body.code !== 0)) {
    throw new Error(`HTTP ${res.status} code=${body.code} msg=${body.msg || body.message || '未知错误'}`);
  }
  return body.data;
}

async function checkinTeleAgent() {
  logSection('TeleAgent');
  const tokenPath = taFindTokenJson();
  if (!tokenPath) { log('错误：未找到 TeleAgent 登录态文件'); return false; }

  let token;
  try {
    const masterKey = readChromiumMasterKey(TA_DATA_ROOT);
    if (masterKey.length !== 32) throw new Error('主密钥解密结果异常');
    token = taDecryptToken(tokenPath, masterKey);
  } catch (e) {
    log(`错误：登录态解密失败 - ${e.message}`);
    return false;
  }

  const statusUrl = `${TA_BASE}/user/portal/companyStore/v2/checkDayTask`;
  const claimUrl = `${TA_BASE}/user/portal/companyStore/checkTask?type=daily_login`;
  const userUrl = `${TA_BASE}/user/portal/companyStore/userCenter`;

  try {
    let status;
    try {
      status = await taApiGet(statusUrl, token);
    } catch (e) {
      if (/401|token|登录/i.test(e.message)) {
        log('错误：登录态已过期，请打开 TeleAgent 客户端重新登录');
      } else {
        log(`错误：状态接口调用失败 - ${e.message}`);
      }
      return false;
    }
    const daily = status?.daily_task;

    if (daily?.claimed_today) {
      const uc = await taApiGet(userUrl, token).catch(() => null);
      log(`今日已签到（按钮状态「${daily.button_text ?? '今日已领'}」）。每日可领 ${daily.daily_claimable_points ?? 100} 分，本期已领 ${daily.total_claim_days} 天，累计 ${daily.total_claimed_points} 分，当前余额 ${uc?.current_points_balance ?? '未知'}`);
      return true;
    }

    await taApiGet(claimUrl, token);

    const [status2, uc2] = await Promise.all([
      taApiGet(statusUrl, token).catch(() => null),
      taApiGet(userUrl, token).catch(() => null)
    ]);
    const d2 = status2?.daily_task;
    if (d2?.claimed_today) {
      log(`签到成功！今日 +${d2.daily_claimable_points ?? 100} 分（按钮状态「${d2.button_text ?? '今日已领'}」）。本期已领 ${d2.total_claim_days} 天，累计 ${d2.total_claimed_points} 分，当前余额 ${uc2?.current_points_balance ?? '未知'}`);
      return true;
    } else {
      log(`领取请求已发送，但复查显示今日仍未领取，请人工确认`);
      return false;
    }
  } catch (e) {
    log(`错误：${e.message}`); return false;
  }
}

// ============================================================
// 4. WorkBuddy 签到
// 2026-10-04 客户端升级后 accessToken 改为 $wbEncrypted 加密信封
// （AES-256-GCM，密钥来自 native 绑定 workbuddyStorage.loggerGet），
// 原由 workbuddy_get_token.js 以 WorkBuddy.exe 的 ELECTRON_RUN_AS_NODE
// 模式运行解密，现内联为进程内函数 wbGetToken()。
// ============================================================
const WB_BASE = 'https://copilot.tencent.com';
// 认证数据目录：优先 LOCALAPPDATA，兜底 os.homedir()\AppData\Local
const WB_AUTH_DIR = path.join(
  process.env.LOCALAPPDATA || path.join(os.homedir(), 'AppData', 'Local'),
  'CodeBuddyExtension', 'Data', 'Public', 'auth'
);

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

function wbFindAuthFile() {
  const preferred = path.join(WB_AUTH_DIR, 'workbuddy-desktop.info');
  if (fs.existsSync(preferred)) return preferred;
  // 兜底：取目录内最新的非时间戳命名 .info 文件
  return pickNewestFile(WB_AUTH_DIR,
    f => f.endsWith('.info') && f !== 'workbuddy-desktop.info' && !/^\d{4}-\d{2}-\d{2}T/.test(f));
}

// ---- WorkBuddy accessToken 解密（内联自 workbuddy_get_token.js）----
// 密钥获取三层：①native binding（本进程即 Electron 时）②本地缓存 ③spawn WorkBuddy.exe
// （ELECTRON_RUN_AS_NODE 模式跑内联脚本，只需 exe 存在，无需客户端正在运行，
//  也不触发单实例锁；实测 1 秒内返回，2026-10-16 修复当日签到失败）
function wbGetAtRestSecretKey() {
  // 1. native binding（进程自身为 WorkBuddy.exe/Electron 时）
  try {
    const ws = process._linkedBinding('electron_browser_workbuddy_storage');
    const raw = JSON.parse(String(ws.loggerGet()));
    if (typeof raw.atRestSecretKey === 'string' && raw.atRestSecretKey.length === 44) {
      return raw.atRestSecretKey;
    }
  } catch {}
  // 2. 上次缓存（客户端升级前的兑底；两代文件名均尝试）
  for (const f of ['wb_key.json', 'wb_atrest_key.json']) {
    try {
      const cached = JSON.parse(fs.readFileSync(path.join(__dirname, '.temp', f), 'utf8'));
      if (typeof cached.atRestSecretKey === 'string' && cached.atRestSecretKey.length === 44) {
        return cached.atRestSecretKey;
      }
    } catch {}
  }
  // 3. spawn 兑底：以 WorkBuddy.exe + ELECTRON_RUN_AS_NODE 运行内联脚本
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
  } catch {}
  return null;
}

// 清除密钥缓存（客户端升级致密钥轮换、解密 authTag 校验失败时调用）
function wbClearKeyCache() {
  for (const f of ['wb_key.json', 'wb_atrest_key.json']) {
    try { fs.rmSync(path.join(__dirname, '.temp', f), { force: true }); } catch {}
  }
}

// 2. AES-GCM 解密信封（sym-v1 field framing）
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

// 3. 主流程（原为子进程读 stdout，现为进程内函数，返回 { token, uid }）
function wbGetToken() {
  const exe = findWorkBuddyExe();
  if (!exe) throw new Error('未找到 WorkBuddy.exe（请确认 WorkBuddy 客户端已安装）');

  const symKeyOf = s => crypto.createHash('sha256').update(s, 'utf8').digest();
  let secret = wbGetAtRestSecretKey();
  if (!secret) throw new Error('错误：无法获取 atRestSecretKey（WorkBuddy.exe 不存在或密钥读取失败）');

  const authFile = path.join(WB_AUTH_DIR, 'workbuddy-desktop.info');
  if (!fs.existsSync(authFile)) throw new Error('错误：未找到 WorkBuddy 登录态文件');

  let session;
  try {
    session = JSON.parse(fs.readFileSync(authFile, 'utf8'));
  } catch (e) { throw new Error(`错误：读取登录态失败 - ${e.message}`); }

  const env = session?.auth?.accessToken;
  if (!env || typeof env.envelope !== 'string') throw new Error('错误：登录态中无加密 accessToken');
  if (!session?.account?.uid) throw new Error('错误：登录态中无 uid');

  // 解密（缓存密钥可能已随客户端升级轮换而失效：authTag 校验失败时
  // 清缓存并强制重新获取新密钥重试一次）
  let token;
  try {
    token = wbOpenEnvelope(env.envelope, symKeyOf(secret)).toString('utf8');
  } catch (e) {
    wbClearKeyCache();
    const fresh = wbGetAtRestSecretKey();
    if (!fresh || fresh === secret) {
      throw new Error('错误：accessToken 解密失败（密钥与登录态不匹配，请打开 WorkBuddy 客户端重新登录）');
    }
    secret = fresh;
    token = wbOpenEnvelope(env.envelope, symKeyOf(secret)).toString('utf8');
  }

  // 缓存密钥（下次免 spawn；升级轮换时上面会自动刷新）
  try {
    const dir = path.join(__dirname, '.temp');
    fs.mkdirSync(dir, { recursive: true });
    fs.writeFileSync(path.join(dir, 'wb_key.json'), JSON.stringify({ atRestSecretKey: secret }));
  } catch {}

  return { token, uid: session.account.uid };
}

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

async function checkinWorkBuddy() {
  logSection('WorkBuddy');
  if (!wbFindAuthFile()) { log('错误：未找到 WorkBuddy 登录态文件'); return false; }

  let session;
  try {
    const t = wbGetToken();
    session = { token: t.token, uid: t.uid, domain: 'www.codebuddy.cn' };
    } catch (e) {
      log(`错误：accessToken 解密失败 - ${e.message}`);
      log('提示：请确认 WorkBuddy 客户端已安装且已登录（脚本会自动以 WorkBuddy.exe 获取密钥，无需客户端正在运行）');
      return false;
    }

  const statusUrl = `${WB_BASE}/billing/meter/checkin-activity-status`;
  const claimUrl = `${WB_BASE}/billing/meter/daily-checkin`;

  try {
    let status;
    try {
      status = await wbApiPost(statusUrl, session);
    } catch (e) {
      if (/401|token|认证|auth/i.test(e.message)) {
        log('错误：登录态已过期，请打开 WorkBuddy 客户端重新登录');
      } else {
        log(`错误：状态接口调用失败 - ${e.message}`);
      }
      return false;
    }

    if (status.today_checked_in) {
      log(`今日已签到。连续 ${status.streak_days} 天，今日积分 ${status.today_credit}，每日可领 ${status.daily_credit}`);
      return true;
    }
    if (!status.active) { log('签到活动未开启'); return true; }

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
      return true;
    } else {
      log(`领取请求已发送，但复查显示今日仍未签到，请人工确认`);
      return false;
    }
  } catch (e) {
    log(`错误：${e.message}`); return false;
  }
}

// ============================================================
// 5. CodeArts Agent 每日签到（积分福利）—— API 直连
//
// 流程：解密本地凭证(HuaweiCloudSession) -> 签名(AWS v4 风格 SDK-HMAC-SHA256)
//       -> GET /v1/ops/delivery?channel=IDE 拉活动
//       -> 每日签到(campaignId=1, USER_LOGIN) claimable 时 POST /v1/ops/claim
//       -> POST /v1/ops/confirm 确认到账
//
// 凭证依赖：CodeArts Agent 客户端已登录（其认证扩展负责每小时续期并写回本地存储）
// 签名形态：X-Sdk-Content-Sha256: UNSIGNED-PAYLOAD（与客户端 kernel 完全一致）
// 零安装：Node 借用 TeleAgent 自带 runtime
// ============================================================

// ---------- 配置 ----------
const CODEARTS_HOST = 'snap-access.cn-north-4.myhuaweicloud.com';
const CODEARTS_CHANNEL = 'IDE';
const CODEARTS_DAILY_CAMPAIGN_ID = 1; // 每日签到领1000积分（type=USER_LOGIN）


// ---------- 华为云 SDK-HMAC-SHA256 签名（复刻客户端 kernel 实现） ----------
// noEscape 表：与客户端 kernel signer 逐位一致（实测验证通过）
const codeartsNoEscape = [
  0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
  0,1,0,0,0,0,0,1,1,1,1,0,0,1,1,0,1,1,1,1,1,1,1,1,1,1,0,0,0,0,0,0,
  0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,0,0,0,1,
  0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,0,0,1,0,
  0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
  0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
  0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
  0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
];
const codeartsHex = [];
function codeartsHexTable() {
  if (!codeartsHex.length) for (let x = 0; x < 256; ++x) codeartsHex[x] = '%' + ((x < 16 ? '0' : '') + x.toString(16)).toUpperCase();
  return codeartsHex;
}
function codeartsUrlEncode(x) {
  if (typeof x !== 'string') x = typeof x === 'object' ? String(x) : x + '';
  let out = '', last = 0;
  for (let i = 0; i < x.length; ++i) {
    const c = x.charCodeAt(i);
    if (c < 128) {
      if (codeartsNoEscape[c] === 1) continue;
      if (last < i) out += x.slice(last, i);
      last = i + 1; out += codeartsHexTable()[c]; continue;
    }
    if (last < i) out += x.slice(last, i);
    if (c < 2048) { last = i + 1; out += codeartsHexTable()[192 | c >> 6] + codeartsHexTable()[128 | c & 63]; continue; }
    if (c < 55296 || c >= 57344) { last = i + 1; out += codeartsHexTable()[224 | c >> 12] + codeartsHexTable()[128 | c >> 6 & 63] + codeartsHexTable()[128 | c & 63]; continue; }
    if (++i, i >= x.length) throw new Error('ERR_INVALID_URI');
    const lo = x.charCodeAt(i) & 1023;
    last = i + 1; const cp = 65536 + ((c & 1023) << 10 | lo);
    out += codeartsHexTable()[240 | cp >> 18] + codeartsHexTable()[128 | cp >> 12 & 63] + codeartsHexTable()[128 | cp >> 6 & 63] + codeartsHexTable()[128 | cp & 63];
  }
  if (last === 0) return x;
  if (last < x.length) return out + x.slice(last);
  return out;
}
function codeartsFmtDate(d) {
  const p = (n) => String(n).padStart(2, '0');
  return `${d.getUTCFullYear()}${p(d.getUTCMonth() + 1)}${p(d.getUTCDate())}T${p(d.getUTCHours())}${p(d.getUTCMinutes())}${p(d.getUTCSeconds())}Z`;
}
const CODEARTS_EMPTY_SHA256 = 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855';

/** 组装签名后的请求头（返回可直接用于 https.request 的 headers） */
function codeartsSignedHeaders(cred, method, endpoint, payloadHeaders = {}, bodyObj = undefined) {
  const url = new URL(endpoint);
  const headers = Object.assign({}, payloadHeaders);
  const Y = {};
  let date = headers['X-Sdk-Date'];
  if (!date) { date = codeartsFmtDate(new Date()); Y['X-Sdk-Date'] = date; }
  Y['host'] = headers['host'] || url.host;
  const H = Object.assign({}, headers, Y);

  const names = Object.keys(H).map((k) => ({ k, l: k.toLowerCase() })).sort((a, b) => a.l.localeCompare(b.l));
  const signedList = names.map((x) => x.l).join(';');
  const canonicalHeaders = names.map((x) => `${x.l}:${H[x.k]}\n`).join('');

  let cu = url.pathname.split('/').map((s) => codeartsUrlEncode(s)).join('/');
  if (cu[cu.length - 1] !== '/') cu += '/';
  const qs = [];
  for (const [k, v] of url.searchParams.entries()) qs.push([codeartsUrlEncode(k), codeartsUrlEncode(v)]);
  qs.sort((a, b) => (a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : 0));
  const canonicalQuery = qs.map(([k, v]) => `${k}=${v}`).join('&');

  // body hash：优先 X-Sdk-Content-Sha256 头（UNSIGNED-PAYLOAD），其次 data 序列化，最后空串
  let bodyHash = H['X-Sdk-Content-Sha256'];
  if (!bodyHash) bodyHash = bodyObj !== undefined ? crypto.createHash('sha256').update(JSON.stringify(bodyObj)).digest('hex') : CODEARTS_EMPTY_SHA256;

  const canonicalRequest = [method, cu, canonicalQuery, canonicalHeaders, signedList, bodyHash].join('\n');
  const stringToSign = ['SDK-HMAC-SHA256', date, crypto.createHash('sha256').update(canonicalRequest).digest('hex')].join('\n');
  const signature = crypto.createHmac('sha256', cred.secretKey).update(stringToSign).digest('hex');

  H['Authorization'] = `SDK-HMAC-SHA256 Access=${cred.accessKey}, SignedHeaders=${signedList}, Signature=${signature}`;
  return H;
}

function codeartsRequest(endpoint, headers, method = 'GET', body) {
  return new Promise((resolve, reject) => {
    const u = new URL(endpoint);
    const req = https.request(
      { host: u.host, path: u.pathname + u.search, method, headers, timeout: 20000 },
      (res) => {
        let d = '';
        res.on('data', (c) => (d += c));
        res.on('end', () => resolve({ status: res.statusCode, body: d }));
      }
    );
    req.on('error', reject);
    req.on('timeout', () => req.destroy(new Error('timeout')));
    if (body) req.write(body);
    req.end();
  });
}
const codeartsUuid = () => crypto.randomUUID();

// ---------- 业务头 ----------
function codeartsBusinessHeaders(cred) {
  return {
    'x-snap-traceid': codeartsUuid(),
    'Content-Type': 'application/json',
    'Agent-Type': 'PromptCenter',
    'X-Language': 'zh-cn',
    // STS 临时凭证形态：声明 body 不参与校验（与客户端 kernel exporter 完全一致）
    'X-Sdk-Content-Sha256': 'UNSIGNED-PAYLOAD',
    'X-Security-Token': cred.securitytoken,
  };
}

// ---------- 凭证获取（纯 Node：DPAPI 主密钥 + node:sqlite 读库 + AES-GCM，无需 Python） ----------
const CODEARTS_DB = path.join(process.env.APPDATA || '', 'codearts-agent', 'User', 'globalStorage', 'state.vscdb');
const CODEARTS_SECRET_KEY = 'secret://{"extensionId":"huaweicloud.authentication","key":"HuaweiCloudSession"}';

function codeartsLoadCredentials() {
  if (!fs.existsSync(CODEARTS_DB)) throw new Error('not_installed: 未找到 CodeArts Agent 数据库');
  let aesKey;
  try {
    aesKey = readChromiumMasterKey(path.join(process.env.APPDATA || '', 'codearts-agent'));
  } catch (e) { throw new Error('decrypt_failed: ' + e.message); }
  let row;
  try {
    const { DatabaseSync } = require('node:sqlite');
    const db = new DatabaseSync(CODEARTS_DB, { readOnly: true });
    row = db.prepare('SELECT value FROM ItemTable WHERE key = ?').get(CODEARTS_SECRET_KEY);
    db.close();
  } catch (e) {
    if (/node:sqlite/.test(e.message)) {
      throw new Error('decrypt_failed: 当前 Node 运行时缺少内置 node:sqlite（需 Node 22.13+/24+），无法解密 CodeArts 凭证');
    }
    throw new Error('decrypt_failed: ' + e.message);
  }
  if (!row) throw new Error('not_logged_in: 未登录（secret 不存在），请打开 CodeArts Agent 登录华为账号');
  try {
    const blob = Buffer.from(JSON.parse(row.value).data);
    const obj = JSON.parse(aesGcmDecryptV10(blob, aesKey).toString('utf8'));
    obj._decrypted_at = new Date().toISOString().replace(/\.\d{3}Z$/, 'Z');
    return obj;
  } catch (e) { throw new Error('decrypt_failed: ' + e.message); }
}

// ---------- 主流程 ----------
async function checkinCodeArts() {
  try {
    log('CodeArts 每日签到启动');
    const cred = codeartsLoadCredentials();
    log(`凭证 OK（账号 ${cred.account && cred.account.label || '?'}，AK=${cred.accessKey.slice(0, 6)}****，有效期至 ${cred.expires_at}）`);
    if (cred.expires_at && new Date(cred.expires_at).getTime() < Date.now()) {
      throw new Error('凭证已过期且客户端未在线续期——请打开 CodeArts Agent 让其刷新登录态后重试');
    }

    // 1. 拉活动列表
    const deliveryUrl = `https://${CODEARTS_HOST}/v1/ops/delivery?channel=${CODEARTS_CHANNEL}`;
    let res = await codeartsRequest(deliveryUrl, codeartsSignedHeaders(cred, 'GET', deliveryUrl, codeartsBusinessHeaders(cred)), 'GET');
    if (res.status !== 200) throw new Error(`delivery HTTP ${res.status}: ${res.body.slice(0, 200)}`);
    const delivery = JSON.parse(res.body);
    if (delivery.code !== 0) throw new Error(`delivery 业务错误 ${delivery.code}: ${delivery.message}`);
    const items = (delivery.data && delivery.data.items) || [];
    log(`活动列表 OK（${items.length} 项）`);

    // 2. 定位每日签到活动
    const daily = items.find((it) => it.campaignId === CODEARTS_DAILY_CAMPAIGN_ID) ||
                  items.find((it) => it.type === 'USER_LOGIN');
    if (!daily) {
      log('未找到每日签到活动（可能活动已下线），跳过。');
      return true;
    }

    // 3. 状态判定（ELIGIBLE 可领 / CLAIMED 已领待确认 / CONFIRMED、CONSUMED 已到账）
    const alreadyDone = daily.status === 'CLAIMED' || daily.status === 'CONFIRMED' || daily.status === 'CONSUMED';
    if (alreadyDone || daily.claimable === false) {
      if (alreadyDone) {
        // CLAIMED = 已领但 confirm 中断的中间态：补一次确认使积分落账，避免一直卡在待确认
        if (daily.status === 'CLAIMED') {
          log(`今日已领待确认（状态 CLAIMED，${daily.benefitAmount}${daily.benefitUnit}），补执行确认...`);
          try {
            const confirmUrl = `https://${CODEARTS_HOST}/v1/ops/confirm`;
            const confirmBody = JSON.stringify({ campaignId: daily.campaignId });
            const r2 = await codeartsRequest(confirmUrl, codeartsSignedHeaders(cred, 'POST', confirmUrl, codeartsBusinessHeaders(cred), JSON.parse(confirmBody)), 'POST', confirmBody);
            const j2 = JSON.parse(r2.body || '{}');
            if (r2.status === 200 && j2.code === 0) {
              log(`补确认成功，${daily.benefitAmount}${daily.benefitUnit} 到账 🎉`);
            } else {
              log(`补确认未通过（HTTP ${r2.status}，code=${j2.code}），若积分未到账请打开 CodeArts Agent 手动确认`);
            }
          } catch (e) {
            log(`补确认调用失败（${e.message}），若积分未到账请打开 CodeArts Agent 手动确认`);
          }
        } else {
          log(`今日签到已完成（campaignId=${daily.campaignId}，状态 ${daily.status}，${daily.benefitAmount}${daily.benefitUnit}），无需重复领取。`);
        }
      } else {
        log(`每日签到当前不可领取（claimable=${daily.claimable}，status=${daily.status}），跳过。`);
      }
      return true;
    }

    // 4. 领取（claim）
    const idempotentKey = `claim_${daily.campaignId}_${Date.now()}`;
    const claimUrl = `https://${CODEARTS_HOST}/v1/ops/claim`;
    const claimBody = JSON.stringify({ campaignId: daily.campaignId, idempotentKey, channel: CODEARTS_CHANNEL });
    log(`开始领取：campaignId=${daily.campaignId}（${daily.title}），idempotentKey=${idempotentKey}`);
    res = await codeartsRequest(claimUrl, codeartsSignedHeaders(cred, 'POST', claimUrl, codeartsBusinessHeaders(cred), JSON.parse(claimBody)), 'POST', claimBody);
    if (res.status !== 200) throw new Error(`claim HTTP ${res.status}: ${res.body.slice(0, 200)}`);
    const claimRes = JSON.parse(res.body);
    if (claimRes.code !== 0) throw new Error(`claim 业务错误 ${claimRes.code}: ${claimRes.message}`);
    const claimStatus = claimRes.data && claimRes.data.status;
    if (!['CLAIMED', 'CONFIRMED', 'CONSUMED'].includes(claimStatus)) {
      throw new Error(`claim 未成功，status=${claimStatus}，message=${claimRes.message}`);
    }
    log(`claim 成功（status=${claimStatus}）`);

    // 5. 确认到账（confirm）
    const confirmUrl = `https://${CODEARTS_HOST}/v1/ops/confirm`;
    const confirmBody = JSON.stringify({ campaignId: daily.campaignId });
    res = await codeartsRequest(confirmUrl, codeartsSignedHeaders(cred, 'POST', confirmUrl, codeartsBusinessHeaders(cred), JSON.parse(confirmBody)), 'POST', confirmBody);
    if (res.status !== 200) throw new Error(`confirm HTTP ${res.status}: ${res.body.slice(0, 200)}`);
    const confirmRes = JSON.parse(res.body);
    if (confirmRes.code !== 0) throw new Error(`confirm 业务错误 ${confirmRes.code}: ${confirmRes.message}`);
    log(`confirm 成功，${daily.benefitAmount}${daily.benefitUnit} 已到账 🎉`);

    return true;
  } catch (e) {
    log('签到失败：' + (e && e.message ? e.message : e));
    return false;
  }
}

// ============================================================
// 6. Qoder 积分签到（API 直连版，无需客户端窗口）
// 活动：「每天领 100 Credits」，每日 10:00（UTC+8）刷新，领取后 30 天有效
// 流程：解密本地登录态 -> (临期自动刷新 token 并写回) -> 查询活动 -> 领取 -> 复查
// 认证：Bearer token + Cosy-* 风控头（runtime-info.exe 设备指纹桥接）
// ============================================================

// ============================================================
// 版本探测：国内版优先，国际版兜底（哪个有登录态用哪个）
// appVersion 为兜底值，实际运行时会从安装目录 package.json 自动探测
// ============================================================
const QD_VARIANTS = [
  {
    name: 'Qoder CN（国内版）',
    dataDir: path.join(process.env.APPDATA || '', 'com.qodercn.app.stable'),
    exeDir: path.join(process.env.LOCALAPPDATA || '', 'Programs', 'Qoder CN'),
    api: 'https://openapi.qoder.com.cn',
    runtimeEnv: '0',          // runtime-info.exe 环境参数：CN=0
    appVersion: '0.3.4',
  },
  {
    name: 'Qoder（国际版）',
    dataDir: path.join(process.env.APPDATA || '', 'com.qoder.app.stable'),
    exeDir: path.join(process.env.LOCALAPPDATA || '', 'Programs', 'Qoder'),
    api: 'https://openapi.qoder.sh',
    runtimeEnv: '3',          // global=3
    appVersion: '0.3.4',
  },
];

// 从安装目录自动探测 Qoder 版本号（用于 Cosy-Version 头），失败则用兜底值
function detectQoderAppVersion(exeDir, fallback) {
  return detectAppVersion([
    path.join(exeDir, 'resources', 'app', 'package.json'),
    path.join(exeDir, 'resources', 'app.asar.unpacked', 'package.json'),
  ], fallback);
}

function qoderDetectVariant() {
  for (const v of QD_VARIANTS) {
    if (fs.existsSync(path.join(v.dataDir, 'auth.v1.dat'))) {
      // 自动覆盖版本号（兜底值保留在变体定义中）
      return { ...v, appVersion: detectQoderAppVersion(v.exeDir, v.appVersion) };
    }
  }
  return null;
}

// ============================================================
// 登录态解密：Local State(DPAPI 主密钥) + auth.v1.dat(v10 AES-256-GCM)
// ============================================================

// 原子写回（与 Qoder 客户端相同的 tmp+rename 模式，避免与客户端写竞争）
function qoderWriteAuthAtomic(authPath, rawBuf) {
  const dir = path.dirname(authPath);
  // 备份（保留 3 份）
  try {
    const bak = authPath + '.bak-' + Date.now();
    fs.copyFileSync(authPath, bak);
    const baks = fs.readdirSync(dir).filter(f => f.startsWith('auth.v1.dat.bak-')).sort();
    while (baks.length > 3) fs.unlinkSync(path.join(dir, baks.shift()));
  } catch {}
  const tmp = path.join(dir, `auth.v1.dat.${process.pid}.${crypto.randomUUID()}.tmp`);
  fs.writeFileSync(tmp, rawBuf, { mode: 0o600 });
  fs.renameSync(tmp, authPath);
}

// ============================================================
// 风控头：runtime-info.exe <env> --account-stdin（stdin 传账号）
// 输出 JSON: {machineToken, machineType, machineCode, vmInfo}
// ============================================================
function qoderRiskIdentity(variant, userId) {
  const exe = path.join(variant.exeDir, 'resources', 'umid', 'runtime-info.exe');
  if (!fs.existsSync(exe)) throw new Error(`未找到设备指纹程序: ${exe}`);
  const out = execFileSync(exe, [variant.runtimeEnv, '--account-stdin'], {
    input: JSON.stringify({ account: userId }) + '\n',
    encoding: 'utf8', timeout: 30000, windowsHide: true,
  });
  const j = JSON.parse(out.split('\n')[0]);
  if (!j.machineToken) throw new Error('设备指纹程序未返回 machineToken');
  return j;
}

function qoderBuildHeaders(variant, token, userId, machineId, risk) {
  const h = {
    'Accept': 'application/json',
    'Authorization': `Bearer ${token}`,
    'Cosy-ClientType': '10',
    'Cosy-Version': variant.appVersion,
    'Cosy-MachineOS': 'x86_64_windows',
    'Cosy-MachineHostname': (process.env.COMPUTERNAME || os.hostname()).trim(),
    'Cosy-MachineId': machineId,
    'User-Agent': 'Qoder',
  };
  if (risk) {
    if (risk.machineToken) h['Cosy-MachineToken'] = risk.machineToken;
    if (risk.machineCode) h['Cosy-MachineCode'] = risk.machineCode;
    if (risk.machineType) h['Cosy-MachineType'] = risk.machineType;
  }
  return h;
}

// ============================================================
// token 刷新：POST /api/v1/deviceToken/refresh {refresh_token}
// ============================================================
async function qoderRefreshToken(variant, dataDir, masterKey, auth) {
  const res = await fetch(`${variant.api}/api/v1/deviceToken/refresh`, {
    method: 'POST',
    headers: { 'Accept': 'application/json', 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token: auth.refreshToken }),
  });
  if (!res.ok) {
    const t = await res.text().catch(() => '');
    throw new Error(`刷新失败 HTTP ${res.status} ${t.slice(0, 200)}`);
  }
  const j = await res.json();
  const newToken = j.token || j.device_token;
  if (!newToken) throw new Error('刷新响应缺少 token 字段');
  const updated = {
    ...auth,
    token: newToken,
    refreshToken: j.refresh_token || auth.refreshToken,
    expiresAt: j.expire_time ? new Date(j.expire_time).toISOString()
      : (j.expires_at ? new Date(j.expires_at).toISOString() : auth.expiresAt),
  };
  // 写回 auth.v1.dat（保持与客户端共享最新凭证）
  try {
    qoderWriteAuthAtomic(path.join(dataDir, 'auth.v1.dat'), aesGcmEncryptV10(JSON.stringify(updated), masterKey));
    log('新凭证已写回 auth.v1.dat（含备份）');
  } catch (e) {
    log(`警告：凭证写回失败（不影响本次签到）- ${e.message}`);
  }
  return updated;
}

// ============================================================
// 活动 API：GET /sash/api/v1/me/campaigns
//           POST /sash/api/v1/me/campaigns/<id>/claim
// ============================================================
async function qoderGetCampaigns(variant, headers) {
  const res = await fetch(`${variant.api}/sash/api/v1/me/campaigns`, { headers });
  if (res.status === 401 || res.status === 403) {
    const err = new Error('AUTH_REJECTED'); err.authRejected = true; throw err;
  }
  if (!res.ok) throw new Error(`活动状态查询失败 HTTP ${res.status}`);
  return res.json();
}

// 今天 10:00（UTC+8）的时间戳（秒）——活动每日刷新点
function qoderTodayRefreshTs() {
  const now = new Date();
  // UTC+8 的今天日期
  const cn = new Date(now.getTime() + 8 * 3600 * 1000);
  const y = cn.getUTCFullYear(), m = cn.getUTCMonth(), d = cn.getUTCDate();
  return Date.UTC(y, m, d, 2, 0, 0) / 1000;  // 10:00 UTC+8 = 02:00 UTC
}

// ============================================================
// 主逻辑
// ============================================================
async function checkinQoder() {
  const variant = qoderDetectVariant();
  if (!variant) { log('错误：未找到 Qoder 登录态（国内版/国际版均未登录）'); return false; }
  log(`版本：${variant.name}  API：${variant.api}`);

  // 1. 解密登录态
  const dataDir = variant.dataDir;
  const authPath = path.join(dataDir, 'auth.v1.dat');
  let auth, masterKey;
  try {
    masterKey = readChromiumMasterKey(dataDir);
    auth = JSON.parse(aesGcmDecryptV10(fs.readFileSync(authPath), masterKey).toString('utf8'));
    if (!auth.token) throw new Error('登录态中没有 token');
  } catch (e) {
    log(`错误：登录态读取失败 - ${e.message}`);
    log('请打开 Qoder 客户端重新登录后再试');
    return false;
  }
  const userId = auth.user?.id || '';
  const machineId = fs.readFileSync(path.join(dataDir, 'auth.machine-id'), 'utf8').trim();
  log(`账号：${auth.user?.name || userId}  token 到期：${auth.expiresAt}`);

  // 2. token 临期（<3 天）自动刷新
  const QODER_TOKEN_REFRESH_LEEWAY_MS = 3 * 24 * 3600 * 1000;
  if (auth.refreshToken && auth.expiresAt && (Date.parse(auth.expiresAt) - Date.now()) < QODER_TOKEN_REFRESH_LEEWAY_MS) {
    log('token 临期，尝试自动刷新...');
    try {
      auth = await qoderRefreshToken(variant, dataDir, masterKey, auth);
      log(`刷新成功，新到期时间：${auth.expiresAt}`);
    } catch (e) {
      log(`token 刷新失败：${e.message}`);
      if (auth.expiresAt && Date.parse(auth.expiresAt) <= Date.now()) {
        log('错误：token 已过期且刷新失败，请打开 Qoder 客户端重新登录');
        return false;
      }
      log('继续使用现有 token 尝试签到...');
    }
  }

  // 3. 风控头
  let risk = null;
  try {
    risk = qoderRiskIdentity(variant, userId);
  } catch (e) {
    log(`警告：设备指纹获取失败（继续尝试）- ${e.message}`);
  }

  // 4. 查询活动
  const headers = qoderBuildHeaders(variant, auth.token, userId, machineId, risk);
  let data;
  try {
    try {
      data = await qoderGetCampaigns(variant, headers);
    } catch (e) {
      if (e.authRejected && auth.refreshToken) {
        // token 失效，强刷一次
        log('token 被拒绝，尝试强制刷新...');
        auth = await qoderRefreshToken(variant, dataDir, masterKey, auth);
        data = await qoderGetCampaigns(variant, qoderBuildHeaders(variant, auth.token, userId, machineId, risk));
      } else throw e;
    }
  } catch (e) {
    if (/AUTH_REJECTED|401|403/.test(e.message)) {
      log('错误：登录态已失效，请打开 Qoder 客户端重新登录');
    } else {
      log(`错误：${e.message}`);
    }
    return false;
  }

  // 5. 找可领取的 Credits 活动（只认 CLAIM_BENEFIT 类型）
  const campaigns = (data.campaigns || []).filter(c => c.actionType === 'CLAIM_BENEFIT');
  if (campaigns.length === 0) {
    log('当前无 Credits 领取类活动（活动可能已下线）');
    return true;
  }

  const claimable = campaigns.filter(c => c.claimStatus === 'CLAIMABLE');
  const claimed = campaigns.filter(c => c.claimStatus === 'CLAIMED');
  const refreshTs = qoderTodayRefreshTs();

  if (claimable.length === 0) {
    // 没有可领取的：判断是"今天已领"还是"今天的活动还没刷新"
    const todayCampaign = campaigns.find(c => (c.startAt || 0) >= refreshTs);
    if (todayCampaign) {
      const benefit = todayCampaign.benefit || {};
      log(`今日已签到。${todayCampaign.campaignKey} 奖励 ${benefit.amount ?? '?'} ${benefit.kind ?? 'CREDITS'}`);
      return true;
    }
    // 都是昨天的活动 -> 今天 10:00 才刷新
    const latest = campaigns[campaigns.length - 1];
    log(`今日活动尚未刷新（每日 10:00 刷新），跳过本次。最近活动：${latest?.campaignKey || '无'}`);
    return true; // 跳过不算失败（由 10:30 的定时任务完成当天领取）
  }

  // 6. 领取
  const h2 = qoderBuildHeaders(variant, auth.token, userId, machineId, risk);
  for (const c of claimable) {
    const benefit = c.benefit || {};
    log(`发现可领活动：${c.campaignKey}（${benefit.amount ?? '?'} ${benefit.kind ?? 'CREDITS'}），领取中...`);
    const res = await fetch(
      `${variant.api}/sash/api/v1/me/campaigns/${encodeURIComponent(c.campaignId)}/claim`,
      { method: 'POST', headers: h2 });
    const text = await res.text().catch(() => '');
    if (!res.ok) {
      log(`领取请求失败 HTTP ${res.status}：${text.slice(0, 200)}`);
      return false;
    }
  }

  // 7. 复查
  await sleep(2);
  const data2 = await qoderGetCampaigns(variant, h2).catch(() => null);
  const after = (data2?.campaigns || []).filter(c => c.actionType === 'CLAIM_BENEFIT');
  const stillClaimable = after.filter(c => c.claimStatus === 'CLAIMABLE').length;
  if (stillClaimable === 0) {
    const today = after.find(c => (c.startAt || 0) >= refreshTs) || after[after.length - 1];
    const benefit = today?.benefit || {};
    log(`签到成功！${today?.campaignKey} 已领取 ${benefit.amount ?? '?'} ${benefit.kind ?? 'CREDITS'}（30 天内有效）`);
    return true;
  } else {
    log('领取请求已发送，但复查仍显示可领取，请人工确认');
    return false;
  }
}

// ============================================================
// 7. 果办 OfficeAce 每日签到（本地 API 桥接版）
// 活动：「每日签到有礼」1000 积分/天，每日 00:00（UTC+8）刷新，当日 23:59:59 过期
// 流程：DPAPI 解密 session.cookie -> oc_sid 会话 -> 查询活动 -> 领取 -> 复查
// 认证：oc_sid 签名 Cookie + 安装目录自签 root-ca.pem TLS 信任
// 依赖：OfficeAce 客户端正在运行（本地 API 服务承载云凭证，无法离线直连）
// 地址：弹性发现（与其他脚本"候选遍历+验证"风格一致，无硬编码地址）：
//       ① 运行态快照 <安装目录>\.office-claw\run\windows\runtime-state.json（快/准/零成本）
//       ② 配置推断 <安装目录>\.env / .inner.env 的 API_SERVER_PORT
//       ③ 已知默认端口候选（3004/3002）
//       ④ 兼底：全量枚举本机回环监听端口并发探测（客户端换端口也能命中）
//       判活依据：GET /api/subscription/current 返回 200/401/403，
//       且响应体含果办特征（401→"Authentication required"/"statusCode"；200→订阅字段）
// 响应语义（2026-10-16 逆向 cloud.fetch 审计流验证，修正早期误判）：
//       - bonus 的 currentValue = 已消耗积分（未用时恒 0），不是"已领取量"，
//         不能用 currentValue < points 判断可领；入账额度看 points 字段
//       - 领取接口 HTTP 200 {bonusSkus:[记录]} = 本次成功入账；
//         {bonusSkus:[]} = 当天无可领（通常 = 当天已领过）
//       - daily 记录的 effectiveTime = 实际领取时刻（当天首领后落在
//         北京时间今日 00:00 之后；未领时列表仅残留昨日已过期记录或无记录）
//       - 客户端自身每小时整点自动尝试领取（00:00:0X 即代领当天），
//         脚本主要职责 = 客户端未及时领取时的兑底 + 确认
// ============================================================

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
// 不用 Get-NetTCPConnection/Get-CimInstance——本机实测 WMI/模块冷启动超过 20 秒）
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

// 策略③：从 .env / .inner.env 读取 API_SERVER_PORT（跳过注释行）
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

  // 策略④：全量枚举回环监听端口并发探测（客户端换端口/多实例时的终极兼底）
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
// 主逻辑
// ============================================================
const OFFICEACE_DAILY_ACTIVITY_ID = 'bonus-daily-checkin-2026';

async function checkinOfficeAce() {
  // 1. 登录态
  if (!fs.existsSync(OFFICEACE_SESSION_COOKIE_PATH)) {
    log('错误：未找到果办登录态文件（请确认已安装并登录 OfficeAce）');
    return false;
  }
  let session;
  try {
    session = officeaceDecryptSessionCookie();
  } catch (e) {
    log(`错误：登录态解密失败 - ${e.message}`);
    log('提示：请打开 OfficeAce 客户端确认已登录');
    return false;
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
    return false;
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
      return false;
    }
    if (res.status !== 200) {
      log(`错误：状态接口返回 HTTP ${res.status}`);
      return false;
    }
    status = JSON.parse(res.body);
  } catch (e) {
    const msg = e.cause?.code || e.cause?.message || e.message;
    if (/ECONNREFUSED|ECONNRESET|ENOTFOUND|fetch failed/i.test(msg)) {
      log('错误：OfficeAce 客户端未运行（本地 API 无法连接），请先启动果办客户端');
    } else {
      log(`错误：状态接口调用失败 - ${msg}`);
    }
    return false;
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
    return true; // 跳过不算失败
  }

  // ---- 判定语义（2026-10-16 审计流逆向修正）----
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
    return true;
  }

  // 今日未领（列表为昨日残留记录或无记录）：发起领取（服务端会领取当天全部可领奖励）
  log(`${daily.activityName} 今日可领（+${total} 积分），领取中...`);
  let claimBody;
  try {
    const res = await post('/api/subscription/claim-bonus');
    const text = res.body || '';
    if (res.status !== 200) {
      log(`领取请求失败 HTTP ${res.status}：${text.slice(0, 200)}`);
      return false;
    }
    claimBody = JSON.parse(text);
  } catch (e) {
    log(`错误：领取请求失败 - ${e.cause?.code || e.cause?.message || e.message}`);
    return false;
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

  // 5. 复查确认（以最新 effectiveTime 判断今日是否已入账；claim 返回空 = 客户端已代领）
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
      return true;
    }
    log('领取请求已发送，但复查未见今日入账记录（疑云端资格判定未通过），请人工确认');
    return false;
  } catch (e) {
    log(`警告：复查失败（领取请求可能已生效）- ${e.cause?.code || e.cause?.message || e.message}`);
    return false;
  }
}

// ============================================================
// 主流程（2026-10-25 重构：分组调度）
// 分组：
//   ai    凌晨组（每日 0 点刷新，计划任务 00:05 跑）
//   daily 白天组（Qoder 每日 10:00 才重置；网盘类白天跑即可，10:35）
// 平台两种形态：
//   fn     内联函数（本文件内实现）
//   script 独立脚本（子进程调用，进程隔离，单脚本崩溃不影响主流程）
// 用法: node checkin_all.js [--group=ai|daily] [--no-delay]
//   不带 --group 则跑全部平台（向后兼容）
// ============================================================
const PLATFORMS = [
  // ---- AI 凌晨组 ----
  { name: 'Trae',      group: 'ai',    fn: checkinTraeUnified },
  { name: 'TeleAgent', group: 'ai',    fn: checkinTeleAgent },
  { name: 'WorkBuddy', group: 'ai',    fn: checkinWorkBuddy },
  { name: 'CodeArts',  group: 'ai',    fn: checkinCodeArts },
  { name: 'OfficeAce', group: 'ai',    fn: checkinOfficeAce },
  { name: '库库AI',    group: 'ai',    script: 'kuku_checkin.js' },
  // ---- 白天组 ----
  { name: 'Qoder',     group: 'daily', fn: checkinQoder },      // 每日 10:00 才重置，不能凌晨跑
  { name: '百度网盘',  group: 'daily', script: 'baidupan_checkin.js' },
  { name: '天翼云盘',  group: 'daily', script: 'tianyi_checkin.js' },
];

// 子进程方式执行独立脚本：--no-delay 由主控统一延时，退出码判成败
function runScriptPlatform(script) {
  const r = spawnSync(process.execPath, [path.join(__dirname, script), '--no-delay'], {
    cwd: __dirname,
    stdio: 'inherit',
    timeout: 600000,
  });
  return r.status === 0;
}

async function main() {
  const noDelay = process.argv.includes('--no-delay');
  const groupArg = (process.argv.find(a => a.startsWith('--group=')) || '').split('=')[1] || '';
  const platforms = PLATFORMS.filter(p => !groupArg || p.group === groupArg);
  if (platforms.length === 0) { log(`错误：--group=${groupArg} 无匹配平台（可选 ai / daily）`); process.exitCode = 1; return; }

  log(`====== 统一签到开始（分组：${groupArg || '全部'}，共 ${platforms.length} 平台）======`);

  const results = [];
  for (let i = 0; i < platforms.length; i++) {
    const p = platforms[i];
    // 每个平台签到前加随机延迟（打乱计划任务的固定启动时间）；--no-delay 跳过
    if (!noDelay) {
      const delay = randomDelaySec();
      log(`[${p.name}] 随机等待 ${delay} 秒后签到...`);
      await sleep(delay);
    }
    try {
      const ok = p.script ? runScriptPlatform(p.script) : await p.fn();
      results.push({ name: p.name, ok });
    } catch (e) {
      log(`[${p.name}] 致命错误：${e.message}`);
      results.push({ name: p.name, ok: false });
    }
  }

  // 汇总
  console.log(`\n${'='.repeat(50)}`);
  log('签到汇总：');
  const success = results.filter(r => r.ok).length;
  const fail = results.filter(r => !r.ok).length;
  for (const r of results) {
    log(`  ${r.ok ? '[OK]' : '[FAIL]'} ${r.name}`);
  }
  log(`成功 ${success}/${results.length}，失败 ${fail}/${results.length}`);
  log('====== 统一签到结束 ======');

  // 用 exitCode 而非 process.exit()：fetch(undici) 后立即强杀会触发 libuv 断言崩溃
  // （Node 24 Windows：UV_HANDLE_CLOSING，退出码变 0xC0000409）；自然退出句柄干净关闭
  if (fail > 0) process.exitCode = 1;
}

// 导出签到函数与公共工具（供测试引用；直接运行时才执行 main）
module.exports = {
  checkinTraeUnified,
  checkinTeleAgent,
  checkinWorkBuddy,
  checkinQoder,
  checkinOfficeAce,
  checkinCodeArts,
  dpapiUnprotect,
  aesGcmDecryptV10,
  aesGcmEncryptV10,
  regQueryInstallLocation,
  detectAppVersion,
  codeartsLoadCredentials,
};

if (require.main === module) {
  main().catch(e => { log(`致命错误：${e.message}`); process.exitCode = 1; });
}
