/* 把《红楼梦》拆分章节 txt 打包成阅读器数据（本地一次性构建，不需要部署到服务器） */
const fs = require('fs');
const path = require('path');

const SRC = path.resolve(__dirname, '../../红楼梦范例/红楼梦_拆分');
const OUT = path.resolve(__dirname, '../app/data');
const BOOK_ID = 'hongloumeng';
const PER_VOLUME = 20;

function cleanParagraph(line) {
  return line.replace(/^[\s\u3000]+/, '').replace(/\s+$/, '');
}

function main() {
  const files = fs.readdirSync(SRC)
    .filter((f) => f.endsWith('.txt'))
    .sort((a, b) => parseInt(a, 10) - parseInt(b, 10));

  if (!files.length) throw new Error('未找到章节文本: ' + SRC);

  const chapters = files.map((file) => {
    const raw = fs.readFileSync(path.join(SRC, file), 'utf8').replace(/^\uFEFF/, '');
    const lines = raw.split(/\r?\n/);
    const title = cleanParagraph(lines[0]) || file.replace(/\.txt$/, '');
    const paragraphs = [];
    for (let i = 1; i < lines.length; i++) {
      const p = cleanParagraph(lines[i]);
      if (p) paragraphs.push(p);
    }
    return { title, paragraphs };
  });

  const bookDir = path.join(OUT, BOOK_ID);
  fs.mkdirSync(bookDir, { recursive: true });

  const toc = chapters.map((c, i) => ({ title: c.title, vol: Math.floor(i / PER_VOLUME) }));
  fs.writeFileSync(path.join(bookDir, 'toc.json'), JSON.stringify(toc));

  const volumeCount = Math.ceil(chapters.length / PER_VOLUME);
  for (let v = 0; v < volumeCount; v++) {
    const slice = chapters.slice(v * PER_VOLUME, (v + 1) * PER_VOLUME);
    fs.writeFileSync(path.join(bookDir, 'vol-' + v + '.json'), JSON.stringify(slice));
  }

  const library = {
    updated: new Date().toISOString().slice(0, 10),
    books: [{
      id: BOOK_ID,
      title: '红楼梦',
      author: '曹雪芹',
      desc: '程乙本 · 一百二十回',
      total: chapters.length,
      perVolume: PER_VOLUME,
      volumes: volumeCount,
      cover: { from: '#7d3b2f', to: '#c98b5f' },
    }],
  };
  fs.writeFileSync(path.join(OUT, 'library.json'), JSON.stringify(library, null, 2));

  const chars = chapters.reduce((n, c) => n + c.paragraphs.join('').length, 0);
  console.log(`章节 ${chapters.length} 回，分卷 ${volumeCount}，正文 ${(chars / 10000).toFixed(1)} 万字`);
  console.log('输出目录:', bookDir);
}

main();
