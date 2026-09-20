// Qoder 签到前提逐项检测（只读，无副作用）
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { execFileSync } = require('child_process');

const dataDir = path.join(process.env.APPDATA, 'com.qodercn.app.stable');
const exeDir = path.join(process.env.LOCALAPPDATA, 'Programs', 'Qoder CN');
const nodeExe = path.join(process.env.USERPROFILE, '.local', 'share', 'TeleAgent', 'runtimes', 'node', 'node.exe');

const results = [];
function check(name, ok, detail) {
  results.push({ name, ok, detail });
  console.log(`${ok ? '[OK] ' : '[NG] '}${name}${detail ? ' — ' + detail : ''}`);
}

// 1. Qoder CN 客户端安装（含设备指纹程序）
const runtimeInfo = path.join(exeDir, 'resources', 'umid', 'runtime-info.exe');
check('1. Qoder CN 客户端已安装', fs.existsSync(runtimeInfo), fs.existsSync(exeDir) ? '含 runtime-info.exe' : '安装目录不存在');

// 2. 登录态文件存在
const authPath = path.join(dataDir, 'auth.v1.dat');
check('2. 客户端登录过（auth.v1.dat 存在）', fs.existsSync(authPath));

// 4. TeleAgent Node 运行时
check('4. TeleAgent Node 运行时', fs.existsSync(nodeExe), fs.existsSync(nodeExe) ? '可执行' : '未找到 node.exe');

// 3+5. DPAPI 解密（同时验证同机同用户绑定 + powershell 可用）
let auth = null, masterKey = null;
try {
  const localState = JSON.parse(fs.readFileSync(path.join(dataDir, 'Local State'), 'utf8'));
  const blob = Buffer.from(localState.os_crypt.encrypted_key, 'base64');
  const payload = blob.slice(5).toString('base64');
  const ps = [
    "Add-Type -AssemblyName System.Security;",
    `$src=[Convert]::FromBase64String('${payload}');`,
    "$dst=New-Object byte[] $src.Length;",
    "[array]::Copy($src,0,$dst,0,$src.Length);",
    "$k=[Security.Cryptography.ProtectedData]::Unprotect($dst,$null,'CurrentUser');",
    "($k|ForEach-Object{$_.ToString('x2')}) -join ''"
  ].join('');
  const hex = execFileSync('powershell.exe', ['-NoProfile', '-NonInteractive', '-Command', ps], { encoding: 'utf8' }).trim();
  masterKey = Buffer.from(hex, 'hex');
  const raw = fs.readFileSync(authPath);
  const nonce = raw.slice(3, 15), tag = raw.slice(raw.length - 16), ct = raw.slice(15, raw.length - 16);
  const d = crypto.createDecipheriv('aes-256-gcm', masterKey, nonce);
  d.setAuthTag(tag);
  auth = JSON.parse(Buffer.concat([d.update(ct), d.final()]).toString('utf8'));
  check('3+5. 凭证解密（DPAPI 同机同用户 + PowerShell）', true, `账号 ${auth.user?.name || auth.user?.id}`);
} catch (e) {
  check('3+5. 凭证解密（DPAPI 同机同用户 + PowerShell）', false, e.message);
}

// 7. 凭证有效期
if (auth) {
  const now = Date.now();
  const tokenLeft = (Date.parse(auth.expiresAt) - now) / 86400000;
  const rtLeft = (Date.parse(auth.refreshTokenExpiresAt) - now) / 86400000;
  check('7a. token 有效', tokenLeft > 0, `剩余 ${tokenLeft.toFixed(1)} 天`);
  check('7b. refreshToken 有效', rtLeft > 0, `剩余 ${rtLeft.toFixed(0)} 天`);
}

// 6+8+9. 网络 + 风控头 + 活动投放
(async () => {
  try {
    // 风控头实测
    const userId = auth?.user?.id || '';
    const out = execFileSync(runtimeInfo, ['0', '--account-stdin'], {
      input: JSON.stringify({ account: userId }) + '\n', encoding: 'utf8', timeout: 30000, windowsHide: true,
    });
    const risk = JSON.parse(out.split('\n')[0]);
    check('10. 风控头生成（runtime-info.exe）', !!risk.machineToken, `machineToken ${risk.machineToken?.length} 字符，VM检测:${risk.vmInfo?.isVm ? '是VM' : '非VM'}`);

    const headers = {
      'Accept': 'application/json',
      'Authorization': `Bearer ${auth.token}`,
      'Cosy-ClientType': '10', 'Cosy-Version': '0.3.4',
      'Cosy-MachineOS': 'x86_64_windows',
      'Cosy-MachineHostname': (process.env.COMPUTERNAME || '').trim(),
      'Cosy-MachineId': fs.readFileSync(path.join(dataDir, 'auth.machine-id'), 'utf8').trim(),
      'User-Agent': 'Qoder',
      'Cosy-MachineToken': risk.machineToken,
      'Cosy-MachineCode': risk.machineCode,
      'Cosy-MachineType': risk.machineType,
    };
    const res = await fetch('https://openapi.qoder.com.cn/sash/api/v1/me/campaigns', { headers });
    check('6. 网络 + 认证（GET campaigns）', res.status === 200, `HTTP ${res.status}`);
    if (res.status === 200) {
      const data = await res.json();
      const benefit = (data.campaigns || []).filter(c => c.actionType === 'CLAIM_BENEFIT');
      const latest = benefit[benefit.length - 1];
      const now = new Date(Date.now() + 8 * 3600e3);
      const cnTime = `UTC+8 ${now.getUTCHours()}:${String(now.getUTCMinutes()).padStart(2, '0')}`;
      check('9. 活动仍在投放', benefit.length > 0, `最新活动 ${latest?.campaignKey}（${latest?.claimStatus}）`);
      const inWindow = now.getUTCHours() >= 10;
      check('8. 活动窗口', true, `当前 ${cnTime}，${now.getUTCHours() >= 10 ? '已过今日 10:00 刷新点，10:30 任务可领' : '今日活动 10:00 生成，10:30 任务负责领取'}`);
    }
  } catch (e) {
    check('6. 网络 + 认证（GET campaigns）', false, e.message);
  }

  const fail = results.filter(r => !r.ok).length;
  console.log(`\n===== 检测完成：${results.length - fail}/${results.length} 项通过 =====`);
  process.exitCode = fail > 0 ? 1 : 0;
})();
