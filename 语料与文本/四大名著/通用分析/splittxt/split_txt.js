// =============================================================================
// TXT章节拆分工具（完整合并版）—— WPS JS宏
//   - 按章节一一拆分：每章一个文件
//   - 聚合拆分：按聚合格式将多章合并为一份
//   - 清洁模式：按正文字数过滤章节，并生成合并文件
//   - 通用编码检测与读写：ANSI / UTF-8(含/无BOM) / UTF-16LE / UTF-16BE
//   复制粘贴到 WPS JS宏编辑器即可运行，无需导入其他模块
//
// 入口：运行 拆分TXT（选择文件 → 选择模式 → 生成文件）
//
// 聚合格式: 每份章数,份数|每份章数,份数|...  或便捷 N（每N章一份）
//   例: 40,3 -> 3份各40章； 20,1|20,1|80,1 -> 3份(1-20,21-40,41-120)
//   不足总章数时余数自动追加1个文件；突破9999章时序号位数自动扩展
// 输出格式: [前缀_]<序号补零>_<章节字数>_<标题或范围>.txt（UTF-8无BOM）
//   - 每章拆分: 序号_字数_标题.txt（标题内半角空格转全角）
//   - 聚合拆分: 序号_第起-止单位.txt
//   - 序号位数自适应：文件数超当前位数容量时自动扩展
//   - 章节字数：统计全部字符（含标题、正文、标点、换行），位数自适应零填充
//   - 正则中文数字含"万"，支持 第一万章 / 第十万章 等大章节号
// =============================================================================

// --- 安全日志（WPS JS宏环境无console对象）---
function debugLog(msg) {
    try { if (typeof console !== "undefined" && debugLog) debugLog(msg); } catch (e) {}
}

// --- 常量 ---
var CHAPTER_PATTERN = /^第([0-9一二三四五六七八九十百千万零两]+)(章|回|节|卷)(\s*)(.*)$/;

// MsgBox 常量
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

// --- 全局计时变量 ---
var g_tSelect = 0;
var g_tTotal0 = 0;
var g_detectedEnc = "";


// =============================================================================
// 工具函数
// =============================================================================

function Timer() {
    return Date.now() / 1000;
}

function zeroPad(n, width) {
    var s = String(Math.floor(n));
    while (s.length < width) s = "0" + s;
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

function countChineseChars(text) {
    var count = 0;
    for (var i = 0; i < text.length; i++) {
        var c = text.charCodeAt(i);
        if (c >= 0x4e00 && c <= 0x9fff) count++;
    }
    return count;
}


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

    // --- BOM 检测 ---
    if (bytes.length >= 2) {
        if (bytes[0] === 0xFF && bytes[1] === 0xFE) return "UTF-16LE";
        if (bytes[0] === 0xFE && bytes[1] === 0xFF) return "UTF-16BE";
    }
    if (bytes.length >= 3) {
        if (bytes[0] === 0xEF && bytes[1] === 0xBB && bytes[2] === 0xBF) return "UTF-8 BOM";
    }

    // --- 无BOM：扫描字节模式判断 UTF-8 vs ANSI ---
    var scanLen = Math.min(bytes.length, 100);
    for (var i = 0; i < scanLen; i++) {
        if (bytes[i] > 0x7F) {
            var b1 = bytes[i];
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
    return "ANSI";
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
    var text = stm.ReadText(-1); // adReadAll
    stm.Close();
    return text;
}

function readTextUTF16(filePath) {
    var fso = CreateCOM("Scripting.FileSystemObject");
    var ts = fso.OpenTextFile(filePath, 1, false, -1); // -1 = TristateTrue (Unicode)
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
    var bin = stm.Read(-1); // adReadAll
    stm.Close();

    var stm2 = CreateCOM("ADODB.Stream");
    stm2.Type = 1; // adTypeBinary
    stm2.Open();
    stm2.Write(bin);
    stm2.SaveToFile(filePath, 2); // adSaveCreateOverWrite
    stm2.Close();
}


// =============================================================================
// 第二部分：共享内部函数
// =============================================================================

function selectTxtFile(title) {
    // 尝试 Application.FileDialog
    try {
        var fd = Application.FileDialog(3); // msoFileDialogFilePicker
        if (fd) {
            fd.Title = title;
            try { fd.Filters.Clear(); } catch (e) {}
            try { fd.Filters.Add("文本文件", "*.txt"); } catch (e) {}
            if (fd.Show() === -1) {
                return fd.SelectedItems(1);
            }
            return "";
        }
    } catch (e) {}

    // 尝试 GetOpenFilename
    try {
        var result = Application.GetOpenFilename("文本文件 (*.txt), *.txt", , title);
        if (result === false) return "";
        return String(result);
    } catch (e) {}

    // 兜底：InputBox
    var input = Application.InputBox("请输入TXT文件完整路径：", title, "", 100, 100, "", 0, 2);
    if (input === false) return "";
    return String(input);
}

function scanChapters(lines) {
    var starts = [];
    var ends = [];
    var titles = [];
    var unit = "回";

    for (var i = 0; i < lines.length; i++) {
        var m = CHAPTER_PATTERN.exec(lines[i]);
        if (m) {
            if (starts.length > 0) {
                ends[starts.length - 1] = i - 1;
            }
            starts.push(i);
            ends.push(0);
            titles.push(m[0].trim());
            if (starts.length === 1) {
                unit = m[2];
            }
        }
    }
    if (starts.length > 0) {
        ends[starts.length - 1] = lines.length - 1;
    }
    return { starts: starts, ends: ends, titles: titles, count: starts.length, unit: unit };
}

function sanitizeFileName(name) {
    var s = name.replace(/ /g, "\u3000"); // 半角空格 -> 全角空格
    s = s.replace(/[\\\/:*?"<>|]/g, "\u3000"); // 非法字符 -> 全角空格
    while (s.indexOf("\u3000\u3000") >= 0) {
        s = s.replace(/\u3000\u3000/g, "\u3000"); // 折叠连续全角空格
    }
    s = s.trim();
    if (s.length === 0) s = "untitled";
    if (s.length > 60) s = s.substring(0, 60);
    return s;
}

function resolveOutputDir(fso, inputPath, outputDir, suffix) {
    if (outputDir && outputDir.length > 0) {
        return outputDir;
    }
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
            // 兜底：使用 DeleteFile 通配符
            try { fso.DeleteFile(outDir + "\\*.txt", true); } catch (e2) {}
        }
    }
}

function formatRange(chStart, chEnd, unit) {
    if (chStart === chEnd) {
        return "第" + chStart + unit;
    }
    return "第" + chStart + "-" + chEnd + unit;
}

function showCompleteReport(title, fileCount, outDir, tRead, tScan, tWrite, extraInfo) {
    var tTotal = Timer() - g_tTotal0;

    var msg = title + "！\n" +
              "生成文件：" + fileCount + " 个\n" +
              "源文件编码：" + g_detectedEnc + " → UTF-8\n" +
              "输出目录：" + outDir + "\n\n" +
              "【计时统计】\n" +
              "  文件选择：" + g_tSelect.toFixed(2) + " 秒\n" +
              "  读取文件：" + tRead.toFixed(2) + " 秒\n" +
              "  识别章节：" + tScan.toFixed(2) + " 秒\n" +
              "  写入文件：" + tWrite.toFixed(2) + " 秒\n" +
              "  总计耗时：" + tTotal.toFixed(2) + " 秒";
    if (tWrite > 0) {
        msg += "\n  写入速率：" + (fileCount / tWrite).toFixed(1) + " 文件/秒";
    }
    if (extraInfo && extraInfo.length > 0) {
        msg += "\n\n" + extraInfo;
    }
    Application.MsgBox(msg, vbInformation, "完成");
}


// =============================================================================
// 第三部分：核心过程 1 - 按章节一一拆分
// =============================================================================

function splitByChapter(inputPath, outputDir, fileNamePrefix, serialWidth,
                        generateTitleOnly, minBodyLen, mergeFlag) {
    // 参数默认值
    outputDir = outputDir || "";
    fileNamePrefix = fileNamePrefix || "";
    serialWidth = serialWidth || 3;
    generateTitleOnly = generateTitleOnly || false;
    minBodyLen = minBodyLen || 0;
    mergeFlag = (mergeFlag === undefined) ? -1 : mergeFlag;

    if (g_tTotal0 === 0) g_tTotal0 = Timer();

    var fso = CreateCOM("Scripting.FileSystemObject");

    // --- 1. 读取源文件 ---
    if (!fso.FileExists(inputPath)) {
        Application.MsgBox("源文件不存在：\n" + inputPath, vbExclamation, "错误");
        return;
    }
    var tRead0 = Timer();
    g_detectedEnc = detectEncodingFile(inputPath);
    var content = readTextAuto(inputPath);
    if (content.length === 0) {
        Application.MsgBox("读取失败或文件为空：\n" + inputPath, vbExclamation, "错误");
        return;
    }
    content = content.replace(/\r\n/g, "\n").replace(/\r/g, "\n");
    var lines = content.split("\n");
    var lineCount = lines.length;
    var tRead1 = Timer() - tRead0;

    // --- 2. 识别章节 ---
    var tScan0 = Timer();
    var ch = scanChapters(lines);
    var chCount = ch.count;
    var chStarts = ch.starts;
    var chEnds = ch.ends;
    var chTitles = ch.titles;
    var unit = ch.unit;
    var tScan1 = Timer() - tScan0;

    if (chCount === 0) {
        Application.MsgBox("未识别到任何章节标题（第N章/第N回/第N节/第N卷）。\n请确认文件格式。", vbExclamation, "提示");
        return;
    }

    // --- 3. 序号位数自适应 ---
    var chCountStr = String(chCount);
    if (chCountStr.length > serialWidth) serialWidth = chCountStr.length;
    var serialFmt = repeatStr("0", serialWidth);
    var prefix = fileNamePrefix;

    // --- 4. 确定输出目录 ---
    var outDirFull = resolveOutputDir(fso, inputPath, outputDir, "_拆分");

    // --- 5. 创建输出目录 + 清理旧文件 ---
    if (!fso.FolderExists(outDirFull)) fso.CreateFolder(outDirFull);
    cleanOutputDir(outDirFull);

    // --- 5.5 预计算章节字数（统计全部字符，含标题和换行，用于文件名显示）---
    var charCounts = [];
    var maxChars = 0;
    for (var ci = 0; ci < chCount; ci++) {
        var nLines = chEnds[ci] - chStarts[ci] + 1;
        if (nLines < 1) nLines = 1;
        var bodyLines = [];
        for (var cj = 0; cj < nLines; cj++) {
            bodyLines.push(lines[chStarts[ci] + cj]);
        }
        var bodyTmp = bodyLines.join("\n");
        charCounts.push(bodyTmp.length);
        if (bodyTmp.length > maxChars) maxChars = bodyTmp.length;
    }
    var charWidth = Math.max(1, String(maxChars).length);
    var charFmt = repeatStr("0", charWidth);
    debugLog("章节字数: 最大" + maxChars + "字  字数位数: " + charWidth);

    // --- 6. 写每章文件 ---
    var titleOnlyCount = 0;
    var writtenCount = 0;
    var skippedCount = 0;
    var shortBodyCount = 0;
    var top1 = 0, top2 = 0, top3 = 0;
    var keptTexts = [];
    var skippedTexts = [];
    var skippedTitles = [];
    var skippedBodyLens = [];
    var outPath = "";

    var t0 = Timer();
    try {
        for (var i = 0; i < chCount; i++) {
            var n = chEnds[i] - chStarts[i] + 1;
            if (n < 1) n = 1;

            // 提取完整章节文本（含标题行）
            var bodyArr = [];
            for (var j = 0; j < n; j++) {
                bodyArr.push(lines[chStarts[i] + j]);
            }
            var body = bodyArr.join("\n");

            // 计算正文汉字数（不含标题行，仅统计汉字）
            var bodyLen = 0;
            if (n > 1) {
                var bodyTextArr = [];
                for (var k = 1; k < n; k++) {
                    bodyTextArr.push(lines[chStarts[i] + k]);
                }
                bodyLen = countChineseChars(bodyTextArr.join(""));
            }

            // 判断是否为不足章节
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
                if (bodyLen >= top1) {
                    top3 = top2; top2 = top1; top1 = bodyLen;
                } else if (bodyLen >= top2) {
                    top3 = top2; top2 = bodyLen;
                } else if (bodyLen >= top3) {
                    top3 = bodyLen;
                }
                if (mergeFlag >= 0) {
                    skippedTitles.push(chTitles[i]);
                    skippedBodyLens.push(bodyLen);
                }
                if (mergeFlag === 0) {
                    skippedTexts.push(body);
                }
                continue;
            }

            var serial = zeroPad(writtenCount + 1, serialWidth);
            var charCnt = zeroPad(charCounts[i], charWidth);
            var safeTitle = sanitizeFileName(chTitles[i]);
            var fileName;
            if (prefix.length > 0) {
                fileName = prefix + "_" + serial + "_" + charCnt + "_" + safeTitle + ".txt";
            } else {
                fileName = serial + "_" + charCnt + "_" + safeTitle + ".txt";
            }
            outPath = outDirFull + "\\" + fileName;

            writeTextUTF8NoBOM(outPath, body);
            if (mergeFlag === 1) keptTexts.push(body);

            if (writtenCount < 3 || i >= chCount - 2) {
                var tag;
                if (n === 1) {
                    tag = "  (仅标题)";
                } else if (minBodyLen > 0 && bodyLen < minBodyLen) {
                    tag = "  (" + n + "行,正文" + bodyLen + "字)";
                } else {
                    tag = "  (" + n + "行)";
                }
                debugLog("  [" + serial + "] " + fileName + tag);
            } else if (writtenCount === 3) {
                debugLog("  ...");
            }

            writtenCount++;
        }
    } catch (e) {
        Application.MsgBox("写入第 " + (i + 1) + " 个文件时出错：\n" +
                           outPath + "\n错误：" + (e.message || e), vbExclamation, "写入错误");
        return;
    }
    var t1 = Timer() - t0;

    // --- 6.5 生成合并文件（清洁模式）---
    if (mergeFlag >= 0) {
        var srcBaseName = fso.GetBaseName(inputPath);
        var hdr = repeatStr("=", 50) + "\n" +
                  "清理说明：正文中文字数小于 " + minBodyLen + " 的章节已跳过\n" +
                  "跳过章节：" + skippedCount + " 个\n";
        if (skippedTitles.length > 0) {
            hdr += "跳过明细：\n";
            for (var mk = 0; mk < skippedTitles.length; mk++) {
                hdr += "  " + skippedTitles[mk] + "（" + skippedBodyLens[mk] + "字）\n";
            }
            var topStr = top1 + "字";
            if (skippedCount >= 2) topStr += "、" + top2 + "字";
            if (skippedCount >= 3) topStr += "、" + top3 + "字";
            hdr += "前三正文：" + topStr + "\n";
        }
        hdr += "保留章节：" + writtenCount + " 个\n";

        var mergeName = "";
        var mergeCol = null;
        if (mergeFlag === 0 && skippedTexts.length > 0) {
            hdr += "本文件内容：跳过章节（正文汉字 < " + minBodyLen + "）\n" +
                   repeatStr("=", 50);
            mergeName = "清理小于" + minBodyLen + "_" + srcBaseName + ".txt";
            mergeCol = skippedTexts;
        } else if (mergeFlag === 1 && keptTexts.length > 0) {
            hdr += "本文件内容：保留章节（正文汉字 >= " + minBodyLen + "）\n" +
                   repeatStr("=", 50);
            mergeName = "保留大于等于" + minBodyLen + "_" + srcBaseName + ".txt";
            mergeCol = keptTexts;
        }
        if (mergeCol) {
            var mergePath = outDirFull + "\\" + mergeName;
            var mergeParts = [hdr].concat(mergeCol);
            var mergeBody = mergeParts.join("\n");
            writeTextUTF8NoBOM(mergePath, mergeBody);
            debugLog("合并文件：" + mergeName + "（" + mergeCol.length + "章合并）");
        }
    }

    // --- 7. 完成报告 ---
    var extraInfo = "";
    var skipDetail = "";
    if (titleOnlyCount > 0) skipDetail = titleOnlyCount + "个仅有标题";
    if (shortBodyCount > 0) {
        if (skipDetail.length > 0) skipDetail += "、";
        skipDetail += shortBodyCount + "个正文不足";
    }
    if (skippedCount > 0) {
        var topStr2 = top1 + "字";
        if (skippedCount >= 2) topStr2 += "、" + top2 + "字";
        if (skippedCount >= 3) topStr2 += "、" + top3 + "字";
        extraInfo = "【跳过统计】\n" +
                    "  跳过章节：" + skippedCount + " 个（" + skipDetail + "）\n" +
                    "  前三正文：" + topStr2;
        debugLog("[提示] 跳过 " + skippedCount + " 个章节（" + skipDetail + "），前三：" + topStr2);
    } else if (skipDetail.length > 0) {
        debugLog("[提示] " + skipDetail + "（已生成）");
    }
    showCompleteReport("按章节拆分完成", writtenCount, outDirFull, tRead1, tScan1, t1, extraInfo);
}


// =============================================================================
// 第四部分：核心过程 2 - 聚合拆分
// =============================================================================

function parseGroups(chunkStr, total) {
    // 返回 { groupLens, groupSpaces, groupCount, error }
    var s = (chunkStr || "").trim();
    if (s.length === 0) {
        return { error: "聚合字符串为空" };
    }

    var groupLens = [];
    var groupSpaces = [];
    var consumed = 0;

    // 便捷模式：纯数字（无逗号无竖线）-> 每N章一份
    if (s.indexOf(",") < 0 && s.indexOf("|") < 0) {
        if (!isDigits(s)) {
            return { error: "便捷模式需为正整数: " + s };
        }
        var n = parseInt(s, 10);
        if (n <= 0) {
            return { error: "每份章数必须为正数: " + s };
        }
        var cnt = Math.ceil(total / n);
        groupLens.push(cnt);
        groupSpaces.push(n);
        return { groupLens: groupLens, groupSpaces: groupSpaces, groupCount: 1, error: "" };
    }

    // 多段格式：每份章数,份数|每份章数,份数|...
    var parts = s.split("|");
    for (var p = 0; p < parts.length; p++) {
        var part = parts[p].trim();
        if (part.length === 0) continue;

        var detail = part.split(",");
        if (detail.length !== 2) {
            return { error: "段格式错误: " + part + "（应为 每份章数,份数）" };
        }
        var d0 = detail[0].trim();
        var d1 = detail[1].trim();
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

function expandGroups(groupLens, groupSpaces, groupCount, total) {
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

function splitByGroups(inputPath, outputDir, chunkStr, fileNamePrefix, serialWidth) {
    // 参数默认值
    outputDir = outputDir || "";
    chunkStr = chunkStr || "40,3";
    fileNamePrefix = fileNamePrefix || "";
    serialWidth = serialWidth || 3;

    if (g_tTotal0 === 0) g_tTotal0 = Timer();

    var fso = CreateCOM("Scripting.FileSystemObject");

    // --- 1. 读取源文件 ---
    if (!fso.FileExists(inputPath)) {
        Application.MsgBox("源文件不存在：\n" + inputPath, vbExclamation, "错误");
        return;
    }
    var tRead0 = Timer();
    g_detectedEnc = detectEncodingFile(inputPath);
    var content = readTextAuto(inputPath);
    content = content.replace(/\r\n/g, "\n").replace(/\r/g, "\n");
    var lines = content.split("\n");
    var lineCount = lines.length;
    var tRead1 = Timer() - tRead0;

    // --- 2. 识别章节 ---
    var tScan0 = Timer();
    var ch = scanChapters(lines);
    var chCount = ch.count;
    var chStartLines = ch.starts;
    var chTitles = ch.titles;
    var unit = ch.unit;
    var tScan1 = Timer() - tScan0;

    if (chCount === 0) {
        Application.MsgBox("未识别到任何章节标题（第N章/第N回/第N节/第N卷）。\n请确认文件格式。", vbExclamation, "提示");
        return;
    }

    // --- 3. 解析聚合格式 ---
    var result = parseGroups(chunkStr, chCount);
    if (result.error && result.error.length > 0) {
        Application.MsgBox("聚合格式错误：\n" + result.error, vbExclamation, "错误");
        return;
    }
    var groupLens = result.groupLens;
    var groupSpaces = result.groupSpaces;
    var groupCount = result.groupCount;

    var consumed = 0;
    for (var g = 0; g < groupCount; g++) {
        consumed += groupLens[g] * groupSpaces[g];
    }
    var remainder = chCount - consumed;

    var segStr = "";
    for (var g2 = 0; g2 < groupCount; g2++) {
        if (g2 > 0) segStr += " | ";
        segStr += groupSpaces[g2] + "," + groupLens[g2];
    }

    // --- 4. 展开为文件列表 ---
    var expandResult = expandGroups(groupLens, groupSpaces, groupCount, chCount);
    var fileChStart = expandResult.fileChStart;
    var fileChEnd = expandResult.fileChEnd;
    var fileCount = expandResult.fileCount;

    // --- 5. 序号位数自适应 ---
    var fcStr = String(fileCount);
    if (fcStr.length > serialWidth) serialWidth = fcStr.length;
    var serialFmt = repeatStr("0", serialWidth);
    var prefix = fileNamePrefix;

    // --- 6. 确定输出目录 ---
    var outDirFull = resolveOutputDir(fso, inputPath, outputDir, "_分组");

    // --- 7. 生成预览并请求确认 ---
    var preview = "【聚合拆分预览】\n" +
                  "源文件：" + inputPath + "\n" +
                  "总行数：" + lineCount + "\n" +
                  "识别章节：" + chCount + "  单位：" + unit + "\n" +
                  "聚合格式：" + chunkStr + "\n" +
                  "解析段：" + segStr + "\n";
    if (remainder > 0) {
        preview += "[提示] 余数 " + remainder + " 章自动追加为1个文件\n";
    }
    preview += "将生成 " + fileCount + " 个文件：\n";
    var showN = Math.min(fileCount, 12);
    for (var f = 0; f < showN; f++) {
        var rangeStr = formatRange(fileChStart[f], fileChEnd[f], unit);
        preview += "  " + zeroPad(f + 1, serialWidth) + "  " + rangeStr + "\n";
    }
    if (fileCount > 12) {
        preview += "  ...（其余 " + (fileCount - 12) + " 份省略）\n";
    }
    preview += "\n输出目录：" + outDirFull + "\n\n确认开始拆分？";

    if (Application.MsgBox(preview, vbOKCancel + vbQuestion, "聚合拆分预览") !== vbOK) return;

    // --- 8. 创建输出目录 + 清理旧文件 ---
    if (!fso.FolderExists(outDirFull)) fso.CreateFolder(outDirFull);
    cleanOutputDir(outDirFull);

    // --- 9. 写每份文件 ---
    var fname = "";
    var t0 = Timer();
    try {
        for (var f2 = 0; f2 < fileCount; f2++) {
            var startLine = chStartLines[fileChStart[f2] - 1];
            var endLine;
            if (fileChEnd[f2] < chCount) {
                endLine = chStartLines[fileChEnd[f2]] - 1;
            } else {
                endLine = lineCount - 1;
            }

            var segCount = endLine - startLine;
            var parts = [];
            for (var li = 0; li <= segCount; li++) {
                parts.push(lines[startLine + li]);
            }
            var body = parts.join("\n");

            var rangeStr2 = formatRange(fileChStart[f2], fileChEnd[f2], unit);
            var safe = sanitizeFileName(rangeStr2);
            var serial = zeroPad(f2 + 1, serialWidth);
            fname = serial + "_" + safe + ".txt";
            if (prefix.length > 0) fname = prefix + "_" + fname;

            writeTextUTF8NoBOM(outDirFull + "\\" + fname, body);
        }
    } catch (e) {
        Application.MsgBox("写入第 " + (f2 + 1) + " 份文件时出错：\n" +
                           outDirFull + "\\" + fname + "\n错误：" + (e.message || e), vbExclamation, "写入错误");
        return;
    }

    // --- 10. 完成报告 ---
    showCompleteReport("聚合拆分完成", fileCount, outDirFull, tRead1, tScan1, Timer() - t0, "");
}


// =============================================================================
// 第五部分：对外入口 —— 选择TXT文件 → 选择拆分模式 → 生成文件
// =============================================================================

function 拆分TXT() {
    // --- 初始化计时 ---
    g_tTotal0 = Timer();
    g_tSelect = 0;

    // --- 步骤1：选择TXT文件 ---
    var tSel0 = Timer();
    var filePath = selectTxtFile("选择要拆分的TXT文件");
    g_tSelect = Timer() - tSel0;
    if (filePath.length === 0) return;

    // --- 步骤2：选择拆分模式 ---
    var mode = Application.MsgBox(
        "请选择拆分模式：\n\n" +
        "  [是]  按章节一一拆分（每章一个文件）\n" +
        "  [否]  聚合拆分（多章合并为一份）\n" +
        "  [取消] 清洁模式（按正文字数过滤并合并）",
        vbYesNoCancel + vbQuestion, "选择拆分模式");

    if (mode === vbCancel) {
        // --- 清洁模式 ---
        var cleanInput = Application.InputBox(
            "请输入清理参数（N,flag）：\n\n" +
            "  N     最小正文字数（正文汉字<N的章节跳过）\n" +
            "  flag  0=合并跳过章节（确定问题）\n" +
            "        1=合并保留章节（得到需要章节，默认）\n\n" +
            "示例：\n" +
            "  100        合并>=100字的保留章节\n" +
            "  100,1     合并>=100字的保留章节\n" +
            "  100,0     合并<100字的跳过章节",
            "清洁模式", "100,1", 100, 100, "", 0, 2);
        if (cleanInput === false) return;
        cleanInput = String(cleanInput).trim();
        if (cleanInput.length === 0) return;

        var cleanParts = cleanInput.split(",");
        if (cleanParts.length > 2) {
            Application.MsgBox("格式错误，请输入 N 或 N,flag", vbExclamation, "提示");
            return;
        }
        var cleanN_str = cleanParts[0].trim();
        if (!isDigits(cleanN_str)) {
            Application.MsgBox("N 必须为正整数。", vbExclamation, "提示");
            return;
        }
        var cleanN = parseInt(cleanN_str, 10);
        var cleanFlag = 1;
        if (cleanParts.length === 2) {
            var flagStr = cleanParts[1].trim();
            if (flagStr !== "0" && flagStr !== "1") {
                Application.MsgBox("flag 必须为 0 或 1。", vbExclamation, "提示");
                return;
            }
            cleanFlag = parseInt(flagStr, 10);
        }
        splitByChapter(filePath, "", "", 3, false, cleanN, cleanFlag);

    } else if (mode === vbYes) {
        // --- 按章节一一拆分 ---
        var contentMode = Application.MsgBox(
            "选择章节内容处理方式：\n\n" +
            "  [是] 生成所有章节（含仅有标题/正文不足）\n" +
            "  [否] 跳过仅有标题的章节（默认）",
            vbYesNo + vbQuestion + vbDefaultButton2, "章节内容处理");

        if (contentMode === vbYes) {
            splitByChapter(filePath, "", "", 3, true, 0, -1);
        } else {
            splitByChapter(filePath, "", "", 3, false, 0, -1);
        }

    } else {
        // --- 聚合拆分：输入格式 ---
        var prompt = "请输入聚合格式（每份章数,份数，以 | 分割多段）：\n\n" +
                     "示例：\n" +
                     "  40,3              每份40章，共3份\n" +
                     "  40                每40章一份（便捷模式）\n" +
                     "  20,1|20,1|80,1    多段：1-20、21-40、41-120\n\n" +
                     "（余数自动补齐，如 40,2 实际得3份）";
        var chunkStr = Application.InputBox(prompt, "聚合拆分 - 输入格式", "40,3", 100, 100, "", 0, 2);
        if (chunkStr === false) return;
        chunkStr = String(chunkStr).trim();
        if (chunkStr.length === 0) {
            Application.MsgBox("未输入格式。", vbExclamation, "提示");
            return;
        }
        splitByGroups(filePath, "", chunkStr, "", 3);
    }
}
