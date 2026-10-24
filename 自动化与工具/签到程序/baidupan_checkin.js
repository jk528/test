// ============================================================
// 百度网盘会员签到脚本（独立运行，参考 tunecc/DuPan 移植为 Node.js）
// 平台：pan.baidu.com 会员成长体系（签到 + 每日答题 + 成长值查询）
//
// 配置：同目录 baidupan_config.json（已被 .gitignore 排除，含 Cookie 严禁提交）
//   {
//     "cookie": "BDUSS=xxx; STOKEN=xxx; BAIDUID=xxx; PTOKEN=xxx; PANWEB=1; csrfToken=xxx"
//   }
//   环境变量可覆盖：BAIDUPAN_COOKIE
//
// 用法: node baidupan_checkin.js [--no-delay] [--status]
//   --status    只查询签到状态与成长值（只读，不执行签到）
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
// 平台常量（移植自 tunecc/DuPan，2026-10-25）
// ============================================================
const UA = 'Mozilla/5.0 (Linux; Android 11; Pixel 5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.91 Mobile Safari/537.36';
const HEADERS_BASE = {
  'Connection': 'keep-alive',
  'Accept': 'application/json, text/plain, */*',
  'User-Agent': UA,
  'X-Requested-With': 'XMLHttpRequest',
  'Sec-Fetch-Site': 'same-origin',
  'Sec-Fetch-Mode': 'cors',
  'Sec-Fetch-Dest': 'empty',
  'Referer': 'https://pan.baidu.com/wap/svip/growth/task',
  'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
};
const URL_SIGNIN = 'https://pan.baidu.com/rest/2.0/membership/level?app_id=250528&web=5&method=signin';
const URL_QUESTION = 'https://pan.baidu.com/act/v2/membergrowv2/getdailyquestion?app_id=250528&web=5';
const URL_ANSWER = 'https://pan.baidu.com/act/v2/membergrowv2/answerquestion';
const URL_USERINFO = 'https://pan.baidu.com/rest/2.0/membership/user?app_id=250528&web=5&method=query';

// ============================================================
// 配置加载
// ============================================================
function loadConfig() {
  const cfgPath = path.join(__dirname, 'baidupan_config.json');
  let fileCfg = {};
  if (fs.existsSync(cfgPath)) {
    try {
      const raw = fs.readFileSync(cfgPath, 'utf8').replace(/^﻿/, '');
      fileCfg = JSON.parse(raw);
    } catch (e) {
      log(`错误：baidupan_config.json 解析失败 - ${e.message}`);
      return null;
    }
  }
  const cookie = (process.env.BAIDUPAN_COOKIE || fileCfg.cookie || '').trim();
  if (!cookie) {
    log('错误：未找到百度网盘签到凭证（cookie 为空）。');
    log('请在脚本同目录创建 baidupan_config.json（已被 .gitignore 排除）：');
    log('  { "cookie": "BDUSS=xxx; STOKEN=xxx; BAIDUID=xxx; PTOKEN=xxx; PANWEB=1; csrfToken=xxx" }');
    log('获取方式：浏览器登录 pan.baidu.com，F12 复制请求头中的完整 Cookie。');
    return null;
  }
  return { cookie };
}

// ============================================================
// HTTP 请求封装
// ============================================================
async function panGet(url, cookie) {
  const res = await fetch(url, { headers: { ...HEADERS_BASE, Cookie: cookie } });
  const text = await res.text();
  return { status: res.status, text };
}

// ============================================================
// 签到 / 答题 / 用户信息
// ============================================================
async function doSignin(cookie) {
  const { status, text } = await panGet(URL_SIGNIN, cookie);
  if (status !== 200) return { ok: false, msg: `HTTP ${status}` };
  let json;
  try { json = JSON.parse(text); } catch { return { ok: false, msg: '响应非 JSON' }; }
  // errno 0 = 成功；-6 常见于 Cookie 失效；其他错误带 error_msg
  if (json.error_code !== 0 && json.error_code !== undefined && json.error_code !== null) {
    return { ok: false, msg: `error_code=${json.error_code} ${json.error_msg || ''}` };
  }
  if (json.errno !== undefined && json.errno !== 0) {
    return { ok: false, msg: `errno=${json.errno} ${json.error_msg || json.errmsg || ''}` };
  }
  const points = json.points ?? json?.data?.points;
  return { ok: true, points, raw: json };
}

async function getDailyQuestion(cookie) {
  const { status, text } = await panGet(URL_QUESTION, cookie);
  if (status !== 200) return null;
  let json;
  try { json = JSON.parse(text); } catch { return null; }
  const answer = json.answer ?? json?.data?.answer;
  const askId = json.ask_id ?? json?.data?.ask_id;
  if (answer !== undefined && askId !== undefined) return { answer, askId };
  return null;
}

async function answerQuestion(cookie, answer, askId) {
  const url = `${URL_ANSWER}?app_id=250528&web=5&ask_id=${askId}&answer=${answer}`;
  const { status, text } = await panGet(url, cookie);
  if (status !== 200) return { ok: false, msg: `HTTP ${status}` };
  let json;
  try { json = JSON.parse(text); } catch { return { ok: false, msg: '响应非 JSON' }; }
  const score = json.score ?? json?.data?.score;
  const showMsg = json.show_msg ?? json?.data?.show_msg ?? '';
  if (score !== undefined) return { ok: true, score, showMsg };
  return { ok: false, msg: showMsg || JSON.stringify(json).slice(0, 100) };
}

async function getUserInfo(cookie) {
  const { status, text } = await panGet(URL_USERINFO, cookie);
  if (status !== 200) return null;
  let json;
  try { json = JSON.parse(text); } catch { return null; }
  // 会员等级/成长值嵌套层级较深的兼容查找
  function deepFind(obj, key) {
    if (!obj || typeof obj !== 'object') return undefined;
    if (obj[key] !== undefined) return obj[key];
    for (const v of Object.values(obj)) {
      const r = deepFind(v, key);
      if (r !== undefined) return r;
    }
    return undefined;
  }
  const currentValue = json.current_value ?? deepFind(json, 'current_value');
  const currentLevel = json.current_level ?? deepFind(json, 'current_level');
  const productType = json?.current_product?.product_type || json?.current_product_v2?.product_type || '';
  if (currentValue !== undefined || currentLevel !== undefined || productType) {
    return { currentValue, currentLevel, productType };
  }
  return null;
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

  logSection('百度网盘签到');

  if (statusOnly) {
    const info = await getUserInfo(cfg.cookie);
    if (info) {
      log(`当前会员等级: ${info.currentLevel ?? '未知'}，成长值: ${info.currentValue ?? '未知'}`);
      process.exitCode = 0;
    } else {
      log('状态查询失败（Cookie 可能已失效）');
      process.exitCode = 1;
    }
    return;
  }

  // 随机延时
  if (!noDelay) {
    const wait = randomDelaySec();
    log(`随机延时 ${wait} 秒防检测...`);
    await sleep(wait);
  }

  // 1. 签到
  const sign = await doSignin(cfg.cookie);
  if (!sign.ok) {
    log(`签到失败：${sign.msg}`);
    process.exitCode = 1;
    return;
  }
  log(`签到成功，获得积分: ${sign.points ?? '未返回'}`);

  // 2. 每日答题
  const q = await getDailyQuestion(cfg.cookie);
  if (q) {
    log(`获取到每日问题 ask_id=${q.askId}，尝试答题...`);
    const ans = await answerQuestion(cfg.cookie, q.answer, q.askId);
    if (ans.ok) {
      log(`答题成功，获得积分: ${ans.score}${ans.showMsg ? `（${ans.showMsg}）` : ''}`);
    } else {
      log(`答题未成功：${ans.msg}`);
    }
  } else {
    log('今日无答题或已答完');
  }

  // 3. 查询成长值
  const info = await getUserInfo(cfg.cookie);
  if (info) {
    log(`当前会员等级: ${info.currentLevel ?? '未知'}，成长值: ${info.currentValue ?? '未知'}`);
  }

  process.exitCode = 0;
}

// 导出供统一签到调用
module.exports = { run: main, name: '百度网盘' };

if (require.main === module) {
  main().catch(e => {
    log(`未捕获异常：${e.message}`);
    process.exitCode = 1;
  });
}
