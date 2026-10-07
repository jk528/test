// =============================================================================
// TXT章节拆分工具 v3.4（去重+乱序修复+卷级感知增强版）—— WPS JS宏 版
//   与 split_txt_v3.bas v3.4 功能对齐，JScript ES3 语法（JScript 5.8+ 兼容）
//   复制粘贴到 WPS JS宏编辑器即可运行，无需导入其他模块
//
// 入口：
//   拆分TXTv3   选择文件 → 选择正则 → 去重+排序组合 → 输出模式 → 生成（仅4个弹窗）
//   分析TXTv3   仅分析不拆分，输出 总-分 结构详细报告文件
//   自动TXTv3   全自动决策（组合+清洁N），一次确认即完成拆分
//   设置TXTv3   查看/修改默认设置（注册表 HKCU\Software\SplitTxtV3 持久化）
//
// 去重+排序组合（弹窗3六选一）：
//   1. 不去重 + 不排序（原样保留）
//   2. 不去重 + 排序（仅按章号重排）
//   3. 保留首次 + 不排序
//   4. 保留首次 + 排序
//   5. 保留最长 + 不排序
//   6. 保留最长 + 排序 ★推荐
//
// 输出模式（弹窗4一体输入，按第一个空格切分模式与参数）：
//   1 [=清洁,N默认100，可输 "1 200"]
//       每章单文件 + 同时生成 保留大于等于N_/清理小于N_ 两个纯净合并文件
//   2 [=聚合,默认40,3，可输 "2 20,1|20,1|80,1"]
//
// 设置TXTv3：一个InputBox改三项默认值
//   广告清理 1/0(默认1)，标题去重 0/1(默认0)，卷模式 1自动/2扁平/3分卷(默认1)
//
// 自动TXTv3 决策规则（仅统计 ch_num>0 且非目录区章节）：
//   dup=0且ooo=0 → none+none；adjRatio>=0.3且ooo<10 → longest+none；
//   ooo>=10 → longest+sort；dup>0 → longest+none；其余 → longest+sort
//   N自动：章节正文汉字数升序，下半区(<=中位数)最大相邻间隔中点取整到10，
//          clamp[50,2000]；章节<20 或 gap<50 或 最大gap<次大×2 → 100
//   输出：<名>_自动\分析报告.txt + 保留大于等于N_<名>.txt + 清理小于N_<名>.txt
//         + 拆分文档\序号_字数_标题.txt
//
// 输出均为 UTF-8 无BOM；源文件支持 ANSI/UTF-8(含/无BOM)/UTF-16LE/BE 自动检测
// =============================================================================

// --- MsgBox 常量 ---
var vbOKOnly = 0;
var vbOKCancel = 1;
var vbYesNoCancel = 3;
var vbYesNo = 4;
var vbQuestion = 32;
var vbExclamation = 48;
var vbInformation = 64;
var vbDefaultButton2 = 256;
var vbOK = 1;
var vbCancel = 2;
var vbYes = 6;
var vbNo = 7;

// --- 全局计时/状态 ---
var g_tSelect = 0;
var g_tTotal0 = 0;
var g_detectedEnc = "";
var g_regexName = "";

// --- 多正则存储 ---
var MAX_REGEX = 10;
var g_regexNames = [];
var g_regexPatterns = [];
var g_regexUnitGroups = [];
var g_regexDefaultUnits = [];
var g_regexMaxLens = [];      // v3.6：最大行长度限制（0=不限制）
var g_regexCount = 0;

var g_selPatterns = [];
var g_selUnitGroups = [];
var g_selDefaultUnits = [];
var g_selOrigIndices = [];
var g_selMaxLens = [];        // v3.6：选中正则的最大行长度限制
var g_selCount = 0;

// --- 去重、排序与卷 ---
var g_dedupStrategy = "longest";   // none/first/longest（双标题场景由目录区检测+清洁模式覆盖）
var g_sortStrategy = "sort";       // none/lis/sort
var g_volumeMode = "auto";         // auto/flat/by_volume

// --- 章节数据（平行数组） ---
var ch_nums = [];        // 章号（无号=0）
var ch_vols = [];        // 卷号（无卷=0）
var ch_units = [];       // 单位词
var ch_levels = [];      // chapter/volume/special
var ch_patterns = [];    // 匹配的正则类型
var ch_bodyLines = [];   // 正文行数
var ch_isTOC = [];       // 是否为目录区章节
// v3.6 优化：扫描时预计算，消除重复遍历
var ch_charCounts = [];  // 每章总字符数（含换行），预计算
var ch_hanziCounts = []; // 每章正文汉字数，预计算
var ch_starts = [];
var ch_ends = [];
var ch_titles = [];
var ch_count = 0;
var ch_unit = "章";

// 去重后索引
var dedup_indices = [];
var dedup_count = 0;

// 目录区检测
var g_tocStartIdx = -1;
var g_tocEndIdx = -1;
var g_tocChapterCount = 0;

// 广告清理（默认关闭：用户自行确认是否清理）
var g_cleanAds = false;
var g_adRemovedCount = 0;

// 标题级去重（默认开启：同章号同标题才算重复，不同标题保留）
var g_titleDedup = true;
var g_titleDiffCount = 0;

// v3.4 统计（总-分报告用）
var g_dedupRemoved = 0;
var g_oooFixed = 0;
var g_actualVolMode = "flat";
var g_skipTitleOnly = 0;
var g_skipShortBody = 0;


// =============================================================================
// 工具函数（ES3 安全）
// =============================================================================

function debugLog(msg) {
    try { if (typeof console !== "undefined" && console && console.log) console.log(msg); } catch (e) {}
}

function Timer() {
    return (new Date()).getTime() / 1000;
}

function zeroPad(n, width) {
    var s = String(Math.floor(n));
    while (s.length < width) s = "0" + s;
    return s;
}

function padLeft(s, width) {
    s = String(s);
    while (s.length < width) s = " " + s;
    return s;
}

function padRight(s, width) {
    s = String(s);
    while (s.length < width) s = s + " ";
    if (s.length > width) s = s.substring(0, width);
    return s;
}

function repeatStr(ch, n) {
    var s = "";
    for (var i = 0; i < n; i++) s += ch;
    return s;
}

function isDigits(s) {
    if (!s || s.length === 0) return false;
    for (var i = 0; i < s.length; i++) {
        if (s.charAt(i) < '0' || s.charAt(i) > '9') return false;
    }
    return true;
}

// 自定义 trim（JScript 5.8 无 String.trim）
function trimStr(s) {
    return s.replace(/^[\s　]+|[\s　]+$/g, "");
}

// 全局替换（ES3 的 replace 字符串模式只换第一个，用 split/join 代替）
function repAll(s, from, to) {
    return s.split(from).join(to);
}

function countChineseChars(text) {
    var count = 0;
    for (var i = 0; i < text.length; i++) {
        var c = text.charCodeAt(i);
        if (c >= 0x4e00 && c <= 0x9fff) count++;
    }
    return count;
}

function containsCI(s, sub) {
    return s.toLowerCase().indexOf(sub.toLowerCase()) >= 0;
}

// 千分位数字格式 "#,##0"
function fmtThousands(n) {
    var s = String(Math.floor(n));
    var neg = false;
    if (s.charAt(0) === "-") { neg = true; s = s.substring(1); }
    var out = "";
    while (s.length > 3) {
        out = "," + s.substring(s.length - 3) + out;
        s = s.substring(0, s.length - 3);
    }
    return (neg ? "-" : "") + s + out;
}

// "0.0%" 百分比格式
function fmtPct1(x) {
    return (x * 100).toFixed(1) + "%";
}

// --- 保序字典（ES3 无 Map；键不会与 Object.prototype 成员冲突，含 "|" 或为数字） ---
function mapNew() { return { m: {}, ks: [] }; }
function mapHas(d, k) { return typeof d.m[k] !== "undefined"; }
function mapSet(d, k, v) { if (!mapHas(d, k)) d.ks.push(k); d.m[k] = v; }
function mapGet(d, k) { return d.m[k]; }
function mapCount(d) { return d.ks.length; }


// =============================================================================
// 第一部分：通用TXT编码检测与读写
// =============================================================================

function CreateCOM(name) {
    try {
        return CreateObject(name);
    } catch (e) {
        try {
            return Application.CreateObject(name);
        } catch (e2) {
            throw new Error("无法创建COM对象: " + name + "\n" + (e.message || e));
        }
    }
}

function readFileBytes(filePath) {
    var stm = CreateCOM("ADODB.Stream");
    stm.Type = 1; // adTypeBinary
    stm.Open();
    stm.LoadFromFile(filePath);
    var bin = stm.Read(-1); // adReadAll
    stm.Close();
    return new VBArray(bin).toArray();
}

function detectEncodingBytes(bytes) {
    if (!bytes || bytes.length === 0) return "ANSI";

    // BOM 检测
    if (bytes.length >= 2) {
        if (bytes[0] === 0xFF && bytes[1] === 0xFE) return "UTF-16LE";
        if (bytes[0] === 0xFE && bytes[1] === 0xFF) return "UTF-16BE";
    }
    if (bytes.length >= 3) {
        if (bytes[0] === 0xEF && bytes[1] === 0xBB && bytes[2] === 0xBF) return "UTF-8 BOM";
    }

    // 无BOM：三段采样判断 UTF-8 vs ANSI
    var totalLen = bytes.length;
    var scanLen = 100;
    var segs = [];
    if (totalLen < scanLen * 3) {
        segs.push([0, totalLen - 1]);
    } else {
        var midStart = Math.floor(totalLen / 2) - Math.floor(scanLen / 2);
        if (midStart < scanLen) midStart = scanLen;
        segs.push([0, scanLen - 1]);
        segs.push([midStart, midStart + scanLen - 1]);
        segs.push([totalLen - scanLen, totalLen - 1]);
    }
    for (var g = 0; g < segs.length; g++) {
        var r = scanBytesForEncoding(bytes, segs[g][0], segs[g][1]);
        if (r.length > 0) return r;
    }
    return "ANSI";
}

function scanBytesForEncoding(bytes, startIdx, endIdx) {
    if (startIdx < 0) startIdx = 0;
    if (endIdx > bytes.length - 1) endIdx = bytes.length - 1;
    for (var i = startIdx; i <= endIdx; i++) {
        if (bytes[i] > 0x7F) {
            var b1 = bytes[i];
            if ((b1 & 0xC0) === 0x80) continue;
            if ((b1 & 0xF0) === 0xE0) {
                if (i + 2 < bytes.length &&
                    (bytes[i + 1] & 0xC0) === 0x80 &&
                    (bytes[i + 2] & 0xC0) === 0x80) {
                    return "UTF-8";
                }
                return "ANSI";
            }
            if ((b1 & 0xF8) === 0xF0) {
                if (i + 3 < bytes.length &&
                    (bytes[i + 1] & 0xC0) === 0x80 &&
                    (bytes[i + 2] & 0xC0) === 0x80 &&
                    (bytes[i + 3] & 0xC0) === 0x80) {
                    return "UTF-8";
                }
                return "ANSI";
            }
            if ((b1 & 0xE0) === 0xC0) {
                if (i + 1 < bytes.length && (bytes[i + 1] & 0xC0) === 0x80) {
                    return "UTF-8";
                }
                return "ANSI";
            }
            return "ANSI";
        }
    }
    return "";
}

function detectEncodingFile(filePath) {
    var bytes = readFileBytes(filePath);
    return detectEncodingBytes(bytes);
}

function readTextANSI(filePath) {
    var stm = CreateCOM("ADODB.Stream");
    stm.Type = 2; // adTypeText
    stm.Charset = "gbk";
    stm.Open();
    stm.LoadFromFile(filePath);
    var text = stm.ReadText(-1); // adReadAll
    stm.Close();
    return text;
}

function readTextUTF8(filePath) {
    var stm = CreateCOM("ADODB.Stream");
    stm.Type = 2; // adTypeText
    stm.Charset = "utf-8";
    stm.Open();
    stm.LoadFromFile(filePath);
    var text = stm.ReadText(-1);
    stm.Close();
    return text;
}

function readTextUTF16(filePath) {
    var fso = CreateCOM("Scripting.FileSystemObject");
    var ts = fso.OpenTextFile(filePath, 1, false, -1); // TristateTrue (Unicode)
    var text = ts.ReadAll();
    ts.Close();
    return text;
}

function readTextAuto(filePath) {
    var enc = detectEncodingFile(filePath);
    switch (enc) {
        case "ANSI":
            return readTextANSI(filePath);
        case "UTF-8 BOM":
        case "UTF-8":
            return readTextUTF8(filePath);
        case "UTF-16LE":
        case "UTF-16BE":
            return readTextUTF16(filePath);
        default:
            return readTextUTF8(filePath);
    }
}

function writeTextUTF8NoBOM(filePath, text) {
    var stm = CreateCOM("ADODB.Stream");
    stm.Type = 2; // adTypeText
    stm.Charset = "utf-8";
    stm.Open();
    stm.WriteText(text);
    // 切二进制模式剥离BOM
    stm.Position = 0;
    stm.Type = 1; // adTypeBinary
    stm.Position = 3; // 跳过 UTF-8 BOM (EF BB BF)
    var bin = stm.Read(-1);
    stm.Close();

    var stm2 = CreateCOM("ADODB.Stream");
    stm2.Type = 1;
    stm2.Open();
    stm2.Write(bin);
    stm2.SaveToFile(filePath, 2); // adSaveCreateOverWrite
    stm2.Close();
}

function selectTxtFile(title) {
    // 尝试 Application.FileDialog
    try {
        var fd = Application.FileDialog(3); // msoFileDialogFilePicker
        if (fd) {
            fd.Title = title;
            try { fd.Filters.Clear(); } catch (e) {}
            try { fd.Filters.Add("文本文件", "*.txt"); } catch (e2) {}
            if (fd.Show() === -1) {
                return fd.SelectedItems(1);
            }
            return "";
        }
    } catch (e3) {}

    // 尝试 GetOpenFilename
    try {
        var result = Application.GetOpenFilename("文本文件 (*.txt), *.txt", undefined, title);
        if (result === false) return "";
        return String(result);
    } catch (e4) {}

    // 兜底：InputBox
    var input = Application.InputBox("请输入TXT文件完整路径：", title, "", 100, 100, "", 0, 2);
    if (input === false) return "";
    return String(input);
}


// =============================================================================
// 第二部分：注册表设置（v3.4 新增，替代 VBA SaveSetting）
// =============================================================================

function regReadSafe(name, defVal) {
    try {
        var sh = CreateCOM("WScript.Shell");
        return String(sh.RegRead("HKCU\\Software\\SplitTxtV3\\" + name));
    } catch (e) {
        return defVal;
    }
}

function regWriteSafe(name, val) {
    try {
        var sh = CreateCOM("WScript.Shell");
        sh.RegWrite("HKCU\\Software\\SplitTxtV3\\" + name, String(val), "REG_SZ");
        return true;
    } catch (e) {
        return false;
    }
}

function LoadSettings() {
    var sAd = regReadSafe("AdClean", "0");
    var sTitle = regReadSafe("TitleDedup", "1");
    var sVol = regReadSafe("VolMode", "1");

    g_cleanAds = (sAd === "1");
    g_titleDedup = (sTitle === "1");
    if (sVol === "2") {
        g_volumeMode = "flat";
    } else if (sVol === "3") {
        g_volumeMode = "by_volume";
    } else {
        g_volumeMode = "auto";
    }
}

function 设置TXTv3() {
    var sAd = regReadSafe("AdClean", "0");
    var sTitle = regReadSafe("TitleDedup", "1");
    var sVol = regReadSafe("VolMode", "1");

    var prompt = "默认设置（当前值 " + sAd + "," + sTitle + "," + sVol + "）：\n\n" +
                 "  第1位 广告/垃圾行清理：0=不清理(默认) 1=清理\n" +
                 "  第2位 标题级去重：1=双重判定(默认，章号+标题) 0=仅章号\n" +
                 "  第3位 卷级别处理：1=自动判定(默认) 2=强制扁平 3=按卷分目录\n\n" +
                 "输入格式 0,1,1（直接回车=保持不变）：";

    var inputVal = Application.InputBox(prompt, "设置TXTv3 - 默认设置", sAd + "," + sTitle + "," + sVol, 100, 100, "", 0, 2);
    if (inputVal === false) return;

    inputVal = normalizeSeparators(String(inputVal));
    inputVal = repAll(trimStr(inputVal), " ", ",");
    if (inputVal.length === 0) return;

    var parts = inputVal.split(",");
    var newAd = sAd, newTitle = sTitle, newVol = sVol;
    if (parts.length >= 1) {
        var p0 = trimStr(parts[0]);
        if (p0 === "0" || p0 === "1") newAd = p0;
    }
    if (parts.length >= 2) {
        var p1 = trimStr(parts[1]);
        if (p1 === "0" || p1 === "1") newTitle = p1;
    }
    if (parts.length >= 3) {
        var p2 = trimStr(parts[2]);
        if (p2 === "1" || p2 === "2" || p2 === "3") newVol = p2;
    }

    regWriteSafe("AdClean", newAd);
    regWriteSafe("TitleDedup", newTitle);
    regWriteSafe("VolMode", newVol);

    Application.MsgBox("设置已保存：\n\n" +
                       "  广告/垃圾行清理：" + newAd + "\n" +
                       "  标题级去重：" + newTitle + "\n" +
                       "  卷级别处理：" + newVol, vbInformation, "设置完成");
}


// =============================================================================
// 第三部分：正则初始化与选择
// =============================================================================

function InitRegexPatterns() {
    g_regexCount = 0;

    // 1. 标准中文（终极数字字符类 + 多单位词）
    g_regexCount++;
    g_regexNames[g_regexCount] = "标准中文（第N章/回/节/卷，含中文数字含〇含大写）";
    g_regexPatterns[g_regexCount] = "^[ \\t　]*第([0-9０-９一二三四五六七八九十百千万亿億零〇○两兩壹貳贰叁參肆伍陸陆柒捌玖拾佰仟廿卅卌皕萬]+)(章|回|节|卷)(?:[ \\t　：:]+(.*))?$";
    g_regexUnitGroups[g_regexCount] = 1;
    g_regexDefaultUnits[g_regexCount] = "章";
    g_regexMaxLens[g_regexCount] = 0;

    // 2. 无第字中文（全数字字符类 + 多单位词）
    g_regexCount++;
    g_regexNames[g_regexCount] = "无第字中文（N章/回/节/卷，含中文数字）";
    g_regexPatterns[g_regexCount] = "^[ \\t　]*([0-9０-９一二三四五六七八九十百千万亿億零〇○两兩壹貳贰叁參肆伍陸陆柒捌玖拾佰仟廿卅卌皕萬]+)(章|回|节|卷)(?:[ \\t　：:]+(.*))?$";
    g_regexUnitGroups[g_regexCount] = 1;
    g_regexDefaultUnits[g_regexCount] = "章";
    g_regexMaxLens[g_regexCount] = 0;

    // 3. 英文Chapter
    g_regexCount++;
    g_regexNames[g_regexCount] = "英文Chapter（Chapter N - Title）";
    g_regexPatterns[g_regexCount] = "^[ \\t　]*[Cc]hapter\\s+([0-9０-９]+)(?:[ \\t　]*[:\\.\\-]?[ \\t　]+(.*))?$";
    g_regexUnitGroups[g_regexCount] = -1;
    g_regexDefaultUnits[g_regexCount] = "Chapter";
    g_regexMaxLens[g_regexCount] = 0;

    // 4. 无号特殊章节
    g_regexCount++;
    g_regexNames[g_regexCount] = "无号特殊章节（序章/楔子/番外/…）";
    g_regexPatterns[g_regexCount] = "^[ \\t　]*(序章|楔子|尾声|番外|引子|后记|终章|序言|前言|跋)(?:[ \\t　：:]+(.*))?$";
    g_regexUnitGroups[g_regexCount] = -1;
    g_regexDefaultUnits[g_regexCount] = "章";
    g_regexMaxLens[g_regexCount] = 0;

    // 5. 纯数字起始
    g_regexCount++;
    g_regexNames[g_regexCount] = "纯数字起始（3-4位数字开头，如 001 标题）";
    g_regexPatterns[g_regexCount] = "^[ \\t　]*([0-9０-９]{3,4})(?:[ \\t　：:]+(.*))?$";
    g_regexUnitGroups[g_regexCount] = -1;
    g_regexDefaultUnits[g_regexCount] = "章";
    g_regexMaxLens[g_regexCount] = 60;

    // 6. 宽泛通配（第N + 任意内容 + 单位词，处理特殊格式）
    g_regexCount++;
    g_regexNames[g_regexCount] = "宽泛通配（第N…章/回/节/卷，数字与单位词间可含内容）";
    g_regexPatterns[g_regexCount] = "^[ \\t　]*第([0-9０-９一二三四五六七八九十百千万亿億零〇○两兩壹貳贰叁參肆伍陸陆柒捌玖拾佰仟廿卅卌皕萬]+).*?(章|回|节|卷).*$";
    g_regexUnitGroups[g_regexCount] = 1;
    g_regexDefaultUnits[g_regexCount] = "章";
    g_regexMaxLens[g_regexCount] = 100;

    // 7. 超宽泛（可选第字 + 可选单位词 + 行长度限制，防止误匹配正文）
    g_regexCount++;
    g_regexNames[g_regexCount] = "超宽泛（第/N + 章/回/节/卷/篇/集/话，限80字内）";
    g_regexPatterns[g_regexCount] = "^[ \\t　]*(?:第)?([0-9０-９一二三四五六七八九十百千万亿億零〇○两兩壹貳贰叁參肆伍陸陆柒捌玖拾佰仟廿卅卌皕萬]+)[章回节卷篇集话部季册]?.*$";
    g_regexUnitGroups[g_regexCount] = -1;
    g_regexDefaultUnits[g_regexCount] = "章";
    g_regexMaxLens[g_regexCount] = 80;

    // 8. 自定义正则
    g_regexCount++;
    g_regexNames[g_regexCount] = "自定义正则（手动输入）";
    g_regexPatterns[g_regexCount] = "";
    g_regexUnitGroups[g_regexCount] = -1;
    g_regexDefaultUnits[g_regexCount] = "章";
    g_regexMaxLens[g_regexCount] = 0;
}

function normalizeSeparators(s) {
    var r = s;
    r = repAll(r, "，", ",");
    r = repAll(r, "｜", "|");
    r = repAll(r, "　", " ");
    r = repAll(r, "０", "0"); r = repAll(r, "１", "1");
    r = repAll(r, "２", "2"); r = repAll(r, "３", "3");
    r = repAll(r, "４", "4"); r = repAll(r, "５", "5");
    r = repAll(r, "６", "6"); r = repAll(r, "７", "7");
    r = repAll(r, "８", "8"); r = repAll(r, "９", "9");
    return r;
}

// 正则选择对话框（支持多选），返回 bool
function SelectRegexPattern() {
    var prompt = "请选择章节正则表达式（可多选并列）：\n\n";
    for (var i = 1; i <= g_regexCount; i++) {
        prompt += "  " + i + ". " + g_regexNames[i] + "\n";
    }
    prompt += "\n输入格式：\n" +
              "  单选:  1\n" +
              "  多选:  1,2,3  或  1 2 3\n" +
              "  示例:  1,2,4    同时使用 标准中文 + 无第字中文 + 无号特殊章节\n\n" +
              "请输入序号：";

    var inputVal = Application.InputBox(prompt, "选择正则表达式（可多选）", "1,2,4", 100, 100, "", 0, 2);
    if (inputVal === false) return false;

    inputVal = normalizeSeparators(String(inputVal));
    inputVal = repAll(trimStr(inputVal), " ", ",");
    while (inputVal.indexOf(",,") >= 0) {
        inputVal = repAll(inputVal, ",,", ",");
    }
    if (inputVal.charAt(0) === ",") inputVal = inputVal.substring(1);
    if (inputVal.charAt(inputVal.length - 1) === ",") inputVal = inputVal.substring(0, inputVal.length - 1);
    if (inputVal.length === 0) {
        Application.MsgBox("未输入序号。", vbExclamation, "提示");
        return false;
    }

    var parts = inputVal.split(",");
    var p, idx;
    var hasCustom = false;

    for (p = 0; p < parts.length; p++) {
        if (!isDigits(trimStr(parts[p]))) {
            Application.MsgBox("包含无效数字：" + parts[p], vbExclamation, "提示");
            return false;
        }
        idx = parseInt(trimStr(parts[p]), 10);
        if (idx < 1 || idx > g_regexCount) {
            Application.MsgBox("序号 " + idx + " 超出范围（1-" + g_regexCount + "）。", vbExclamation, "提示");
            return false;
        }
        if (idx === g_regexCount && g_regexPatterns[idx].length === 0) {
            hasCustom = true;
        }
    }

    // 处理自定义正则
    if (hasCustom) {
        // v3.6 优化：更宽泛的默认值，允许缩进+可选第字+多种单位词，减少用户输入
        var defaultPat = "^[ \\t　]*(?:第)?([0-9０-９一二三四五六七八九十百千万亿零〇○两]+)[章回节卷篇集话]?.*$";
        var customPattern = Application.InputBox("请输入自定义正则表达式：\n\n" +
                              "示例：\n" +
                              "  ^第(\\d+)章\\s*(.*)$\n" +
                              "  ^卷(\\d+)\\s*(.*)$\n\n" +
                              "默认值（宽泛匹配：缩进+可选第+章/回/节/卷等）：\n" +
                              "  " + defaultPat + "\n\n" +
                              "提示：数字建议写 [0-9０-９] 同时匹配半角/全角。",
                              "自定义正则", defaultPat, 100, 100, "", 0, 2);
        if (customPattern === false) return false;
        customPattern = trimStr(String(customPattern));
        if (customPattern.length === 0) return false;
        g_regexPatterns[g_regexCount] = customPattern;
    }

    // 填充选中数组 + 验证
    g_selPatterns = [];
    g_selUnitGroups = [];
    g_selDefaultUnits = [];
    g_selOrigIndices = [];
    g_selMaxLens = [];
    g_selCount = 0;
    var nameParts = [];

    for (p = 0; p < parts.length; p++) {
        idx = parseInt(trimStr(parts[p]), 10);
        g_selPatterns[g_selCount] = g_regexPatterns[idx];
        g_selUnitGroups[g_selCount] = g_regexUnitGroups[idx];
        g_selDefaultUnits[g_selCount] = g_regexDefaultUnits[idx];
        g_selOrigIndices[g_selCount] = idx;
        g_selMaxLens[g_selCount] = g_regexMaxLens[idx];
        nameParts[g_selCount] = g_regexNames[idx];

        try {
            var reTest = new RegExp(g_selPatterns[g_selCount], "i");
            reTest.test("test");
        } catch (e) {
            Application.MsgBox("正则[" + idx + "]错误：" + (e.message || e) + "\n\n" +
                               "正则：" + g_selPatterns[g_selCount], vbExclamation, "正则错误");
            return false;
        }
        g_selCount++;
    }

    g_regexName = nameParts.join(" + ");
    if (g_selCount > 1) {
        g_regexName = g_selCount + "套正则: " + g_regexName;
    }

    debugLog("[正则选择] " + g_selCount + "套: " + g_regexName);
    return true;
}

// v3.4：去重+排序组合选择（一次六选一）
function SelectDedupSortCombo() {
    var dedupArr = ["none", "none", "first", "first", "longest", "longest"];
    var sortArr = ["none", "sort", "none", "sort", "none", "sort"];

    var prompt = "【步骤3/4】请选择去重+排序组合：\n\n" +
                 "  1. 不去重 + 不排序（原样保留）\n" +
                 "  2. 不去重 + 排序（仅按章号重排）\n" +
                 "  3. 保留首次 + 不排序\n" +
                 "  4. 保留首次 + 排序\n" +
                 "  5. 保留最长 + 不排序\n" +
                 "  6. 保留最长 + 排序 ★推荐\n\n" +
                 "说明：乱序严重选排序；想保留最全内容选保留最长。\n\n" +
                 "请输入序号：";

    var inputVal = Application.InputBox(prompt, "选择去重+排序组合", "6", 100, 100, "", 0, 2);
    if (inputVal === false) return false;

    inputVal = trimStr(String(inputVal));
    if (!isDigits(inputVal)) {
        Application.MsgBox("请输入数字序号。", vbExclamation, "提示");
        return false;
    }

    var i = parseInt(inputVal, 10) - 1;
    if (i < 0 || i > 5) {
        Application.MsgBox("序号超出范围（1-6）。", vbExclamation, "提示");
        return false;
    }

    g_dedupStrategy = dedupArr[i];
    g_sortStrategy = sortArr[i];
    debugLog("[去重+排序组合] 去重=" + g_dedupStrategy + " 排序=" + g_sortStrategy);
    return true;
}


// =============================================================================
// 第四部分：中文数字转阿拉伯数字
// =============================================================================

var CN_NUM_MAP = null;
function getCnNumMap() {
    if (CN_NUM_MAP) return CN_NUM_MAP;
    var d = {};
    d["零"] = 0; d["〇"] = 0; d["○"] = 0;
    d["一"] = 1; d["二"] = 2; d["三"] = 3; d["四"] = 4;
    d["五"] = 5; d["六"] = 6; d["七"] = 7; d["八"] = 8; d["九"] = 9;
    d["十"] = 10; d["百"] = 100; d["千"] = 1000;
    d["万"] = 10000; d["亿"] = 100000000;
    d["兩"] = 2; d["两"] = 2;
    d["壹"] = 1; d["貳"] = 2; d["贰"] = 2;
    d["參"] = 3; d["叁"] = 3; d["肆"] = 4; d["伍"] = 5;
    d["陸"] = 6; d["陆"] = 6; d["柒"] = 7; d["捌"] = 8; d["玖"] = 9;
    d["拾"] = 10; d["佰"] = 100; d["仟"] = 1000;
    d["萬"] = 10000; d["億"] = 100000000;
    d["廿"] = 20; d["卅"] = 30; d["卌"] = 40; d["皕"] = 200;
    CN_NUM_MAP = d;
    return d;
}

function CnToInt(s) {
    var cnNum = getCnNumMap();
    var ss = trimStr(s);
    // 全角转半角
    for (var i = 0; i <= 9; i++) {
        ss = repAll(ss, String.fromCharCode(0xFF10 + i), String(i));
    }
    // 纯数字直接转（防溢出：超过10位返回0）
    if (isDigits(ss)) {
        if (ss.length > 10) return 0;
        return parseInt(ss, 10);
    }

    var total = 0, section = 0, current = 0, lastDigit = 0;
    for (i = 0; i < ss.length; i++) {
        var ch = ss.charAt(i);
        if (typeof cnNum[ch] === "undefined") continue;
        var val = cnNum[ch];
        if (val < 10) {
            lastDigit = val;
        } else if (val === 10) {
            current += (lastDigit > 0) ? lastDigit * 10 : 10;
            lastDigit = 0;
        } else if (val === 100) {
            current += (lastDigit > 0) ? lastDigit * 100 : 100;
            lastDigit = 0;
        } else if (val === 1000) {
            current += (lastDigit > 0) ? lastDigit * 1000 : 1000;
            lastDigit = 0;
        } else if (val === 10000) {
            if (lastDigit > 0) { current += lastDigit; lastDigit = 0; }
            section = (section + current) * 10000;
            current = 0;
        } else if (val === 100000000) {
            if (lastDigit > 0) { current += lastDigit; lastDigit = 0; }
            total = (total + section + current) * 100000000;
            section = 0; current = 0;
        }
    }

    if (lastDigit > 0) current += lastDigit;
    return total + section + current;
}


// =============================================================================
// 第五部分：增强章节扫描（卷识别+章号提取）
// =============================================================================

function GetVolumePattern() {
    return "^[ \\t　]*第([0-9０-９一二三四五六七八九十百千万亿億零〇○两兩壹貳贰叁參肆伍陸陆柒捌玖拾佰仟廿卅卌皕萬]+)(卷|部|册|篇|集|季)(?:[ \\t　：:]+(.*))?$";
}

// 行归一化（仅用于正则匹配，不影响原始内容）
function normalizeLineForMatch(s) {
    var r = s;
    // 1. 全角数字 → 半角
    for (var i = 0; i <= 9; i++) {
        r = repAll(r, String.fromCharCode(0xFF10 + i), String(i));
    }
    // 2. 全角空格 → 半角空格
    r = repAll(r, "　", " ");
    // 3. 全角冒号 → 半角冒号
    r = repAll(r, "：", ":");
    // 4. 不可见字符清理
    r = repAll(r, "​", "");
    r = repAll(r, "‌", "");
    r = repAll(r, "‍", "");
    r = repAll(r, "﻿", "");
    // 5. Tab → 空格
    r = repAll(r, "\t", " ");
    // 6. 压缩连续空格
    var result = "";
    var prevSpace = false;
    for (i = 0; i < r.length; i++) {
        var c = r.charAt(i);
        if (c === " ") {
            if (!prevSpace) { result += c; prevSpace = true; }
        } else {
            result += c; prevSpace = false;
        }
    }
    return result;
}

// 标题规范化（标题级去重的键生成）
function NormalizeTitle(s) {
    var r = trimStr(s);
    var i;
    // 1. 全角数字 → 半角
    for (i = 0; i <= 9; i++) {
        r = repAll(r, String.fromCharCode(0xFF10 + i), String(i));
    }
    // 2. 全角字母 → 半角
    for (i = 0; i < 26; i++) {
        r = repAll(r, String.fromCharCode(0xFF41 + i), String.fromCharCode(97 + i));
        r = repAll(r, String.fromCharCode(0xFF21 + i), String.fromCharCode(65 + i));
    }
    // 3. 空白删除
    r = repAll(r, "　", "");
    r = repAll(r, " ", "");
    r = repAll(r, "\t", "");
    // 4. 全角标点删除
    r = repAll(r, "：", ""); r = repAll(r, "；", "");
    r = repAll(r, "，", ""); r = repAll(r, "。", "");
    r = repAll(r, "、", "");
    // 5. 零宽字符
    r = repAll(r, "​", ""); r = repAll(r, "‌", "");
    r = repAll(r, "‍", ""); r = repAll(r, "﻿", "");
    // 6. 半角标点删除
    var halfPunct = [",", ".", ":", ";", "!", "?", "'", "\"", "(", ")", "[", "]", "<", ">", "-", "_"];
    for (i = 0; i < halfPunct.length; i++) r = repAll(r, halfPunct[i], "");
    // 7. 中文标点删除
    var cnPunct = ["（", "）", "《", "》", "【", "】", "「", "」", "『", "』", "！", "？", "·", "…", "—", "～"];
    for (i = 0; i < cnPunct.length; i++) r = repAll(r, cnPunct[i], "");
    // 8. 转小写
    return r.toLowerCase();
}

// 增强版章节扫描
function ScanChaptersV3(lines) {
    var lineCount = lines.length;
    var i, r;

    // 回退默认
    if (g_selCount === 0) {
        g_selPatterns = ["^[ \\t　]*第([0-9０-９一二三四五六七八九十百千万亿億零〇○两兩壹貳贰叁參肆伍陸陆柒捌玖拾佰仟廿卅卌皕萬]+)(章|回|节|卷)(?:[ \\t　：:]+(.*))?$"];
        g_selUnitGroups = [1];
        g_selDefaultUnits = ["章"];
        g_selOrigIndices = [1];
        g_selCount = 1;
        g_regexName = "标准中文（默认回退）";
    }

    // 初始化数组
    ch_starts = []; ch_ends = []; ch_titles = [];
    ch_nums = []; ch_vols = []; ch_units = [];
    ch_levels = []; ch_patterns = []; ch_bodyLines = []; ch_isTOC = [];
    ch_count = 0;
    ch_unit = g_selDefaultUnits[0];

    // 重置目录区检测
    g_tocStartIdx = -1;
    g_tocEndIdx = -1;
    g_tocChapterCount = 0;

    // 预编译正则
    var regVol = new RegExp(GetVolumePattern(), "i");
    var regs = [];
    for (r = 0; r < g_selCount; r++) {
        regs.push(new RegExp(g_selPatterns[r], "i"));
    }

    var currentVol = 0;
    var currentVolUnit = "";

    for (i = 0; i < lineCount; i++) {
        var line = lines[i];
        if (trimStr(line).length === 0) continue;

        var normLine = normalizeLineForMatch(line);
        var matched = false;
        var matchRegIdx = -1;
        var m;

        // 先检查卷级标题
        m = regVol.exec(normLine);
        if (m) {
            var vNumStr = m[1];
            var vUnitStr = m[2];
            var vNum = CnToInt(vNumStr);

            currentVol = vNum;
            currentVolUnit = vUnitStr;

            if (ch_count > 0) ch_ends[ch_count - 1] = i - 1;
            ch_starts[ch_count] = i;
            ch_ends[ch_count] = i;
            ch_titles[ch_count] = trimStr(m[0]);
            ch_nums[ch_count] = 0;
            ch_vols[ch_count] = vNum;
            ch_units[ch_count] = vUnitStr;
            ch_levels[ch_count] = "volume";
            ch_patterns[ch_count] = "volume";
            ch_bodyLines[ch_count] = 0;
            ch_isTOC[ch_count] = false;
            ch_count++;
            continue;
        }

        // 再检查章节级正则
        for (r = 0; r < g_selCount; r++) {
            // v3.6：行长度限制检查（超宽泛正则等有限制的，超长行跳过，防止误匹配正文）
            if (g_selMaxLens[r] > 0 && normLine.length > g_selMaxLens[r]) continue;
            if (regs[r].test(normLine)) {
                matched = true;
                matchRegIdx = r;
                break;
            }
        }

        if (matched) {
            m = regs[matchRegIdx].exec(normLine);
            var fullTitle = trimStr(m[0]);
            var numStr, chNum, unitStr;

            if (g_selUnitGroups[matchRegIdx] >= 0) {
                // 有单位组：数字组是 m[1]
                if (m.length >= 2 && typeof m[1] !== "undefined") {
                    numStr = m[1];
                    chNum = CnToInt(numStr);
                } else {
                    chNum = 0;
                }
                var ug = g_selUnitGroups[matchRegIdx];
                if (m.length - 1 > ug && typeof m[ug + 1] !== "undefined") {
                    unitStr = m[ug + 1];
                } else {
                    unitStr = g_selDefaultUnits[matchRegIdx];
                }
            } else {
                // 无单位组：尝试从第一个子匹配提取数字
                chNum = 0;
                if (m.length >= 2 && typeof m[1] !== "undefined") {
                    numStr = m[1];
                    if (isDigits(repAll(numStr, "０", "0"))) {
                        chNum = CnToInt(numStr);
                    }
                }
                unitStr = g_selDefaultUnits[matchRegIdx];
            }

            // 判断是否为无号特殊章节
            var lvl = "chapter";
            var patType = "standard";
            if (chNum === 0) {
                if (g_selOrigIndices[matchRegIdx] === 4) {
                    lvl = "special";
                    patType = "no_num";
                }
            }

            if (ch_count === 0) ch_unit = unitStr;

            if (ch_count > 0) ch_ends[ch_count - 1] = i - 1;
            ch_starts[ch_count] = i;
            ch_ends[ch_count] = i;
            ch_titles[ch_count] = fullTitle;
            ch_nums[ch_count] = chNum;
            ch_vols[ch_count] = currentVol;
            ch_units[ch_count] = unitStr;
            ch_levels[ch_count] = lvl;
            ch_patterns[ch_count] = patType;
            ch_bodyLines[ch_count] = 0;
            ch_isTOC[ch_count] = false;
            ch_count++;
        }
    }

    if (ch_count > 0) ch_ends[ch_count - 1] = lineCount - 1;

    // 计算正文行数
    for (i = 0; i < ch_count; i++) {
        if (ch_ends[i] >= ch_starts[i]) {
            ch_bodyLines[i] = ch_ends[i] - ch_starts[i];
        } else {
            ch_bodyLines[i] = 0;
        }
    }
    
    // v3.6 优化：一次预计算字符数+汉字数，后续所有环节直接读取
    PrecomputeChapterCounts(lines);
}

// v3.6 优化：预计算每章的字符数和汉字数（一次遍历，后续所有环节复用）
//   性能收益：消除 AutoN、清洁模式、预计算字数 三处的重复行遍历
//   复杂度：O(总行数)，一次性完成
function PrecomputeChapterCounts(lines) {
    if (ch_count === 0) return;
    var i, j, nLines, curChar, curHanzi;
    ch_charCounts = new Array(ch_count);
    ch_hanziCounts = new Array(ch_count);
    
    for (i = 0; i < ch_count; i++) {
        nLines = ch_ends[i] - ch_starts[i] + 1;
        if (nLines < 1) nLines = 1;
        
        curChar = 0;
        curHanzi = 0;
        
        // 逐行累计：字符数（含换行）+ 汉字数
        for (j = ch_starts[i]; j <= ch_ends[i]; j++) {
            curChar += lines[j].length;
            // 正文行（标题行之后）才计汉字
            if (j > ch_starts[i]) {
                curHanzi += countChineseChars(lines[j]);
            }
        }
        
        // 加上换行符数
        if (nLines > 1) curChar += (nLines - 1);
        
        ch_charCounts[i] = curChar;
        ch_hanziCounts[i] = curHanzi;
    }
}

// v3.2：目录区自动检测
function DetectTOC(minTOCchapters, maxBodyLines) {
    if (typeof minTOCchapters === "undefined") minTOCchapters = 10;
    if (typeof maxBodyLines === "undefined") maxBodyLines = 2;

    g_tocStartIdx = -1;
    g_tocEndIdx = -1;
    g_tocChapterCount = 0;

    if (ch_count < minTOCchapters) return;

    var i, bodyLn;

    // 先计算正文行数
    for (i = 0; i < ch_count; i++) {
        if (ch_levels[i] === "chapter" || ch_levels[i] === "special") {
            bodyLn = ch_ends[i] - ch_starts[i];
            if (bodyLn < 0) bodyLn = 0;
            ch_bodyLines[i] = bodyLn;
        }
    }

    // 从头扫描，找第一段连续的短正文章节
    var inTOC = false;
    var consecCount = 0;
    var prevNum = 0;
    var chapStart = -1;
    var done = false;

    for (i = 0; i < ch_count && !done; i++) {
        if (ch_levels[i] !== "chapter") continue;

        bodyLn = ch_bodyLines[i];

        if (bodyLn <= maxBodyLines) {
            if (!inTOC) {
                // 检查是否在文件开头位置（前30%的章节内）
                if (i > ch_count * 0.3) break;
                chapStart = i;
                consecCount = 1;
                prevNum = ch_nums[i];
                inTOC = true;
            } else {
                if (ch_nums[i] > prevNum || ch_nums[i] === 0) {
                    consecCount++;
                    prevNum = ch_nums[i];
                } else {
                    if (consecCount >= minTOCchapters) {
                        g_tocStartIdx = chapStart;
                        g_tocEndIdx = i - 1;
                        g_tocChapterCount = consecCount;
                        done = true;
                    } else {
                        inTOC = false;
                        consecCount = 0;
                        chapStart = -1;
                    }
                }
            }
        } else {
            if (inTOC) {
                if (consecCount >= minTOCchapters) {
                    g_tocStartIdx = chapStart;
                    g_tocEndIdx = i - 1;
                    g_tocChapterCount = consecCount;
                    done = true;
                } else {
                    inTOC = false;
                    consecCount = 0;
                    chapStart = -1;
                }
            }
        }
    }

    // 循环结束时还在 TOC 中
    if (!done && inTOC && consecCount >= minTOCchapters) {
        g_tocStartIdx = chapStart;
        g_tocEndIdx = ch_count - 1;
        g_tocChapterCount = consecCount;
    }

    // 标记 TOC 章节
    if (g_tocChapterCount > 0) {
        for (i = g_tocStartIdx; i <= g_tocEndIdx; i++) {
            ch_isTOC[i] = true;
        }
    }
}

// 获取仅章节（排除volume，排除目录区）的原索引数组
function GetChapterIndices() {
    var out = [];
    for (var i = 0; i < ch_count; i++) {
        if ((ch_levels[i] === "chapter" || ch_levels[i] === "special") && !ch_isTOC[i]) {
            out.push(i);
        }
    }
    return out;
}


// =============================================================================
// 第六部分：去重策略与排序
// =============================================================================

// 去重键（卷感知 + 可选标题级）
function DedupKey(idx, volMode, titleDedup) {
    var chNum = ch_nums[idx];
    var volNum = ch_vols[idx];
    var unitStr = ch_units[idx];
    var key;

    if (volMode === "flat" || volNum === 0) {
        key = "F|" + chNum + "|" + unitStr;
    } else {
        key = "V|" + volNum + "|" + chNum + "|" + unitStr;
    }

    if (titleDedup && chNum > 0) {
        key += "|T|" + NormalizeTitle(ch_titles[idx]);
    }
    return key;
}

// 策略1：保留首次出现
function DedupFirst(volMode, titleDedup) {
    var chapIdx = GetChapterIndices();
    if (chapIdx.length === 0) return [];

    var seen = mapNew();
    var out = [];

    for (var i = 0; i < chapIdx.length; i++) {
        var key;
        if (ch_levels[chapIdx[i]] === "special") {
            key = "S|" + ch_titles[chapIdx[i]];
        } else {
            key = DedupKey(chapIdx[i], volMode, titleDedup);
        }
        if (!mapHas(seen, key)) {
            mapSet(seen, key, 1);
            out.push(chapIdx[i]);
        }
    }
    return out;
}

// 策略2：保留内容最长的
function DedupLongest(volMode, titleDedup) {
    var chapIdx = GetChapterIndices();
    if (chapIdx.length === 0) return [];

    var best = mapNew();   // key -> 最优原索引
    var order = [];        // 键出现顺序

    for (var i = 0; i < chapIdx.length; i++) {
        var key;
        if (ch_levels[chapIdx[i]] === "special") {
            key = "S|" + ch_titles[chapIdx[i]];
        } else {
            key = DedupKey(chapIdx[i], volMode, titleDedup);
        }
        if (!mapHas(best, key)) {
            mapSet(best, key, chapIdx[i]);
            order.push(key);
        } else {
            if (ch_bodyLines[chapIdx[i]] > ch_bodyLines[mapGet(best, key)]) {
                mapSet(best, key, chapIdx[i]);
            }
        }
    }

    var out = [];
    for (i = 0; i < order.length; i++) {
        out.push(mapGet(best, order[i]));
    }
    return out;
}

// 执行去重（调度）
function ApplyDedup(strategy, volMode, titleDedup) {
    if (strategy === "none") {
        dedup_indices = GetChapterIndices();
        dedup_count = dedup_indices.length;
        return;
    }
    var out = null;
    if (strategy === "first") {
        out = DedupFirst(volMode, titleDedup);
    } else if (strategy === "longest") {
        out = DedupLongest(volMode, titleDedup);
    } else {
        Application.MsgBox("未知去重策略：" + strategy, vbExclamation, "错误");
        dedup_indices = [];
        dedup_count = 0;
        return;
    }
    dedup_indices = out;
    dedup_count = out.length;
}

// 排序（在去重结果基础上）
function ApplySort(strategy, volMode) {
    if (strategy === "none") return;
    if (strategy === "lis") {
        SortLISFromIndices(volMode);
    } else if (strategy === "sort") {
        SortFullFromIndices(volMode);
    } else {
        Application.MsgBox("未知排序策略：" + strategy, vbExclamation, "错误");
        dedup_count = 0;
    }
}

// LIS 排序（O(n log n)，键=(卷号,章号) 严格递增）
function SortLISFromIndices(volMode) {
    var n = dedup_count;
    if (n === 0) return;

    var tailsValVol = [];
    var tailsValCh = [];
    var tailsIdx = [];
    var prevArr = [];
    var i;
    for (i = 0; i < n; i++) prevArr[i] = -1;

    var tailLen = 0;

    for (i = 0; i < n; i++) {
        var origIdx = dedup_indices[i];
        var vol_i = ch_vols[origIdx];
        var ch_i = ch_nums[origIdx];
        if (ch_i === 0) ch_i = -1;   // 无号章节放最前面
        if (volMode === "flat") vol_i = 0;

        // 二分查找：第一个 >= (vol_i, ch_i) 的位置
        var left = 0, right = tailLen;
        while (left < right) {
            var mid = Math.floor((left + right) / 2);
            if (tailsValVol[mid] < vol_i) {
                left = mid + 1;
            } else if (tailsValVol[mid] > vol_i) {
                right = mid;
            } else {
                if (tailsValCh[mid] < ch_i) {
                    left = mid + 1;
                } else {
                    right = mid;
                }
            }
        }
        var pos = left;

        if (pos === tailLen) {
            tailsValVol[tailLen] = vol_i;
            tailsValCh[tailLen] = ch_i;
            tailsIdx[tailLen] = i;
            tailLen++;
        } else {
            tailsValVol[pos] = vol_i;
            tailsValCh[pos] = ch_i;
            tailsIdx[pos] = i;
        }

        if (pos > 0) {
            prevArr[i] = tailsIdx[pos - 1];
        }
    }

    if (tailLen === 0) {
        dedup_count = 0;
        return;
    }

    // 回溯
    var resultIdx = [];
    var curr = tailsIdx[tailLen - 1];
    for (i = tailLen - 1; i >= 0; i--) {
        resultIdx[i] = dedup_indices[curr];
        if (i > 0) curr = prevArr[curr];
    }

    dedup_count = tailLen;
    for (i = 0; i < tailLen; i++) {
        dedup_indices[i] = resultIdx[i];
    }
}

// 完全重排（按 卷号,章号 冒泡排序；special 保持在前）
function SortFullFromIndices(volMode) {
    var n = dedup_count;
    if (n === 0) return;

    var keysVol = [], keysCh = [], origIdxArr = [], isSpecial = [];
    var i, j;

    for (i = 0; i < n; i++) {
        origIdxArr[i] = dedup_indices[i];
        if (ch_levels[origIdxArr[i]] === "special") {
            isSpecial[i] = true;
            keysVol[i] = 0;
            keysCh[i] = 0;
        } else {
            isSpecial[i] = false;
            keysVol[i] = ch_vols[origIdxArr[i]];
            keysCh[i] = (ch_nums[origIdxArr[i]] === 0) ? 999999 : ch_nums[origIdxArr[i]];
            if (volMode === "flat") keysVol[i] = 0;
        }
    }

    // 冒泡排序（跳过 special）
    for (i = 0; i < n - 1; i++) {
        if (isSpecial[i]) continue;
        for (j = i + 1; j < n; j++) {
            if (isSpecial[j]) continue;
            if (keysVol[i] > keysVol[j] ||
                (keysVol[i] === keysVol[j] && keysCh[i] > keysCh[j])) {
                var tv = keysVol[i]; keysVol[i] = keysVol[j]; keysVol[j] = tv;
                var tc = keysCh[i]; keysCh[i] = keysCh[j]; keysCh[j] = tc;
                var ti = origIdxArr[i]; origIdxArr[i] = origIdxArr[j]; origIdxArr[j] = ti;
                var ts = isSpecial[i]; isSpecial[i] = isSpecial[j]; isSpecial[j] = ts;
            }
        }
    }

    // 写回：special 在前，normal 在后
    var outIdx = 0;
    for (i = 0; i < n; i++) {
        if (isSpecial[i]) { dedup_indices[outIdx] = origIdxArr[i]; outIdx++; }
    }
    for (i = 0; i < n; i++) {
        if (!isSpecial[i]) { dedup_indices[outIdx] = origIdxArr[i]; outIdx++; }
    }
}

// 统计章号回退次数（仅 ch_num>0 且非目录区章节）
function CountOOO() {
    var cnt = 0, prevNum = 0;
    for (var i = 0; i < ch_count; i++) {
        if (ch_levels[i] === "chapter" && ch_nums[i] > 0 && !ch_isTOC[i]) {
            if (prevNum > 0 && ch_nums[i] < prevNum) cnt++;
            prevNum = ch_nums[i];
        }
    }
    return cnt;
}

// 统计 dedup_indices 当前顺序中的章号回退次数
function CountOOOInDedup() {
    var cnt = 0, prevNum = 0;
    for (var i = 0; i < dedup_count; i++) {
        var oIdx = dedup_indices[i];
        if (ch_nums[oIdx] > 0) {
            if (prevNum > 0 && ch_nums[oIdx] < prevNum) cnt++;
            prevNum = ch_nums[oIdx];
        }
    }
    return cnt;
}

// v3.4：自动判定清洁模式的最小正文字数 N
// v3.6 优化：直接读取预计算的汉字数，O(章节数)
function AutoNFromBodies() {
    if (ch_count === 0) return 100;

    var cnts = [];
    var i;
    for (i = 0; i < ch_count; i++) {
        if ((ch_levels[i] === "chapter" || ch_levels[i] === "special") && !ch_isTOC[i]) {
            if (ch_hanziCounts[i] > 0) {
                cnts.push(ch_hanziCounts[i]);
            }
        }
    }

    var cnt = cnts.length;
    if (cnt < 20) return 100;

    // 原生 sort（V8/Timsort，O(n log n)）
    cnts.sort(function(a, b) { return a - b; });

    // 下半区（<=中位数）找最大相邻间隔
    var lowerCnt = Math.floor(cnt / 2) + 1;
    if (lowerCnt < 2) return 100;
    var maxGap = 0, secondGap = 0, maxGapAt = -1;
    for (var k = 0; k < lowerCnt - 1; k++) {
        var gap = cnts[k + 1] - cnts[k];
        if (gap > maxGap) {
            secondGap = maxGap;
            maxGap = gap;
            maxGapAt = k;
        } else if (gap > secondGap) {
            secondGap = gap;
        }
    }

    if (maxGap < 50) return 100;
    if (secondGap > 0 && maxGap < secondGap * 2) return 100;

    // N=间隔中点取整到10，上限锁死1000
    var nResult = Math.floor((cnts[maxGapAt] + cnts[maxGapAt + 1]) / 2);
    nResult = Math.floor((nResult + 5) / 10) * 10;
    if (nResult < 50) nResult = 50;
    if (nResult > 1000) nResult = 1000;
    return nResult;
}

// 确定实际卷模式
function ResolveVolMode(mode) {
    if (mode === "flat") return "flat";
    // auto 或 by_volume：先检测是否有多卷
    var volSet = mapNew();
    for (var i = 0; i < ch_count; i++) {
        if (ch_levels[i] === "volume" && ch_vols[i] > 0) {
            if (!mapHas(volSet, ch_vols[i])) mapSet(volSet, ch_vols[i], 1);
            if (mapCount(volSet) >= 2) return "volume";
        }
    }
    return "flat";
}


// =============================================================================
// 第七部分：广告/垃圾行清理
// =============================================================================

function CleanAdLines(text) {
    var linesArr = text.split("\n");
    var out = [];
    var removed = 0;

    for (var i = 0; i < linesArr.length; i++) {
        var line = linesArr[i];
        var tline = trimStr(line);
        var isAd = false;

        if (tline.length === 0) {
            isAd = false;
        } else if (containsCI(tline, "http://") || containsCI(tline, "https://") || containsCI(tline, "www.")) {
            // 网址行
            isAd = true;
        } else if (tline.length < 60 &&
                   (containsCI(tline, ".com") || containsCI(tline, ".net") || containsCI(tline, ".cc") ||
                    containsCI(tline, ".cn") || containsCI(tline, ".org") || containsCI(tline, ".info"))) {
            // 常见域名后缀（短行确认）
            if (tline.length < 40) isAd = true;
        } else if (containsCI(tline, "记住本站") || containsCI(tline, "收藏本站") ||
                   containsCI(tline, "推荐收藏") || containsCI(tline, "手机用户") ||
                   containsCI(tline, "请访问") || containsCI(tline, "永久域名") ||
                   containsCI(tline, "最新地址") || containsCI(tline, "笔趣阁") ||
                   containsCI(tline, "顶点小说")) {
            // 站点推广语
            isAd = true;
        } else if (containsCI(tline, "本章未完") || containsCI(tline, "下一页继续") ||
                   containsCI(tline, "点击下一页") || containsCI(tline, "上一页") ||
                   containsCI(tline, "返回目录") || containsCI(tline, "加入书架")) {
            // 分页提示语
            isAd = true;
        } else if ((containsCI(tline, "求月票") || containsCI(tline, "求推荐") ||
                    containsCI(tline, "求收藏") || containsCI(tline, "求打赏") ||
                    containsCI(tline, "感谢打赏") || containsCI(tline, "感谢订阅")) &&
                   tline.length < 40) {
            // 求票/求收藏类
            isAd = true;
        } else if (tline.length >= 5) {
            // 纯符号分隔线
            var firstCh = tline.charAt(0);
            if (firstCh === "*" || firstCh === "-" || firstCh === "=" ||
                firstCh === "~" || firstCh === "·" || firstCh === "—" ||
                firstCh === "＋" || firstCh === "+") {
                var allSame = true;
                for (var j = 1; j < tline.length; j++) {
                    if (tline.charAt(j) !== firstCh) { allSame = false; break; }
                }
                if (allSame) isAd = true;
            }
        }

        if (!isAd) {
            out.push(line);
        } else {
            removed++;
        }
    }

    g_adRemovedCount += removed;
    return out.join("\n");
}


// =============================================================================
// 第八部分：聚合格式解析与展开
// =============================================================================

// 返回 { groupLens, groupSpaces, groupCount, error }
function ParseGroups(chunkStr, total) {
    var s = trimStr(chunkStr || "");
    if (s.length === 0) return { error: "聚合字符串为空" };

    var groupLens = [];
    var groupSpaces = [];
    var consumed = 0;

    // 便捷模式：纯数字
    if (s.indexOf(",") < 0 && s.indexOf("|") < 0) {
        if (!isDigits(s)) return { error: "便捷模式需为正整数: " + s };
        var n = parseInt(s, 10);
        if (n <= 0) return { error: "每份章数必须为正数: " + s };
        var cnt = Math.floor(total / n);
        if (total % n > 0) cnt++;
        groupLens.push(cnt);
        groupSpaces.push(n);
        return { groupLens: groupLens, groupSpaces: groupSpaces, groupCount: 1, error: "" };
    }

    // 多段格式：每份章数,份数|...
    var parts = s.split("|");
    for (var p = 0; p < parts.length; p++) {
        var part = trimStr(parts[p]);
        if (part.length === 0) continue;
        var detail = part.split(",");
        if (detail.length !== 2) {
            return { error: "段格式错误: " + part + "（应为 每份章数,份数）" };
        }
        var d0 = trimStr(detail[0]);
        var d1 = trimStr(detail[1]);
        if (!isDigits(d0) || !isDigits(d1)) {
            return { error: "每份章数和份数需为正整数: " + part };
        }
        var spacing = parseInt(d0, 10);
        var length = parseInt(d1, 10);
        if (length <= 0 || spacing <= 0) {
            return { error: "每份章数和份数必须为正数: " + part };
        }
        groupLens.push(length);
        groupSpaces.push(spacing);
        consumed += length * spacing;
    }

    if (consumed > total) {
        return { error: "消耗章节数 " + consumed + " 超过总章节数 " + total };
    }
    if (consumed < total) {
        groupLens.push(1);
        groupSpaces.push(total - consumed);
    }
    return { groupLens: groupLens, groupSpaces: groupSpaces, groupCount: groupLens.length, error: "" };
}

// 返回 { fileChStart, fileChEnd, fileCount }
function ExpandGroups(groupLens, groupSpaces, groupCount, total) {
    var fileChStart = [];
    var fileChEnd = [];
    var ch = 0;

    for (var g = 0; g < groupCount; g++) {
        for (var k = 0; k < groupLens[g]; k++) {
            if (ch >= total) break;
            fileChStart.push(ch + 1);
            if (ch + groupSpaces[g] < total) {
                fileChEnd.push(ch + groupSpaces[g]);
            } else {
                fileChEnd.push(total);
            }
            ch = fileChEnd[fileChEnd.length - 1];
        }
        if (ch >= total) break;
    }
    return { fileChStart: fileChStart, fileChEnd: fileChEnd, fileCount: fileChStart.length };
}


// =============================================================================
// 第九部分：共享小工具
// =============================================================================

function sanitizeFileName(name) {
    var s = repAll(name, " ", "　");
    var chars = "\\/:*?\"<>|";
    for (var k = 0; k < chars.length; k++) {
        s = repAll(s, chars.charAt(k), "　");
    }
    while (s.indexOf("　　") >= 0) {
        s = repAll(s, "　　", "　");
    }
    s = trimStr(s);
    if (s.length === 0) s = "untitled";
    if (s.length > 60) s = s.substring(0, 60);
    return s;
}

function resolveOutputDir(fso, inputPath, outputDir, suffix) {
    if (outputDir && outputDir.length > 0) return outputDir;
    return fso.GetParentFolderName(inputPath) + "\\" +
           fso.GetBaseName(inputPath) + suffix;
}

function cleanOutputDir(outDir) {
    var fso = CreateCOM("Scripting.FileSystemObject");
    if (fso.FolderExists(outDir)) {
        var folder = fso.GetFolder(outDir);
        try {
            var en = new Enumerator(folder.Files);
            for (; !en.atEnd(); en.moveNext()) {
                var file = en.item();
                if (fso.GetExtensionName(file.Name).toLowerCase() === "txt") {
                    file.Delete();
                }
            }
        } catch (e) {
            try { fso.DeleteFile(outDir + "\\*.txt", true); } catch (e2) {}
        }
    }
}

function formatRange(chStart, chEnd, unit) {
    if (chStart === chEnd) return "第" + chStart + unit;
    return "第" + chStart + "-" + chEnd + unit;
}


// =============================================================================
// 第十部分：完成报告（v3.4 总-分结构）
// =============================================================================

function ShowCompleteReportV3(title, fileCount, outDir, tRead, tScan, tDedup, tWrite, extraInfo) {
    var tTotal = Timer() - g_tTotal0;
    var skippedTotal = g_skipTitleOnly + g_skipShortBody;

    // 【总】
    var msg = "【总】" + title + "完成：生成 " + fileCount + " 个文件（耗时 " +
              tTotal.toFixed(1) + " 秒）\n" +
              "输出：" + outDir + "\n" +
              repeatStr("-", 30) + "\n";

    // 【分】
    msg += "【分】\n";
    msg += "  来源：编码 " + g_detectedEnc + "→UTF-8｜正则 " + g_regexName +
           "｜识别章节 " + ch_count + "\n";

    // 质量行
    var qualityLine = "  质量：";
    if (g_dedupStrategy !== "none") {
        qualityLine += "去重 " + g_dedupStrategy + "(-" + g_dedupRemoved + "章)｜";
    } else {
        qualityLine += "去重 none｜";
    }
    if (g_sortStrategy !== "none") {
        qualityLine += "排序 " + g_sortStrategy + "(修" + g_oooFixed + "处)｜";
    } else {
        qualityLine += "排序 none｜";
    }
    qualityLine += "卷模式 " + g_actualVolMode;
    if (g_tocChapterCount > 0) {
        qualityLine += "｜目录区跳过 " + g_tocChapterCount + "章";
    }
    msg += qualityLine + "\n";

    // 清理行
    if (g_cleanAds || skippedTotal > 0) {
        var cleanLine = "  清理：";
        if (g_cleanAds) {
            cleanLine += "广告行 -" + g_adRemovedCount;
            if (skippedTotal > 0) cleanLine += "｜";
        }
        if (skippedTotal > 0) {
            cleanLine += "跳过 " + skippedTotal + " 章";
            if (g_skipTitleOnly > 0 || g_skipShortBody > 0) {
                cleanLine += "（仅标题" + g_skipTitleOnly + "/正文不足" + g_skipShortBody + "）";
            }
        }
        msg += cleanLine + "\n";
    }

    msg += "  计时：读取 " + tRead.toFixed(2) + "s｜识别 " + tScan.toFixed(2) +
           "s｜去重 " + tDedup.toFixed(2) + "s｜写入 " + tWrite.toFixed(2) +
           "s｜总计 " + tTotal.toFixed(2) + "s";

    if (extraInfo && extraInfo.length > 0) {
        msg += "\n" + extraInfo;
    }

    Application.MsgBox(msg, vbInformation, "完成");
}


// =============================================================================
// 第十一部分：核心拆分过程 v3
// =============================================================================

function SplitByChapterV3(inputPath, outputDir, fileNamePrefix, serialWidth,
                          generateTitleOnly, minBodyLen, mergeFlag) {
    // 参数默认值
    outputDir = outputDir || "";
    fileNamePrefix = fileNamePrefix || "";
    serialWidth = serialWidth || 3;
    generateTitleOnly = generateTitleOnly || false;
    minBodyLen = minBodyLen || 0;
    mergeFlag = (typeof mergeFlag === "undefined") ? -1 : mergeFlag;

    if (g_tTotal0 === 0) g_tTotal0 = Timer();

    var fso = CreateCOM("Scripting.FileSystemObject");

    // 1. 读取
    if (!fso.FileExists(inputPath)) {
        Application.MsgBox("源文件不存在：\n" + inputPath, vbExclamation, "错误");
        return;
    }
    var t0 = Timer();
    g_detectedEnc = detectEncodingFile(inputPath);
    var content = readTextAuto(inputPath);
    content = repAll(repAll(content, "\r\n", "\n"), "\r", "\n");
    var lines = content.split("\n");
    var lineCount = lines.length;
    var tRead = Timer() - t0;

    // 2. 扫描
    t0 = Timer();
    ScanChaptersV3(lines);
    DetectTOC();
    var tScan = Timer() - t0;
    if (ch_count === 0) {
        Application.MsgBox("未识别到任何章节标题。\n使用正则：" + g_regexName, vbExclamation, "提示");
        return;
    }

    // 3. 卷模式
    var actualVolMode = ResolveVolMode(g_volumeMode);
    var byVolFlag = (g_volumeMode === "by_volume" && actualVolMode === "volume");
    g_actualVolMode = actualVolMode;

    // 4. 去重（统计减少章数）
    var chapBefore = GetChapterIndices().length;
    t0 = Timer();
    ApplyDedup(g_dedupStrategy, actualVolMode, g_titleDedup);
    var tDedup = Timer() - t0;
    g_dedupRemoved = chapBefore - dedup_count;

    if (dedup_count === 0) {
        Application.MsgBox("去重后无有效章节！", vbExclamation, "错误");
        return;
    }

    // 4b. 排序（统计乱序修复处数）
    t0 = Timer();
    var oooBefore = CountOOOInDedup();
    ApplySort(g_sortStrategy, actualVolMode);
    g_oooFixed = oooBefore - CountOOOInDedup();

    if (dedup_count === 0) {
        Application.MsgBox("排序后无有效章节！", vbExclamation, "错误");
        return;
    }

    // 5. 输出目录
    var outDirFull = resolveOutputDir(fso, inputPath, outputDir, "_拆分");
    if (!fso.FolderExists(outDirFull)) fso.CreateFolder(outDirFull);
    cleanOutputDir(outDirFull);

    // 6. 序号位数
    if (String(dedup_count).length > serialWidth) serialWidth = String(dedup_count).length;

    // 7. 预计算章节字数（v3.6 优化：直接读扫描时预计算的结果，O(章节数)）
    var charCounts = new Array(dedup_count);
    var maxChars = 0;
    var i, j, n, origIdx;
    for (i = 0; i < dedup_count; i++) {
        origIdx = dedup_indices[i];
        charCounts[i] = ch_charCounts[origIdx];
        if (charCounts[i] > maxChars) maxChars = charCounts[i];
    }
    var charWidth = String(maxChars).length;
    if (charWidth < 1) charWidth = 1;

    // 8. 写文件
    var titleOnlyCount = 0, writtenCount = 0, skippedCount = 0, shortBodyCount = 0;
    var top1 = 0, top2 = 0, top3 = 0;
    var keptTexts = [], skippedTexts = [], skippedTitles = [], skippedBodyLens = [];
    var outPath = "";

    t0 = Timer();
    try {
        for (i = 0; i < dedup_count; i++) {
            origIdx = dedup_indices[i];
            n = ch_ends[origIdx] - ch_starts[origIdx] + 1;
            if (n < 1) n = 1;

            bodyArr = [];
            for (j = 0; j < n; j++) bodyArr.push(lines[ch_starts[origIdx] + j]);
            body = bodyArr.join("\n");

            // v3.6 优化：正文汉字数直接读预计算结果，O(1)
            var bodyLen = ch_hanziCounts[origIdx];

            // 判断不足
            var isInsufficient = false;
            if (n === 1) {
                titleOnlyCount++;
                isInsufficient = true;
            } else if (minBodyLen > 0 && bodyLen < minBodyLen) {
                shortBodyCount++;
                isInsufficient = true;
            }

            if (isInsufficient && !generateTitleOnly) {
                skippedCount++;
                if (n === 1) {
                    g_skipTitleOnly++;
                } else if (minBodyLen > 0 && bodyLen < minBodyLen) {
                    g_skipShortBody++;
                }
                if (bodyLen >= top1) { top3 = top2; top2 = top1; top1 = bodyLen; }
                else if (bodyLen >= top2) { top3 = top2; top2 = bodyLen; }
                else if (bodyLen >= top3) { top3 = bodyLen; }
                if (mergeFlag >= 0) {
                    skippedTitles.push(ch_titles[origIdx]);
                    skippedBodyLens.push(bodyLen);
                    skippedTexts.push(body);
                }
                continue;
            }

            // 文件名
            var serial = zeroPad(writtenCount + 1, serialWidth);
            var charCnt = zeroPad(charCounts[i], charWidth);
            var safeTitle = sanitizeFileName(ch_titles[origIdx]);
            var fileName;
            if (fileNamePrefix.length > 0) {
                fileName = fileNamePrefix + "_" + serial + "_" + charCnt + "_" + safeTitle + ".txt";
            } else {
                fileName = serial + "_" + charCnt + "_" + safeTitle + ".txt";
            }

            // 按卷分目录
            var fileDir = outDirFull;
            if (byVolFlag && ch_vols[origIdx] > 0) {
                var volDir = "第" + ch_vols[origIdx] + ch_units[origIdx];
                volDir = sanitizeFileName(volDir);
                fileDir = outDirFull + "\\" + volDir;
                if (!fso.FolderExists(fileDir)) fso.CreateFolder(fileDir);
            }

            outPath = fileDir + "\\" + fileName;

            // 广告清理
            var finalBody = body;
            if (g_cleanAds) {
                finalBody = CleanAdLines(body);
            }

            writeTextUTF8NoBOM(outPath, finalBody);
            if (mergeFlag === 1 || mergeFlag === 2) keptTexts.push(finalBody);

            writtenCount++;
        }
    } catch (e) {
        Application.MsgBox("写入第 " + (i + 1) + " 个文件时出错：\n" +
                           outPath + "\n错误：" + (e.message || e), vbExclamation, "写入错误");
        return;
    }
    var tWrite = Timer() - t0;

    // 清洁模式合并文件（MergeFlag=2 同时输出保留和清理两个合并文件）
    if (mergeFlag >= 0) {
        var srcBaseName = fso.GetBaseName(inputPath);
        var mergeName, mergeBody;
        if (keptTexts.length > 0) {
            mergeName = "保留大于等于" + minBodyLen + "_" + srcBaseName + ".txt";
            mergeBody = keptTexts.join("\n");
            writeTextUTF8NoBOM(outDirFull + "\\" + mergeName, mergeBody);
            debugLog("合并文件：" + mergeName + "（" + keptTexts.length + "章合并）");
        }
        if (mergeFlag === 2 && skippedTexts.length > 0) {
            mergeName = "清理小于" + minBodyLen + "_" + srcBaseName + ".txt";
            mergeBody = skippedTexts.join("\n");
            writeTextUTF8NoBOM(outDirFull + "\\" + mergeName, mergeBody);
            debugLog("合并文件：" + mergeName + "（" + skippedTexts.length + "章合并）");
        }
    }

    // 完成报告
    var skipDetail = "";
    if (titleOnlyCount > 0) skipDetail = titleOnlyCount + "个仅有标题";
    if (shortBodyCount > 0) {
        if (skipDetail.length > 0) skipDetail += "、";
        skipDetail += shortBodyCount + "个正文不足";
    }

    var extraInfo = "";
    if (skippedCount > 0) {
        var topStr = top1 + "字";
        if (skippedCount >= 2) topStr += "、" + top2 + "字";
        if (skippedCount >= 3) topStr += "、" + top3 + "字";
        extraInfo = "  跳过章节前三正文：" + topStr;
    } else if (skipDetail.length > 0) {
        extraInfo = "  " + skipDetail + "（已生成）";
    }

    var rptTitle = (mergeFlag >= 0) ? "清洁模式" : "按章节拆分";
    ShowCompleteReportV3(rptTitle, writtenCount, outDirFull, tRead, tScan, tDedup, tWrite, extraInfo);
}

// 聚合拆分 v3
function SplitByGroupsV3(inputPath, outputDir, chunkStr, fileNamePrefix, serialWidth) {
    outputDir = outputDir || "";
    chunkStr = chunkStr || "40,3";
    fileNamePrefix = fileNamePrefix || "";
    serialWidth = serialWidth || 3;

    if (g_tTotal0 === 0) g_tTotal0 = Timer();

    var fso = CreateCOM("Scripting.FileSystemObject");

    // 1. 读取
    if (!fso.FileExists(inputPath)) {
        Application.MsgBox("源文件不存在：\n" + inputPath, vbExclamation, "错误");
        return;
    }
    var t0 = Timer();
    g_detectedEnc = detectEncodingFile(inputPath);
    var content = readTextAuto(inputPath);
    content = repAll(repAll(content, "\r\n", "\n"), "\r", "\n");
    var lines = content.split("\n");
    var lineCount = lines.length;
    var tRead = Timer() - t0;

    // 2. 扫描
    t0 = Timer();
    ScanChaptersV3(lines);
    DetectTOC();
    var tScan = Timer() - t0;
    if (ch_count === 0) {
        Application.MsgBox("未识别到任何章节标题。", vbExclamation, "提示");
        return;
    }

    // 3. 卷模式
    var actualVolMode = ResolveVolMode(g_volumeMode);
    // v3.5: 聚合优先级大于卷——聚合按全局章号连续切块，卷分组无意义，强制扁平
    if (actualVolMode !== "flat") {
        actualVolMode = "flat";
        Application.Echo("卷模式: 聚合拆分优先 → 强制扁平（忽略卷结构）");
    }
    g_actualVolMode = actualVolMode;

    // 4. 去重
    var chapBefore = GetChapterIndices().length;
    t0 = Timer();
    ApplyDedup(g_dedupStrategy, actualVolMode, g_titleDedup);
    var tDedup = Timer() - t0;
    g_dedupRemoved = chapBefore - dedup_count;

    if (dedup_count === 0) {
        Application.MsgBox("去重后无有效章节！", vbExclamation, "错误");
        return;
    }

    // 4b. 排序
    t0 = Timer();
    var oooBefore = CountOOOInDedup();
    ApplySort(g_sortStrategy, actualVolMode);
    g_oooFixed = oooBefore - CountOOOInDedup();

    if (dedup_count === 0) {
        Application.MsgBox("排序后无有效章节！", vbExclamation, "错误");
        return;
    }

    var unitStr = ch_unit;

    // 5. 解析聚合格式
    var pg = ParseGroups(chunkStr, dedup_count);
    if (pg.error && pg.error.length > 0) {
        Application.MsgBox("聚合格式错误：\n" + pg.error, vbExclamation, "错误");
        return;
    }

    // 6. 展开文件列表
    var ex = ExpandGroups(pg.groupLens, pg.groupSpaces, pg.groupCount, dedup_count);
    var fileChStart = ex.fileChStart, fileChEnd = ex.fileChEnd, fileCount = ex.fileCount;

    // 7. 序号位数
    if (String(fileCount).length > serialWidth) serialWidth = String(fileCount).length;

    // 8. 输出目录
    var outDirFull = resolveOutputDir(fso, inputPath, outputDir, "_分组");
    if (!fso.FolderExists(outDirFull)) fso.CreateFolder(outDirFull);
    cleanOutputDir(outDirFull);

    // 9. 写文件
    var fname = "";
    t0 = Timer();
    var f;
    try {
        for (f = 0; f < fileCount; f++) {
            var origIdxS = dedup_indices[fileChStart[f] - 1];
            var startLine = ch_starts[origIdxS];
            var endLine;
            if (fileChEnd[f] < dedup_count) {
                var origIdxE = dedup_indices[fileChEnd[f]];
                endLine = ch_starts[origIdxE] - 1;
            } else {
                endLine = lineCount - 1;
            }

            var parts = [];
            for (var li = startLine; li <= endLine; li++) parts.push(lines[li]);
            var body = parts.join("\n");

            var rangeStr = formatRange(fileChStart[f], fileChEnd[f], unitStr);
            var safe = sanitizeFileName(rangeStr);
            var serial = zeroPad(f + 1, serialWidth);
            fname = serial + "_" + safe + ".txt";
            if (fileNamePrefix.length > 0) fname = fileNamePrefix + "_" + fname;

            // 广告清理
            var groupFinalBody = body;
            if (g_cleanAds) {
                groupFinalBody = CleanAdLines(body);
            }

            writeTextUTF8NoBOM(outDirFull + "\\" + fname, groupFinalBody);
        }
    } catch (e) {
        Application.MsgBox("写入第 " + (f + 1) + " 份文件时出错：\n" +
                           outDirFull + "\\" + fname + "\n错误：" + (e.message || e), vbExclamation, "写入错误");
        return;
    }
    var tWrite = Timer() - t0;

    // 完成报告
    var extraInfo = "  聚合格式：" + chunkStr + "（单位：" + unitStr + "）";
    ShowCompleteReportV3("聚合模式", fileCount, outDirFull, tRead, tScan, tDedup, tWrite, extraInfo);
}


// =============================================================================
// 第十二部分：深度分析报告（总-分结构）
// =============================================================================

function DeepAnalyzeFile(filePath, outputDir) {
    outputDir = outputDir || "";

    var fso = CreateCOM("Scripting.FileSystemObject");
    if (!fso.FileExists(filePath)) {
        Application.MsgBox("源文件不存在：\n" + filePath, vbExclamation, "错误");
        return;
    }

    g_titleDiffCount = 0;

    // 读取
    var t0 = Timer();
    g_detectedEnc = detectEncodingFile(filePath);
    var content = readTextAuto(filePath);
    content = repAll(repAll(content, "\r\n", "\n"), "\r", "\n");
    var lines = content.split("\n");
    var lineCount = lines.length;
    var tRead = Timer() - t0;

    // 扫描
    t0 = Timer();
    ScanChaptersV3(lines);
    DetectTOC();
    var tScan = Timer() - t0;

    var rpt = [];
    var i, k, kk;

    rpt.push(repeatStr("=", 70));
    rpt.push("  深度分析报告: " + fso.GetFileName(filePath));
    rpt.push(repeatStr("=", 70));
    rpt.push("总行数: " + fmtThousands(lineCount));
    rpt.push("总字符: " + fmtThousands(content.length));
    rpt.push("编码: " + g_detectedEnc);

    // 统计卷和章
    var volCnt = 0, chapCnt = 0;
    for (i = 0; i < ch_count; i++) {
        if (ch_levels[i] === "volume") volCnt++;
        if (ch_levels[i] === "chapter" || ch_levels[i] === "special") chapCnt++;
    }
    var structLine = "识别结构: 卷级 " + volCnt + " 个, 章节级 " + chapCnt + " 个";
    if (g_tocChapterCount > 0) {
        structLine += "\n              其中目录区 " + g_tocChapterCount + " 章（已跳过）";
    }
    rpt.push(structLine);
    rpt.push("使用正则: " + g_regexName);
    rpt.push("");

    // 一、卷结构分析
    rpt.push(repeatStr("-", 50));
    rpt.push("【一、卷/部结构分析】");
    if (volCnt > 0) {
        var volSet = mapNew();
        var volUnitSet = mapNew();
        var volChapterCnt = mapNew();
        var curVol = 0;
        var curVolLabel = "无卷";
        if (!mapHas(volChapterCnt, curVolLabel)) mapSet(volChapterCnt, curVolLabel, 0);

        for (i = 0; i < ch_count; i++) {
            if (ch_levels[i] === "volume") {
                curVol = ch_vols[i];
                curVolLabel = "第" + ch_vols[i] + ch_units[i];
                if (!mapHas(volSet, String(ch_vols[i]))) mapSet(volSet, String(ch_vols[i]), 1);
                if (!mapHas(volUnitSet, ch_units[i])) mapSet(volUnitSet, ch_units[i], 1);
                if (!mapHas(volChapterCnt, curVolLabel)) mapSet(volChapterCnt, curVolLabel, 0);
            } else if (ch_levels[i] === "chapter" || ch_levels[i] === "special") {
                mapSet(volChapterCnt, curVolLabel, mapGet(volChapterCnt, curVolLabel) + 1);
            }
        }

        rpt.push("  卷级标题数: " + volCnt);
        rpt.push("  不同卷号数: " + mapCount(volSet));
        rpt.push("  卷单位词: " + volUnitSet.ks.join(", "));
        rpt.push("  各卷章节数:");
        for (k = 0; k < volChapterCnt.ks.length; k++) {
            kk = volChapterCnt.ks[k];
            rpt.push("    " + kk + ": " + mapGet(volChapterCnt, kk) + " 章");
        }

        // 卷间章号重复检测
        if (mapCount(volSet) >= 2) {
            var volChs = mapNew(); // "vol_N" -> mapNew()
            curVol = 0;
            var firstDone = false;
            var firstVolKey = "", secondVolKey = "";
            for (i = 0; i < ch_count; i++) {
                if (ch_levels[i] === "volume") {
                    curVol = ch_vols[i];
                    var vkey = "vol_" + curVol;
                    if (!mapHas(volChs, vkey)) {
                        mapSet(volChs, vkey, mapNew());
                        if (!firstDone) { firstVolKey = vkey; firstDone = true; }
                        else if (secondVolKey.length === 0) { secondVolKey = vkey; }
                    }
                } else if (ch_levels[i] === "chapter" && ch_nums[i] > 0) {
                    var vvkey = "vol_" + curVol;
                    if (!mapHas(volChs, vvkey)) mapSet(volChs, vvkey, mapNew());
                    var sub = mapGet(volChs, vvkey);
                    if (!mapHas(sub, String(ch_nums[i]))) mapSet(sub, String(ch_nums[i]), 1);
                }
            }
            if (firstVolKey.length > 0 && secondVolKey.length > 0) {
                var commonCnt = 0, commonList = "";
                var firstSet = mapGet(volChs, firstVolKey);
                var secondSet = mapGet(volChs, secondVolKey);
                for (k = 0; k < firstSet.ks.length; k++) {
                    if (mapHas(secondSet, firstSet.ks[k])) {
                        commonCnt++;
                        if (commonCnt <= 10) {
                            if (commonList.length > 0) commonList += ",";
                            commonList += firstSet.ks[k];
                        }
                    }
                }
                if (commonCnt > 0) {
                    rpt.push("");
                    rpt.push("  ⚠ 卷间章号重复: " + firstVolKey + " 和 " + secondVolKey +
                             " 共享 " + commonCnt + " 个章号");
                    rpt.push("    示例: " + commonList + "...");
                }
            }
        }
    } else {
        rpt.push("  未检测到卷/部/册级结构");
    }
    rpt.push("");

    // 二、重复分析
    rpt.push(repeatStr("-", 50));
    rpt.push("【二、重复章节分析】");
    rpt.push("  扁平视角（忽略卷）:");

    var flatMap = mapNew();
    for (i = 0; i < ch_count; i++) {
        if (ch_levels[i] === "chapter" && ch_nums[i] > 0) {
            var numKey = String(ch_nums[i]);
            if (!mapHas(flatMap, numKey)) mapSet(flatMap, numKey, 0);
            mapSet(flatMap, numKey, mapGet(flatMap, numKey) + 1);
        }
    }

    var uniqueCnt = mapCount(flatMap);
    var dupCnt = 0;
    for (k = 0; k < flatMap.ks.length; k++) {
        if (mapGet(flatMap, flatMap.ks[k]) > 1) dupCnt++;
    }

    rpt.push("    不重复章号数: " + uniqueCnt);
    rpt.push("    存在重复的章号数: " + dupCnt);

    if (dupCnt > 0) {
        // 找重复最严重的10个
        var topNums = [], topCounts = [], topTitles = [], topLineInfo = [];
        var topCount = 0;
        for (k = 0; k < flatMap.ks.length; k++) {
            kk = flatMap.ks[k];
            var vv = mapGet(flatMap, kk);
            if (vv > 1) {
                var insPos = topCount;
                while (insPos > 0 && topCounts[insPos - 1] < vv) insPos--;
                if (insPos < 10) {
                    var mvStart = (topCount < 9) ? topCount : 9;
                    for (var mv = mvStart; mv >= insPos + 1; mv--) {
                        topNums[mv] = topNums[mv - 1];
                        topCounts[mv] = topCounts[mv - 1];
                        topTitles[mv] = topTitles[mv - 1];
                        topLineInfo[mv] = topLineInfo[mv - 1];
                    }
                    topNums[insPos] = kk;
                    topCounts[insPos] = vv;
                    // 收集该章号的首次标题和前5次行号
                    var occLines = "", occCnt = 0;
                    var numK = parseInt(kk, 10);
                    for (var fi = 0; fi < ch_count; fi++) {
                        if (ch_levels[fi] === "chapter" && ch_nums[fi] === numK) {
                            if (occCnt === 0) topTitles[insPos] = ch_titles[fi];
                            if (occCnt < 5) {
                                if (occCnt > 0) occLines += "、";
                                occLines += (ch_starts[fi] + 1);
                            }
                            occCnt++;
                        }
                    }
                    topLineInfo[insPos] = occLines;
                    if (topCount < 10) topCount++;
                }
            }
        }

        rpt.push("");
        rpt.push("    重复最严重的前10个章号：");
        for (i = 0; i < topCount; i++) {
            rpt.push("      第" + topNums[i] + "章 (" + topCounts[i] + "次): " + topTitles[i]);
            rpt.push("        出现行号: " + topLineInfo[i]);
        }

        // 重复次数分布
        var countDist = mapNew();
        for (k = 0; k < flatMap.ks.length; k++) {
            var cc = String(mapGet(flatMap, flatMap.ks[k]));
            if (!mapHas(countDist, cc)) mapSet(countDist, cc, 0);
            mapSet(countDist, cc, mapGet(countDist, cc) + 1);
        }
        rpt.push("");
        rpt.push("    重复次数分布：");
        for (k = 0; k < countDist.ks.length; k++) {
            rpt.push("      出现" + countDist.ks[k] + "次的章号: " + mapGet(countDist, countDist.ks[k]) + "个");
        }

        // v3.3：同章异题统计
        var titleDiffCnt = 0;
        var titleDiffDict = mapNew();    // 章号 -> 标题列表文本
        var titleDiffCntDict = mapNew(); // 章号 -> 不同标题数
        for (k = 0; k < flatMap.ks.length; k++) {
            var numK2 = flatMap.ks[k];
            if (mapGet(flatMap, numK2) <= 1) continue;
            var normTitles = mapNew();
            var numV = parseInt(numK2, 10);
            for (var chk = 0; chk < ch_count; chk++) {
                if (ch_levels[chk] === "chapter" && ch_nums[chk] === numV) {
                    var ntStr = NormalizeTitle(ch_titles[chk]);
                    if (!mapHas(normTitles, ntStr)) mapSet(normTitles, ntStr, 1);
                }
            }
            if (mapCount(normTitles) > 1) {
                titleDiffCnt++;
                var tdTitles = "";
                for (var tt = 0; tt < normTitles.ks.length; tt++) {
                    if (tt > 0) tdTitles += "\r\n";
                    tdTitles += "        · " + normTitles.ks[tt];
                }
                mapSet(titleDiffDict, numK2, tdTitles);
                mapSet(titleDiffCntDict, numK2, mapCount(normTitles));
            }
        }

        g_titleDiffCount = titleDiffCnt;
        if (titleDiffCnt > 0) {
            rpt.push("");
            rpt.push("  ⚠ 章号相同但标题不同: " + titleDiffCnt + " 个章号");
            rpt.push("    （仅按章号去重可能误删，建议启用标题级去重）");
            rpt.push("    完整列表：");
            for (k = 0; k < titleDiffDict.ks.length; k++) {
                var tdKey = titleDiffDict.ks[k];
                rpt.push("      第" + tdKey + "章（" + mapGet(titleDiffCntDict, tdKey) + "个不同标题）:");
                rpt.push(mapGet(titleDiffDict, tdKey));
            }
        }
    }
    rpt.push("");

    // 三、乱序分析
    rpt.push(repeatStr("-", 50));
    rpt.push("【三、乱序分析】");
    rpt.push("  扁平视角（忽略卷）:");

    var oooCnt = 0, maxDrop = 0, prevNum = 0;
    var maxDropInfoPrev = 0, maxDropInfoCur = 0;
    for (i = 0; i < ch_count; i++) {
        if (ch_levels[i] === "chapter" && ch_nums[i] > 0) {
            if (prevNum > 0 && ch_nums[i] < prevNum) {
                oooCnt++;
                var drop = prevNum - ch_nums[i];
                if (drop > maxDrop) {
                    maxDrop = drop;
                    maxDropInfoPrev = prevNum;
                    maxDropInfoCur = ch_nums[i];
                }
            }
            prevNum = ch_nums[i];
        }
    }

    rpt.push("    乱序次数: " + oooCnt);
    if (maxDrop > 0) {
        rpt.push("    最大跌幅: 第" + maxDropInfoPrev + "章 → 第" + maxDropInfoCur +
                 "章 (跌" + maxDrop + ")");
    }
    rpt.push("");

    // 四、多轨目录检测
    rpt.push(repeatStr("-", 50));
    rpt.push("【四、多轨目录检测】");

    if (g_tocChapterCount > 0) {
        rpt.push("  ⚠ 检测到目录区（已自动跳过，不参与去重/排序）");
        rpt.push("    目录章节数: " + g_tocChapterCount + " 章");
        rpt.push("    目录位置: 第 " + (g_tocStartIdx + 1) + " - " + (g_tocEndIdx + 1) + " 个识别项");
        if (g_tocStartIdx >= 0 && g_tocStartIdx < ch_count) {
            rpt.push("    起始标题: " + ch_titles[g_tocStartIdx]);
        }
    } else {
        rpt.push("  未检测到独立目录区");
    }
    rpt.push("");

    // 相邻双标题比例
    var adjDup = 0, prevChIdx = -1;
    for (i = 0; i < ch_count; i++) {
        if (ch_levels[i] === "chapter" && ch_nums[i] > 0) {
            if (prevChIdx >= 0) {
                if (ch_nums[i] === ch_nums[prevChIdx] && ch_starts[i] - ch_starts[prevChIdx] <= 2) {
                    adjDup++;
                }
            }
            prevChIdx = i;
        }
    }
    var adjRatio = 0;
    if (chapCnt > 0) adjRatio = adjDup / chapCnt;
    rpt.push("  相邻双标题数: " + adjDup + " (占比 " + fmtPct1(adjRatio) + ")");
    if (adjRatio > 0.3) {
        rpt.push("  → 疑似每章双标题结构（目录式+正文式各一次）");
    }

    // 最长连续递增段
    if (chapCnt > 1) {
        var seqLen = 1, maxSeq = 1;
        prevNum = 0;
        for (i = 0; i < ch_count; i++) {
            if (ch_levels[i] === "chapter" && ch_nums[i] > 0) {
                if (prevNum > 0 && ch_nums[i] === prevNum + 1) {
                    seqLen++;
                    if (seqLen > maxSeq) maxSeq = seqLen;
                } else {
                    seqLen = 1;
                }
                prevNum = ch_nums[i];
            }
        }
        rpt.push("  最长连续递增章号段长度: " + maxSeq);
    }
    rpt.push("");

    // 五、格式多样性
    rpt.push(repeatStr("-", 50));
    rpt.push("【五、格式多样性分析】");
    var patCnt = mapNew(), unitCnt = mapNew();
    for (i = 0; i < ch_count; i++) {
        if (ch_levels[i] === "chapter" || ch_levels[i] === "special") {
            if (!mapHas(patCnt, ch_patterns[i])) mapSet(patCnt, ch_patterns[i], 0);
            mapSet(patCnt, ch_patterns[i], mapGet(patCnt, ch_patterns[i]) + 1);
            if (!mapHas(unitCnt, ch_units[i])) mapSet(unitCnt, ch_units[i], 0);
            mapSet(unitCnt, ch_units[i], mapGet(unitCnt, ch_units[i]) + 1);
        }
    }
    rpt.push("  正则类型分布:");
    for (k = 0; k < patCnt.ks.length; k++) {
        rpt.push("    " + padRight(patCnt.ks[k], 15) + ": " + mapGet(patCnt, patCnt.ks[k]) + " 章");
    }
    rpt.push("  单位词分布:");
    for (k = 0; k < unitCnt.ks.length; k++) {
        rpt.push("    " + padRight(unitCnt.ks[k], 6) + ": " + mapGet(unitCnt, unitCnt.ks[k]) + " 章");
    }
    rpt.push("");

    // 六、章号连续性
    rpt.push(repeatStr("-", 50));
    rpt.push("【六、章号连续性分析】");
    var numSet = mapNew();
    var minNum = 999999, maxNum = 0;
    for (i = 0; i < ch_count; i++) {
        if (ch_levels[i] === "chapter" && ch_nums[i] > 0) {
            if (!mapHas(numSet, String(ch_nums[i]))) mapSet(numSet, String(ch_nums[i]), 1);
            if (ch_nums[i] < minNum) minNum = ch_nums[i];
            if (ch_nums[i] > maxNum) maxNum = ch_nums[i];
        }
    }
    if (mapCount(numSet) > 0) {
        var expected = maxNum - minNum + 1;
        var missing = expected - mapCount(numSet);
        rpt.push("  章号范围: " + minNum + " - " + maxNum);
        rpt.push("  应有章节数: " + expected);
        rpt.push("  实际章号数: " + mapCount(numSet));
        rpt.push("  缺失章号数: " + missing);

        if (missing > 0) {
            rpt.push("  缺失章号（全部列出，共" + missing + "个）:");
            var missCount = 0;
            var missList = "";
            for (var nn = minNum; nn <= maxNum; nn++) {
                if (!mapHas(numSet, String(nn))) {
                    if (missCount > 0 && missCount % 20 === 0) {
                        rpt.push("    " + missList + ",");
                        missList = "";
                    }
                    if (missList.length > 0) missList += ",";
                    missList += nn;
                    missCount++;
                }
            }
            if (missList.length > 0) {
                rpt.push("    " + missList);
            }
        }
    }
    rpt.push("");

    // 七、各策略效果预览
    rpt.push(repeatStr("-", 50));
    rpt.push("【七、各策略组合效果预览（扁平模式）】");

    var comboLabels = ["none+none", "none+sort", "first+none", "first+sort", "longest+none", "longest+sort"];
    var comboDedup = ["none", "none", "first", "first", "longest", "longest"];
    var comboSort = ["none", "sort", "none", "sort", "none", "sort"];

    for (var sIdx = 0; sIdx < 6; sIdx++) {
        ApplyDedup(comboDedup[sIdx], "flat", false);
        ApplySort(comboSort[sIdx], "flat");
        var tmpCnt = dedup_count;
        var oooAfter = 0;
        prevNum = 0;
        for (var pp = 0; pp < tmpCnt; pp++) {
            if (ch_nums[dedup_indices[pp]] > 0) {
                if (prevNum > 0 && ch_nums[dedup_indices[pp]] < prevNum) oooAfter++;
                prevNum = ch_nums[dedup_indices[pp]];
            }
        }
        rpt.push("  " + padRight(comboLabels[sIdx], 14) + ": 剩" + padLeft(tmpCnt, 3) +
                 "章, 乱序" + padLeft(oooAfter, 3) + "处");
    }
    rpt.push("");

    // 处理建议
    rpt.push(repeatStr("=", 70));
    rpt.push("  处理建议：");
    if (oooCnt > 10) {
        rpt.push("  • 乱序严重，推荐 sort 策略（最彻底）或 lis 策略（智能）");
    } else if (dupCnt > 0) {
        rpt.push("  • 有重复但乱序轻微，推荐 longest 策略（保留内容最长的）");
    }
    if (adjRatio > 0.3) {
        rpt.push("  • 每章双标题明显，用组合3 保留最长+不排序 即可");
    }
    if (volCnt > 1) {
        rpt.push("  • 检测到多卷结构，注意选择正确的卷模式");
    }
    rpt.push(repeatStr("=", 70));

    // v3.4：【总】结论与建议
    var recCombo;
    if (dupCnt === 0 && oooCnt === 0) {
        recCombo = "none+none（干净型：不去重不排序）";
    } else if (adjRatio >= 0.3 && oooCnt < 10) {
        recCombo = "longest+none（双标题型：保留最长不排序）";
    } else if (oooCnt >= 10) {
        recCombo = "longest+sort（乱序严重：保留最长并排序）";
    } else if (dupCnt > 0) {
        recCombo = "longest+none（仅重复：保留最长不排序）";
    } else {
        recCombo = "longest+sort（稳妥默认）";
    }

    var autoN = AutoNFromBodies();
    var volStructDesc = (volCnt > 0) ? ("有卷（卷级标题 " + volCnt + " 个）") : "无卷";
    var tocDesc = (g_tocChapterCount > 0) ? ("有（" + g_tocChapterCount + " 章，已跳过）") : "无";

    var summary = "【总】结论与建议\n" +
                  "  问题计数：\n" +
                  "    重复章号数：" + dupCnt + "\n" +
                  "    乱序处数：" + oooCnt + "\n" +
                  "    卷结构：" + volStructDesc + "\n" +
                  "    同章异题数：" + g_titleDiffCount + "\n" +
                  "    目录区：" + tocDesc + "\n" +
                  "  推荐组合：" + recCombo + "\n" +
                  "  建议清洁N值：" + autoN + "\n" +
                  repeatStr("-", 50) + "\n" +
                  "【分】各维度明细\n";

    // 输出报告（总-分结构）
    var report = summary + rpt.join("\r\n");
    debugLog(report);

    var outPath;
    if (outputDir.length > 0) {
        outPath = outputDir + "\\分析报告.txt";
    } else {
        outPath = fso.GetParentFolderName(filePath) + "\\" + fso.GetBaseName(filePath) + "_分析报告.txt";
    }
    writeTextUTF8NoBOM(outPath, report);

    if (outputDir.length === 0) {
        Application.MsgBox("【总】分析完成\n" +
                           "  重复章号 " + dupCnt + "｜乱序 " + oooCnt + " 处｜同章异题 " + g_titleDiffCount + "\n" +
                           "  推荐组合：" + recCombo + "\n" +
                           "  建议清洁N值：" + autoN + "\n\n" +
                           "报告已保存：\n" + outPath, vbInformation, "分析完成");
    }
}


// =============================================================================
// 第十三部分：对外入口
// =============================================================================

function 拆分TXTv3() {
    // 初始化
    g_tTotal0 = Timer();
    g_tSelect = 0;
    g_regexName = "";
    g_selCount = 0;
    g_dedupStrategy = "longest";
    g_sortStrategy = "sort";
    g_adRemovedCount = 0;
    g_dedupRemoved = 0;
    g_oooFixed = 0;
    g_skipTitleOnly = 0;
    g_skipShortBody = 0;

    // 弹窗1：选择文件
    var tSel0 = Timer();
    var filePath = selectTxtFile("选择要拆分的TXT文件");
    g_tSelect = Timer() - tSel0;
    if (filePath.length === 0) return;

    // 弹窗2：选择正则（多选）
    InitRegexPatterns();
    if (!SelectRegexPattern()) return;

    // 弹窗3：去重+排序组合（六选一）
    if (!SelectDedupSortCombo()) return;

    // 卷模式/广告清理/标题级去重：改由设置读取
    LoadSettings();

    // 弹窗4：输出模式+参数一体输入
    var prompt = "【步骤4/4】请选择输出模式（可带参数）：\n\n" +
                 "  1. 清洁模式（默认）\n" +
                 "       每章一个文件 + 生成 保留≥N / 清理<N 两个合并文件\n" +
                 "       输入 1 → N=100；输入 1 200 → N=200\n" +
                 "  2. 聚合模式（多章合并为一份）\n" +
                 "       输入 2 → 40,3；输入 2 20,1|20,1|80,1 → 自定义\n\n" +
                 "请输入：";
    var outInput = Application.InputBox(prompt, "输出模式+参数", "1", 100, 100, "", 0, 2);
    if (outInput === false) return;

    outInput = normalizeSeparators(String(outInput));
    outInput = trimStr(outInput);
    if (outInput.length === 0) {
        Application.MsgBox("未输入模式。", vbExclamation, "提示");
        return;
    }

    // 解析：按第一个空格切开
    var modeStr, paramStr;
    var spPos = outInput.indexOf(" ");
    if (spPos > 0) {
        modeStr = trimStr(outInput.substring(0, spPos));
        paramStr = trimStr(outInput.substring(spPos + 1));
    } else {
        modeStr = outInput;
        paramStr = "";
    }

    if (modeStr === "1") {
        // 清洁模式
        var cleanN;
        if (paramStr.length === 0) {
            cleanN = 100;
        } else {
            if (!isDigits(paramStr)) {
                Application.MsgBox("清洁模式参数应为正整数（最小正文字数）。", vbExclamation, "提示");
                return;
            }
            cleanN = parseInt(paramStr, 10);
        }
        SplitByChapterV3(filePath, "", "", 3, false, cleanN, 2);
    } else if (modeStr === "2") {
        // 聚合模式
        var chunkStr = (paramStr.length === 0) ? "40,3" : paramStr;

        // 自定义正则的单位词询问
        for (var selIdx = 0; selIdx < g_selCount; selIdx++) {
            if (g_selOrigIndices[selIdx] === g_regexCount) {
                var unitInput = Application.InputBox("检测到自定义正则，请输入聚合拆分用的单位词：",
                                                      "聚合拆分单位词", "章", 100, 100, "", 0, 2);
                if (unitInput === false || trimStr(String(unitInput)).length === 0) {
                    g_selDefaultUnits[selIdx] = "章";
                } else {
                    g_selDefaultUnits[selIdx] = trimStr(String(unitInput));
                }
            }
        }

        SplitByGroupsV3(filePath, "", chunkStr, "", 3);
    } else {
        Application.MsgBox("无效模式：" + modeStr + "（应为 1 或 2）。", vbExclamation, "提示");
        return;
    }
}

function 分析TXTv3() {
    g_tTotal0 = Timer();
    g_tSelect = 0;
    g_regexName = "";
    g_selCount = 0;
    g_adRemovedCount = 0;

    // 选择文件
    var tSel0 = Timer();
    var filePath = selectTxtFile("选择要分析的TXT文件");
    g_tSelect = Timer() - tSel0;
    if (filePath.length === 0) return;

    // v3.4：读取默认设置
    LoadSettings();

    // 选择正则
    InitRegexPatterns();
    if (!SelectRegexPattern()) return;

    // 执行分析
    DeepAnalyzeFile(filePath);
}

function 自动TXTv3() {
    // 初始化
    g_tTotal0 = Timer();
    g_tSelect = 0;
    g_regexName = "";
    g_selCount = 0;
    g_adRemovedCount = 0;
    g_dedupRemoved = 0;
    g_oooFixed = 0;
    g_skipTitleOnly = 0;
    g_skipShortBody = 0;

    // 弹窗1：选择文件
    var tSel0 = Timer();
    var filePath = selectTxtFile("选择要自动拆分的TXT文件");
    g_tSelect = Timer() - tSel0;
    if (filePath.length === 0) return;

    // 读取设置
    LoadSettings();

    var fso = CreateCOM("Scripting.FileSystemObject");

    // 读取并扫描
    var t0 = Timer();
    g_detectedEnc = detectEncodingFile(filePath);
    var content = readTextAuto(filePath);
    content = repAll(repAll(content, "\r\n", "\n"), "\r", "\n");
    var lines = content.split("\n");
    var tRead = Timer() - t0;

    // 自动正则：固定 "1,2,4"（标准中文+无第字中文+无号特殊章节）
    InitRegexPatterns();
    var autoParts = ["1", "2", "4"];
    g_selPatterns = [];
    g_selUnitGroups = [];
    g_selDefaultUnits = [];
    g_selOrigIndices = [];
    g_selMaxLens = [];
    g_selCount = 0;
    for (var p = 0; p < autoParts.length; p++) {
        var idx = parseInt(autoParts[p], 10);
        g_selPatterns[g_selCount] = g_regexPatterns[idx];
        g_selUnitGroups[g_selCount] = g_regexUnitGroups[idx];
        g_selDefaultUnits[g_selCount] = g_regexDefaultUnits[idx];
        g_selOrigIndices[g_selCount] = idx;
        g_selMaxLens[g_selCount] = g_regexMaxLens[idx];
        g_selCount++;
    }
    g_regexName = "标准中文 + 无第字中文 + 无号特殊章节";

    t0 = Timer();
    ScanChaptersV3(lines);
    DetectTOC();
    var tScan = Timer() - t0;
    if (ch_count === 0) {
        Application.MsgBox("未识别到任何章节标题。", vbExclamation, "提示");
        return;
    }

    // 自动决策：统计（仅 ch_num>0 且非目录区章节）
    var flatMap = mapNew();
    var chapCnt = 0, dupCnt = 0, oooCnt = 0, adjDup = 0, prevChIdx = -1, prevNum = 0;
    for (var i = 0; i < ch_count; i++) {
        if (ch_levels[i] === "chapter" && ch_nums[i] > 0 && !ch_isTOC[i]) {
            chapCnt++;
            var numKey = String(ch_nums[i]);
            if (!mapHas(flatMap, numKey)) mapSet(flatMap, numKey, 0);
            mapSet(flatMap, numKey, mapGet(flatMap, numKey) + 1);

            if (prevNum > 0 && ch_nums[i] < prevNum) oooCnt++;
            prevNum = ch_nums[i];

            if (prevChIdx >= 0) {
                if (ch_nums[i] === ch_nums[prevChIdx] && ch_starts[i] - ch_starts[prevChIdx] <= 2) {
                    adjDup++;
                }
            }
            prevChIdx = i;
        }
    }
    for (var k = 0; k < flatMap.ks.length; k++) {
        if (mapGet(flatMap, flatMap.ks[k]) > 1) dupCnt++;
    }
    var adjRatio = 0;
    if (chapCnt > 0) adjRatio = adjDup / chapCnt;

    // 自动决策规则
    var recDedup, recSort, recComboStr;
    if (dupCnt === 0 && oooCnt === 0) {
        recDedup = "none"; recSort = "none";
        recComboStr = "none+none（干净型）";
    } else if (adjRatio >= 0.3 && oooCnt < 10) {
        recDedup = "longest"; recSort = "none";
        recComboStr = "longest+none（双标题型）";
    } else if (oooCnt >= 10) {
        recDedup = "longest"; recSort = "sort";
        recComboStr = "longest+sort（乱序严重）";
    } else if (dupCnt > 0) {
        recDedup = "longest"; recSort = "none";
        recComboStr = "longest+none（仅重复）";
    } else {
        recDedup = "longest"; recSort = "sort";
        recComboStr = "longest+sort（稳妥默认）";
    }

    // 自动判定N（v3.6：直接读预计算结果，O(章节数)）
    var autoN = AutoNFromBodies();

    // 卷结构统计
    var volCnt = 0;
    for (i = 0; i < ch_count; i++) {
        if (ch_levels[i] === "volume") volCnt++;
    }

    // 确认弹窗
    var confirmMsg = "【自动方案】\n" +
                     "  正则：标准中文 + 无号章节\n" +
                     "  去重+排序：" + recComboStr + "\n" +
                     "  理由：重复章号=" + dupCnt + "，乱序=" + oooCnt +
                     "，相邻双标题占比=" + fmtPct1(adjRatio) + "\n" +
                     "  清洁N值：" + autoN + "\n" +
                     "  卷模式：" + g_volumeMode + "（" + ((volCnt > 1) ? "检测多卷" : "扁平") + "）\n" +
                     "  广告清理：" + (g_cleanAds ? "是" : "否") + "\n" +
                     "  标题级去重：" + (g_titleDedup ? "是" : "否") + "\n\n" +
                     "[确定]执行   [取消]退出";
    if (Application.MsgBox(confirmMsg, vbOKCancel + vbQuestion, "自动TXTv3 - 确认方案") !== vbOK) return;

    // 执行
    g_dedupStrategy = recDedup;
    g_sortStrategy = recSort;

    var autoDir = fso.GetParentFolderName(filePath) + "\\" + fso.GetBaseName(filePath) + "_自动";
    var autoSubDir = autoDir + "\\拆分文档";
    if (!fso.FolderExists(autoDir)) fso.CreateFolder(autoDir);
    if (!fso.FolderExists(autoSubDir)) fso.CreateFolder(autoSubDir);

    // 生成分析报告
    DeepAnalyzeFile(filePath, autoDir);

    // 拆分（清洁模式，MergeFlag=2）
    SplitByChapterV3(filePath, autoSubDir, "", 3, false, autoN, 2);

    // 把合并文件从 autoSubDir 移到 autoDir
    try {
        var mvPaths = [];
        var en = new Enumerator(fso.GetFolder(autoSubDir).Files);
        for (; !en.atEnd(); en.moveNext()) {
            var mvFile = en.item();
            if (mvFile.Name.indexOf("保留大于等于") >= 0 || mvFile.Name.indexOf("清理小于") >= 0) {
                mvPaths.push(String(mvFile.Path));
            }
        }
        for (var mi = 0; mi < mvPaths.length; mi++) {
            fso.MoveFile(mvPaths[mi], autoDir + "\\");
        }
    } catch (e) {}
}
