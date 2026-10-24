// ============================================================
// 库库AI（KukuAI / 酷酷客户端 / GenFlowPro）独立签到脚本（API 直连版）
// 平台：百度 kuku.baidu.com 活动平台（/act/v2/kukuai30/）
// 逆向记录：文档/库库AI签到逆向记录.md（2026-10-25）
//
// 定位：完全独立运行，不依赖也不影响 checkin_all.js 统一签到任务；
//       凭证稳定运行一段时间后，可按平台模块模式并入统一脚本。
//
// 配置：同目录 kuku_config.json（已被 .gitignore 排除，含 BDUSS 严禁提交）
//   {
//     "bduss":  "xxx",   // 必填：百度账号 BDUSS（客户端抓包获取）
//     "stoken": "xxx",   // 可选：genflowpro 的 STOKEN（缺省时可用 ptoken 自动换取）
//     "ptoken": "xxx",   // 可选：passport 凭证，用于自动换取 STOKEN
//     "uid":    "123",   // 可选：账号 uk 数字串（留空由服务端按 BDUSS 识别）
//     "version": "",     // 可选：客户端版本号（默认 1.6.28）
//     "user_agent": ""   // 可选：自定义 User-Agent
//   }
//   环境变量可覆盖文件值：KUKU_BDUSS / KUKU_STOKEN / KUKU_UID
//
// 用法: node kuku_checkin.js [--no-delay] [--status] [--lottery]
//   --status    只查询签到状态（只读，不执行签到）
//   --lottery   签到后尝试执行抽奖（试验性：抽奖接口 jsToken 风控未完全逆向）
//   --no-delay  跳过随机延时（默认签到前等待 30~300 秒防检测）
//
// 退出码: 0=签到成功/今日已签/状态查询成功  1=失败（凭证缺失/失效/网络异常）
// 退出方式: process.exitCode 自然退出（Node 24+Windows 下 process.exit 强杀
//           会触发 libuv 断言，与 checkin_all.js 保持一致）
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
// 平台常量（2026-10-25 逆向自 app.asar，详见逆向记录文档）
// ============================================================
const BASE = 'https://kuku.baidu.com';          // 主网关（_y.main）
const APP_ID = '123971023';                     // defaultParams.app_id
const CHANNEL = 'chunlei';                      // 百度网盘同源渠道标识
const CLIENTTYPE = '0';                         // PC 客户端类型
const VERSION_FALLBACK = '1.6.28';              // GenFlowPro 版本兜底
const TID_SIGNIN30 = '291651792210';            // activityPromo.signin30Tid（V3.0 签到）
const TID_LOTTERY = '531681788278';             // activityPromo.lotteryTid（签到送抽奖）
const PASSPORT_STOKEN_URL = 'https://passport.baidu.com/v3/login/api/auth'; // bduss+ptoken 换 stoken
const UA_DEFAULT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) GenFlowPro/1.6.28 Chrome/124.0.0.0 Safari/537.36';

// ============================================================
// 配置加载（kuku_config.json + 环境变量覆盖）
// ============================================================
function loadConfig() {
  const cfgPath = path.join(__dirname, 'kuku_config.json');
  let fileCfg = {};
  if (fs.existsSync(cfgPath)) {
    try {
      // 去 BOM：Windows 记事本保存的 JSON 常带 UTF-8 BOM，会让 JSON.parse 失败
      const raw = fs.readFileSync(cfgPath, 'utf8').replace(/^\uFEFF/, '');
      fileCfg = JSON.parse(raw);
    } catch (e) {
      log(`错误：kuku_config.json 解析失败 - ${e.message}（请检查 JSON 格式，注意用无注释的纯 JSON）`);
      return null;
    }
  }
  const cfg = {
    bduss: (process.env.KUKU_BDUSS || fileCfg.bduss || '').trim(),
    stoken: (process.env.KUKU_STOKEN || fileCfg.stoken || '').trim(),
    ptoken: String(fileCfg.ptoken || '').trim(),
    uid: String(process.env.KUKU_UID || fileCfg.uid || '').trim(),
    version: String(fileCfg.version || '').trim() || VERSION_FALLBACK,
    user_agent: String(fileCfg.user_agent || '').trim() || UA_DEFAULT,
  };
  if (!cfg.bduss) {
    log('错误：未找到库库AI签到凭证（bduss 为空）。');
    log(`请在脚本同目录创建 kuku_config.json（已被 .gitignore 排除，不会提交到 Git）：`);
    log('  {');
    log('    "bduss":  "必填-百度账号BDUSS",');
    log('    "stoken": "可选-genflowpro的STOKEN",');
    log('    "ptoken": "可选-用于自动换取STOKEN",');
    log('    "uid":    "可选-账号uk数字串"');
    log('  }');
    log('获取方式：库库AI客户端内触发任意 kuku.baidu.com 请求，用 F12/抓包工具（Fiddler）');
    log('复制请求 Cookie 头中的 BDUSS（及 STOKEN）值。详见 文档/库库AI签到逆向记录.md §八');
    return null;
  }
  return cfg;
}

// ============================================================
// STOKEN 换取（passport：bduss+ptoken → stoken_list.genflowpro）
// ============================================================
async function exchangeStoken(bduss, ptoken, userAgent) {
  const body = new URLSearchParams({ bduss, ptoken }).toString();
  const res = await fetch(PASSPORT_STOKEN_URL, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
      'User-Agent': userAgent || UA_DEFAULT,
    },
    body,
  });
  const json = await res.json();
  const errno = json?.errno;
  if (typeof errno === 'number' && errno !== 0) {
    throw new Error(`errno=${errno} ${json?.errmsg || ''}`);
  }
  const st = json?.stoken_list?.genflowpro;
  if (!st) throw new Error('stoken_list.genflowpro 为空');
  return st;
}

// ============================================================
// API 请求封装（Cookie 鉴权：BDUSS + STOKEN + gfprotpl）
// ============================================================
function buildCookie(cfg) {
  const parts = [`BDUSS=${cfg.bduss}`];
  if (cfg.stoken) parts.push(`STOKEN=${cfg.stoken}`);
  parts.push('gfprotpl=genflowpro');
  return parts.join('; ');
}

function buildQuery(cfg, extraParams) {
  // 公共参数与客户端 native http 附加的一致：app_id/channel/clienttype/version/uid
  const params = {
    app_id: APP_ID,
    channel: CHANNEL,
    clienttype: CLIENTTYPE,
    version: cfg.version,
    uid: cfg.uid || '',
    ...(extraParams || {}),
  };
  return new URLSearchParams(params).toString();
}

async function apiRequest(cfg, method, apiPath, extraParams) {
  const url = `${BASE}${apiPath}?${buildQuery(cfg, extraParams)}`;
  const headers = {
    'Cookie': buildCookie(cfg),
    'User-Agent': cfg.user_agent,
    'Referer': 'https://kuku.baidu.com/',
    'Accept': 'application/json, text/plain, */*',
  };
  if (method === 'POST') headers['Content-Type'] = 'application/json';
  const res = await fetch(url, { method, headers, body: method === 'POST' ? '' : undefined });
  let json;
  try { json = await res.json(); } catch { throw new Error(`HTTP ${res.status} 响应非 JSON`); }
  return { status: res.status, json };
}

// 业务错误统一判定（客户端 G 函数还原：errno ?? code，非 0 即失败）
function businessError(json) {
  const errno = json?.errno ?? json?.code;
  if (typeof errno === 'number' && errno !== 0) {
    return { errno, showMsg: json?.show_msg || json?.message || '' };
  }
  return null;
}

// ============================================================
// 签到状态查询（POST /act/v2/kukuai30/homepage）
// 返回字段还原自客户端 ue()：signed_today/continuous_days/next_reward_*/calendar
// ============================================================
async function kukuHomepage(cfg) {
  const { status, json } = await apiRequest(cfg, 'POST', '/act/v2/kukuai30/homepage', { tid: TID_SIGNIN30 });
  if (status !== 200) return { ok: false, errno: `http_${status}`, showMsg: '' };
  const err = businessError(json);
  if (err) return { ok: false, ...err };
  const data = json?.data ?? json?.result;
  if (!data || typeof data !== 'object') return { ok: false, errno: 'protocol', showMsg: '响应缺少 data 字段' };
  return {
    ok: true,
    signedToday: data.signed_today === true,
    continuousDays: Number(data.continuous_days ?? 0) || 0,
    nextRewardDays: Number(data.next_reward_days ?? 0) || 0,
    nextRewardAward: typeof data.next_reward_award === 'string' ? data.next_reward_award : '',
    calendar: Array.isArray(data.calendar) ? data.calendar : [],
  };
}

// ============================================================
// 执行签到（POST /act/v2/kukuai30/signin）
// ============================================================
async function kukuSignin(cfg) {
  const { status, json } = await apiRequest(cfg, 'POST', '/act/v2/kukuai30/signin', { tid: TID_SIGNIN30 });
  if (status !== 200) return { ok: false, errno: `http_${status}`, showMsg: '' };
  const err = businessError(json);
  if (err) return { ok: false, ...err };
  return { ok: true };
}

// ============================================================
// 抽奖（试验性，--lottery 开启）
// 接口还原自 app.asar：GET /act/v2/lottery/lotterycommit（l() 为 http.get）
// jsToken 为活动页 H5 风控 token，生成逻辑未逆向，留空尝试；失败不影响签到结果
// ============================================================
async function kukuLottery(cfg) {
  log('--- 抽奖（试验性）---');
  try {
    // 1) 查抽奖机会（homeinfo）
    let chances = null;
    try {
      const info = await apiRequest(cfg, 'GET', '/act/v2/component/lottery/homeinfo', {
        tid: TID_LOTTERY, comp_ver: '2', action: 'lottery_cnt,view_list,used_cnt',
      });
      const d = info.json?.data ?? info.json;
      if (d && typeof d === 'object' && typeof d.lottery_cnt !== 'undefined') {
        chances = Number(d.lottery_cnt) || 0;
        log(`当前抽奖机会：${chances} 次`);
      } else {
        log(`抽奖状态响应（未能解析机会数）：${JSON.stringify(info.json).slice(0, 200)}`);
      }
    } catch (e) {
      log(`抽奖状态查询失败：${e.message}`);
    }
    if (chances !== null && chances <= 0) { log('无抽奖机会，跳过'); return; }

    // 2) 提交一次抽奖
    const draw = await apiRequest(cfg, 'GET', '/act/v2/lottery/lotterycommit', {
      tid: TID_LOTTERY, cnt: '1', action: 'lottery_cnt,view_list,used_cnt', jsToken: '',
    });
    const err = businessError(draw.json);
    if (err) {
      log(`抽奖未成功：errno=${err.errno} ${err.showMsg}（jsToken 风控可能导致，属预期内，不影响签到）`);
      return;
    }
    const list = Array.isArray(draw.json) ? draw.json : (draw.json?.data ?? []);
    if (Array.isArray(list) && list.length > 0) {
      for (const item of list.slice(0, 3)) log(`抽奖结果：${JSON.stringify(item).slice(0, 200)}`);
    } else {
      log(`抽奖响应：${JSON.stringify(draw.json).slice(0, 200)}`);
    }
  } catch (e) {
    log(`抽奖请求异常：${e.message}（不影响签到结果）`);
  }
}

// ============================================================
// 主流程
// ============================================================
async function main() {
  const args = process.argv.slice(2);
  const noDelay = args.includes('--no-delay');
  const statusOnly = args.includes('--status');
  const withLottery = args.includes('--lottery');

  logSection('库库AI 签到');

  const cfg = loadConfig();
  if (!cfg) { process.exitCode = 1; return; }

  // STOKEN 缺失但提供 ptoken 时自动换取（passport 接口）
  if (!cfg.stoken && cfg.ptoken) {
    try {
      cfg.stoken = await exchangeStoken(cfg.bduss, cfg.ptoken, cfg.user_agent);
      log('已通过 passport 接口自动换取 STOKEN（genflowpro）');
    } catch (e) {
      log(`警告：STOKEN 自动换取失败 - ${e.message}，将仅用 BDUSS 尝试`);
    }
  }

  // 1) 签到状态查询
  let hp;
  try {
    hp = await kukuHomepage(cfg);
  } catch (e) {
    log(`错误：签到状态查询失败 - ${e.message}`);
    process.exitCode = 1;
    return;
  }
  if (!hp.ok) {
    if (hp.errno === -6) {
      log('登录态已失效（errno -6）：BDUSS/STOKEN 过期或错误，请重新抓取 Cookie 并更新 kuku_config.json');
    } else {
      log(`签到状态查询失败：errno=${hp.errno} ${hp.showMsg}`);
    }
    process.exitCode = 1;
    return;
  }

  const milestone = hp.nextRewardDays > 0 && hp.nextRewardAward
    ? `，再签 ${hp.nextRewardDays} 天可得「${hp.nextRewardAward}」` : '';
  log(`连续签到 ${hp.continuousDays} 天${milestone}`);

  if (statusOnly) {
    log(hp.signedToday ? '今日已签到（--status 只读模式）' : '今日未签到（--status 只读模式，未执行签到）');
    return;
  }

  if (hp.signedToday) {
    log('今日已签到，无需重复操作');
    return;
  }

  // 2) 签到前随机延时（打乱固定时间模式；--no-delay 跳过）
  if (!noDelay) {
    const delay = randomDelaySec();
    log(`随机等待 ${delay} 秒后签到...（--no-delay 可跳过）`);
    await sleep(delay);
  }

  // 3) 执行签到
  let sn;
  try {
    sn = await kukuSignin(cfg);
  } catch (e) {
    log(`错误：签到请求失败 - ${e.message}`);
    process.exitCode = 1;
    return;
  }
  if (!sn.ok) {
    if (sn.errno === -6) {
      log('登录态已失效（errno -6）：请更新 kuku_config.json 中的 Cookie');
    } else {
      log(`签到失败：errno=${sn.errno} ${sn.showMsg}`);
    }
    process.exitCode = 1;
    return;
  }

  // 4) 复查确认（还原客户端 he()：签到后再查 homepage 展示最新连签状态）
  let after = hp;
  try { after = await kukuHomepage(cfg); } catch {}
  if (after.ok && after.signedToday) {
    const milestone2 = after.nextRewardDays > 0 && after.nextRewardAward
      ? `，再签 ${after.nextRewardDays} 天可得「${after.nextRewardAward}」` : '';
    log(`签到成功！连续签到 ${after.continuousDays} 天${milestone2}`);
  } else {
    log('签到请求已受理（errno=0），但复查状态未翻转，建议稍后用 --status 确认');
  }

  // 5) 可选抽奖（试验性）
  if (withLottery) await kukuLottery(cfg);
}

// 导出（供未来并入 checkin_all.js 统一脚本时复用；直接运行时才执行 main）
module.exports = {
  loadConfig,
  exchangeStoken,
  kukuHomepage,
  kukuSignin,
  kukuLottery,
};

if (require.main === module) {
  main().catch(e => { log(`致命错误：${e.message}`); process.exitCode = 1; });
}