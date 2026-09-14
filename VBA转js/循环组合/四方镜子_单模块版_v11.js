/*============================================================
 * 四方镜子 - JS宏 v11.5（HTML窗体版 + InputBox回退）
 * 对应 VBA v11.5 最终版：
 *   - 7 个按钮 + 3 个复选框（合并 / 数据反转 / 四象限对称）
 *   - 四象限对称：真正镜像（行反转+元素反转），开关绑定按钮1~4
 *   - 备选算法验证（7种：A~G）
 * 使用方法：运行 四方镜子_主入口()
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
    } catch (e) {}
    输入框模式();
}

// ============================================================
//  操作分发（HTML窗体 与 InputBox 共用）
// ============================================================

function 处理操作(操作号, 连接符, 是否合并, 数据是否反转, 四象限是否对称) {
    if (连接符 === "" || 连接符 === undefined || 连接符 === null) 连接符 = "-";
    try {
        switch (操作号) {
            case 1: // 反向竖向
                if (四象限是否对称) 四象限_执行(false, false, 连接符, 是否合并, 数据是否反转);
                else 四方循环_执行(false, false, 连接符, 是否合并, 数据是否反转);
                break;
            case 2: // 正向横向
                if (四象限是否对称) 四象限_执行(true, true, 连接符, 是否合并, 数据是否反转);
                else 四方循环_执行(true, true, 连接符, 是否合并, 数据是否反转);
                break;
            case 3: // 正向竖向
                if (四象限是否对称) 四象限_执行(true, false, 连接符, 是否合并, 数据是否反转);
                else 四方循环_执行(true, false, 连接符, 是否合并, 数据是否反转);
                break;
            case 4: // 反向横向
                if (四象限是否对称) 四象限_执行(false, true, 连接符, 是否合并, 数据是否反转);
                else 四方循环_执行(false, true, 连接符, 是否合并, 数据是否反转);
                break;
            case 5: 双边循环_执行(true, 连接符, 是否合并, 数据是否反转); break;  // 双边竖
            case 6: 双边循环_执行(false, 连接符, 是否合并, 数据是否反转); break; // 双边横
            case 7: 备选算法_执行(连接符, 是否合并, 数据是否反转); break;         // 备选算法
            default:
                Application.Alert("未知操作: " + 操作号, "提示");
        }
    } catch (e) {
        Application.Alert("执行错误: " + e.message, "错误");
    }
}

// ============================================================
//  HTML 窗体模式
// ============================================================

function 显示窗体() {
    var html = 获取窗体HTML();
    if (html === "") return false;

    try {
        var dlg = Application.CreateDialog(html);
        dlg.ShowDialog();
        return true;
    } catch (e) {
        try {
            // WPS 另一种写法
            var dlg2 = Application.ShowDialog(html);
            return true;
        } catch (e2) {
            return false;
        }
    }
}

// HTML 窗体回调（不同 WPS 版本回调名可能不同）
function OnDialogNotify(msg) {
    处理回调(msg);
}

function Notify(msg) {
    处理回调(msg);
}

function 处理回调(msg) {
    if (msg === "close") return;
    var parts = msg.split("|");
    var 操作号 = parseInt(parts[0]);
    var 连接符 = parts[1] || "-";
    var 是否合并 = (parts[2] === "1");
    var 数据是否反转 = (parts[3] === "1");
    var 四象限是否对称 = (parts[4] === "1");
    处理操作(操作号, 连接符, 是否合并, 数据是否反转, 四象限是否对称);
}

// ============================================================
//  HTML 窗体内容
// ============================================================

function 获取窗体HTML() {
    return [
        "<!DOCTYPE html>",
        "<html><head><meta charset=\"utf-8\">",
        "<style>",
        "body{font-family:'Microsoft YaHei';margin:8px;background:#f5f7fa;width:560px;}",
        ".title{text-align:center;font-size:22px;font-weight:bold;color:#2b6cb0;margin-bottom:8px;}",
        ".top{display:flex;align-items:center;gap:12px;margin-bottom:10px;background:#fff;border-radius:8px;padding:8px;flex-wrap:wrap;}",
        ".top label{font-size:14px;color:#333;}",
        ".top input[type=text]{width:50px;font-size:14px;padding:3px;border:1px solid #a0aec0;border-radius:4px;}",
        ".top .cbx{display:flex;align-items:center;gap:4px;}",
        ".field{border:2px solid #2b6cb0;border-radius:8px;padding:8px;margin-bottom:10px;background:#fff;}",
        ".ftitle{font-weight:bold;color:#2b6cb0;margin-bottom:6px;font-size:14px;}",
        ".grid{display:grid;grid-template-columns:1fr 1fr;gap:6px;}",
        ".btn{border:1px solid #2b6cb0;background:#fff;border-radius:6px;padding:5px;cursor:pointer;font-size:12px;}",
        ".btn:hover{background:#e6f0ff;}",
        ".btn7{border:1px solid #d69e2e;background:#fff8e1;border-radius:6px;padding:8px;cursor:pointer;font-size:13px;font-weight:bold;color:#744210;width:100%;}",
        ".btn7:hover{background:#faf089;}",
        "pre{margin:0;font-family:Consolas,monospace;font-size:11px;line-height:1.35;text-align:center;}",
        ".close{display:block;margin:10px auto 0;width:120px;background:#dc5050;color:#fff;border:none;padding:8px;font-size:14px;border-radius:6px;cursor:pointer;}",
        ".quad-on{border-color:#9f7aea !important;background:#faf5ff !important;}",
        "</style></head><body>",
        "<div class=\"title\">四方镜 v11.5</div>",

        // 顶部开关
        "<div class=\"top\">",
        "<label>连接符:</label><input type=\"text\" id=\"conn\" value=\"-\" oninput=\"refresh()\">",
        "<label class=\"cbx\"><input type=\"checkbox\" id=\"merge\" checked onchange=\"refresh()\"> 合并</label>",
        "<label class=\"cbx\"><input type=\"checkbox\" id=\"revData\" onchange=\"refresh()\"> 数据反转</label>",
        "<label class=\"cbx\"><input type=\"checkbox\" id=\"quad\" onchange=\"refresh()\"> 四象限对称</label>",
        "</div>",

        // 四方循环 4 按钮
        "<div class=\"field\"><div class=\"ftitle\">四方循环（笛卡尔积）</div><div class=\"grid\">",
        "<button class=\"btn\" id=\"b1\" onclick=\"go(1)\"></button>",
        "<button class=\"btn\" id=\"b3\" onclick=\"go(3)\"></button>",
        "<button class=\"btn\" id=\"b2\" onclick=\"go(2)\"></button>",
        "<button class=\"btn\" id=\"b4\" onclick=\"go(4)\"></button>",
        "</div></div>",

        // 双边循环 2 按钮
        "<div class=\"field\"><div class=\"ftitle\">双边循环（LCM独立循环）</div><div class=\"grid\">",
        "<button class=\"btn\" id=\"b5\" onclick=\"go(5)\"></button>",
        "<button class=\"btn\" id=\"b6\" onclick=\"go(6)\"></button>",
        "</div></div>",

        // 备选算法
        "<button class=\"btn7\" onclick=\"go(7)\">备选算法验证（7种：A/B/C/D/E/F/G）</button>",

        "<button class=\"close\" onclick=\"closeWin()\">关闭窗体</button>",

        "<script>",
        "var d1a='A1',d2a='A2',d1b='B3',d2b='B4',d3b='B5';",
        "function jo(x,y,s){return x+s+y;}",
        "function refresh(){",
        "  var conn=document.getElementById('conn').value||'-';",
        "  var merge=document.getElementById('merge').checked;",
        "  var rev=document.getElementById('revData').checked;",
        "  var quad=document.getElementById('quad').checked;",
        "  var s=merge?conn:'  ';",
        "  // 数据反转：A列上下颠倒（A2,A1），B列上下颠倒（B5,B4,B3）",
        "  var a1=rev?d2a:d1a, a2=rev?d1a:d2a;",
        "  var b1=rev?d3b:d1b, b2=d2b, b3=rev?d1b:d3b;",
        "  var m1=jo(a1,b1,s),m2=jo(a2,b1,s),m3=jo(a1,b2,s),m4=jo(a2,b2,s),m5=jo(a1,b3,s),m6=jo(a2,b3,s);",
        "  // 按钮1：反竖（左慢右快）",
        "  document.getElementById('b1').innerHTML='<pre>'+m1+'<br>'+m3+'<br>'+m5+'<br>'+m2+'<br>'+m4+'<br>'+m6+'</pre>';",
        "  // 按钮3：正竖（左快右慢）",
        "  document.getElementById('b3').innerHTML='<pre>'+m1+'<br>'+m2+'<br>'+m3+'<br>'+m4+'<br>'+m5+'<br>'+m6+'</pre>';",
        "  // 按钮2：正横",
        "  document.getElementById('b2').innerHTML='<pre>'+m1+'  '+m2+'  '+m3+'  '+m4+'  '+m5+'  '+m6+'</pre>';",
        "  // 按钮4：反横",
        "  document.getElementById('b4').innerHTML='<pre>'+m1+'  '+m3+'  '+m5+'  '+m2+'  '+m4+'  '+m6+'</pre>';",
        "  // 按钮5：双边竖",
        "  document.getElementById('b5').innerHTML='<pre>'+m1+'<br>'+m4+'<br>'+m5+'<br>'+m2+'<br>'+m3+'<br>'+m6+'</pre>';",
        "  // 按钮6：双边横",
        "  document.getElementById('b6').innerHTML='<pre>'+m1+'  '+m4+'  '+m5+'  '+m2+'  '+m3+'  '+m6+'</pre>';",
        "  // 四象限开关：高亮四方循环按钮",
        "  var btns=['b1','b2','b3','b4'];",
        "  for(var i=0;i<btns.length;i++){",
        "    var el=document.getElementById(btns[i]);",
        "    if(quad) el.classList.add('quad-on'); else el.classList.remove('quad-on');",
        "  }",
        "}",
        "function go(op){",
        "  var conn=document.getElementById('conn').value||'-';",
        "  var merge=document.getElementById('merge').checked?1:0;",
        "  var rev=document.getElementById('revData').checked?1:0;",
        "  var quad=document.getElementById('quad').checked?1:0;",
        "  var msg=op+'|'+conn+'|'+merge+'|'+rev+'|'+quad;",
        "  try{window.external.notify(msg);}catch(e){try{window.external.Notify(msg);}catch(e2){}}",
        "}",
        "function closeWin(){try{window.external.notify('close');}catch(e){try{window.external.Notify('close');}catch(e2){}}}",
        "refresh();",
        "</script></body></html>"
    ].join("\n");
}

// ============================================================
//  输入框回退模式
// ============================================================

function 输入框模式() {
    var 菜单 = "===== 四方镜子 v11.5 =====\n\n"
        + "【四方循环（笛卡尔积）】\n"
        + "  1 = 反向竖向（左慢右快）\n"
        + "  2 = 正向横向（左快右慢）\n"
        + "  3 = 正向竖向（左快右慢）\n"
        + "  4 = 反向横向（左慢右快）\n\n"
        + "【双边循环（LCM独立循环）】\n"
        + "  5 = 竖向输出\n"
        + "  6 = 横向输出\n\n"
        + "【其他】\n"
        + "  7 = 备选算法验证（7种）\n\n"
        + "输入数字选择操作（1-7）：";

    while (true) {
        var 输入 = Application.InputBox(菜单, "四方镜子", "3");
        if (输入 === false || 输入 === "") break;
        var 操作号 = parseInt(输入);
        if (isNaN(操作号) || 操作号 < 1 || 操作号 > 7) {
            Application.Alert("请输入1-7之间的数字", "提示");
            continue;
        }
        var 连接符 = Application.InputBox("输入连接符号（如 - _ / 等）", "连接符", "-");
        if (连接符 === false || 连接符 === "") 连接符 = "-";
        var 合并输入 = Application.InputBox("输出模式：\n  1 = 合并（多列拼成一列）\n  0 = 分开（多列保持独立）", "合并模式", "1");
        var 是否合并 = (String(合并输入) === "1");
        var 反转输入 = Application.InputBox("数据反转：\n  1 = 是（每列从下往上读）\n  0 = 否（从上往下读）", "数据反转", "0");
        var 数据是否反转 = (String(反转输入) === "1");
        var 四象限输入 = "0";
        if (操作号 >= 1 && 操作号 <= 4) {
            四象限输入 = Application.InputBox("四象限对称：\n  1 = 是（生成4个镜像象限）\n  0 = 否（单表输出）", "四象限对称", "0");
        }
        var 四象限是否对称 = (String(四象限输入) === "1");
        处理操作(操作号, 连接符, 是否合并, 数据是否反转, 四象限是否对称);
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

// 读取源数据（支持数据反转）
function 读取源数据(ws, 总行数, 总列数, 每列行数, 数据是否反转) {
    var 原始 = ws.Range(ws.Cells.Item(1, 1), ws.Cells.Item(总行数, 总列数)).Value2;
    if (!数据是否反转) return 原始;
    // 数据反转：每列上下颠倒
    var 结果 = [];
    for (var r = 0; r < 总行数; r++) {
        结果[r] = [];
        for (var c = 0; c < 总列数; c++) {
            var 源行 = 每列行数[c] - 1 - (r % 每列行数[c]);
            if (r >= 每列行数[c]) 源行 = r;
            结果[r][c] = 原始[源行][c];
        }
    }
    return 结果;
}

// ============================================================
//  核心算法一：四方循环（笛卡尔积）
// ============================================================

function 四方循环_执行(是否正向, 是否横向, 连接符, 是否合并, 数据是否反转) {
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

        var 源数据 = 读取源数据(ws, 总行数, 总列数, 每列行数, 数据是否反转);

        // 步长：正向=左快右慢；反向=左慢右快
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

        // 结果按列存：结果[列][行]
        var 结果 = [];
        for (var c = 0; c < 总列数; c++) {
            结果[c] = [];
            for (var r = 0; r < 总行数; r++) {
                var 源行 = 循环索引(向上取整(r + 1, 步长[c]), 每列行数[c]) - 1;
                结果[c][r] = 源数据[源行][c];
            }
        }

        var 方向名 = (是否正向 ? "正" : "反") + (是否横向 ? "横" : "竖");
        var 合并名 = 是否合并 ? "合并" : "分开";
        var 反转后缀 = 数据是否反转 ? "_反序" : "";
        var 新表 = 新建结果表("四方_" + 方向名 + "_" + 合并名 + 反转后缀);

        输出结果(新表, 结果, 总列数, 总行数, 是否横向, 连接符, 是否合并);
    } finally {
        Application.ScreenUpdating = 原刷新;
        Application.Calculation = 原计算;
    }
}

// 通用输出函数（结果按列存）
function 输出结果(新表, 结果, 总列数, 总行数, 是否横向, 连接符, 是否合并) {
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
}

// ============================================================
//  核心算法二：双边循环（LCM独立循环）
// ============================================================

function 双边循环_执行(是否竖向, 连接符, 是否合并, 数据是否反转) {
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
        var 源数据 = 读取源数据(ws, lcm, 总列数, 每列行数, 数据是否反转);

        var 结果 = [];
        for (var c = 0; c < 总列数; c++) {
            结果[c] = [];
            for (var r = 0; r < lcm; r++) {
                var 源行 = 循环索引(r + 1, 每列行数[c]) - 1;
                结果[c][r] = 源数据[源行][c];
            }
        }

        var 方向名 = 是否竖向 ? "竖" : "横";
        var 合并名 = 是否合并 ? "合并" : "分开";
        var 完整名 = 是否完整 ? "完整" : ("残缺" + 列乘积 + "-" + lcm);
        var 反转后缀 = 数据是否反转 ? "_反序" : "";
        var 新表 = 新建结果表("双边_" + 方向名 + "_" + 完整名 + "_" + 合并名 + 反转后缀);

        输出结果(新表, 结果, 总列数, lcm, 是否竖向, 连接符, 是否合并);
    } finally {
        Application.ScreenUpdating = 原刷新;
        Application.Calculation = 原计算;
    }
}

// ============================================================
//  核心算法三：四象限镜像对称
//  左上=基准，右上=左右镜像，左下=上下镜像，右下=中心镜像
// ============================================================

function 四象限_执行(是否正向, 是否横向, 连接符, 是否合并, 数据是否反转) {
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
        if (总行数 > 500000) { Application.Alert("行数过大，四象限暂不支持（单象限需在50万行内）", "提示"); return; }

        var 源数据 = 读取源数据(ws, 总行数, 总列数, 每列行数, 数据是否反转);

        // 步长
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

        // Q1 左上 = 基准数据（按列存）
        var Q1 = [];
        for (var c = 0; c < 总列数; c++) {
            Q1[c] = [];
            for (var r = 0; r < 总行数; r++) {
                var 源行 = 循环索引(向上取整(r + 1, 步长[c]), 每列行数[c]) - 1;
                Q1[c][r] = 源数据[源行][c];
            }
        }

        // Q2 右上 = 左右镜像（每行元素反转）
        var Q2 = [];
        for (var c = 0; c < 总列数; c++) {
            Q2[c] = [];
            for (var r = 0; r < 总行数; r++) {
                Q2[c][r] = Q1[总列数 - 1 - c][r];
            }
        }

        // Q3 左下 = 上下镜像（行顺序反转）
        var Q3 = [];
        for (var c = 0; c < 总列数; c++) {
            Q3[c] = [];
            for (var r = 0; r < 总行数; r++) {
                Q3[c][r] = Q1[c][总行数 - 1 - r];
            }
        }

        // Q4 右下 = 中心镜像（行反转 + 元素反转）
        var Q4 = [];
        for (var c = 0; c < 总列数; c++) {
            Q4[c] = [];
            for (var r = 0; r < 总行数; r++) {
                Q4[c][r] = Q1[总列数 - 1 - c][总行数 - 1 - r];
            }
        }

        var 基准名 = (是否正向 ? "正" : "反") + (是否横向 ? "横" : "竖");
        var 合并名 = 是否合并 ? "合并" : "分开";
        var 反转后缀 = 数据是否反转 ? "_反序" : "";
        var 新表 = 新建结果表("四象限_" + 基准名 + "_" + 合并名 + 反转后缀);
        var 是否竖向 = !是否横向;

        // ===== 输出四象限 =====
        if (是否竖向) {
            四象限_竖向输出(新表, Q1, Q2, Q3, Q4, 总列数, 总行数, 连接符, 是否合并);
        } else {
            四象限_横向输出(新表, Q1, Q2, Q3, Q4, 总列数, 总行数, 连接符, 是否合并);
        }

        新表.Cells.EntireColumn.AutoFit;
        Application.Alert("四象限镜像生成完成（基准：" + 基准名 + "）：" + 总行数 + " 组 × 4 象限。", "四象限镜像");
    } finally {
        Application.ScreenUpdating = 原刷新;
        Application.Calculation = 原计算;
    }
}

// 四象限竖向输出：左上Q1 | 右上Q2，左下Q3 | 右下Q4
function 四象限_竖向输出(新表, Q1, Q2, Q3, Q4, 总列数, 总行数, 连接符, 是否合并) {
    if (是否合并) {
        // 合并模式：每象限1列
        var 左列 = [];
        var 右列 = [];
        for (var r = 0; r < 总行数; r++) {
            var 左片 = [], 右片 = [];
            for (var c = 0; c < 总列数; c++) {
                左片.push(Q1[c][r]);
                右片.push(Q2[c][r]);
            }
            左列.push([左片.join(连接符)]);
            右列.push([右片.join(连接符)]);
        }
        // 标签
        新表.Cells.Item(1, 1).Value2 = "原始";
        新表.Cells.Item(1, 2).Value2 = "左右镜像";
        // 上半部分
        新表.Range("A2").Resize(总行数, 1).Value2 = 左列;
        新表.Range("B2").Resize(总行数, 1).Value2 = 右列;
        // 下半部分
        var 下起始 = 总行数 + 3;
        新表.Cells.Item(下起始, 1).Value2 = "上下镜像";
        新表.Cells.Item(下起始, 2).Value2 = "中心镜像";
        var 下左 = [], 下右 = [];
        for (var r = 0; r < 总行数; r++) {
            var 左片2 = [], 右片2 = [];
            for (var c = 0; c < 总列数; c++) {
                左片2.push(Q3[c][r]);
                右片2.push(Q4[c][r]);
            }
            下左.push([左片2.join(连接符)]);
            下右.push([右片2.join(连接符)]);
        }
        新表.Range("A" + (下起始 + 1)).Resize(总行数, 1).Value2 = 下左;
        新表.Range("B" + (下起始 + 1)).Resize(总行数, 1).Value2 = 下右;
    } else {
        // 分开模式：每象限多列
        // 上半：Q1 + Q2
        var 上半左 = [];
        for (var r = 0; r < 总行数; r++) {
            上半左[r] = [];
            for (var c = 0; c < 总列数; c++) {
                上半左[r][c] = Q1[c][r];
            }
        }
        var 上半右 = [];
        for (var r = 0; r < 总行数; r++) {
            上半右[r] = [];
            for (var c = 0; c < 总列数; c++) {
                上半右[r][c] = Q2[c][r];
            }
        }
        // 标签
        新表.Cells.Item(1, 1).Value2 = "原始";
        新表.Cells.Item(1, 总列数 + 2).Value2 = "左右镜像";
        新表.Range("A2").Resize(总行数, 总列数).Value2 = 上半左;
        新表.Range(新表.Cells.Item(2, 总列数 + 2), 新表.Cells.Item(总行数 + 1, 总列数 * 2 + 1)).Value2 = 上半右;

        // 下半：Q3 + Q4
        var 下起始 = 总行数 + 3;
        var 下半左 = [];
        for (var r = 0; r < 总行数; r++) {
            下半左[r] = [];
            for (var c = 0; c < 总列数; c++) {
                下半左[r][c] = Q3[c][r];
            }
        }
        var 下半右 = [];
        for (var r = 0; r < 总行数; r++) {
            下半右[r] = [];
            for (var c = 0; c < 总列数; c++) {
                下半右[r][c] = Q4[c][r];
            }
        }
        新表.Cells.Item(下起始, 1).Value2 = "上下镜像";
        新表.Cells.Item(下起始, 总列数 + 2).Value2 = "中心镜像";
        新表.Range("A" + (下起始 + 1)).Resize(总行数, 总列数).Value2 = 下半左;
        新表.Range(新表.Cells.Item(下起始 + 1, 总列数 + 2), 新表.Cells.Item(下起始 + 总行数, 总列数 * 2 + 1)).Value2 = 下半右;
    }
}

// 四象限横向输出：Q1在上左，Q2在上右，Q3在下左，Q4在下右
function 四象限_横向输出(新表, Q1, Q2, Q3, Q4, 总列数, 总行数, 连接符, 是否合并) {
    if (是否合并) {
        // 合并模式：每象限1行
        var 上左 = [], 上右 = [];
        for (var r = 0; r < 总行数; r++) {
            var 左片 = [], 右片 = [];
            for (var c = 0; c < 总列数; c++) {
                左片.push(Q1[c][r]);
                右片.push(Q2[c][r]);
            }
            上左.push(左片.join(连接符));
            上右.push(右片.join(连接符));
        }
        var 下左 = [], 下右 = [];
        for (var r = 0; r < 总行数; r++) {
            var 左片 = [], 右片 = [];
            for (var c = 0; c < 总列数; c++) {
                左片.push(Q3[c][r]);
                右片.push(Q4[c][r]);
            }
            下左.push(左片.join(连接符));
            下右.push(右片.join(连接符));
        }
        // 标签
        新表.Cells.Item(1, 1).Value2 = "原始";
        新表.Cells.Item(1, 总行数 + 2).Value2 = "左右镜像";
        新表.Range("A2").Resize(1, 总行数).Value2 = [上左];
        新表.Range(新表.Cells.Item(2, 总行数 + 2), 新表.Cells.Item(2, 总行数 * 2 + 1)).Value2 = [上右];
        // 下半
        var 下起始 = 4;
        新表.Cells.Item(下起始, 1).Value2 = "上下镜像";
        新表.Cells.Item(下起始, 总行数 + 2).Value2 = "中心镜像";
        新表.Range("A" + (下起始 + 1)).Resize(1, 总行数).Value2 = [下左];
        新表.Range(新表.Cells.Item(下起始 + 1, 总行数 + 2), 新表.Cells.Item(下起始 + 1, 总行数 * 2 + 1)).Value2 = [下右];
    } else {
        // 分开模式：每象限多列（横向 = 每列一个组合，组合内部纵向排列）
        // 上半：Q1 + Q2
        var 上左 = Q1; // 按列存
        var 上右 = Q2;
        新表.Cells.Item(1, 1).Value2 = "原始";
        新表.Range("A2").Resize(总列数, 总行数).Value2 = 上左;
        新表.Cells.Item(1, 总行数 + 2).Value2 = "左右镜像";
        新表.Range(新表.Cells.Item(2, 总行数 + 2), 新表.Cells.Item(总列数 + 1, 总行数 * 2 + 1)).Value2 = 上右;

        // 下半：Q3 + Q4
        var 下起始行 = 总列数 + 3;
        var 下左 = Q3;
        var 下右 = Q4;
        新表.Cells.Item(下起始行, 1).Value2 = "上下镜像";
        新表.Range("A" + (下起始行 + 1)).Resize(总列数, 总行数).Value2 = 下左;
        新表.Cells.Item(下起始行, 总行数 + 2).Value2 = "中心镜像";
        新表.Range(新表.Cells.Item(下起始行 + 1, 总行数 + 2), 新表.Cells.Item(下起始行 + 总列数, 总行数 * 2 + 1)).Value2 = 下右;
    }
}

// ============================================================
//  核心算法四：备选算法验证（7种）
// ============================================================

function 备选算法_执行(连接符, 是否合并, 数据是否反转) {
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
        if (总行数 > 10000) { Application.Alert("数据量过大，备选算法验证暂不支持（10000以内）", "提示"); return; }

        var 源数据 = 读取源数据(ws, 总行数, 总列数, 每列行数, 数据是否反转);

        var 算法列表 = [
            { 名: "A_进位计数法", fn: 算法A_进位计数法 },
            { 名: "B_回溯法(DFS)", fn: 算法B_回溯法 },
            { 名: "C_随机抽样", fn: 算法C_随机抽样 },
            { 名: "D_LCM双边循环", fn: 算法D_LCM双边循环 },
            { 名: "E_逐列扩展法", fn: 算法E_逐列扩展法 },
            { 名: "F_格雷码遍历", fn: 算法F_格雷码遍历 },
            { 名: "G_混合进制随机访问", fn: 算法G_混合进制随机访问 }
        ];

        var 合并名 = 是否合并 ? "合并" : "分开";
        var 反转后缀 = 数据是否反转 ? "_反序" : "";
        var 新表 = 新建结果表("备选算法_对比_" + 合并名 + 反转后缀);

        var 当前行 = 1;
        for (var a = 0; a < 算法列表.length; a++) {
            var 算法 = 算法列表[a];
            var 结果;
            try {
                结果 = 算法.fn(源数据, 每列行数, 总列数, 总行数);
            } catch (e) {
                结果 = null;
            }

            // 写标签
            新表.Cells.Item(当前行, 1).Value2 = "【" + 算法.名 + "】";
            新表.Cells.Item(当前行, 1).Font.Bold = true;
            当前行++;

            if (结果 && 结果.length > 0) {
                var 行数 = 结果[0].length;
                if (是否合并) {
                    var 合并 = [];
                    for (var r = 0; r < 行数; r++) {
                        var 片段 = [];
                        for (var c = 0; c < 结果.length; c++) {
                            片段.push(结果[c][r]);
                        }
                        合并.push([片段.join(连接符)]);
                    }
                    新表.Range("A" + 当前行).Resize(行数, 1).Value2 = 合并;
                } else {
                    var 转置 = [];
                    for (var r = 0; r < 行数; r++) {
                        转置[r] = [];
                        for (var c = 0; c < 结果.length; c++) {
                            转置[r][c] = 结果[c][r];
                        }
                    }
                    新表.Range("A" + 当前行).Resize(行数, 总列数).Value2 = 转置;
                }
                当前行 += 行数 + 1;
            } else {
                新表.Cells.Item(当前行, 1).Value2 = "(未实现或出错)";
                当前行 += 2;
            }
        }

        新表.Cells.EntireColumn.AutoFit;
        Application.Alert("备选算法验证完成：共 " + 算法列表.length + " 种算法。", "备选算法");
    } finally {
        Application.ScreenUpdating = 原刷新;
        Application.Calculation = 原计算;
    }
}

// 算法A：进位计数法（mixed-radix odometer）
function 算法A_进位计数法(源数据, 每列行数, 总列数, 总行数) {
    var 结果 = [];
    for (var c = 0; c < 总列数; c++) 结果[c] = [];
    var 计数 = [];
    for (var c = 0; c < 总列数; c++) 计数[c] = 0;

    for (var r = 0; r < 总行数; r++) {
        for (var c = 0; c < 总列数; c++) {
            结果[c][r] = 源数据[计数[c]][c];
        }
        // 进位
        for (var c = 总列数 - 1; c >= 0; c--) {
            计数[c]++;
            if (计数[c] < 每列行数[c]) break;
            计数[c] = 0;
        }
    }
    return 结果;
}

// 算法B：回溯法（DFS）
function 算法B_回溯法(源数据, 每列行数, 总列数, 总行数) {
    var 结果 = [];
    for (var c = 0; c < 总列数; c++) 结果[c] = [];
    var 当前路径 = [];
    var 行号 = 0;

    function dfs(列) {
        if (列 === 总列数) {
            for (var c = 0; c < 总列数; c++) {
                结果[c][行号] = 当前路径[c];
            }
            行号++;
            return;
        }
        for (var i = 0; i < 每列行数[列]; i++) {
            当前路径.push(源数据[i][列]);
            dfs(列 + 1);
            当前路径.pop();
        }
    }
    dfs(0);
    return 结果;
}

// 算法C：随机抽样（Fisher-Yates 洗牌，不放回）
function 算法C_随机抽样(源数据, 每列行数, 总列数, 总行数) {
    // 生成所有组合索引后洗牌
    var 索引 = [];
    for (var i = 0; i < 总行数; i++) 索引.push(i);
    // Fisher-Yates
    for (var i = 索引.length - 1; i > 0; i--) {
        var j = Math.floor(Math.random() * (i + 1));
        var t = 索引[i]; 索引[i] = 索引[j]; 索引[j] = t;
    }
    // 取全部（随机顺序的完整排列）
    var 样本数 = Math.min(总行数, 20); // 取20行演示
    var 结果 = [];
    for (var c = 0; c < 总列数; c++) 结果[c] = [];

    // 用正向算法生成所有组合，再按洗牌索引取
    var 全部 = [];
    for (var c = 0; c < 总列数; c++) 全部[c] = [];
    var 步长 = [1];
    for (var c = 1; c < 总列数; c++) {
        步长[c] = 步长[c - 1] * 每列行数[c - 1];
    }
    for (var r = 0; r < 总行数; r++) {
        for (var c = 0; c < 总列数; c++) {
            var 源行 = Math.floor(r / 步长[c]) % 每列行数[c];
            全部[c][r] = 源数据[源行][c];
        }
    }
    for (var i = 0; i < 样本数; i++) {
        var idx = 索引[i];
        for (var c = 0; c < 总列数; c++) {
            结果[c][i] = 全部[c][idx];
        }
    }
    return 结果;
}

// 算法D：LCM双边循环
function 算法D_LCM双边循环(源数据, 每列行数, 总列数, 总行数) {
    var lcm = 最小公倍数(每列行数);
    var 结果 = [];
    for (var c = 0; c < 总列数; c++) {
        结果[c] = [];
        for (var r = 0; r < lcm; r++) {
            结果[c][r] = 源数据[r % 每列行数[c]][c];
        }
    }
    return 结果;
}

// 算法E：逐列扩展法
function 算法E_逐列扩展法(源数据, 每列行数, 总列数, 总行数) {
    // 从第1列开始，每加入一列就把已有结果复制 该列行数 份
    var 当前行数 = 每列行数[0];
    var 结果 = [[]];
    for (var r = 0; r < 每列行数[0]; r++) {
        结果[0][r] = 源数据[r][0];
    }
    for (var c = 1; c < 总列数; c++) {
        var 新行数 = 当前行数 * 每列行数[c];
        var 新结果 = [];
        for (var nc = 0; nc <= c; nc++) 新结果[nc] = [];
        for (var i = 0; i < 每列行数[c]; i++) {
            for (var r = 0; r < 当前行数; r++) {
                var 目标行 = i * 当前行数 + r;
                for (var pc = 0; pc < c; pc++) {
                    新结果[pc][目标行] = 结果[pc][r];
                }
                新结果[c][目标行] = 源数据[i][c];
            }
        }
        结果 = 新结果;
        当前行数 = 新行数;
    }
    return 结果;
}

// 算法F：格雷码遍历（相邻组合仅一列变化）
function 算法F_格雷码遍历(源数据, 每列行数, 总列数, 总行数) {
    var 结果 = [];
    for (var c = 0; c < 总列数; c++) 结果[c] = [];
    var 计数 = [];
    for (var c = 0; c < 总列数; c++) 计数[c] = 0;
    var 方向 = [];
    for (var c = 0; c < 总列数; c++) 方向[c] = 1; // 1=增，-1=减

    for (var r = 0; r < 总行数; r++) {
        for (var c = 0; c < 总列数; c++) {
            结果[c][r] = 源数据[计数[c]][c];
        }
        // 找最低位可变化的列
        for (var c = 总列数 - 1; c >= 0; c--) {
            var 下一个 = 计数[c] + 方向[c];
            if (下一个 >= 0 && 下一个 < 每列行数[c]) {
                计数[c] = 下一个;
                break;
            } else {
                方向[c] = -方向[c]; // 反向
            }
        }
    }
    return 结果;
}

// 算法G：混合进制随机访问（直接算第k个组合）
function 算法G_混合进制随机访问(源数据, 每列行数, 总列数, 总行数) {
    // 随机取20个位置
    var 样本数 = Math.min(总行数, 20);
    var 位置 = [];
    for (var i = 0; i < 样本数; i++) {
        位置.push(Math.floor(Math.random() * 总行数));
    }
    位置.sort(function(a, b){return a-b;});

    var 结果 = [];
    for (var c = 0; c < 总列数; c++) 结果[c] = [];

    // 算步长（左快右慢）
    var 步长 = [1];
    for (var c = 1; c < 总列数; c++) {
        步长[c] = 步长[c - 1] * 每列行数[c - 1];
    }

    for (var i = 0; i < 样本数; i++) {
        var k = 位置[i];
        for (var c = 总列数 - 1; c >= 0; c--) {
            var idx = Math.floor(k / 步长[c]) % 每列行数[c];
            结果[c][i] = 源数据[idx][c];
        }
    }
    return 结果;
}
