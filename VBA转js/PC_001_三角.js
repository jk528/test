// PC_001_三角.js - VBA 代码转 JavaScript

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

// 主函数：生成统合三角
function 生成_统合三角() {
    // 获取用户输入
    const typeChoice = prompt(
        "请选择三角类型：\n" +
        "1 = 组合不放回 C(m,k)(杨辉三角)(元素不重复去镜像)\n" +
        "2 = 组合放回 C(m+k-1,k)（元素重复去镜像）\n" +
        "3 = 排列不放回 P(m,k)=m!/(m-k)!(元素不重复镜像)\n" +
        "4 = 排列放回 m^k(元素重复镜像)"
    );

    if (typeChoice === null) return;
    const type = parseInt(typeChoice);
    if (isNaN(type) || type < 1 || type > 4) {
        alert("类型必须是 1..4 的整数。");
        return;
    }

    const NInput = prompt("请输入总数最大值 N（>=0）：");
    if (NInput === null) return;
    const n = parseInt(NInput);
    if (isNaN(n) || n < 0) {
        alert("N 必须为 >= 0 的整数。");
        return;
    }

    let outArr, sheetName;

    // 根据类型生成二维数组与工作表名
    switch (type) {
        case 1:
            outArr = 构建_组合不放回_C三角二维数组(n);
            sheetName = "三角_组合不放回_杨辉三角";
            break;
        case 2:
            outArr = 构建_组合放回_C三角_XX二维数组(n);
            sheetName = "三角_组合放回_重复元素";
            break;
        case 3:
            outArr = 构建_排列不放回_P三角二维数组(n);
            sheetName = "三角_排列不放回_镜像";
            break;
        case 4:
            outArr = 构建_m次幂_三角二维数组(n);
            sheetName = "三角_排列放回_m次幂_完备";
            break;
    }

    // 输出结果（在浏览器中显示）
    console.log("生成结果:", sheetName);
    console.table(outArr);
    
    // 简单的 HTML 表格显示
    let html = `<h2>${sheetName}</h2><table border="1" style="border-collapse: collapse;">`;
    outArr.forEach(row => {
        html += "<tr>";
        row.forEach(cell => {
            html += `<td style="padding: 5px;">${cell}</td>`;
        });
        html += "</tr>";
    });
    html += "</table>";

    // 创建临时 div 显示结果
    const div = document.createElement('div');
    div.innerHTML = html;
    div.style.margin = "20px";
    document.body.appendChild(div);

    alert(`已生成：${sheetName}（行 m=0..N，列 k=0..N）。`);
}

// 示例调用
// 生成_统合三角();
