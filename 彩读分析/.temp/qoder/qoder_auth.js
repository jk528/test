// Qoder auth.v1.dat 解密：DPAPI 主密钥 + AES-256-GCM
// 用法: node qoder_auth.js [数据目录]  （默认国内版 com.qodercn.app.stable）
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { execFileSync } = require('child_process');

const dataDir = process.argv[2] || path.join(process.env.APPDATA, 'com.qodercn.app.stable');

// 1. DPAPI 解密主密钥
const localState = JSON.parse(fs.readFileSync(path.join(dataDir, 'Local State'), 'utf8'));
const encKeyB64 = localState?.os_crypt?.encrypted_key;
if (!encKeyB64) throw new Error('Local State 无 encrypted_key');
const blob = Buffer.from(encKeyB64, 'base64');
if (blob.slice(0, 5).toString('ascii') !== 'DPAPI') throw new Error('前缀非 DPAPI');
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
if (!/^[0-9a-f]{64}$/.test(hex)) throw new Error('主密钥解密结果异常: ' + hex.slice(0, 40));
const masterKey = Buffer.from(hex, 'hex');
console.log('主密钥: OK (32字节)');

// 2. 解密 auth.v1.dat
const raw = fs.readFileSync(path.join(dataDir, 'auth.v1.dat'));
const prefix = raw.slice(0, 3).toString('ascii');
if (prefix !== 'v10') throw new Error('未知前缀: ' + prefix);
const nonce = raw.slice(3, 15);
const tag = raw.slice(raw.length - 16);
const ct = raw.slice(15, raw.length - 16);
const d = crypto.createDecipheriv('aes-256-gcm', masterKey, nonce);
d.setAuthTag(tag);
const plain = Buffer.concat([d.update(ct), d.final()]).toString('utf8');

// 3. 解析并脱敏输出
const auth = JSON.parse(plain);
const mask = (s) => typeof s === 'string' && s.length > 20 ? s.slice(0, 16) + '...' + s.slice(-6) + `(${s.length})` : s;
const out = JSON.parse(JSON.stringify(auth));
if (out.token) out.token = mask(out.token);
if (out.refreshToken) out.refreshToken = mask(out.refreshToken);
console.log(JSON.stringify(out, null, 2));
// token 原文写入临时文件供后续测试（仅本机）
fs.writeFileSync(path.join(__dirname, 'qoder_token.json'), JSON.stringify(auth, null, 2), { encoding: 'utf8' });
console.log('\n完整凭证已写入 qoder_token.json（本地临时文件）');
