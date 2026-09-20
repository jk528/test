// asar 解析与提取工具（无依赖版）
// 用法:
//   node asar_tool.js list <asar路径> [过滤词]     列出文件
//   node asar_tool.js extract <asar路径> <内部路径> <输出路径>  提取单个文件
//   node asar_tool.js grep <asar路径> <关键词> [最大命中]  在所有文本文件里搜关键词
const fs = require('fs');

function readHeader(asarPath) {
  const fd = fs.openSync(asarPath, 'r');
  const headBuf = Buffer.alloc(16);
  fs.readSync(fd, headBuf, 0, 16, 0);
  // Chromium Pickle 格式: @0 UInt32(=4) @4 UInt32(pickle大小) @8 UInt32(json+4) @12 UInt32(jsonLen) @16 JSON
  const pickleSize = headBuf.readUInt32LE(4);
  const jsonLen = headBuf.readUInt32LE(12);
  const jsonBuf = Buffer.alloc(jsonLen);
  fs.readSync(fd, jsonBuf, 0, jsonLen, 16);
  fs.closeSync(fd);
  return { header: JSON.parse(jsonBuf.toString('utf8')), baseOffset: 8 + pickleSize };
}

function walk(node, prefix, out) {
  if (node.files) {
    for (const [name, child] of Object.entries(node.files)) {
      const p = prefix ? prefix + '/' + name : name;
      if (child.files) walk(child, p, out);
      else out.push({ path: p, size: child.size, offset: child.offset, unpacked: !!child.unpacked });
    }
  }
  return out;
}

const [, , cmd, asarPath, arg1, arg2, arg3] = process.argv;

if (cmd === 'list') {
  const { header } = readHeader(asarPath);
  let files = walk(header, '', []);
  if (arg1) files = files.filter(f => f.path.toLowerCase().includes(arg1.toLowerCase()));
  for (const f of files) console.log(`${f.size}\t${f.unpacked ? 'U' : 'P'}\t${f.path}`);
  console.error(`共 ${files.length} 个文件`);
} else if (cmd === 'extract') {
  const { header, baseOffset } = readHeader(asarPath);
  const files = walk(header, '', []);
  const f = files.find(x => x.path === arg1);
  if (!f) { console.error('未找到: ' + arg1); process.exit(1); }
  if (f.unpacked) {
    // unpacked 文件在 app.asar.unpacked 目录
    const unpackedPath = asarPath.replace(/app\.asar$/i, 'app.asar.unpacked') + '/' + f.path;
    fs.copyFileSync(unpackedPath, arg2);
  } else {
    const fd = fs.openSync(asarPath, 'r');
    const buf = Buffer.alloc(f.size);
    fs.readSync(fd, buf, 0, f.size, baseOffset + Number(f.offset));
    fs.closeSync(fd);
    fs.writeFileSync(arg2, buf);
  }
  console.log('已提取: ' + arg1 + ' -> ' + arg2);
} else if (cmd === 'grep') {
  const keyword = arg1;
  const maxHits = parseInt(arg2 || '50', 10);
  const { header, baseOffset } = readHeader(asarPath);
  const files = walk(header, '', []).filter(f => !f.unpacked && /\.(js|mjs|cjs|json|html|css|map)$/.test(f.path) && f.size < 60 * 1024 * 1024);
  let hits = 0;
  const fd = fs.openSync(asarPath, 'r');
  for (const f of files) {
    if (hits >= maxHits) break;
    const buf = Buffer.alloc(f.size);
    fs.readSync(fd, buf, 0, f.size, baseOffset + Number(f.offset));
    const text = buf.toString('utf8');
    let idx = 0, count = 0;
    while ((idx = text.indexOf(keyword, idx)) !== -1) { count++; idx += keyword.length; }
    if (count > 0) { console.log(`${count}x\t${f.path}`); hits++; }
  }
  fs.closeSync(fd);
  console.error(`扫描 ${files.length} 个文本文件，命中 ${hits} 个文件`);
} else {
  console.error('未知命令: ' + cmd);
  process.exit(1);
}
