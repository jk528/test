// ============================================================
// Qoder 每日签到（独立分享版）
//
// 原理：读取 Qoder 客户端本地登录凭证（auth.v1.dat，Chromium 系
//       v10 AES-256-GCM 加密，主密钥经 DPAPI 从 Local State 取），
//       调用活动 API 领取「每天领 100 Credits」。token 临期自动刷新
//       并加密写回（与客户端同款 tmp+rename 原子写）。全程只读本机
//       文件，凭证不外传。
//
// 重要：活动每日 10:00（UTC+8）才刷新！定时任务请设在 10:30 之后
//       （注册计划任务.ps1 默认 10:40），凌晨跑会扑空（不算失败，
//       但当天领不到）。
//
// 前置条件：
//   1. 已安装 Qoder CN（国内版）或 Qoder（国际版）客户端并登录
//      （脚本只复用本地登录态；风控头依赖客户端自带的
//       resources\umid\runtime-info.exe，卸载客户端则签到失效）
//   2. Node.js 18+（无 Node 时 run_checkin.cmd 会尝试用 Qoder 客户端兜底）
//
// 用法: node qoder_checkin.js [--no-delay] [--status]
//   --no-delay  跳过随机延迟（手动测试用）
//   --status    只查询活动状态，不执行领取
// 退出码: 0=成功/已签/活动未刷新/查询成功  1=失败
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

function logSection(name) {
  console.log(`\n${'='.repeat(50)}\n[${name}]\n${'='.repeat(50)}`);
}

// ============================================================
// 登录态解密：Local State(DPAPI 主密钥) + auth.v1.dat(v10 AES-256-GCM)
// ============================================================

// ---- DPAPI(CurrentUser) 解密；入参为去掉 "DPAPI" 前缀后的密文 ----
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

function aesGcmEncryptV10(plain, key) {
  const nonce = crypto.randomBytes(12);
  const c = crypto.createCipheriv('aes-256-gcm', key, nonce);
  const ct = Buffer.concat([c.update(Buffer.from(plain, 'utf8')), c.final()]);
  return Buffer.concat([Buffer.from('v10', 'ascii'), nonce, ct, c.getAuthTag()]);
}

// ---- 应用版本探测：从候选 package.json 读取 version ----
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
async function checkinQoder({ statusOnly, noDelay }) {
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
  const refreshTs = qoderTodayRefreshTs();

  if (statusOnly) {
    const todayCampaign = campaigns.find(c => (c.startAt || 0) >= refreshTs);
    for (const c of campaigns) {
      const benefit = c.benefit || {};
      const tag = (c.startAt || 0) >= refreshTs ? '（今日）' : '';
      log(`${c.campaignKey}${tag} 状态 ${c.claimStatus} 奖励 ${benefit.amount ?? '?'} ${benefit.kind ?? 'CREDITS'}`);
    }
    log(claimable.length > 0 ? `有 ${claimable.length} 个活动可领取（--status 只读模式，未领取）`
      : (todayCampaign ? '今日已领取（--status 只读模式）' : '今日活动尚未刷新（每日 10:00 刷新）'));
    return true;
  }

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
    return true; // 跳过不算失败（由 10:30 之后的定时任务完成当天领取）
  }

  // 6. 随机延迟防检测
  if (!noDelay) {
    const sec = DELAY_MIN + Math.floor(Math.random() * (DELAY_MAX - DELAY_MIN + 1));
    log(`随机延迟 ${sec} 秒...`);
    await sleep(sec);
  }

  // 7. 领取
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

  // 8. 复查
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

async function main() {
  const args = process.argv.slice(2);
  const statusOnly = args.includes('--status');
  const noDelay = args.includes('--no-delay');

  logSection('Qoder 每日签到');
  const ok = await checkinQoder({ statusOnly, noDelay });
  if (!ok) process.exitCode = 1;
}

main().catch(e => { log(`致命错误：${e.message}`); process.exitCode = 1; });
