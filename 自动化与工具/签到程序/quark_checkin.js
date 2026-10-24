// ============================================================
// 夸克网盘签到脚本（独立运行，参考 Cp0204/quark-auto-save 移植为 Node.js）
// 平台：夸克网盘（drive-m.quark.cn）成长值签到领空间
//
// 配置：同目录 quark_config.json（已被 .gitignore 排除，含 Cookie 严禁提交）
//   {
//     "cookie": "完整 Cookie 串（含 kps/sign/vcode 字段）",
//     "kps":   "可选：客户端抓包获取的 kps",
//     "sign":  "可选：客户端抓包获取的 sign",
//     "vcode": "可选：客户端抓包获取的 vcode"
//   }
//   环境变量可覆盖：QUARK_COOKIE / QUARK_KPS / QUARK_SIGN / QUARK_VCODE
//
// 凭证获取（二选一）：
//   1. 手机 APP 或 PC 客户端抓包，从 https://drive-m.quark.cn/1/clouddrive/capacity/growth/info
//      请求中提取 query 参数 kps/sign/vcode，并复制完整 Cookie；
//   2. 夸克网盘 PC 客户端登录后，运行同目录 extract_quark_cookies.js 提取 Cookie，
//      若提取结果包含 kps/sign/vcode 则可直接使用（客户端版本决定）。
//
// 用法: node quark_checkin.js [--no-delay] [--status]
//   --status    只查询签到状态（只读，不执行签到）
//   --no-delay  跳过随机延时（默认签到前等待 30~300 秒防检测）
//
// 退出码: 0=签到成功/今日已签/状态查询成功  1=失败（凭证缺失/失效/网络异常）
// ============================================================
'use strict';
const fs = require('fs');
const path = require('path');

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
// 平台常量（参考 quark-auto-save，2026-10-25）
// ============================================================
const UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) quark-cloud-drive/3.14.2 Chrome/112.0.5615.165 Electron/24.1.3.8 Safari/537.36 Channel/pckk_other_ch';
const BASE_PC = 'https://drive-pc.quark.cn';
const BASE_M = 'https://drive-m.quark.cn';
const URL_ACCOUNT = 'https://pan.quark.cn/account/info';
const URL_GROWTH_INFO = `${BASE_M}/1/clouddrive/capacity/growth/info`;
const URL_GROWTH_SIGN = `${BASE_M}/1/clouddrive/capacity/growth/sign`;

const VIP_MAP = {
  '0': '普通用户',
  '1': '会员',
  '2': '超级会员',
};

// ============================================================
// 配置加载
// ============================================================
function loadConfig() {
  const cfgPath = path.join(__dirname, 'quark_config.json');
  let fileCfg = {};
  if (fs.existsSync(cfgPath)) {
    try {
      const raw = fs.readFileSync(cfgPath, 'utf8').replace(/^﻿/, '');
      fileCfg = JSON.parse(raw);
    } catch (e) {
      log(`错误：quark_config.json 解析失败 - ${e.message}`);
      return null;
    }
  }
  const cfg = {
    cookie: (process.env.QUARK_COOKIE || fileCfg.cookie || '').trim(),
    kps: (process.env.QUARK_KPS || fileCfg.kps || '').trim(),
    sign: (process.env.QUARK_SIGN || fileCfg.sign || '').trim(),
    vcode: (process.env.QUARK_VCODE || fileCfg.vcode || '').trim(),
  };
  // 从 cookie 中自动提取 kps/sign/vcode（若单独字段未填）
  if (!cfg.kps || !cfg.sign || !cfg.vcode) {
    const m = cfg.cookie.match(/kps=([a-zA-Z0-9%+/=]+)/);
    const s = cfg.cookie.match(/sign=([a-zA-Z0-9%+/=]+)/);
    const v = cfg.cookie.match(/vcode=([a-zA-Z0-9%+/=]+)/);
    if (m && !cfg.kps) cfg.kps = m[1];
    if (s && !cfg.sign) cfg.sign = s[1];
    if (v && !cfg.vcode) cfg.vcode = v[1];
  }
  if (!cfg.cookie) {
    log('错误：未找到夸克网盘凭证（cookie 为空）。');
    log('请在脚本同目录创建 quark_config.json（已被 .gitignore 排除）：');
    log('  { "cookie": "完整Cookie串", "kps": "...", "sign": "...", "vcode": "..." }');
    return null;
  }
  return cfg;
}

// ============================================================
// HTTP 请求封装
// ============================================================
async function quarkGet(url, params, cfg) {
  const qs = new URLSearchParams({
    pr: 'ucpro',
    fr: 'android',
    kps: cfg.kps,
    sign: cfg.sign,
    vcode: cfg.vcode,
    ...params,
  }).toString();
  const res = await fetch(`${url}?${qs}`, {
    headers: {
      'Cookie': cfg.cookie,
      'Content-Type': 'application/json',
      'User-Agent': UA,
    },
  });
  return res.json();
}

async function quarkPost(url, params, body, cfg) {
  const qs = new URLSearchParams({
    pr: 'ucpro',
    fr: 'android',
    kps: cfg.kps,
    sign: cfg.sign,
    vcode: cfg.vcode,
    ...params,
  }).toString();
  const res = await fetch(`${url}?${qs}`, {
    method: 'POST',
    headers: {
      'Cookie': cfg.cookie,
      'Content-Type': 'application/json',
      'User-Agent': UA,
    },
    body: JSON.stringify(body),
  });
  return res.json();
}

// ============================================================
// 账号 / 成长值 / 签到
// ============================================================
async function getAccountInfo(cfg) {
  const qs = new URLSearchParams({ fr: 'pc', platform: 'pc' }).toString();
  const res = await fetch(`${URL_ACCOUNT}?${qs}`, {
    headers: { 'Cookie': cfg.cookie, 'User-Agent': UA },
  });
  const json = await res.json();
  return json?.data || null;
}

async function getGrowthInfo(cfg) {
  const json = await quarkGet(URL_GROWTH_INFO, {}, cfg);
  return json?.data || null;
}

async function doGrowthSign(cfg) {
  const json = await quarkPost(URL_GROWTH_SIGN, {}, { sign_cyclic: true }, cfg);
  if (json?.data?.sign_daily_reward !== undefined) {
    return { ok: true, reward: json.data.sign_daily_reward };
  }
  return { ok: false, msg: json?.message || JSON.stringify(json).slice(0, 120) };
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

  logSection('夸克网盘签到');

  // 账号验证
  const account = await getAccountInfo(cfg);
  if (!account) {
    log('账号信息查询失败：Cookie 可能已失效');
    process.exitCode = 1;
    return;
  }
  log(`账号：${account.nickname || '未知'}（${account.member_type === '2' ? '超级会员' : account.member_type === '1' ? '会员' : '普通用户'}）`);

  // 随机延时
  if (!noDelay && !statusOnly) {
    const wait = randomDelaySec();
    log(`随机延时 ${wait} 秒防检测...`);
    await sleep(wait);
  }

  // 查询成长状态
  const growth = await getGrowthInfo(cfg);
  if (!growth) {
    log('成长值信息查询失败（kps/sign/vcode 可能缺失或已失效）');
    log('提示：需从夸克网盘 APP/PC 客户端抓包获取 kps/sign/vcode');
    process.exitCode = 1;
    return;
  }

  const totalGB = (growth.total_capacity / 1024 / 1024 / 1024).toFixed(2);
  const signMB = Math.floor((growth.cap_composition?.sign_reward || 0) / 1024 / 1024);
  log(`总空间：${totalGB}GB，签到累计获得：${signMB}MB`);

  if (statusOnly) {
    if (growth.cap_sign?.sign_daily) {
      log(`今日已签到，连签进度 ${growth.cap_sign.sign_progress}/${growth.cap_sign.sign_target}`);
    } else {
      log(`今日未签到，连签进度 ${growth.cap_sign?.sign_progress ?? 0}/${growth.cap_sign?.sign_target ?? 7}`);
    }
    process.exitCode = 0;
    return;
  }

  // 执行签到
  if (growth.cap_sign?.sign_daily) {
    log(`今日已签到 +${Math.floor((growth.cap_sign.sign_daily_reward || 0) / 1024 / 1024)}MB，连签进度(${growth.cap_sign.sign_progress}/${growth.cap_sign.sign_target})`);
    process.exitCode = 0;
    return;
  }

  const sign = await doGrowthSign(cfg);
  if (sign.ok) {
    const rewardMB = Math.floor((sign.reward || 0) / 1024 / 1024);
    log(`签到成功 +${rewardMB}MB，连签进度(${growth.cap_sign?.sign_progress ?? 0 + 1}/${growth.cap_sign?.sign_target ?? 7})`);
    process.exitCode = 0;
  } else {
    log(`签到失败：${sign.msg}`);
    process.exitCode = 1;
  }
}

// 导出供统一签到调用
module.exports = { run: main, name: '夸克网盘' };

if (require.main === module) {
  main().catch(e => {
    log(`未捕获异常：${e.message}`);
    process.exitCode = 1;
  });
}
