// UNI_中文Unicode转义_Lib.js
// 中文 ↔ Unicode 转义序列 互转工具库
// 用途：将中文字符串转为 \uXXXX 转义序列以便在编码不友好的环境（WPS 宏、
//       ANSI 编辑器、跨平台传输）中安全存储；亦可反向还原。
//
// ======================== 引入方式 ========================
// 方式1（WPS 宏）：将本文件代码粘贴到调用脚本顶部
// 方式2（Node.js）：const UNI = require('./UNI_中文Unicode转义_Lib.js');
// 方式3（浏览器）：<script src="UNI_中文Unicode转义_Lib.js"></script>
//
// ======================== API 一览 ========================
// UNI.toUnicode(str, opts)        编码：中文 → \uXXXX 转义序列
//   opts.all   : 是否转义全部字符（默认 false，仅转义非 ASCII）
//   opts.upper : 十六进制是否大写（默认 true）
//   opts.brace : 是否使用 ES6 \u{XXXXX} 形式（默认 false，用 \uXXXX 代理对）
// UNI.fromUnicode(str)            解码：\uXXXX / \u{XXXXX} → 中文
// UNI.hasNonASCII(str)            检测：字符串是否含非 ASCII 字符
// UNI.toUnicodeLines(str, opts)   批量：按行编码，返回行数组（便于多行存储）
// UNI.fromUnicodeLines(arr)       批量：行数组解码还原
// UNI.version                     库版本号
// =========================================================

(function (factory) {
    if (typeof module === 'object' && module.exports) {
        module.exports = factory();
    } else if (typeof define === 'function' && define.amd) {
        define([], factory);
    } else {
        var g = typeof globalThis !== 'undefined' ? globalThis
              : typeof self !== 'undefined' ? self
              : typeof window !== 'undefined' ? window
              : typeof global !== 'undefined' ? global
              : (this || {});
        g.UNI = factory();
    }
}(function () {
    'use strict';

    var VERSION = '1.0.0';

    // ----------------------------------------------------------
    // 内部工具：码点 → 4 位十六进制补零
    // ----------------------------------------------------------
    function pad4(n) {
        var s = n.toString(16).toUpperCase();
        while (s.length < 4) s = '0' + s;
        return s;
    }

    // ----------------------------------------------------------
    // 内部工具：码点 → 转义字符串（处理 BMP 与补充平面）
    //   brace=true  → \u{XXXXX}（ES6 形式，可表示任意码点）
    //   brace=false → \uXXXX 代理对形式（兼容性最佳）
    // ----------------------------------------------------------
    function codePointToEscape(cp, upper, brace) {
        var hex = cp.toString(16);
        if (!upper) hex = hex.toLowerCase(); else hex = hex.toUpperCase();
        if (brace) {
            return '\\u{' + hex + '}';
        }
        if (cp <= 0xFFFF) {
            return '\\u' + pad4(cp);
        }
        // 补充平面 → UTF-16 代理对
        cp -= 0x10000;
        var hi = 0xD800 + (cp >> 10);
        var lo = 0xDC00 + (cp & 0x3FF);
        return '\\u' + pad4(hi) + '\\u' + pad4(lo);
    }

    // ----------------------------------------------------------
    // toUnicode：中文 → \uXXXX 转义序列
    //   str        : 原始字符串
    //   opts.all   : true 转义全部字符；false（默认）仅转义非 ASCII
    //   opts.upper : 十六进制大写（默认 true）
    //   opts.brace : 使用 \u{XXXXX} 形式（默认 false）
    // 边界处理：空串返回空串；非字符串先 String() 转换
    // ----------------------------------------------------------
    function toUnicode(str, opts) {
        str = (str === null || str === undefined) ? '' : String(str);
        opts = opts || {};
        var all = opts.all === true;
        var upper = opts.upper !== false;
        var brace = opts.brace === true;

        var out = [];
        var i = 0, len = str.length;
        while (i < len) {
            var c = str.charCodeAt(i);
            var cp, step;
            // 正确处理代理对：高位代理 [0xD800, 0xDBFF]
            if (c >= 0xD800 && c <= 0xDBFF && i + 1 < len) {
                var lo = str.charCodeAt(i + 1);
                if (lo >= 0xDC00 && lo <= 0xDFFF) {
                    cp = 0x10000 + ((c - 0xD800) << 10) + (lo - 0xDC00);
                    step = 2;
                } else {
                    cp = c; step = 1; // 孤立高位代理，按单单元处理
                }
            } else {
                cp = c; step = 1;
            }

            if (all || cp > 0x7F) {
                out.push(codePointToEscape(cp, upper, brace));
            } else {
                out.push(str.charAt(i));
            }
            i += step;
        }
        return out.join('');
    }

    // ----------------------------------------------------------
    // fromUnicode：\uXXXX / \u{XXXXX} → 中文
    //   同时兼容 \uXXXX 代理对与 ES6 \u{XXXXX} 形式
    //   混合普通文本时保留普通文本
    // 边界处理：无转义序列的原样返回；非法序列保留原字面量
    // ----------------------------------------------------------
    var RE_ESC = /\\u\{([0-9a-fA-F]+)\}|\\u([0-9a-fA-F]{4})/g;

    function fromUnicode(str) {
        str = (str === null || str === undefined) ? '' : String(str);
        return str.replace(RE_ESC, function (m, braceHex, plainHex) {
            var cp;
            if (braceHex !== undefined) {
                cp = parseInt(braceHex, 16);
            } else {
                cp = parseInt(plainHex, 16);
            }
            // 合法码点范围 [0, 0x10FFFF]，排除代理区间
            if (cp > 0x10FFFF || (cp >= 0xD800 && cp <= 0xDFFF)) {
                return m; // 非法，保留原字面量
            }
            return String.fromCodePoint(cp);
        });
    }

    // ----------------------------------------------------------
    // hasNonASCII：检测字符串是否含非 ASCII 字符
    // ----------------------------------------------------------
    function hasNonASCII(str) {
        str = (str === null || str === undefined) ? '' : String(str);
        for (var i = 0; i < str.length; i++) {
            if (str.charCodeAt(i) > 0x7F) return true;
        }
        return false;
    }

    // ----------------------------------------------------------
    // toUnicodeLines：按行编码，返回行数组（便于多行文本存储）
    // ----------------------------------------------------------
    function toUnicodeLines(str, opts) {
        str = (str === null || str === undefined) ? '' : String(str);
        // 统一换行符后拆分
        var lines = str.replace(/\r\n/g, '\n').replace(/\r/g, '\n').split('\n');
        var out = [];
        for (var i = 0; i < lines.length; i++) {
            out.push(toUnicode(lines[i], opts));
        }
        return out;
    }

    // ----------------------------------------------------------
    // fromUnicodeLines：行数组解码还原（用 \n 重新拼接）
    // ----------------------------------------------------------
    function fromUnicodeLines(arr) {
        if (!arr || !arr.length) return '';
        var out = [];
        for (var i = 0; i < arr.length; i++) {
            out.push(fromUnicode(arr[i]));
        }
        return out.join('\n');
    }

    // ----------------------------------------------------------
    // 导出
    // ----------------------------------------------------------
    return {
        version: VERSION,
        toUnicode: toUnicode,
        fromUnicode: fromUnicode,
        hasNonASCII: hasNonASCII,
        toUnicodeLines: toUnicodeLines,
        fromUnicodeLines: fromUnicodeLines
    };
}));
