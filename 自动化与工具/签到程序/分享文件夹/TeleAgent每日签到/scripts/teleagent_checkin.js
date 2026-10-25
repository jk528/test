// ============================================================
// TeleAgent 每日签到（独立分享版）
//
// 原理：读取 TeleAgent 客户端本地登录凭证（token.json 中加密存储的
//       encryptedToken，Chromium OSCrypt v10 信封：先用 DPAPI 解 Local State
//       里的主密钥，再用 AES-256-GCM 解密出 token），调用签到 API。
//       全程只读本机文件，凭证不落盘、不上传。
//
// 前置条件：
//   1. 已安装 TeleAgent 客户端并登录（脚本只复用本地登录态）
//   2. Node.js 18+（无 Node 时 run_checkin.cmd 会依次尝试客户端自带
//      Node 运行时、TeleAgent 客户端自身兜底）
//
// 用法: node teleagent_checkin.js [--no-delay] [--status]
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
// 凭证提取：Local State(DPAPI) -> 32B 主密钥 -> AES-256-GCM("v10") 解密 token
// （Electron safeStorage 在 Windows 上即 Chromium OSCrypt，算法逆向自客户端）
// ============================================================

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
function readChromiumMasterKey(dataDir) {
  const localState = JSON.parse(fs.readFileSync(path.join(dataDir, 'Local State'), 'utf8'));
  const encKeyB64 = localState?.os_crypt?.encrypted_key;
  if (!encKeyB64) throw new Error('Local State 中未找到 os_crypt.encrypted_key');
  const blob = Buffer.from(encKeyB64, 'base64');
  if (blob.slice(0, 5).toString('ascii') !== 'DPAPI') throw new Error('encrypted_key 前缀非 DPAPI');
  return dpapiUnprotect(blob.slice(5));
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

// ============================================================
// 环境探测（全自动，无硬编码）
// ============================================================
// TeleAgent 用户数据目录（登录态、Local State、设备元数据均在其下）
const TA_DATA_ROOT = path.join(os.homedir(), '.local', 'share', 'TeleAgent');

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

// 客户端版本号（用于 X-App-Version 请求头）：注册表 -> 常见安装路径，
// 全部失败时回退到已知版本（缺失也能通过，仅为完整模拟客户端请求）
const TA_APP_VERSION_FALLBACK = '2.5.2';
let _taAppVersion = '';
function findTeleAgentAppVersion() {
  if (_taAppVersion) return _taAppVersion;
  const candidates = [];
  const installDir = regQueryInstallLocation('TeleAgent');
  if (installDir) candidates.push(path.join(installDir, 'resources', 'app', 'package.json'));
  const lad = process.env.LOCALAPPDATA || '';
  candidates.push(path.join(lad, 'Programs', 'TeleAgent', 'resources', 'app', 'package.json'));
  candidates.push(path.join('C:\\Program Files', 'TeleAgent', 'resources', 'app', 'package.json'));
  _taAppVersion = detectAppVersion(candidates, TA_APP_VERSION_FALLBACK);
  return _taAppVersion;
}

// 登录态定位：current-owner.json 指向当前用户目录；失败则遍历 users\ 兜底
function taFindTokenJson() {
  try {
    const owner = JSON.parse(fs.readFileSync(path.join(TA_DATA_ROOT, 'current-owner.json'), 'utf8'));
    const p = path.join(TA_DATA_ROOT, 'users', owner.ownerDir, 'app-auth', 'token.json');
    if (fs.existsSync(p)) return p;
  } catch { /* 继续走遍历兜底 */ }
  const usersDir = path.join(TA_DATA_ROOT, 'users');
  try {
    for (const d of fs.readdirSync(usersDir)) {
      const p = path.join(usersDir, d, 'app-auth', 'token.json');
      if (fs.existsSync(p)) return p;
    }
  } catch { /* 目录不存在 */ }
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

// ============================================================
// 签到 API
// ============================================================
const TA_BASE = 'https://agent.teleai.com.cn/superCowork/sapi';

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

async function main() {
  const args = process.argv.slice(2);
  const statusOnly = args.includes('--status');
  const noDelay = args.includes('--no-delay');

  logSection('TeleAgent 每日签到');

  // 1) 登录态文件
  const tokenPath = taFindTokenJson();
  if (!tokenPath) {
    log('错误：未找到 TeleAgent 登录态文件（请先安装并登录 TeleAgent 客户端）');
    process.exitCode = 1; return;
  }
  log(`检测到登录态文件：${tokenPath}`);

  // 2) 解密登录态
  let token;
  try {
    const masterKey = readChromiumMasterKey(TA_DATA_ROOT);
    if (masterKey.length !== 32) throw new Error('主密钥解密结果异常');
    token = taDecryptToken(tokenPath, masterKey);
  } catch (e) {
    log(`错误：登录态解密失败 - ${e.message}`);
    process.exitCode = 1; return;
  }

  const statusUrl = `${TA_BASE}/user/portal/companyStore/v2/checkDayTask`;
  const claimUrl = `${TA_BASE}/user/portal/companyStore/checkTask?type=daily_login`;
  const userUrl = `${TA_BASE}/user/portal/companyStore/userCenter`;

  // 3) 查状态
  let status;
  try {
    status = await taApiGet(statusUrl, token);
  } catch (e) {
    if (/401|token|登录/i.test(e.message)) {
      log('错误：登录态已过期，请打开 TeleAgent 客户端重新登录');
    } else {
      log(`错误：状态接口调用失败 - ${e.message}`);
    }
    process.exitCode = 1; return;
  }
  const daily = status?.daily_task;

  const uc = await taApiGet(userUrl, token).catch(() => null);
  log(`今日已签：${daily?.claimed_today ? '是' : '否'}　本期已领 ${daily?.total_claim_days ?? '?'} 天，累计 ${daily?.total_claimed_points ?? '?'} 分，当前余额 ${uc?.current_points_balance ?? '未知'}`);

  if (statusOnly) return;
  if (daily?.claimed_today) {
    log(`今日已签到（按钮状态「${daily.button_text ?? '今日已领'}」），跳过`);
    return;
  }

  // 4) 随机延迟防检测
  if (!noDelay) {
    const sec = DELAY_MIN + Math.floor(Math.random() * (DELAY_MAX - DELAY_MIN + 1));
    log(`随机延迟 ${sec} 秒...`);
    await sleep(sec);
  }

  // 5) 签到 + 复查
  try {
    await taApiGet(claimUrl, token);
    const [status2, uc2] = await Promise.all([
      taApiGet(statusUrl, token).catch(() => null),
      taApiGet(userUrl, token).catch(() => null)
    ]);
    const d2 = status2?.daily_task;
    if (d2?.claimed_today) {
      log(`签到成功！今日 +${d2.daily_claimable_points ?? 100} 分（按钮状态「${d2.button_text ?? '今日已领'}」）。本期已领 ${d2.total_claim_days} 天，累计 ${d2.total_claimed_points} 分，当前余额 ${uc2?.current_points_balance ?? '未知'}`);
    } else {
      log('领取请求已发送，但复查显示今日仍未领取，请人工确认');
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
