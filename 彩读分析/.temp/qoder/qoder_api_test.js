// Qoder campaigns API 实测
// 用法: node qoder_api_test.js [claim]  不带参数=仅查状态, claim=尝试领取
const fs = require('fs');
const path = require('path');
const os = require('os');
const crypto = require('crypto');
const { execFileSync } = require('child_process');

const dataDir = path.join(process.env.APPDATA, 'com.qodercn.app.stable');
const exeDir = path.join(process.env.LOCALAPPDATA, 'Programs', 'Qoder CN', 'resources', 'umid');

// ---- 读取 token（从临时文件，已由 qoder_auth.js 解密）----
const auth = JSON.parse(fs.readFileSync(path.join(__dirname, 'qoder_token.json'), 'utf8'));
const token = auth.token;
const userId = auth.user.id;
console.log(`token: ${token.slice(0, 10)}...  user: ${userId}`);

// ---- 读取 machine-id ----
const machineId = fs.readFileSync(path.join(dataDir, 'auth.machine-id'), 'utf8').trim();
console.log(`machineId: ${machineId}`);

// ---- DPAPI 解密主密钥 ----
function dpapiMasterKey() {
  const localState = JSON.parse(fs.readFileSync(path.join(dataDir, 'Local State'), 'utf8'));
  const blob = Buffer.from(localState?.os_crypt?.encrypted_key, 'base64');
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
  return Buffer.from(hex, 'hex');
}
function decryptV10(raw, masterKey) {
  const nonce = raw.slice(3, 15);
  const tag = raw.slice(raw.length - 16);
  const ct = raw.slice(15, raw.length - 16);
  const d = crypto.createDecipheriv('aes-256-gcm', masterKey, nonce);
  d.setAuthTag(tag);
  return Buffer.concat([d.update(ct), d.final()]).toString('utf8');
}

// ---- runtime-info.exe 获取风控身份 ----
function riskIdentity() {
  const exe = path.join(exeDir, 'runtime-info.exe');
  const out = execFileSync(exe, ['0', '--account-stdin'], {
    input: JSON.stringify({ account: userId }) + '\n',
    encoding: 'utf8', timeout: 30000
  });
  return JSON.parse(out.split('\n')[0]);
}

// ---- 构造请求头 ----
function buildHeaders() {
  const risk = riskIdentity();
  const ver = '0.3.4';
  const headers = {
    'Accept': 'application/json',
    'Authorization': `Bearer ${token}`,
    'Cosy-ClientType': '10',
    'Cosy-Version': ver,
    'Cosy-MachineOS': 'x86_64_windows',
    'Cosy-MachineHostname': process.env.COMPUTERNAME || os.hostname(),
    'Cosy-MachineId': machineId,
    'User-Agent': 'Qoder'
  };
  if (risk.machineToken) headers['Cosy-MachineToken'] = risk.machineToken;
  if (risk.machineCode) headers['Cosy-MachineCode'] = risk.machineCode;
  if (risk.machineType) headers['Cosy-MachineType'] = risk.machineType;
  return headers;
}

const BASE = 'https://openapi.qoder.com.cn';

async function main() {
  const doClaim = process.argv[2] === 'claim';
  const headers = buildHeaders();
  console.log('请求头（token 脱敏）: ' + JSON.stringify({ ...headers, Authorization: 'Bearer ' + token.slice(0, 6) + '...' }));

  // 1. 状态查询
  const res = await fetch(`${BASE}/sash/api/v1/me/campaigns`, { headers });
  console.log(`\n状态: HTTP ${res.status}`);
  const data = await res.json();
  console.log(JSON.stringify(data, null, 2));

  if (!doClaim) return;

  // 2. 找可领取的活动
  const claimable = (data.campaigns || []).filter(c => c.claimStatus === 'CLAIMABLE');
  if (claimable.length === 0) { console.log('\n无可领取活动'); return; }
  for (const c of claimable) {
    console.log(`\n尝试领取: ${c.campaignId} (${c.campaignKey})`);
    const cres = await fetch(`${BASE}/sash/api/v1/me/campaigns/${encodeURIComponent(c.campaignId)}/claim`, {
      method: 'POST', headers
    });
    console.log(`领取: HTTP ${cres.status}`);
    const ctext = await cres.text();
    console.log(ctext.slice(0, 500));
  }
  // 3. 复查
  const res2 = await fetch(`${BASE}/sash/api/v1/me/campaigns`, { headers });
  const data2 = await res2.json();
  console.log(`\n复查 claimable=${data2.claimable}`);
}

main().catch(e => { console.error('错误: ' + e.message); process.exit(1); });
