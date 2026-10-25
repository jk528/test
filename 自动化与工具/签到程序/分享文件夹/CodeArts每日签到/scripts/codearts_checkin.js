// ============================================================
// CodeArts Agent 每日签到（独立分享版）
//
// 原理：读取 CodeArts Agent 客户端本地登录凭证（VSCode SecretStorage
//       落盘 state.vscdb，Chromium OSCrypt AES-256-GCM 加密，主密钥经
//       DPAPI 保护），解密得华为云 STS 临时凭证（AK/SK/SecurityToken），
//       按 SDK-HMAC-SHA256 签名调用积分福利 API。
//       全程只读本机文件，凭证不落盘、不上传。
//
// 前置条件：
//   1. 已安装 CodeArts Agent 客户端并登录华为账号（脚本只复用本地登录态；
//      凭证 2 小时有效，客户端在线时每小时自动续期写回）
//   2. Node.js 22.13+（推荐 24+）：解密依赖内置 node:sqlite 模块
//      （无 Node 时 run_checkin.cmd 会尝试用客户端自带运行时兜底，
//       版本不足会明确报错）
//
// 用法: node codearts_checkin.js [--no-delay] [--status]
//   --no-delay  跳过随机延迟（手动测试用）
//   --status    只查询签到状态，不执行领取
// 退出码: 0=成功/已签/查询成功  1=失败
//
// 可选配置：上级目录 config.json，如 {"delayMinSec":30,"delayMaxSec":300}
// ============================================================
'use strict';
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const https = require('https');
const { execFileSync } = require('child_process');

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
// 凭证解密公共件：DPAPI(CurrentUser) + Chromium OSCrypt 主密钥
// + AES-256-GCM "v10" 信封（3B 前缀 + 12B nonce + 密文 + 16B tag）
// ============================================================
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

// Chromium 系客户端 AES 主密钥：Local State -> os_crypt.encrypted_key -> DPAPI
function readChromiumMasterKey(dataDir) {
  const localState = JSON.parse(fs.readFileSync(path.join(dataDir, 'Local State'), 'utf8'));
  const encKeyB64 = localState?.os_crypt?.encrypted_key;
  if (!encKeyB64) throw new Error('Local State 中未找到 os_crypt.encrypted_key');
  const blob = Buffer.from(encKeyB64, 'base64');
  if (blob.slice(0, 5).toString('ascii') !== 'DPAPI') throw new Error('encrypted_key 前缀非 DPAPI');
  return dpapiUnprotect(blob.slice(5));
}

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
// 华为云 SDK-HMAC-SHA256 签名（复刻客户端 kernel 实现）
// ============================================================
const CODEARTS_HOST = 'snap-access.cn-north-4.myhuaweicloud.com';
const CODEARTS_CHANNEL = 'IDE';
const CODEARTS_DAILY_CAMPAIGN_ID = 1; // 每日签到领1000积分（type=USER_LOGIN）

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

// ============================================================
// 凭证获取（纯 Node：DPAPI 主密钥 + node:sqlite 读库 + AES-GCM）
// ============================================================
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

// ============================================================
// 主流程
// ============================================================
async function main() {
  const args = process.argv.slice(2);
  const statusOnly = args.includes('--status');
  const noDelay = args.includes('--no-delay');

  logSection('CodeArts 每日签到');

  // 1) 解密本地凭证
  let cred;
  try {
    cred = codeartsLoadCredentials();
  } catch (e) {
    const m = e && e.message ? e.message : String(e);
    if (m.startsWith('not_installed')) {
      log('错误：未检测到 CodeArts Agent 数据目录（请先安装并登录 CodeArts Agent 客户端）');
    } else if (m.startsWith('not_logged_in')) {
      log(`错误：${m.replace(/^not_logged_in: /, '')}`);
    } else {
      log(`错误：凭证解密失败 - ${m.replace(/^decrypt_failed: /, '')}`);
    }
    process.exitCode = 1; return;
  }
  log(`凭证 OK（账号 ${cred.account && cred.account.label || '?'}，AK=${cred.accessKey.slice(0, 6)}****，有效期至 ${cred.expires_at}）`);
  if (cred.expires_at && new Date(cred.expires_at).getTime() < Date.now()) {
    log('错误：凭证已过期且客户端未在线续期——请打开 CodeArts Agent 让其刷新登录态后重试');
    process.exitCode = 1; return;
  }

  try {
    // 2) 拉活动列表
    const deliveryUrl = `https://${CODEARTS_HOST}/v1/ops/delivery?channel=${CODEARTS_CHANNEL}`;
    let res = await codeartsRequest(deliveryUrl, codeartsSignedHeaders(cred, 'GET', deliveryUrl, codeartsBusinessHeaders(cred)), 'GET');
    if (res.status !== 200) throw new Error(`delivery HTTP ${res.status}: ${res.body.slice(0, 200)}`);
    const delivery = JSON.parse(res.body);
    if (delivery.code !== 0) throw new Error(`delivery 业务错误 ${delivery.code}: ${delivery.message}`);
    const items = (delivery.data && delivery.data.items) || [];
    log(`活动列表 OK（${items.length} 项）`);

    // 3) 定位每日签到活动
    const daily = items.find((it) => it.campaignId === CODEARTS_DAILY_CAMPAIGN_ID) ||
                  items.find((it) => it.type === 'USER_LOGIN');
    if (!daily) {
      log('未找到每日签到活动（可能活动已下线），跳过。');
      return;
    }
    log(`每日签到活动：${daily.title}（campaignId=${daily.campaignId}，状态 ${daily.status ?? '未领取'}，claimable=${daily.claimable}，奖励 ${daily.benefitAmount}${daily.benefitUnit}）`);

    if (statusOnly) return;

    // 4) 状态判定（ELIGIBLE 可领 / CLAIMED 已领待确认 / CONFIRMED、CONSUMED 已到账）
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
      return;
    }

    // 5) 随机延迟防检测
    if (!noDelay) {
      const sec = DELAY_MIN + Math.floor(Math.random() * (DELAY_MAX - DELAY_MIN + 1));
      log(`随机延迟 ${sec} 秒...`);
      await sleep(sec);
    }

    // 6) 领取（claim）
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

    // 7) 确认到账（confirm）
    const confirmUrl = `https://${CODEARTS_HOST}/v1/ops/confirm`;
    const confirmBody = JSON.stringify({ campaignId: daily.campaignId });
    res = await codeartsRequest(confirmUrl, codeartsSignedHeaders(cred, 'POST', confirmUrl, codeartsBusinessHeaders(cred), JSON.parse(confirmBody)), 'POST', confirmBody);
    if (res.status !== 200) throw new Error(`confirm HTTP ${res.status}: ${res.body.slice(0, 200)}`);
    const confirmRes = JSON.parse(res.body);
    if (confirmRes.code !== 0) throw new Error(`confirm 业务错误 ${confirmRes.code}: ${confirmRes.message}`);
    log(`confirm 成功，${daily.benefitAmount}${daily.benefitUnit} 已到账 🎉`);
  } catch (e) {
    log(`签到失败：${e && e.message ? e.message : e}`);
    process.exitCode = 1;
  }
}

main().catch(e => { log(`致命错误：${e.message}`); process.exitCode = 1; });
