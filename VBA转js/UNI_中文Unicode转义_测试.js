// UNI_中文Unicode转义_测试.js
// 测试 UNI 库：中文 ↔ Unicode 转义序列互转
// 运行：node UNI_中文Unicode转义_测试.js

var UNI = require('./UNI_中文Unicode转义_Lib.js');

var pass = 0, fail = 0;

function eq(actual, expected, label) {
    if (actual === expected) {
        pass++;
    } else {
        fail++;
        console.log('  [FAIL] ' + label);
        console.log('         期望: ' + JSON.stringify(expected));
        console.log('         实际: ' + JSON.stringify(actual));
    }
}

console.log('================ Unicode 转义库测试 ================');
console.log('库版本: ' + UNI.version);
console.log('');

// ===== 一、标准场景 =====
console.log('--- 一、标准场景 ---');

// 1. 中文编码
eq(UNI.toUnicode('中文'), '\\u4E2D\\u6587', '中文 → \\u4E2D\\u6587');

// 2. 中英混合（默认仅转义非 ASCII）
eq(UNI.toUnicode('Hello 世界'), 'Hello \\u4E16\\u754C', '中英混合仅转义中文');

// 3. 纯 ASCII 不转义
eq(UNI.toUnicode('ABC123'), 'ABC123', '纯 ASCII 不转义');

// 4. 小写十六进制
eq(UNI.toUnicode('中文', { upper: false }), '\\u4e2d\\u6587', '小写十六进制');

// 5. 转义全部字符
eq(UNI.toUnicode('AB', { all: true }), '\\u0041\\u0042', 'all=true 转义全部');

// 6. ES6 \u{} 形式
eq(UNI.toUnicode('中', { brace: true }), '\\u{4E2D}', 'ES6 大括号形式');

// ===== 二、解码还原 =====
console.log('--- 二、解码还原 ---');

// 7. 标准解码
eq(UNI.fromUnicode('\\u4E2D\\u6587'), '中文', '标准解码还原');

// 8. 小写转义解码
eq(UNI.fromUnicode('\\u4e2d\\u6587'), '中文', '小写转义解码');

// 9. ES6 大括号形式解码
eq(UNI.fromUnicode('\\u{4E16}\\u{754C}'), '世界', 'ES6 形式解码');

// 10. 混合文本解码
eq(UNI.fromUnicode('Hello \\u4E16\\u754C'), 'Hello 世界', '混合文本解码');

// 11. 无转义序列原样返回
eq(UNI.fromUnicode('普通文本'), '普通文本', '无转义原样返回');

// ===== 三、往返一致性（round-trip）=====
console.log('--- 三、往返一致性 ---');

var samples = [
    '中文测试',
    'Hello 世界！2026',
    '排列组合 C(n,k)',
    '特殊符号：①②③★☆【】',
    '日文テスト 한국어',
    '',                           // 空串
    '单',                         // 单字符
    'AAAA',                       // 纯 ASCII
    '混合\\u0041转义'              // 含已有转义字面量
];

samples.forEach(function (s, idx) {
    var enc = UNI.toUnicode(s);
    var dec = UNI.fromUnicode(enc);
    eq(dec, s, '往返一致 #' + idx + ' (' + s.slice(0, 8) + ')');
});

// ===== 四、边界条件 =====
console.log('--- 四、边界条件 ---');

// 12. 空串
eq(UNI.toUnicode(''), '', '空串编码');
eq(UNI.fromUnicode(''), '', '空串解码');

// 13. null / undefined 安全
eq(UNI.toUnicode(null), '', 'null 编码安全');
eq(UNI.toUnicode(undefined), '', 'undefined 编码安全');
eq(UNI.fromUnicode(null), '', 'null 解码安全');

// 14. 数字自动转字符串
eq(UNI.toUnicode(123), '123', '数字转字符串编码');

// 15. 非法码点保留原字面量（代理区间）
eq(UNI.fromUnicode('\\uD800'), '\\uD800', '代理区间码点保留原样');

// 16. 超出码点范围保留原字面量
eq(UNI.fromUnicode('\\u{110000}'), '\\u{110000}', '超范围码点保留原样');

// ===== 五、补充平面字符（emoji 代理对）=====
console.log('--- 五、补充平面字符（emoji 代理对）---');

// 17. emoji 编码为代理对
var emoji = '😀'; // U+1F600
var encEmoji = UNI.toUnicode(emoji);
eq(encEmoji, '\\uD83D\\uDE00', 'emoji → 代理对 \\uD83D\\uDE00');

// 18. emoji 往返一致
eq(UNI.fromUnicode(encEmoji), emoji, 'emoji 代理对解码还原');

// 19. emoji ES6 大括号形式
eq(UNI.toUnicode(emoji, { brace: true }), '\\u{1F600}', 'emoji ES6 大括号形式');

// 20. emoji ES6 形式解码
eq(UNI.fromUnicode('\\u{1F600}'), emoji, 'emoji ES6 形式解码');

// ===== 六、检测函数 =====
console.log('--- 六、检测函数 ---');

eq(UNI.hasNonASCII('中文'), true, '检测中文为 true');
eq(UNI.hasNonASCII('ABC123'), false, '检测纯 ASCII 为 false');
eq(UNI.hasNonASCII('Hello 世界'), true, '检测混合为 true');
eq(UNI.hasNonASCII(''), false, '空串检测为 false');

// ===== 七、多行批量 =====
console.log('--- 七、多行批量 ---');

var multi = '第一行中文\nSecond line\n第三行';
var linesEnc = UNI.toUnicodeLines(multi);
eq(linesEnc.length, 3, '多行拆分为 3 行');
eq(linesEnc[0], '\\u7B2C\\u4E00\\u884C\\u4E2D\\u6587', '第1行编码');
eq(linesEnc[1], 'Second line', '第2行 ASCII 原样');
eq(linesEnc[2], '\\u7B2C\\u4E09\\u884C', '第3行编码');
eq(UNI.fromUnicodeLines(linesEnc), multi, '多行批量往返一致');

// ===== 八、随机输入往返测试 =====
console.log('--- 八、随机输入往返测试 ---');

// 构造随机中文字符串（CJK 统一汉字区 U+4E00 ~ U+9FFF）
function randomChinese(n) {
    var s = '';
    for (var i = 0; i < n; i++) {
        var cp = 0x4E00 + Math.floor(Math.random() * (0x9FFF - 0x4E00 + 1));
        s += String.fromCodePoint(cp);
    }
    return s;
}

var randomFail = 0;
for (var t = 0; t < 1000; t++) {
    var len = 1 + Math.floor(Math.random() * 20);
    var rs = randomChinese(len);
    if (UNI.fromUnicode(UNI.toUnicode(rs)) !== rs) {
        randomFail++;
    }
}
if (randomFail === 0) { pass++; console.log('  [PASS] 1000 次随机中文往返测试全部一致'); }
else { fail++; console.log('  [FAIL] 随机测试失败 ' + randomFail + ' 次'); }

// 含 emoji 的随机往返
var randomEmojiFail = 0;
for (var e = 0; e < 200; e++) {
    var parts = [];
    var n = 1 + Math.floor(Math.random() * 5);
    for (var j = 0; j < n; j++) {
        if (Math.random() < 0.5) {
            parts.push(randomChinese(1 + Math.floor(Math.random() * 3)));
        } else {
            var cp = 0x1F300 + Math.floor(Math.random() * 0x600);
            parts.push(String.fromCodePoint(cp));
        }
    }
    var es = parts.join('');
    if (UNI.fromUnicode(UNI.toUnicode(es)) !== es) randomEmojiFail++;
}
if (randomEmojiFail === 0) { pass++; console.log('  [PASS] 200 次随机中文+emoji 往返测试全部一致'); }
else { fail++; console.log('  [FAIL] emoji 随机测试失败 ' + randomEmojiFail + ' 次'); }

// ===== 结果汇总 =====
console.log('');
console.log('==================================================');
console.log('通过: ' + pass + '  失败: ' + fail);
console.log(fail === 0 ? '✓ 全部通过' : '✗ 存在失败用例');
console.log('==================================================');

// ===== 演示输出 =====
console.log('');
console.log('===== 演示：实际转换效果 =====');
var demo = '排列组合四象限：C(n,k) 组合不放回';
console.log('原文  : ' + demo);
console.log('编码  : ' + UNI.toUnicode(demo));
console.log('解码  : ' + UNI.fromUnicode(UNI.toUnicode(demo)));

process.exit(fail === 0 ? 0 : 1);
