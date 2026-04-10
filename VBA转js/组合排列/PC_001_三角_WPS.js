// PC_001_三角_WPS.js - 适配 WPS 环境的 JavaScript 代码

// 组合数计算函数
function combNum(n, k) {
    if (k < 0 || k > n) {
        return 0;
    }
    // 计算组合数 C(n,k) = n!/(k!*(n-k)!)
    let result = 1;
    for (let i = 1; i <= k; i++) {
        result = result * (n - k + i) / i;
    }
    return result;
}

// 构建组合不放回三角二维数组 (C(m,k))
function 构建_组合不放回_C三角二维数组(n) {
    const rowsTotal = n + 2;
    const colsTotal = n + 3;
    const colStart = 3;
    const outArr = Array(rowsTotal).fill().map(() => Array(colsTotal).fill(''));

    outArr[0][0] = "总和";
    outArr[0][1] = "总数";
    for (let k = 0; k <= n; k++) {
        outArr[0][colStart + k] = "拿" + k + "个";
    }

    let row = 1;
    for (let m = 0; m <= n; m++) {
        outArr[row][1] = m;
        let sumRow = 0;
        for (let k = 0; k <= m; k++) {
            const val = combNum(m, k);
            outArr[row][colStart + k] = val;
            sumRow += val;
        }
        for (let k = m + 1; k <= n; k++) {
            outArr[row][colStart + k] = "";
        }
        outArr[row][0] = sumRow;
        row++;
    }

    return outArr;
}

// 构建组合放回三角二维数组 (C(m+k-1,k))
function 构建_组合放回_C三角_XX二维数组(n) {
    const rowsTotal = n + 2;
    const colsTotal = n + 3;
    const colStart = 3;
    const outArr = Array(rowsTotal).fill().map(() => Array(colsTotal).fill(''));

    outArr[0][0] = "总和";
    outArr[0][1] = "总数";
    for (let k = 0; k <= n; k++) {
        outArr[0][colStart + k] = "拿" + k + "个";
    }

    let row = 1;
    for (let m = 0; m <= n; m++) {
        outArr[row][1] = m;
        if (m === 0) {
            outArr[row][colStart + 0] = 1;
            outArr[row][0] = 1;
            for (let k = 1; k <= n; k++) {
                outArr[row][colStart + k] = "";
            }
        } else {
            let prefix = 0;
            for (let k = 0; k <= m - 1; k++) {
                const val = combNum(m + k - 1, k);
                outArr[row][colStart + k] = val;
                prefix += val;
            }
            outArr[row][colStart + m] = prefix;
            outArr[row][0] = prefix + prefix;
            for (let k = m + 1; k <= n; k++) {
                outArr[row][colStart + k] = "";
            }
        }
        row++;
    }

    return outArr;
}

// 构建排列不放回三角二维数组 (P(m,k))
function 构建_排列不放回_P三角二维数组(n) {
    const rowsTotal = n + 2;
    const colsTotal = n + 3;
    const colStart = 3;
    const outArr = Array(rowsTotal).fill().map(() => Array(colsTotal).fill(''));

    outArr[0][0] = "总和";
    outArr[0][1] = "总数";
    for (let k = 0; k <= n; k++) {
        outArr[0][colStart + k] = "拿" + k + "个";
    }

    let row = 1;
    for (let m = 0; m <= n; m++) {
        outArr[row][1] = m;
        let sumRow = 0;

        for (let k = 0; k <= m; k++) {
            let val;
            if (k === 0) {
                val = 1;
            } else {
                val = 1;
                for (let t = 0; t < k; t++) {
                    val *= (m - t);
                }
            }
            outArr[row][colStart + k] = val;
            sumRow += val;
        }

        for (let k = m + 1; k <= n; k++) {
            outArr[row][colStart + k] = "";
        }

        outArr[row][0] = sumRow;
        row++;
    }

    return outArr;
}

// 构建 m 次幂三角二维数组 (m^k)
function 构建_m次幂_三角二维数组(n) {
    const rowsTotal = n + 2;
    const colsTotal = n + 3;
    const colStart = 3;
    const outArr = Array(rowsTotal).fill().map(() => Array(colsTotal).fill(''));

    outArr[0][0] = "总和";
    outArr[0][1] = "总数";
    for (let k = 0; k <= n; k++) {
        outArr[0][colStart + k] = "拿" + k + "个";
    }

    let row = 1;
    for (let m = 0; m <= n; m++) {
        outArr[row][1] = m;
        let sumRow = 0;

        for (let k = 0; k <= m; k++) {
            let val;
            if (k === 0) {
                val = 1;
            } else {
                val = Math.pow(m, k);
            }
            outArr[row][colStart + k] = val;
            sumRow += val;
        }

        for (let k = m + 1; k <= n; k++) {
            outArr[row][colStart + k] = "";
        }

        outArr[row][0] = sumRow;
        row++;
    }

    return outArr;
}

// 工具：获取或创建工作表
function GetOrInitWorksheet(Name) {
    let ws;
    try {
        ws = ThisWorkbook.Worksheets(Name);
    } catch (e) {
        ws = ThisWorkbook.Worksheets.Add();
        ws.Name = Name;
    }
    return ws;
}

// 主函数：生成统合三角
function 生成_统合三角() {
    // 获取用户输入
    const typeChoice = Application.InputBox(
        "请选择三角类型：\n" +
        "1 = 组合不放回 C(m,k)(杨辉三角)\n" +
        "2 = 组合放回 C(m+k-1,k)\n" +
        "3 = 排列不放回 P(m,k)\n" +
        "4 = 排列放回 m^k\n" +
        "5 = 全部生成（all）",
        "统合三角类型选择",
        "5",
        100,
        100,
        "",
        0,
        1
    );

    if (typeChoice === false) return;
    const typeInput = parseInt(typeChoice);
    if (isNaN(typeInput) || typeInput < 1 || typeInput > 5) {
        Application.MsgBox("类型必须是 1..5 的整数。", 48);
        return;
    }

    const NInput = Application.InputBox("请输入总数最大值 N（>=0）：", "统合三角 - N设置", "", 100, 100, "", 0, 1);
    if (NInput === false) return;
    const n = parseInt(NInput);
    if (isNaN(n) || n < 0) {
        Application.MsgBox("N 必须为 >= 0 的整数。", 48);
        return;
    }

    const startTime = new Date().getTime();
    const typeConfigs = {
        1: { name: "三角_组合不放回_杨辉三角", func: 构建_组合不放回_C三角二维数组 },
        2: { name: "三角_组合放回_重复元素", func: 构建_组合放回_C三角_XX二维数组 },
        3: { name: "三角_排列不放回_镜像", func: 构建_排列不放回_P三角二维数组 },
        4: { name: "三角_排列放回_m次幂_完备", func: 构建_m次幂_三角二维数组 }
    };

    const typesToGenerate = typeInput === 5 ? [1, 2, 3, 4] : [typeInput];

    for (let t = 0; t < typesToGenerate.length; t++) {
        const type = typesToGenerate[t];
        const config = typeConfigs[type];

        let outArr = config.func(n);
        let ws = GetOrInitWorksheet(config.name);
        ws.Cells.Clear();

        const rows = outArr.length;
        const cols = outArr[0].length;
        try {
            const range = ws.Range(ws.Cells(1, 1), ws.Cells(rows, cols));
            range.Value2 = outArr;
        } catch (e) {
            Application.MsgBox("数组赋值失败，正在使用逐单元格写入方式...", 48, "提示");
            for (let i = 0; i < rows; i++) {
                for (let j = 0; j < cols; j++) {
                    ws.Cells(i + 1, j + 1).Value2 = outArr[i][j];
                }
            }
        }
    }

    const endTime = new Date().getTime();
    const elapsed = ((endTime - startTime) / 1000).toFixed(3);
    const typeLabel = typeInput === 5 ? "全部4种三角" : ["组合不放回", "组合放回", "排列不放回", "排列放回"][typeInput - 1];
    console.log("已生成【" + typeLabel + "】（N=0.." + n + "）到工作表。用时：" + elapsed + " 秒");
}
