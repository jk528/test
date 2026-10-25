// ============================================================
// Trae 每日签到（独立分享版）
//
// 原理：读取 Trae 客户端本地登录凭证（storage.json 中加密存储的
//       iCubeAuthInfo，AES-128-CBC 解密后取 token），调用签到 API。
//       全程只读本机文件，凭证不落盘、不上传。
//
// 前置条件：
//   1. 已安装 Trae CN 客户端并登录（脚本只复用本地登录态）
//   2. Node.js 18+（无 Node 时 run_checkin.cmd 会尝试用 Trae 客户端兜底）
//
// 用法: node trae_checkin.js [--no-delay] [--status]
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
const { execSync } = require('child_process');

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
// 凭证提取：加密 auth 块 -> AES-128-CBC 解密 -> token
// （密钥材料由密文内嵌字段 + 两组内置常量推导，算法逆向自客户端）
// ============================================================
const HP = 16, q8_AES128 = 16, WP = HP, rh = 64, Rv = 32, VP = 64, Em = 6;
const ure = Uint8Array.from([82,9,106,213,48,54,165,56,191,64,163,158,129,243,215,251,124,227,57,130,155,47,255,135,52,142,67,68,196,222,233,203,84,123,148,50,166,194,35,61,238,76,149,11,66,250,195,78,8,46,161,102,40,217,36,178,118,91,162,73,109,139,209,37]);
const dre = Uint8Array.from([31,221,168,51,136,7,199,49,177,18,16,89,39,128,236,95,96,81,127,169,25,181,74,13,45,229,122,159,147,201,156,239,160,224,59,77,174,42,245,176,200,235,187,60,131,83,153,97,23,43,4,126,186,119,214,38,225,105,20,99,85,33,12,125]);

async function sha512(data) {
  return new Uint8Array(await crypto.subtle.digest('SHA-512', data));
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
// 环境探测（全自动，无硬编码）
// ============================================================
// Trae 数据目录：新名 "Trae CN" 优先，旧名 "TRAE SOLO CN" 兜底
function findTraeAppDataRoot() {
  const ad = process.env.APPDATA;
  if (!ad) return null;
  for (const name of ['Trae CN', 'TRAE SOLO CN']) {
    const root = path.join(ad, name);
    if (fs.existsSync(path.join(root, 'User', 'globalStorage', 'storage.json'))) return root;
  }
  return null;
}

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

// 客户端版本号（用于 x-app-version 请求头）：注册表 -> 常见安装路径
function findTraeAppVersion() {
  const candidates = [];
  const installDir = regQueryInstallLocation('Trae');
  if (installDir) candidates.push(path.join(installDir, 'resources', 'app', 'package.json'));
  const lad = process.env.LOCALAPPDATA || '';
  candidates.push(path.join(lad, 'Programs', 'Trae CN', 'resources', 'app', 'package.json'));
  candidates.push(path.join(lad, 'Programs', 'TRAE SOLO CN', 'resources', 'app', 'package.json'));
  for (const p of candidates) {
    try {
      if (p && fs.existsSync(p)) {
        const v = JSON.parse(fs.readFileSync(p, 'utf8')).version;
        if (v) return v;
      }
    } catch { /* 忽略单个候选读取失败 */ }
  }
  return '';
}

// ============================================================
// 签到 API
// ============================================================
const BASE = 'https://api.trae.cn/trae/api/v2/ug/checkin_credits';

async function main() {
  const args = process.argv.slice(2);
  const statusOnly = args.includes('--status');
  const noDelay = args.includes('--no-delay');

  logSection('Trae 每日签到');

  // 1) 数据目录
  const root = findTraeAppDataRoot();
  if (!root) {
    log('错误：未检测到 Trae 数据目录（请先安装并登录 Trae CN 客户端）');
    process.exitCode = 1; return;
  }
  log(`检测到数据目录：${root}`);

  // 2) 解密登录态
  let auth;
  try {
    const storage = JSON.parse(fs.readFileSync(path.join(root, 'User', 'globalStorage', 'storage.json'), 'utf8'));
    const enc = storage['iCubeAuthInfo://icube.cloudide'];
    if (!enc) { log('错误：未找到登录态数据，请打开 Trae 客户端确认已登录'); process.exitCode = 1; return; }
    auth = JSON.parse(await decryptTrae(enc));
    if (!auth.token) { log('错误：登录态中没有 token'); process.exitCode = 1; return; }
  } catch (e) {
    log(`错误：登录态读取失败 - ${e.message}`);
    process.exitCode = 1; return;
  }

  // 3) 设备信息（签到接口要求）
  let deviceId = '';
  try {
    const envPath = path.join(root, 'ModularData', 'ckg_server', 'local_env.json');
    deviceId = String(JSON.parse(fs.readFileSync(envPath, 'utf8')).device_id || '');
  } catch { /* 可缺省，但会被拒 */ }
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
  const statusUrl = `${BASE}/status`;
  const claimUrl = `${BASE}/claim`;

  // 4) 查状态
  let status;
  try {
    const statusRes = await fetch(statusUrl, { method: 'POST', headers, body });
    if (statusRes.status === 401 || statusRes.status === 403) {
      log('错误：登录态已过期，请打开 Trae 客户端重新登录');
      process.exitCode = 1; return;
    }
    status = await statusRes.json();
  } catch (e) {
    log(`错误：状态查询失败 - ${e.message}`);
    process.exitCode = 1; return;
  }
  const extraNote = status.extra_credits ? `（含额外 ${status.extra_credits}）` : '';
  log(`当前积分：${status.credits ?? '?'}${extraNote}　今日已签：${status.checked_in ? '是' : '否'}`);

  if (statusOnly) return;
  if (status.checked_in) { log('今日已签到，跳过'); return; }
  if (!status.enable) { log('签到功能未启用'); return; }

  // 5) 随机延迟防检测
  if (!noDelay) {
    const sec = DELAY_MIN + Math.floor(Math.random() * (DELAY_MAX - DELAY_MIN + 1));
    log(`随机延迟 ${sec} 秒...`);
    await sleep(sec);
  }

  // 6) 签到 + 复查
  try {
    const claimRes = await fetch(claimUrl, { method: 'POST', headers, body });
    const claim = await claimRes.json();
    if (claim.code === 0) {
      let credits = status.credits || 200;
      try {
        const refresh = await (await fetch(statusUrl, { method: 'POST', headers, body })).json();
        if (typeof refresh.credits === 'number') credits = refresh.credits;
      } catch { /* 复查失败不影响结果 */ }
      log(`签到成功！积分：${credits}${extraNote}`);
    } else {
      log(`签到失败：${claim.message || JSON.stringify(claim)}`);
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
