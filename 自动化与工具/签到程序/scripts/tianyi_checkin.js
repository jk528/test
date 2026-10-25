// ============================================================
// 天翼云盘签到脚本（独立运行）
// 平台：天翼云盘（cloud.189.cn）浏览器 Cookie → 每日签到领空间
//
// 配置：..\config\tianyi_config.json（已被 .gitignore 排除，严禁提交）
//   { "cookie": "cloud.189.cn 网页登录态 Cookie" }
//   环境变量可覆盖：TIANYI_COOKIE
//   Cookie 缺失/失效时自动从夸克浏览器重新提取（需管理员权限走 VSS 卷影）
//
// 用法: node tianyi_checkin.js [--no-delay] [--status]
//   --status    只查询登录状态（只读，不执行签到）
//   --no-delay  跳过随机延时（默认签到前等待 30~300 秒防检测）
//
// 退出码: 0=签到成功/今日已签  1=失败（无有效 Cookie/网络异常）
// 历史：账号密码登录链路已于 2026-10-25 删除——设备锁（result=-133
//       二次设备校验）使密码链路无法自动化，逆向过程见
//       文档\02-逆向中-接口攻坚\三云盘签到平移实现记录.md
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
  const cookie = (process.env.TIANYI_COOKIE || fileCfg.cookie || '').trim();
  return { cookie, cfgPath };
}

// ============================================================
// Cookie 模式签到（cloud.189.cn 网页登录态，绕过设备锁）
// 2026-10-25 验证：COOKIE_LOGIN_USER + JSESSIONID 即可调 userSign.action
// ============================================================
const TY_UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36';
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

// 提取成功则回写 tianyi_config.json
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

  // 随机延时
  if (!noDelay && !statusOnly) {
    const wait = randomDelaySec();
    log(`随机延时 ${wait} 秒防检测...`);
    await sleep(wait);
  }

  // config 无 Cookie 时先尝试从浏览器提取一次
  let cookie = cfg.cookie;
  if (!cookie) {
    log('config 中无 Cookie，尝试从夸克浏览器提取（需已登录 cloud.189.cn 网页版）...');
    cookie = extractCookieFromQuarkBrowser();
    if (cookie) saveCookieToConfig(cfg.cfgPath, cookie);
  }

  // Cookie 签到；失效自动从夸克浏览器重提取后再试一次
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

  log('错误：签到失败 - 无有效 Cookie。请用夸克浏览器登录 https://cloud.189.cn 网页版后重试');
  process.exitCode = 1;
}

// 导出供统一签到调用
module.exports = { run: main, name: '天翼云盘' };

if (require.main === module) {
  main().catch(e => {
    log(`未捕获异常：${e.message}`);
    process.exitCode = 1;
  });
}
