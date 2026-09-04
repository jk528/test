// =============================================================
//  四方镜子 - JS宏单模块版
//  特点：一个JS文件搞定全部，HTML窗体内嵌，无需额外文件
//  使用：运行 四方镜子_主入口() 即可
// =============================================================

// -------------------------------------------------------------
//  第一部分：内嵌HTML窗体
// -------------------------------------------------------------

function 获取窗体HTML() {
    return `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:"Microsoft YaHei","微软雅黑",sans-serif;background:#f5f7fa;padding:18px;color:#333;user-select:none}
.title{font-size:17px;font-weight:bold;color:#2c3e50;margin-bottom:14px;text-align:center;border-bottom:2px solid #3498db;padding-bottom:8px}
.section{background:#fff;border-radius:8px;padding:12px;margin-bottom:12px;box-shadow:0 2px 6px rgba(0,0,0,.08)}
.section-title{font-size:13px;font-weight:bold;color:#3498db;margin-bottom:8px;padding-left:6px;border-left:3px solid #3498db}
.row{display:flex;align-items:center;gap:8px;margin-bottom:6px}
label{font-size:12px;color:#555;min-width:60px}
input[type=text]{flex:1;padding:5px 8px;border:1px solid #ddd;border-radius:4px;font-size:12px;outline:none}
input[type=text]:focus{border-color:#3498db}
input[type=checkbox]{cursor:pointer}
.grid-2x2{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.grid-2x1{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.btn{padding:10px 6px;border:1px solid #ddd;border-radius:5px;background:#fff;cursor:pointer;font-size:11px;line-height:1.6;text-align:center;transition:all .2s;color:#444;white-space:pre-line;font-family:Consolas,monospace}
.btn:hover{background:#ecf5ff;border-color:#3498db;color:#3498db;transform:translateY(-1px);box-shadow:0 3px 8px rgba(52,152,219,.2)}
.btn-wide{font-family:"Microsoft YaHei",sans-serif;font-size:12px;padding:10px;font-weight:500}
.hint{font-size:10px;color:#999;margin-top:4px;line-height:1.5}
</style>
</head>
<body>
<div class="title">🔷 四方镜</div>

<div class="section">
  <div class="section-title">连接符号</div>
  <div class="row">
    <label>连接符：</label>
    <input type="text" id="connector" value="-" maxlength="10">
  </div>
  <div class="row">
    <label></label>
    <input type="checkbox" id="mergeMode" checked>
    <label for="mergeMode" style="min-width:auto;cursor:pointer;font-size:12px">合并模式</label>
  </div>
</div>

<div class="section">
  <div class="section-title">四方循环（笛卡尔积）</div>
  <div class="grid-2x2">
    <button class="btn" onclick="runFourWay(false,false)" id="btn1">A1B1
A1B2
A2B1
A2B2</button>
    <button class="btn" onclick="runFourWay(true,false)" id="btn3">A1B1
A2B1
A1B2
A2B2</button>
    <button class="btn" onclick="runFourWay(true,true)" id="btn2">A1B1 A2B1 A1B2 A2B2</button>
    <button class="btn" onclick="runFourWay(false,true)" id="btn4">A1B1 A1B2 A2B1 A2B2</button>
  </div>
  <div class="hint">左上=反向竖 &nbsp; 右上=正向竖 &nbsp; 左下=正向横 &nbsp; 右下=反向横</div>
</div>

<div class="section">
  <div class="section-title">双边循环（LCM独立循环）</div>
  <div class="grid-2x1">
    <button class="btn btn-wide" onclick="runLcm(true)" id="btn5">双边循环_合并_竖</button>
    <button class="btn btn-wide" onclick="runLcm(false)" id="btn6">双边循环_合并_横</button>
  </div>
</div>

<script>
// 合并模式切换
document.getElementById('mergeMode').addEventListener('change', function(e){
  var m=e.target.checked;
  var b1=document.getElementById('btn1'),b2=document.getElementById('btn2'),
      b3=document.getElementById('btn3'),b4=document.getElementById('btn4'),
      b5=document.getElementById('btn5'),b6=document.getElementById('btn6');
  if(m){
    b1.textContent="A1B1\\nA1B2\\nA2B1\\nA2B2";
    b3.textContent="A1B1\\nA2B1\\nA1B2\\nA2B2";
    b2.textContent="A1B1 A2B1 A1B2 A2B2";
    b4.textContent="A1B1 A1B2 A2B1 A2B2";
    b5.textContent="双边循环_合并_竖";b6.textContent="双边循环_合并_横";
  }else{
    b1.textContent="A1  B1\\nA1  B2\\nA2  B1\\nA2  B2";
    b3.textContent="A1  B1\\nA2  B1\\nA1  B2\\nA2  B2";
    b2.textContent="A1  B1  A2  B1  A1  B2  A2  B2";
    b4.textContent="A1  B1  A1  B2  A2  B1  A2  B2";
    b5.textContent="双边循环_分_竖";b6.textContent="双边循环_分_横";
  }
});
function runFourWay(f,h){
  var c=document.getElementById('connector').value;
  var m=document.getElementById('mergeMode').checked;
  window.external.Notify(JSON.stringify({action:'fourWay',forward:f,horizontal:h,connector:m?c:''}));
  window.close();
}
function runLcm(v){
  var c=document.getElementById('connector').value;
  var m=document.getElementById('mergeMode').checked;
  window.external.Notify(JSON.stringify({action:'lcm',vertical:v,connector:m?c:''}));
  window.close();
}
<\/script>
</body>
</html>`;
}

// -------------------------------------------------------------
//  第二部分：窗体通信 + 主入口
// -------------------------------------------------------------

var g_当前连接符号 = "";
var g_是否合并模式 = true;

/**
 * 主入口：打开HTML窗体
 * HTML内容直接内嵌，无需外部文件
 */
function 四方镜子_主入口() {
    try {
        // 1. 将内嵌HTML写入临时文件
        var fso = new ActiveXObject("Scripting.FileSystemObject");
        var tempPath = Application.ThisWorkbook.Path + "\\_四方镜子_temp.html";
        var ts = fso.CreateTextFile(tempPath, true);
        ts.Write(获取窗体HTML());
        ts.Close();

        // 2. 注册消息接收回调
        window.DialogResult = null;
        function OnDialogNotify(msg) {
            try {
                var params = JSON.parse(msg);
                g_当前连接符号 = params.connector || "";
                g_是否合并模式 = (g_当前连接符号 !== "");

                switch (params.action) {
                    case "fourWay":
                        执行四方循环(params.forward, params.horizontal);
                        break;
                    case "lcm":
                        执行双边循环(params.vertical);
                        break;
                }
            } catch (e) {
                弹窗提示("解析参数失败: " + (e.message || String(e)), 48);
            }
        }

        // 3. 弹出对话框
        Application.ShowDialog(tempPath, 340, 520, "四方镜");

        // 4. 清理临时文件
        try { fso.DeleteFile(tempPath); } catch (e) {}

    } catch (e) {
        // HTML方式失败则回退到InputBox方式
        try {
            四方镜子_输入框模式();
        } catch (e2) {
            弹窗提示("启动失败: " + (e.message || String(e)), 48);
        }
    }
}

/**
 * 备用入口：纯InputBox模式（HTML不可用时）
 */
function 四方镜子_输入框模式() {
    var 选择 = Application.InputBox(
        "请选择操作：\n1: 四方循环_合并_竖\n2: 四方循环_合并_横\n3: 四方循环_分_竖\n4: 四方循环_分_横\n5: 双边循环_合并_竖\n6: 双边循环_合并_横\n7: 双边循环_分_竖\n8: 双边循环_分_横",
        "四方镜子", "1", 100, 100, "", 0, 1
    );
    if (选择 === false || 选择 === null) return;
    选择 = parseInt(选择);

    var 连接符 = "";
    if (选择 === 1 || 选择 === 2 || 选择 === 5 || 选择 === 6) {
        连接符 = Application.InputBox("请输入连接符号:", "连接符号", "-", 100, 100, "", 0, 2);
        if (连接符 === false || 连接符 === null) return;
        g_当前连接符号 = 连接符 || "-";
    } else {
        g_当前连接符号 = "";
    }

    switch (选择) {
        case 1: 执行四方循环(false, false); break;
        case 2: 执行四方循环(true, true); break;
        case 3: 执行四方循环(false, false); break;
        case 4: 执行四方循环(true, true); break;
        case 5: 执行双边循环(true); break;
        case 6: 执行双边循环(false); break;
        case 7: 执行双边循环(true); break;
        case 8: 执行双边循环(false); break;
        default: 弹窗提示("无效选择", 48);
    }
}

// -------------------------------------------------------------
//  第三部分：工具函数
// -------------------------------------------------------------

function 弹窗提示(消息内容, 图标类型) {
    try { Application.MsgBox(消息内容, 图标类型 || 64, "四方镜子"); }
    catch (e) { try { Application.Alert(消息内容); } catch (e2) { console.log("【四方镜子】" + 消息内容); } }
}

function 循环索引(序号, 周期长度) {
    return ((序号 + 周期长度 - 1) % 周期长度) + 1;
}

function 向上取整除法(被除数, 除数) {
    return Math.ceil(被除数 / 除数);
}

function 获取最后一列(工作表) {
    try { return 工作表.Cells(1, 工作表.Columns.Count).End(-4159).Column; }
    catch (e) { return 工作表.UsedRange.Columns.Count; }
}

function 获取最后一行(工作表, 列号) {
    try { return 工作表.Cells(工作表.Rows.Count, 列号).End(-4162).Row; }
    catch (e) { return 工作表.UsedRange.Rows.Count; }
}

function 批量读取区域(工作表, 起始行, 起始列, 结束行, 结束列) {
    return 工作表.Range(工作表.Cells(起始行, 起始列), 工作表.Cells(结束行, 结束列)).Value2;
}

function 计算数组乘积(数组) {
    var 乘积 = 1;
    for (var i = 0; i < 数组.length; i++) 乘积 *= 数组[i];
    return 乘积;
}

// -------------------------------------------------------------
//  第四部分：核心算法 - 四方循环
// -------------------------------------------------------------

function 计算循环步长数组(每列元素个数, 是否正向) {
    var 列数 = 每列元素个数.length;
    var 步长数组 = [];
    if (是否正向) {
        步长数组[0] = 1;
        for (var i = 1; i < 列数; i++) {
            步长数组[i] = 步长数组[i - 1] * 每列元素个数[i - 1];
        }
    } else {
        var 总行数 = 1;
        for (var i = 0; i < 列数; i++) 总行数 *= 每列元素个数[i];
        var 累计乘积 = 1;
        for (var i = 0; i < 列数; i++) {
            累计乘积 *= 每列元素个数[i];
            步长数组[i] = 总行数 / 累计乘积;
        }
    }
    return 步长数组;
}

function 构建笛卡尔积矩阵(源数据, 每列元素个数, 步长数组, 结果行数) {
    var 列数 = 每列元素个数.length;
    var 结果 = [];
    for (var 列 = 0; 列 < 列数; 列++) {
        结果[列] = [];
        var 该列元素数 = 每列元素个数[列];
        var 该列步长 = 步长数组[列];
        for (var 行 = 0; 行 < 结果行数; 行++) {
            var 源行号 = 循环索引(向上取整除法(行 + 1, 该列步长), 该列元素数);
            结果[列][行] = 源数据[源行号 - 1][列];
        }
    }
    return 结果;
}

function 矩阵转置(矩阵, 列数, 行数) {
    var 结果 = [];
    for (var 行 = 0; 行 < 行数; 行++) {
        结果[行] = [];
        for (var 列 = 0; 列 < 列数; 列++) {
            结果[行][列] = 矩阵[列][行];
        }
    }
    return 结果;
}

function 按行合并字符串(矩阵, 列数, 行数, 是否列优先, 连接符) {
    var 结果 = [];
    for (var 行 = 0; 行 < 行数; 行++) {
        var 片段 = [];
        for (var 列 = 0; 列 < 列数; 列++) {
            片段.push(是否列优先 ? 矩阵[列][行] : 矩阵[行][列]);
        }
        结果[行] = 片段.join(连接符);
    }
    return 结果;
}

// -------------------------------------------------------------
//  第五部分：核心算法 - 双边循环
// -------------------------------------------------------------

function 构建LCM循环矩阵(源数据, 每列元素个数, 结果行数) {
    var 列数 = 每列元素个数.length;
    var 结果 = [];
    for (var 列 = 0; 列 < 列数; 列++) {
        结果[列] = [];
        var 周期长度 = 每列元素个数[列];
        for (var 行 = 0; 行 < 结果行数; 行++) {
            var 源行号 = 循环索引(行 + 1, 周期长度);
            结果[列][行] = 源数据[源行号 - 1][列];
        }
    }
    return 结果;
}

// -------------------------------------------------------------
//  第六部分：输出
// -------------------------------------------------------------

function 写入结果(目标工作表, 起始单元格, 数据数组, 输出行数, 输出列数, 是否合并模式) {
    if (是否合并模式) {
        if (输出列数 === 1) {
            var 列格式 = [];
            for (var i = 0; i < 数据数组.length; i++) 列格式[i] = [数据数组[i]];
            目标工作表.Range(起始单元格).Resize(输出行数, 1).Value2 = 列格式;
        } else {
            目标工作表.Range(起始单元格).Resize(1, 输出列数).Value2 = 数据数组;
        }
    } else {
        目标工作表.Range(起始单元格).Resize(输出行数, 输出列数).Value2 = 数据数组;
    }
}

// -------------------------------------------------------------
//  第七部分：业务主函数
// -------------------------------------------------------------

function 执行四方循环(是否正向, 是否横向输出) {
    var 原屏幕刷新 = true;
    var 原计算模式 = -4105;
    try { 原屏幕刷新 = Application.ScreenUpdating; Application.ScreenUpdating = false; } catch (e) {}
    try { 原计算模式 = Application.Calculation; Application.Calculation = -4135; } catch (e) {}

    try {
        var 工作表 = Application.ActiveSheet;
        var 总列数 = 获取最后一列(工作表);
        if (总列数 <= 0) { 弹窗提示("无有效数据列", 48); return false; }

        var 每列元素个数 = [];
        for (var 列 = 0; 列 < 总列数; 列++) {
            var 行数 = 获取最后一行(工作表, 列 + 1);
            每列元素个数[列] = 行数 < 1 ? 1 : 行数;
        }

        var 结果总行数 = 计算数组乘积(每列元素个数);
        if (结果总行数 > 1048576) { 弹窗提示("已超出表格限制", 48); return false; }

        var 原始数据 = 批量读取区域(工作表, 1, 1, 结果总行数, 总列数);
        var 步长数组 = 计算循环步长数组(每列元素个数, 是否正向);
        var 结果矩阵 = 构建笛卡尔积矩阵(原始数据, 每列元素个数, 步长数组, 结果总行数);

        var 输出数据, 输出行数, 输出列数;
        var 是否合并 = (g_当前连接符号 !== "");

        if (是否横向输出) {
            if (是否合并) {
                输出数据 = 按行合并字符串(结果矩阵, 总列数, 结果总行数, true, g_当前连接符号);
                输出行数 = 1; 输出列数 = 结果总行数;
            } else {
                输出数据 = 结果矩阵;
                输出行数 = 总列数; 输出列数 = 结果总行数;
            }
        } else {
            if (是否合并) {
                输出数据 = 按行合并字符串(结果矩阵, 总列数, 结果总行数, true, g_当前连接符号);
                输出行数 = 结果总行数; 输出列数 = 1;
            } else {
                输出数据 = 矩阵转置(结果矩阵, 总列数, 结果总行数);
                输出行数 = 结果总行数; 输出列数 = 总列数;
            }
        }

        写入结果(工作表, "F2", 输出数据, 输出行数, 输出列数, 是否合并);
        return true;
    } catch (e) {
        弹窗提示("执行错误: " + (e.message || String(e)), 48);
        return false;
    } finally {
        try { Application.Calculation = 原计算模式; } catch (e) {}
        try { Application.ScreenUpdating = 原屏幕刷新; } catch (e) {}
    }
}

function 执行双边循环(是否竖向输出) {
    var 原屏幕刷新 = true;
    var 原计算模式 = -4105;
    try { 原屏幕刷新 = Application.ScreenUpdating; Application.ScreenUpdating = false; } catch (e) {}
    try { 原计算模式 = Application.Calculation; Application.Calculation = -4135; } catch (e) {}

    try {
        var 工作表 = Application.ActiveSheet;
        var 总列数 = 获取最后一列(工作表);
        if (总列数 <= 0) { 弹窗提示("无有效数据列", 48); return false; }

        var 每列元素个数 = [];
        for (var 列 = 0; 列 < 总列数; 列++) {
            var 行数 = 获取最后一行(工作表, 列 + 1);
            每列元素个数[列] = 行数 < 1 ? 1 : 行数;
        }

        var 列数乘积 = 计算数组乘积(每列元素个数);
        var 最小公倍数 = Application.WorksheetFunction.Lcm(每列元素个数);
        if (最小公倍数 > 1048576) { 弹窗提示("已超出表格限制", 48); return false; }

        var 是否完整循环 = (列数乘积 === 最小公倍数);
        var 原始数据 = 批量读取区域(工作表, 1, 1, 最小公倍数, 总列数);
        var 结果矩阵 = 构建LCM循环矩阵(原始数据, 每列元素个数, 最小公倍数);

        var 新工作表 = Application.Worksheets.Add();
        新工作表.Name = 是否完整循环
            ? "完整_" + 最小公倍数 + "sheet" + Application.Sheets.Count
            : "残缺_" + 列数乘积 + "|" + 最小公倍数 + "sheet" + Application.Sheets.Count;

        var 输出数据, 输出行数, 输出列数;
        var 是否合并 = (g_当前连接符号 !== "");

        if (是否竖向输出) {
            if (是否合并) {
                输出数据 = 按行合并字符串(结果矩阵, 总列数, 最小公倍数, true, g_当前连接符号);
                输出行数 = 最小公倍数; 输出列数 = 1;
            } else {
                输出数据 = 矩阵转置(结果矩阵, 总列数, 最小公倍数);
                输出行数 = 最小公倍数; 输出列数 = 总列数;
            }
        } else {
            if (是否合并) {
                输出数据 = 按行合并字符串(结果矩阵, 总列数, 最小公倍数, true, g_当前连接符号);
                输出行数 = 1; 输出列数 = 最小公倍数;
            } else {
                输出数据 = 结果矩阵;
                输出行数 = 总列数; 输出列数 = 最小公倍数;
            }
        }

        写入结果(新工作表, "A1", 输出数据, 输出行数, 输出列数, 是否合并);
        return true;
    } catch (e) {
        弹窗提示("执行错误: " + (e.message || String(e)), 48);
        return false;
    } finally {
        try { Application.Calculation = 原计算模式; } catch (e) {}
        try { Application.ScreenUpdating = 原屏幕刷新; } catch (e) {}
    }
}
