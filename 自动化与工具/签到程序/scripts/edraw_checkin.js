// ============================================================
// 万兴脑图（MindMaster）独立签到脚本（网页版会话直连版）
// 平台：userapi.edrawsoft.cn（APP 与网页版共用后端）
// 逆向记录：DEX 字符串提取自 MindMaster_7.10.24.apk（2026-10-25）
//
// 接口（实测验证）：
//   POST /api/user/{uid}/clockin       签到（响应 msg=="already check in" 为已签）
//   GET  /api/user/{uid}/clockin/list  本周 7 天签到状态（[1,1,1,1,1,1,1]）
//   GET  /api/user/{uid}/point         当前积分
//
// 凭证：EDCurrent Cookie（夸克浏览器登录 mm.edrawsoft.cn 产生）
//   值为 URL 编码 JSON：{"user_id":"...","token":"eyJ..."(JWT,2小时有效)}
//   因 token 短寿，本脚本【每次运行现从浏览器提取】，无配置文件、零维护：
//   只要浏览器里 mm.edrawsoft.cn 保持登录即永久可用。
//   提取链路：VSS 卷影绕过 Cookie 库独占 -> DPAPI 解 Local State 主密钥
//             -> AES-256-GCM 解 v10 密文 -> 剥除 SHA256(host_key) 前缀
//
// 用法: node edraw_checkin.js [--no-delay] [--status]
//   --status    只查询签到状态（只读，不执行签到）
//   --no-delay  跳过随机延时（默认签到前等待 30~300 秒防检测）
//
// 退出码: 0=签到成功/今日已签/状态查询成功  1=失败（未登录/网络异常）
// 注意: VSS 提取需管理员权限（计划任务已配 Highest）
// ============================================================
'use strict';
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { execFileSync, execSync } = require('child_process');
const { DatabaseSync } = require('node:sqlite');

// ============================================================
// 公共工具（与 checkin_all.js 同风格）
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

function randomDelaySec() {
  return 30 + Math.floor(Math.random() * 271);
}

// ============================================================
// 浏览器凭证提取（VSS + DPAPI + AES-GCM，与天翼/百度同链路）
// ============================================================
const BROWSER_UD = path.join(process.env.LOCALAPPDATA || '', 'Quark', 'User Data');
const COOKIE_NAME = 'EDCurrent';
const COOKIE_DOMAIN = 'mm.edrawsoft.cn';

function dpapiUnprotect(buf) {
  const payload = Buffer.from(buf).toString('base64');
  const ps = [
    "Add-Type -AssemblyName System.Security;",
    `$src=[Convert]::FromBase64String('${payload}');`,
    "$k=[Security.Cryptography.ProtectedData]::Unprotect($src,$null,'CurrentUser');",
    "[Convert]::ToBase64String($k)"
  ].join('');
  const out = execFileSync('powershell.exe',
    ['-NoProfile', '-NonInteractive', '-Command', ps],
    { encoding: 'utf8' }).trim();
  return Buffer.from(out, 'base64');
}

// VSS 卷影复制被运行中浏览器独占的 Cookies 库（需管理员）
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
  // WAL/SHM 附属文件一并拷贝（浏览器写入未落库时数据在 WAL 里）
  for (const ext of ['-wal', '-shm']) {
    try { fs.copyFileSync(path.join(link, rel + ext), dstFile + ext); } catch { /* 可缺省 */ }
  }
  try { execSync(`vssadmin delete shadows /for=${vol} /oldest /quiet`, { stdio: 'pipe' }); } catch { /* 清理失败无碍 */ }
  return dstFile;
}

// 从 Cookies 库解密 EDCurrent，返回 { user_id, token }
function extractEDCurrent() {
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
  const row = db.prepare("SELECT host_key, encrypted_value FROM cookies WHERE name=? AND host_key LIKE ?").get(COOKIE_NAME, `%${COOKIE_DOMAIN}%`);
  db.close();
  if (!row) throw new Error(`浏览器中未找到 ${COOKIE_DOMAIN} 的 ${COOKIE_NAME}，请先在浏览器登录 https://mm.edrawsoft.cn/app`);

  const b = Buffer.from(row.encrypted_value);
  if (b.slice(0, 3).toString() !== 'v10') throw new Error('EDCurrent 密文前缀非 v10');
  const d = crypto.createDecipheriv('aes-256-gcm', masterKey, b.slice(3, 15));
  d.setAuthTag(b.slice(-16));
  let dec = Buffer.concat([d.update(b.slice(15, -16)), d.final()]);
  // 新版 Chromium 明文前附 SHA256(host_key) 32 字节，剥除
  const sha = crypto.createHash('sha256').update(row.host_key).digest();
  if (dec.length > 32 && dec.slice(0, 32).equals(sha)) dec = dec.slice(32);

  const ed = JSON.parse(decodeURIComponent(dec.toString('utf8')));
  if (!ed.user_id || !ed.token) throw new Error('EDCurrent 结构异常（缺 user_id/token），请重新登录网页版');
  return { userId: String(ed.user_id), token: ed.token };
}

// ============================================================
// API 封装
// ============================================================
const API = 'https://userapi.edrawsoft.cn';
const UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Quark/4.5.5.275 Chrome/112.0.0.0 Safari/537.36';

async function apiRequest(auth, method, apiPath) {
  const res = await fetch(`${API}${apiPath}?lang=cn`, {
    method,
    headers: {
      'Authorization': `Bearer ${auth.token}`,
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

async function edrawStatus(auth) {
  const list = await apiRequest(auth, 'GET', `/api/user/${auth.userId}/clockin/list`);
  const point = await apiRequest(auth, 'GET', `/api/user/${auth.userId}/point`);
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

async function edrawSign(auth) {
  const { status, json } = await apiRequest(auth, 'POST', `/api/user/${auth.userId}/clockin`);
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

  // 1) 从浏览器提取凭证（每次现提，token 仅 2 小时有效）
  let auth;
  try {
    auth = extractEDCurrent();
    log(`凭证提取成功：user_id=${auth.userId}`);
  } catch (e) {
    log(`错误：凭证提取失败 - ${e.message}`);
    log('处理：在夸克浏览器打开 https://mm.edrawsoft.cn/app 并登录万兴账号后重试');
    process.exitCode = 1;
    return;
  }

  // 2) 查状态
  let st;
  try {
    st = await edrawStatus(auth);
  } catch (e) {
    log(`错误：状态查询失败 - ${e.message}（token 可能已过期，请在浏览器刷新 mm.edrawsoft.cn 页面后重试）`);
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

  // 3) 签到
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
    const r = await edrawSign(auth);
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
    // 签到后复查
    const st2 = await edrawStatus(auth);
    if (st2.ok) log(`复查：本周 ${st2.week.map(x => x ? '[√]' : '[×]').join('')}　积分：${st2.point}`);
  } catch (e) {
    log(`错误：签到请求异常 - ${e.message}`);
    process.exitCode = 1;
  }
}

main().catch(e => { log(`致命错误：${e.message}`); process.exitCode = 1; });
