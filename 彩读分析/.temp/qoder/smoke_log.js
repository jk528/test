// 冒烟测试：模拟 checkin_all.js 的 log() 输出中文
function log(msg) {
  const ts = new Date().toLocaleString('zh-CN', { hour12: false });
  console.log(`${ts} ${msg}`);
}
log('====== 统一签到开始 ======');
log('[TraeWork] 随机等待 66 秒后签到...');
log('签到成功！积分：200');
log('[Qoder] 今日活动尚未刷新（每日 10:00 刷新），跳过本次。');
log('====== 冒烟测试结束 ======');
