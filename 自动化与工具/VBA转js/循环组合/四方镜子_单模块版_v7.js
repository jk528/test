/*============================================================
 * 四方镜子 - JS宏 v7（HTML窗体版 + InputBox回退）
 * 根据 VBA v5/v6 最新设计优化：
 *   - HTML 窗体模拟 VBA 界面（2x2按钮网格 + 双边区）
 *   - 按钮显示 2x3 完整6个组合预览（A列a1,a2 / B列b1,b2,b3）
 *   - 算法与命名与 VBA 完全一致（正向=左快右慢，反向=左慢右快）
 *   - ShowDialog 不可用时自动回退 InputBox 模式
 * 使用方法：运行 四方镜子_主入口()
 * 注意：不同 WPS 版本的回调机制可能有差异，若 HTML 窗体
 *       点击按钮无反应，请改用 输入框模式() 并调整回调函数名
 *============================================================*/

// 常量
var xlToLeft = -4159;
var xlUp = -4162;
var xlCalculationManual = -4135;
var xlCalculationAutomatic = -4105;

// ============================================================
//  主入口：优先 HTML 窗体，失败回退 InputBox
// ============================================================

function 四方镜子_主入口() {
    try {
        if (显示窗体()) return;
    } catch (e) {
        // 窗体不可用，回退
    }
    输入框模式();
}

// ============================================================
//  操作分发（HTML窗体 与 InputBox 共用）
// ============================================================

function 处理操作(操作号, 连接符, 是否合并) {
    if (连接符 === "" || 连接符 === undefined || 连接符 === null) 连接符 = "-";
    try {
        switch (操作号) {
            case 1: 四方循环_执行(false, false, 连接符, 是否合并); break; // 反向竖向
            case 2: 四方循环_执行(true, true, 连接符, 是否合并); break;   // 正向横向
            case 3: 四方循环_执行(true, false, 连接符, 是否合并); break;  // 正向竖向
            case 4: 四方循环_执行(false, true, 连接符, 是否合并); break;  // 反向横向
            case 5: 双边循环_执行(true, 连接符, 是否合并); break;         // 双边竖
            case 6: 双边循环_执行(false, 连接符, 是否合并); break;        // 双边横
            default:
                Application.Alert("未知操作: " + 操作号, "提示");
        }
    } catch (e) {
        Application.Alert("执行错误: " + e.message, "错误");
    }
}

// ============================================================
//  HTML 窗体模式（内嵌 HTML 字符串 + ShowDialog）
// ============================================================

function 显示窗体() {
    var html = 获取窗体HTML();
    if (html === "") return false;

    // 写入临时 HTML 文件（与工作簿同目录）
    var fso = new ActiveXObject("Scripting.FileSystemObject");
    var 路径 = Application.ThisWorkbook.Path + "\\四方镜子_窗体.html";
    var 文件 = fso.CreateTextFile(路径, true);
    文件.Write(html);
    文件.Close();

    // 尝试 ShowDialog（不同版本回调机制不同）
    try {
        // 方式A：回调函数作为第二参数（部分WPS版本支持）
        var 已处理 = false;
        var 回调 = function(msg) {
            已处理 = true;
            try {
                var p = String(msg).split("|");
                var op = parseInt(p[0]);
                var conn = p[1] || "-";
                var merge = (String(p[2]) === "1");
                处理操作(op, conn, merge);
            } catch (e) {
                Application.Alert("回调错误: " + e.message, "错误");
            }
        };
        Application.ShowDialog(路径, 回调);
        // ShowDialog 返回后，若回调未执行则提示
        if (!已处理) {
            var r = Application.Alert("窗体已关闭。若按钮无反应，请改用输入框模式。", "提示");
        }
        return true;
    } catch (e) {
        // ShowDialog 不可用，删除临时文件，回退
        try { fso.DeleteFile(路径); } catch (e2) {}
        return false;
    }
}

// HTML 窗体点击按钮时触发的全局回调（兼容 window.external.notify 机制）
function OnDialogNotify(msg) {
    try {
        var p = String(msg).split("|");
        var op = parseInt(p[0]);
        var conn = p[1] || "-";
        var merge = (String(p[2]) === "1");
        处理操作(op, conn, merge);
    } catch (e) {
        Application.Alert("回调错误: " + e.message, "错误");
    }
}

// ============================================================
//  HTML 界面（内嵌，模拟 VBA 窗体）
// ============================================================

function 获取窗体HTML() {
    return [
        "<!DOCTYPE html>",
        "<html><head><meta charset=\"utf-8\">",
        "<style>",
        "body{font-family:'Microsoft YaHei';margin:8px;background:#f5f7fa;width:540px;}",
        ".title{text-align:center;font-size:22px;font-weight:bold;color:#2b6cb0;margin-bottom:8px;}",
        ".top{display:flex;align-items:center;gap:12px;margin-bottom:10px;background:#fff;border-radius:8px;padding:8px;}",
        ".top label{font-size:14px;color:#333;}",
        ".top input[type=text]{width:60px;font-size:14px;padding:3px;border:1px solid #a0aec0;border-radius:4px;}",
        ".field{border:2px solid #2b6cb0;border-radius:8px;padding:8px;margin-bottom:10px;background:#fff;}",
        ".ftitle{font-weight:bold;color:#2b6cb0;margin-bottom:6px;font-size:14px;}",
        ".grid{display:grid;grid-template-columns:1fr 1fr;gap:6px;}",
        ".btn{border:1px solid #2b6cb0;background:#fff;border-radius:6px;padding:5px;cursor:pointer;font-size:12px;}",
        ".btn:hover{background:#e6f0ff;}",
        "pre{margin:0;font-family:Consolas,monospace;font-size:11px;line-height:1.35;text-align:center;}",
        ".close{display:block;margin:0 auto;width:120px;background:#dc5050;color:#fff;border:none;padding:8px;font-size:14px;border-radius:6px;cursor:pointer;}",
        "</style></head><body>",
        "<div class=\"title\">四方镜</div>",
        "<div class=\"top\">",
        "<label>连接符号:</label><input type=\"text\" id=\"conn\" value=\"-\" oninput=\"refresh()\">",
        "<label><input type=\"checkbox\" id=\"merge\" checked onchange=\"refresh()\"> 合并</label>",
        "</div>",
        "<div class=\"field\"><div class=\"ftitle\">四方循环（笛卡尔积）</div><div class=\"grid\">",
        "<button class=\"btn\" id=\"b1\" onclick=\"go(1)\"></button>",
        "<button class=\"btn\" id=\"b3\" onclick=\"go(3)\"></button>",
        "<button class=\"btn\" id=\"b2\" onclick=\"go(2)\"></button>",
        "<button class=\"btn\" id=\"b4\" onclick=\"go(4)\"></button>",
        "</div></div>",
        "<div class=\"field\"><div class=\"ftitle\">双边循环（LCM独立循环）</div><div class=\"grid\">",
        "<button class=\"btn\" id=\"b5\" onclick=\"go(5)\"></button>",
        "<button class=\"btn\" id=\"b6\" onclick=\"go(6)\"></button>",
        "</div></div>",
        "<button class=\"close\" onclick=\"closeWin()\">关闭窗体</button>",
        "<script>",
        "var d1a='a1',d2a='a2',d1b='b1',d2b='b2',d3b='b3';",
        "function jo(x,y,s){return x+s+y;}",
        "function refresh(){",
        "  var conn=document.getElementById('conn').value||'-';",
        "  var merge=document.getElementById('merge').checked;",
        "  var s=merge?conn:'  ';",
        "  var m1=jo(d1a,d1b,s),m2=jo(d2a,d1b,s),m3=jo(d1a,d2b,s),m4=jo(d2a,d2b,s),m5=jo(d1a,d3b,s),m6=jo(d2a,d3b,s);",
        "  // 反竖（左慢右快）：a1b1 a1b2 a1b3 a2b1 a2b2 a2b3",
        "  document.getElementById('b1').innerHTML='<pre>'+m1+'<br>'+m3+'<br>'+m5+'<br>'+m2+'<br>'+m4+'<br>'+m6+'</pre>';",
        "  // 正竖（左快右慢）：a1b1 a2b1 a1b2 a2b2 a1b3 a2b3",
        "  document.getElementById('b3').innerHTML='<pre>'+m1+'<br>'+m2+'<br>'+m3+'<br>'+m4+'<br>'+m5+'<br>'+m6+'</pre>';",
        "  // 正横（一行6个）",
        "  document.getElementById('b2').innerHTML='<pre>'+m1+'  '+m2+'  '+m3+'  '+m4+'  '+m5+'  '+m6+'</pre>';",
        "  // 反横（一行6个）",
        "  document.getElementById('b4').innerHTML='<pre>'+m1+'  '+m3+'  '+m5+'  '+m2+'  '+m4+'  '+m6+'</pre>';",
        "  // 双边竖（独立循环）：a1b1 a2b2 a1b3 a2b1 a1b2 a2b3",
        "  document.getElementById('b5').innerHTML='<pre>'+m1+'<br>'+m4+'<br>'+m5+'<br>'+m2+'<br>'+m3+'<br>'+m6+'</pre>';",
        "  // 双边横",
        "  document.getElementById('b6').innerHTML='<pre>'+m1+'  '+m4+'  '+m5+'  '+m2+'  '+m3+'  '+m6+'</pre>';",
        "}",
        "function go(op){",
        "  var conn=document.getElementById('conn').value||'-';",
        "  var merge=document.getElementById('merge').checked?1:0;",
        "  var msg=op+'|'+conn+'|'+merge;",
        "  try{window.external.notify(msg);}catch(e){try{window.external.Notify(msg);}catch(e2){}}",
        "}",
        "function closeWin(){try{window.external.notify('close');}catch(e){try{window.external.Notify('close');}catch(e2){}}}",
        "refresh();",
        "</script></body></html>"
    ].join("\n");
}

// ============================================================
//  InputBox 回退模式（无窗体，纯对话框交互）
// ============================================================

function 输入框模式() {
    var 菜单 = "===== 四方镜子 =====\n\n"
        + "【四方循环（笛卡尔积）】\n"
        + "  1 = 反向竖向（左慢右快）\n"
        + "  2 = 正向横向（左快右慢）\n"
        + "  3 = 正向竖向（左快右慢）\n"
        + "  4 = 反向横向（左慢右快）\n\n"
        + "【双边循环（LCM独立循环）】\n"
        + "  5 = 竖向输出\n"
        + "  6 = 横向输出\n\n"
        + "输入数字选择操作（1-6）：";

    while (true) {
        var 输入 = Application.InputBox(菜单, "四方镜子", "1");
        if (输入 === false || 输入 === "") break;
        var 操作号 = parseInt(输入);
        if (isNaN(操作号) || 操作号 < 1 || 操作号 > 6) {
            Application.Alert("请输入1-6之间的数字", "提示");
            continue;
        }
        var 连接符 = Application.InputBox("输入连接符号（如 - _ / 等）", "连接符", "-");
        if (连接符 === false || 连接符 === "") 连接符 = "-";
        var 合并输入 = Application.InputBox("输出模式：\n  1 = 合并（多列拼成一列）\n  0 = 分开（多列保持独立）", "合并模式", "1");
        var 是否合并 = (String(合并输入) === "1");
        处理操作(操作号, 连接符, 是否合并);
        var 继续 = Application.InputBox("操作完成！\n\n  1 = 继续\n  0 = 退出", "四方镜子", "0");
        if (String(继续) !== "1") break;
    }
}

// ============================================================
//  工具函数
// ============================================================

function 循环索引(n, Y) {
    return ((n + Y - 1) % Y) + 1;
}

function 向上取整(c, d) {
    return Math.ceil(c / d);
}

function 最后列(ws) {
    return ws.Cells.Item(1, ws.Columns.Count).End(xlToLeft).Column;
}

function 最后行(ws, 列) {
    return ws.Cells.Item(ws.Rows.Count, 列).End(xlUp).Row;
}

function 数组乘积(数组) {
    var p = 1;
    for (var i = 0; i < 数组.length; i++) {
        p *= 数组[i];
    }
    return p;
}

function 最大公约数(a, b) {
    while (b !== 0) {
        var t = b;
        b = a % b;
        a = t;
    }
    return a;
}

function 最小公倍数(数组) {
    var lcm = 数组[0];
    for (var i = 1; i < 数组.length; i++) {
        lcm = (lcm * 数组[i]) / 最大公约数(lcm, 数组[i]);
    }
    return lcm;
}

function 新建结果表(名称前缀) {
    var ws = Worksheets.Add({ After: Application.ActiveSheet });
    var 序号 = Application.Sheets.Count;
    var 表名 = 名称前缀 + "_" + 序号;
    if (表名.length > 31) {
        表名 = 表名.substring(0, 31 - String(序号).length - 1) + "_" + 序号;
    }
    try {
        ws.Name = 表名;
    } catch (e) {
        ws.Name = "结果_" + new Date().getHours() + "" + new Date().getMinutes() + "" + new Date().getSeconds();
    }
    return ws;
}

// ============================================================
//  核心算法一：四方循环（笛卡尔积）
//  正向 = 左快右慢（A每行变，B每2行变）
//  反向 = 左慢右快（A每3行变，B每行变）
// ============================================================

function 四方循环_执行(是否正向, 是否横向, 连接符, 是否合并) {
    var 原刷新 = Application.ScreenUpdating;
    var 原计算 = Application.Calculation;
    Application.ScreenUpdating = false;
    Application.Calculation = xlCalculationManual;

    try {
        var ws = Application.ActiveSheet;
        var 总列数 = 最后列(ws);
        if (总列数 === 0) { Application.Alert("无有效数据", "提示"); return; }

        var 每列行数 = [];
        for (var c = 1; c <= 总列数; c++) {
            每列行数.push(最后行(ws, c));
        }

        var 总行数 = 数组乘积(每列行数);
        if (总行数 > 1048576) { Application.Alert("已超出表格限制", "提示"); return; }

        var 源数据 = ws.Range(ws.Cells.Item(1, 1), ws.Cells.Item(总行数, 总列数)).Value2;

        // 步长：正向=1,n1,n1*n2...（左快右慢）；反向=总数/累计（左慢右快）
        var 步长 = [];
        if (是否正向) {
            步长[0] = 1;
            for (var c = 1; c < 总列数; c++) {
                步长[c] = 步长[c - 1] * 每列行数[c - 1];
            }
        } else {
            var 累计 = 1;
            for (var c = 0; c < 总列数; c++) {
                累计 *= 每列行数[c];
                步长[c] = 总行数 / 累计;
            }
        }

        var 结果 = [];
        for (var c = 0; c < 总列数; c++) {
            结果[c] = [];
            for (var r = 0; r < 总行数; r++) {
                var 源行 = 循环索引(向上取整(r + 1, 步长[c]), 每列行数[c]);
                结果[c][r] = 源数据[源行 - 1][c];
            }
        }

        var 方向名 = (是否正向 ? "正" : "反") + (是否横向 ? "横" : "竖");
        var 合并名 = 是否合并 ? "合并" : "分开";
        var 新表 = 新建结果表("四方_" + 方向名 + "_" + 合并名);

        if (是否横向) {
            if (是否合并) {
                var 横合并 = [];
                for (var r = 0; r < 总行数; r++) {
                    var 片段 = [];
                    for (var c = 0; c < 总列数; c++) {
                        片段.push(结果[c][r]);
                    }
                    横合并.push(片段.join(连接符));
                }
                新表.Range("A1").Resize(1, 总行数).Value2 = [横合并];
            } else {
                新表.Range("A1").Resize(总列数, 总行数).Value2 = 结果;
            }
        } else {
            if (是否合并) {
                var 竖合并 = [];
                for (var r = 0; r < 总行数; r++) {
                    var 片段 = [];
                    for (var c = 0; c < 总列数; c++) {
                        片段.push(结果[c][r]);
                    }
                    竖合并.push([片段.join(连接符)]);
                }
                新表.Range("A1").Resize(总行数, 1).Value2 = 竖合并;
            } else {
                var 竖结果 = [];
                for (var r = 0; r < 总行数; r++) {
                    竖结果[r] = [];
                    for (var c = 0; c < 总列数; c++) {
                        竖结果[r][c] = 结果[c][r];
                    }
                }
                新表.Range("A1").Resize(总行数, 总列数).Value2 = 竖结果;
            }
        }
    } finally {
        Application.ScreenUpdating = 原刷新;
        Application.Calculation = 原计算;
    }
}

// ============================================================
//  核心算法二：双边循环（LCM独立循环）
// ============================================================

function 双边循环_执行(是否竖向, 连接符, 是否合并) {
    var 原刷新 = Application.ScreenUpdating;
    var 原计算 = Application.Calculation;
    Application.ScreenUpdating = false;
    Application.Calculation = xlCalculationManual;

    try {
        var ws = Application.ActiveSheet;
        var 总列数 = 最后列(ws);
        if (总列数 === 0) { Application.Alert("无有效数据", "提示"); return; }

        var 每列行数 = [];
        for (var c = 1; c <= 总列数; c++) {
            每列行数.push(最后行(ws, c));
        }

        var 列乘积 = 数组乘积(每列行数);
        var lcm = 最小公倍数(每列行数);
        if (lcm > 1048576) { Application.Alert("已超出表格限制", "提示"); return; }

        var 是否完整 = (列乘积 === lcm);

        var 源数据 = ws.Range(ws.Cells.Item(1, 1), ws.Cells.Item(lcm, 总列数)).Value2;

        var 结果 = [];
        for (var c = 0; c < 总列数; c++) {
            结果[c] = [];
            for (var r = 0; r < lcm; r++) {
                var 源行 = 循环索引(r + 1, 每列行数[c]);
                结果[c][r] = 源数据[源行 - 1][c];
            }
        }

        var 方向名 = 是否竖向 ? "竖" : "横";
        var 合并名 = 是否合并 ? "合并" : "分开";
        var 完整名 = 是否完整 ? "完整" : ("残缺" + 列乘积 + "-" + lcm);
        var 新表 = 新建结果表("双边_" + 方向名 + "_" + 完整名 + "_" + 合并名);

        if (是否竖向) {
            if (是否合并) {
                var 竖合并 = [];
                for (var r = 0; r < lcm; r++) {
                    var 片段 = [];
                    for (var c = 0; c < 总列数; c++) {
                        片段.push(结果[c][r]);
                    }
                    竖合并.push([片段.join(连接符)]);
                }
                新表.Range("A1").Resize(lcm, 1).Value2 = 竖合并;
            } else {
                var 竖结果 = [];
                for (var r = 0; r < lcm; r++) {
                    竖结果[r] = [];
                    for (var c = 0; c < 总列数; c++) {
                        竖结果[r][c] = 结果[c][r];
                    }
                }
                新表.Range("A1").Resize(lcm, 总列数).Value2 = 竖结果;
            }
        } else {
            if (是否合并) {
                var 横合并 = [];
                for (var r = 0; r < lcm; r++) {
                    var 片段 = [];
                    for (var c = 0; c < 总列数; c++) {
                        片段.push(结果[c][r]);
                    }
                    横合并.push(片段.join(连接符));
                }
                新表.Range("A1").Resize(1, lcm).Value2 = [横合并];
            } else {
                新表.Range("A1").Resize(总列数, lcm).Value2 = 结果;
            }
        }
    } finally {
        Application.ScreenUpdating = 原刷新;
        Application.Calculation = 原计算;
    }
}
