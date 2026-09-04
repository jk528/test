// =============================================================
//  四方镜子 - JS版窗体代码（PC_003_组合.UserForm）
//  对应 VBA 的 PC_003_组合.frm
//  窗体控件（在WPS窗体设计器中添加）：
//    Label1        - "连接符号:"
//    TextBox1      - 输入连接符号
//    CheckBox1     - "合并" 复选框
//    CommandButton1 - 反向竖向
//    CommandButton2 - 正向横向
//    CommandButton3 - 正向竖向
//    CommandButton4 - 反向横向
//    CommandButton5 - 双边循环_竖
//    CommandButton6 - 双边循环_横
// =============================================================

// -------------------------------------------------------------
//  全局状态（与模块共享）
// -------------------------------------------------------------

var 当前连接符号 = "";
var 是否合并模式 = true;

// -------------------------------------------------------------
//  窗体初始化事件
// -------------------------------------------------------------

function UserForm_Initialize() {
    this.Caption = "四方镜";
    Label1.Caption = "连接符号:";
    CheckBox1.Caption = "合并";
    CheckBox1.Value = true;
    TextBox1.Text = "-";
    当前连接符号 = "-";
    是否合并模式 = true;

    // 初始化按钮标题
    更新按钮标题();
}

// -------------------------------------------------------------
//  连接符号文本框变化事件
// -------------------------------------------------------------

function TextBox1_Change() {
    当前连接符号 = TextBox1.Text;
}

// -------------------------------------------------------------
//  合并复选框点击事件
// -------------------------------------------------------------

function CheckBox1_Click() {
    是否合并模式 = CheckBox1.Value;
    更新按钮标题();
    CommandButton1.SetFocus();
}

// -------------------------------------------------------------
//  更新所有按钮的显示文字
//  合并模式和分开模式下按钮的图示不同
// -------------------------------------------------------------

function 更新按钮标题() {
    if (是否合并模式) {
        // ===== 合并模式按钮图示（A列+B列紧凑拼接） =====
        // 按钮1：反向竖向（A列慢，B列快）
        // A1B1 → 第1行：A列第1个 + B列第1个
        // A1B2 → 第2行：A列第1个 + B列第2个
        // A2B1 → 第3行：A列第2个 + B列第1个
        // A2B2 → 第4行：A列第2个 + B列第2个
        CommandButton1.Caption = "A1B1\nA1B2\nA2B1\nA2B2";

        // 按钮3：正向竖向（A列快，B列慢）
        CommandButton3.Caption = "A1B1\nA2B1\nA1B2\nA2B2";

        // 按钮2：正向横向
        CommandButton2.Caption = "A1B1 A2B1 A1B2 A2B2";

        // 按钮4：反向横向
        CommandButton4.Caption = "A1B1 A1B2 A2B1 A2B2";

        // 双边循环按钮
        CommandButton5.Caption = "双边循环_合并_竖";
        CommandButton6.Caption = "双边循环_合并_横";
    } else {
        // ===== 分开模式按钮图示（A列  B列 分明） =====
        CommandButton1.Caption = "A1  B1\nA1  B2\nA2  B1\nA2  B2";
        CommandButton3.Caption = "A1  B1\nA2  B1\nA1  B2\nA2  B2";
        CommandButton2.Caption = "A1  B1  A2  B1  A1  B2  A2  B2";
        CommandButton4.Caption = "A1  B1  A1  B2  A2  B1  A2  B2";

        // 双边循环按钮
        CommandButton5.Caption = "双边循环_分_竖";
        CommandButton6.Caption = "双边循环_分_横";
    }
}

// -------------------------------------------------------------
//  四方循环 - 四个按钮
//  参数说明：
//    执行四方循环(是否正向, 是否横向输出)
//      是否正向 = true  → 左慢右快（正向循环）
//      是否正向 = false → 左快右慢（反向循环）
//      是否横向输出 = true  → 列×行 横向排列
//      是否横向输出 = false → 行×列 竖向排列
// -------------------------------------------------------------

// 按钮1：反向 + 竖向
// （最常用：左列变化最快，结果竖向排列，符合阅读习惯）
function CommandButton1_Click() {
    执行四方循环(false, false);
    this.Close();
}

// 按钮2：正向 + 横向
function CommandButton2_Click() {
    执行四方循环(true, true);
    this.Close();
}

// 按钮3：正向 + 竖向
function CommandButton3_Click() {
    执行四方循环(true, false);
    this.Close();
}

// 按钮4：反向 + 横向
function CommandButton4_Click() {
    执行四方循环(false, true);
    this.Close();
}

// -------------------------------------------------------------
//  双边循环 - 两个按钮
// -------------------------------------------------------------

// 按钮5：双边循环 - 竖向输出
function CommandButton5_Click() {
    执行双边循环(true);
    this.Close();
}

// 按钮6：双边循环 - 横向输出
function CommandButton6_Click() {
    执行双边循环(false);
    this.Close();
}
