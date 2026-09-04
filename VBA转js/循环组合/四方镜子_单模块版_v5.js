/*============================================================
 * 四方镜子 - JS宏 v5（modeless 循环模式）
 * 对应 VBA v5：窗体保持打开，可反复操作，操作间可编辑Excel
 * 使用方法：运行 四方镜子_主入口()
 *============================================================*/

// 常量
var xlToLeft = -4159;
var xlUp = -4162;
var xlCalculationManual = -4135;
var xlCalculationAutomatic = -4105;

// ============================================================
//  主入口（循环模式：每次操作后询问是否继续）
// ============================================================

function 四方镜子_主入口() {
    var 菜单 = "===== 四方镜子 =====\n\n"
        + "【四方循环（笛卡尔积）】\n"
        + "  1 = 正向竖向（左慢右快）\n"
        + "  2 = 正向横向\n"
        + "  3 = 反向竖向（左快右慢）\n"
        + "  4 = 反向横向\n\n"
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
        var 是否合并 = (合并输入 === "1");

        try {
            switch (操作号) {
                case 1: 四方循环_执行(true, false, 连接符, 是否合并); break;
                case 2: 四方循环_执行(true, true, 连接符, 是否合并); break;
                case 3: 四方循环_执行(false, false, 连接符, 是否合并); break;
                case 4: 四方循环_执行(false, true, 连接符, 是否合并); break;
                case 5: 双边循环_执行(true, 连接符, 是否合并); break;
                case 6: 双边循环_执行(false, 连接符, 是否合并); break;
            }
        } catch (e) {
            Application.Alert("执行错误: " + e.message, "错误");
        }

        var 继续 = Application.InputBox("操作完成！\n\n  1 = 继续（可选择另一个操作）\n  0 = 退出", "四方镜子", "0");
        if (继续 !== "1") break;
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
