// ============================================================
// 天翼云盘签到脚本（独立运行，参考 vistal8/tianyiyun 移植为 Node.js）
// 平台：天翼云盘（cloud.189.cn）账号密码登录 → 每日签到领空间
//
// 配置：同目录 tianyi_config.json（已被 .gitignore 排除，含账号密码严禁提交）
//   {
//     "username": "手机号",
//     "password": "登录密码"
//   }
//   环境变量可覆盖：TIANYI_USERNAME / TIANYI_PASSWORD
//
// 用法: node tianyi_checkin.js [--no-delay] [--status]
//   --status    只查询登录状态（只读，不执行签到）
//   --no-delay  跳过随机延时（默认签到前等待 30~300 秒防检测）
//
// 退出码: 0=签到成功/今日已签  1=失败（凭证缺失/登录失败/网络异常）
// 注意：出现图形验证码属风控，需网页端手动登录解除后再运行
// ============================================================
'use strict';
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { execFileSync, execSync } = require('child_process');

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
// 天翼登录常量与工具
// ============================================================
const BI_RM = '0123456789abcdefghijklmnopqrstuvwxyz'.split('');
const B64MAP = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';

function int2char(a) { return BI_RM[a]; }

// 移植自 Python 版：Base64 字符串 → 自定义 hex 串（RSA 输出编码用）
function b64tohex(a) {
  let d = '';
  let e = 0;
  let c = 0;
  for (let i = 0; i < a.length; i++) {
    if (a[i] === '=') continue;
    const v = B64MAP.indexOf(a[i]);
    if (0 === e) {
      e = 1;
      d += int2char(v >> 2);
      c = 3 & v;
    } else if (1 === e) {
      e = 2;
      d += int2char(c << 2 | v >> 4);
      c = 15 & v;
    } else if (2 === e) {
      e = 3;
      d += int2char(c);
      d += int2char(v >> 2);
      c = 3 & v;
    } else {
      e = 0;
      d += int2char(c << 2 | v >> 4);
      d += int2char(15 & v);
    }
  }
  if (e === 1) d += int2char(c << 2);
  return d;
}

// RSA 加密（PC 链路：encryptConf.do 公钥，hex 输出，前缀由服务端 pre 字段指定）
function rsaEncryptHex(pubKey, text) {
  const pem = `-----BEGIN PUBLIC KEY-----\n${pubKey}\n-----END PUBLIC KEY-----`;
  return crypto.publicEncrypt(
    { key: pem, padding: crypto.constants.RSA_PKCS1_PADDING },
    Buffer.from(text, 'utf8')
  ).toString('hex');
}

// ============================================================
// 配置加载
// ============================================================
function loadConfig() {
  const cfgPath = path.join(__dirname, '..', 'config', 'tianyi_config.json');
  let fileCfg = {};
  if (fs.existsSync(cfgPath)) {
    try {
      const raw = fs.readFileSync(cfgPath, 'utf8').replace(/^﻿/, '');
      fileCfg = JSON.parse(raw);
    } catch (e) {
      log(`错误：tianyi_config.json 解析失败 - ${e.message}`);
      return null;
    }
  }
  const username = (process.env.TIANYI_USERNAME || fileCfg.username || '').trim();
  const password = (process.env.TIANYI_PASSWORD || fileCfg.password || '').trim();
  const cookie = (process.env.TIANYI_COOKIE || fileCfg.cookie || '').trim();
  if (!username && !cookie) {
    log('错误：未找到天翼云盘凭证。');
    log('请在脚本同目录创建 tianyi_config.json（已被 .gitignore 排除）：');
    log('  { "cookie": "浏览器Cookie（优先）", "username": "手机号", "password": "密码（兜底）" }');
    return null;
  }
  return { username, password, cookie, cfgPath };
}

// ============================================================
// 带 Cookie 的 HTTP 会话
// ============================================================
class Session {
  constructor() {
    this.cookies = new Map();
    this.headers = {};
  }
  setCookie(cookieStr, url) {
    if (!cookieStr) return;
    const host = new URL(url).hostname;
    for (const part of cookieStr.split(/;(?=\s*[^=]+=[^;]+)/)) {
      const [kv, ...attrs] = part.split(';');
      const [name, ...valParts] = kv.split('=');
      const value = valParts.join('=');
      if (!name || value === undefined) continue;
      // 简单按域名存取（忽略 path/expires，脚本场景够用）
      this.cookies.set(name.trim(), value.trim());
    }
  }
  getCookieHeader() {
    return [...this.cookies.entries()].map(([k, v]) => `${k}=${v}`).join('; ');
  }
  async request(method, url, options = {}) {
    const headers = { ...this.headers, ...(options.headers || {}) };
    const cookie = this.getCookieHeader();
    if (cookie) headers.Cookie = cookie;
    const res = await fetch(url, { method, headers, body: options.body, redirect: 'manual' });
    const setCookies = res.headers.getSetCookie ? res.headers.getSetCookie() : [];
    for (const sc of setCookies) this.setCookie(sc, url);
    // 处理重定向（保留 cookie）
    if ([301, 302, 303, 307, 308].includes(res.status)) {
      const loc = res.headers.get('location');
      if (loc) {
        const next = new URL(loc, url).href;
        return this.request(method === 'POST' && [301, 302, 303].includes(res.status) ? 'GET' : method, next, options);
      }
    }
    return res;
  }
  async get(url, headers = {}) { return this.request('GET', url, { headers }); }
  async post(url, body, headers = {}) { return this.request('POST', url, { headers, body }); }
}

// ============================================================
// 登录流程（PC 链路，参考 cloud189-sdk / Cloud189Checkin）
//   1. encryptConf.do 取 RSA 公钥与前缀
//   2. unifyLoginForPC.action 取 captchaToken/lt/paramId/reqId
//   3. loginSubmit.do 提交（带 lt + REQID 头）
//   4. 跟随 toUrl 建立会话
// ============================================================
const TY_APP_ID = '8025431004';
const TY_CLIENT_TYPE = '10020';
const TY_RETURN_URL = 'https://m.cloud.189.cn/zhuanti/2020/loginErrorPc/index.html';
const TY_UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36';

async function tianyiLogin(username, password) {
  log('正在执行登录流程...');
  const s = new Session();
  s.headers['User-Agent'] = TY_UA;

  // 1) 取 RSA 公钥与前缀
  const rEnc = await s.post('https://open.e.189.cn/api/logbox/config/encryptConf.do', '', {
    'Accept': 'application/json;charset=UTF-8',
  });
  const encJson = await rEnc.json();
  const pubKey = encJson?.data?.pubKey;
  const pre = encJson?.data?.pre || '';
  if (!pubKey) { log(`错误：获取加密配置失败 - ${JSON.stringify(encJson).slice(0, 200)}`); return null; }

  // 2) 取登录表单参数
  const formUrl = `https://cloud.189.cn/api/portal/unifyLoginForPC.action?appId=${TY_APP_ID}&clientType=${TY_CLIENT_TYPE}&returnURL=${encodeURIComponent(TY_RETURN_URL)}&timeStamp=${Date.now()}`;
  const rForm = await s.get(formUrl, { 'Accept': 'text/html' });
  const html = await rForm.text();
  const captchaToken = (html.match(/'captchaToken' value='(.+?)'/) || [])[1];
  const lt = (html.match(/lt = "(.+?)"/) || [])[1];
  const paramId = (html.match(/paramId = "(.+?)"/) || [])[1];
  const reqId = (html.match(/reqId = "(.+?)"/) || [])[1];
  if (!lt || !paramId || !reqId) { log('错误：登录表单参数提取失败（captchaToken/lt/paramId/reqId）'); return null; }

  // 3) 提交登录
  const form = new URLSearchParams({
    appKey: TY_APP_ID,
    accountType: '02',
    validateCode: '',
    captchaToken: captchaToken || '',
    dynamicCheck: 'FALSE',
    clientType: '1',
    cb_SaveName: '3',
    isOauth2: 'false',
    returnUrl: TY_RETURN_URL,
    paramId,
    userName: `${pre}${rsaEncryptHex(pubKey, username)}`,
    password: `${pre}${rsaEncryptHex(pubKey, password)}`,
  }).toString();
  const r5 = await s.post('https://open.e.189.cn/api/logbox/oauth2/loginSubmit.do', form, {
    'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
    'Referer': 'https://open.e.189.cn/',
    'lt': lt,
    'REQID': reqId,
  });
  const result = await r5.json();
  if (String(result.result) !== '0') {
    log(`登录错误：${result.msg || '未知错误'}`);
    log(`完整响应：${JSON.stringify(result).slice(0, 400)}`);
    if ((result.msg || '').includes('验证码')) log('提示：出现图形验证码属风控，请网页端登录解除后再试');
    return null;
  }
  if (!result.toUrl) { log('错误：登录响应缺少 toUrl'); return null; }

  // 4) 跟随 toUrl 建立会话（写 SSON 等 cookie）
  await s.get(result.toUrl);
  log('登录成功');
  return s;
}

// ============================================================
// 签到
// ============================================================
async function tianyiSignin(session) {
  const rand = Date.now();
  const signUrl = `https://api.cloud.189.cn/mkt/userSign.action?rand=${rand}&clientType=TELEANDROID&version=8.6.3&model=SM-G930K`;
  const headers = {
    'User-Agent': 'Mozilla/5.0 (Linux; Android 5.1.1; SM-G930K Build/NRD90M; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/74.0.3729.136 Mobile Safari/537.36 Ecloud/8.6.3 Android/22 clientId/355325117317828 clientModel/SM-G930K imsi/460071114317824 clientChannelId/qq proVersion/1.0.6',
    'Referer': 'https://m.cloud.189.cn/zhuanti/2016/sign/index.jsp?albumBackupOpened=1',
    'Host': 'm.cloud.189.cn',
  };
  const res = await session.get(signUrl, headers);
  const json = await res.json();
  return json;
}

// ============================================================
// Cookie 模式签到（cloud.189.cn 网页登录态，绕过设备锁）
// 2026-10-25 验证：COOKIE_LOGIN_USER + JSESSIONID 即可调 userSign.action
// ============================================================
const TY_SIGN_HEADERS = {
  'User-Agent': TY_UA,
  'Referer': 'https://cloud.189.cn/web/portal.html',
  'Accept': 'application/json;charset=UTF-8',
};

// 返回 { ok, isSign, netdiskBonus, invalid }；invalid=true 表示 Cookie 已失效
async function signinWithCookie(cookie) {
  try {
    const signUrl = `https://cloud.189.cn/mkt/userSign.action?rand=${Date.now()}&clientType=TELEANDROID&version=8.6.3&model=SM-G930K`;
    const res = await fetch(signUrl, { headers: { ...TY_SIGN_HEADERS, Cookie: cookie } });
    const text = await res.text();
    let json;
    try { json = JSON.parse(text); } catch { return { ok: false, invalid: true }; }
    if (json && (json.isSign !== undefined || json.netdiskBonus !== undefined)) {
      return {
        ok: true,
        isSign: json.isSign === true || json.isSign === 'true',
        netdiskBonus: json.netdiskBonus,
        signTime: json.signTime,
      };
    }
    return { ok: false, invalid: true, raw: text.slice(0, 200) };
  } catch (e) {
    return { ok: false, invalid: false, error: e.message };
  }
}

// ============================================================
// 从夸克浏览器自动提取 cloud.189.cn Cookie（VSS 卷影 + DPAPI + AES-GCM）
// 浏览器需已登录 cloud.189.cn 网页版；Cookie 库被占用时走卷影副本
// ============================================================
function dpapiUnprotect(buf) {
  const payload = buf.toString('base64');
  const ps = [
    'Add-Type -AssemblyName System.Security;',
    `$src=[Convert]::FromBase64String('${payload}');`,
    '$k=[Security.Cryptography.ProtectedData]::Unprotect($src,$null,\'CurrentUser\');',
    '[Convert]::ToBase64String($k)',
  ].join('');
  const out = execFileSync('powershell.exe', ['-NoProfile', '-NonInteractive', '-Command', ps], { encoding: 'utf8' }).trim();
  return Buffer.from(out, 'base64');
}

function aesGcmDecryptV10(buf, key) {
  const nonce = buf.slice(3, 15);
  const tag = buf.slice(buf.length - 16);
  const ct = buf.slice(15, buf.length - 16);
  const d = crypto.createDecipheriv('aes-256-gcm', key, nonce);
  d.setAuthTag(tag);
  return Buffer.concat([d.update(ct), d.final()]);
}

function extractCookieFromQuarkBrowser() {
  const userData = path.join(process.env.LOCALAPPDATA, 'Quark', 'User Data');
  const cookiesSrc = path.join(userData, 'Default', 'Network', 'Cookies');
  const localStatePath = path.join(userData, 'Local State');
  if (!fs.existsSync(localStatePath)) { log('未找到夸克浏览器 Local State'); return ''; }

  const tmpDir = path.join(process.env.TEMP, `ty_cookie_${Date.now()}`);
  fs.mkdirSync(tmpDir, { recursive: true });
  let sid = null;
  const link = path.join(process.env.TEMP, `ty_vss_${Date.now()}`);
  try {
    // Cookie 库被运行中的浏览器独占，先拷；失败则走 VSS 卷影
    const dstDb = path.join(tmpDir, 'Cookies');
    try {
      fs.copyFileSync(cookiesSrc, dstDb);
    } catch {
      const shadowOut = execSync('vssadmin create shadow /for=C:', { encoding: 'utf8' });
      sid = shadowOut.match(/Shadow Copy ID: (\{[^}]+\})/)?.[1];
      const dev = shadowOut.match(/Shadow Copy Volume Name: (\S+)/)?.[1];
      if (!dev) throw new Error('卷影创建失败');
      execSync(`cmd.exe /c mklink /d "${link}" "${dev}\\"`, { stdio: 'pipe' });
      const driveLetter = cookiesSrc.slice(0, 2); // 如 C:
      const relInShadow = cookiesSrc.slice(2);    // 去盘符
      fs.copyFileSync(path.join(link + relInShadow), dstDb);
      fs.copyFileSync(path.join(link, localStatePath.slice(2)), path.join(tmpDir, 'Local State'));
    }
    const lsPath = fs.existsSync(path.join(tmpDir, 'Local State')) ? path.join(tmpDir, 'Local State') : localStatePath;
    const ls = JSON.parse(fs.readFileSync(lsPath, 'utf8'));
    const masterKey = dpapiUnprotect(Buffer.from(ls.os_crypt.encrypted_key, 'base64').slice(5));

    const { DatabaseSync } = require('node:sqlite');
    const db = new DatabaseSync(dstDb, { readOnly: true });
    const rows = db.prepare("SELECT host_key, name, encrypted_value FROM cookies WHERE host_key LIKE '%cloud.189.cn%'").all();
    const parts = [];
    for (const r of rows) {
      const b = Buffer.from(r.encrypted_value);
      if (b.length < 3 || b.slice(0, 3).toString() !== 'v10') continue;
      let dec = aesGcmDecryptV10(b, masterKey);
      // 新版 Chromium 明文前 32 字节为 SHA256(host_key)，剥除
      const sha = crypto.createHash('sha256').update(r.host_key).digest();
      if (dec.length > 32 && dec.slice(0, 32).equals(sha)) dec = dec.slice(32);
      parts.push(`${r.name}=${dec.toString('utf8')}`);
    }
    db.close();
    const cookie = parts.join('; ');
    if (!cookie.includes('COOKIE_LOGIN_USER')) { log('浏览器提取的 Cookie 缺少 COOKIE_LOGIN_USER（浏览器可能未登录天翼云盘网页版）'); return ''; }
    return cookie;
  } catch (e) {
    log(`浏览器 Cookie 提取失败：${e.message}`);
    return '';
  } finally {
    if (sid) { try { execSync(`vssadmin delete shadows /shadow="${sid}" /quiet`, { stdio: 'pipe' }); } catch {} }
    try { execSync(`cmd.exe /c rd "${link}"`, { stdio: 'pipe' }); } catch {}
    try { fs.rmSync(tmpDir, { recursive: true, force: true }); } catch {}
  }
}

// 提取成功则回写 tianyi_config.json（保留账号密码字段）
function saveCookieToConfig(cfgPath, cookie) {
  try {
    let cfg = {};
    if (fs.existsSync(cfgPath)) {
      cfg = JSON.parse(fs.readFileSync(cfgPath, 'utf8').replace(/^﻿/, ''));
    }
    cfg.cookie = cookie;
    fs.writeFileSync(cfgPath, JSON.stringify(cfg, null, 2), 'utf8');
    log('已将新 Cookie 回写 tianyi_config.json');
  } catch (e) {
    log(`Cookie 回写失败（不影响本次签到）：${e.message}`);
  }
}

// ============================================================
// 主流程
// ============================================================
async function main() {
  const argv = process.argv.slice(2);
  const noDelay = argv.includes('--no-delay');
  const statusOnly = argv.includes('--status');

  const cfg = loadConfig();
  if (!cfg) { process.exitCode = 1; return; }

  logSection('天翼云盘签到');
  if (cfg.username) log(`账号：${cfg.username.slice(0, 3)}****${cfg.username.slice(-4)}`);

  // 随机延时
  if (!noDelay && !statusOnly) {
    const wait = randomDelaySec();
    log(`随机延时 ${wait} 秒防检测...`);
    await sleep(wait);
  }

  // ---- 模式一：Cookie 签到（优先，绕过设备锁）----
  let cookie = cfg.cookie;
  for (let attempt = 0; attempt < 2; attempt++) {
    if (!cookie) break;
    const r = await signinWithCookie(cookie);
    if (r.ok) {
      if (statusOnly) {
        log(`Cookie 登录态有效（最近签到：${r.signTime || '未知'}）`);
      } else if (r.isSign) {
        log(`今日已签到，累计空间奖励 +${r.netdiskBonus ?? '?'}M`);
      } else {
        log(`签到成功，获得空间: +${r.netdiskBonus ?? '?'}M`);
      }
      process.exitCode = 0;
      return;
    }
    if (r.error) { log(`签到请求异常：${r.error}`); break; }
    // Cookie 失效 → 自动从浏览器重新提取后再试一次
    log('Cookie 已失效，尝试从夸克浏览器自动提取新 Cookie...');
    cookie = extractCookieFromQuarkBrowser();
    if (cookie) {
      saveCookieToConfig(cfg.cfgPath, cookie);
      continue;
    }
    break;
  }

  // ---- 模式二：账号密码登录（兜底，可能触发设备锁二次校验）----
  if (!cfg.username || !cfg.password) {
    log('错误：Cookie 不可用且未配置账号密码兜底');
    process.exitCode = 1;
    return;
  }
  const session = await tianyiLogin(cfg.username, cfg.password);
  if (!session) { process.exitCode = 1; return; }

  if (statusOnly) {
    log('登录状态正常（--status 模式不执行签到）');
    process.exitCode = 0;
    return;
  }

  const result = await tianyiSignin(session);
  if (result.isSign === 'false' || result.isSign === false) {
    log(`签到成功，获得空间: +${result.netdiskBonus ?? '?'}M`);
  } else {
    log(`今日已签到，本次返回: +${result.netdiskBonus ?? '?'}M`);
  }
  process.exitCode = 0;
}

// 导出供统一签到调用
module.exports = { run: main, name: '天翼云盘' };

if (require.main === module) {
  main().catch(e => {
    log(`未捕获异常：${e.message}`);
    process.exitCode = 1;
  });
}
