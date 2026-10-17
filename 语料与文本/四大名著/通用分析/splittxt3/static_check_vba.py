# -*- coding: utf-8 -*-
"""静态验证 VBA 代码结构：检查 If/End If, For/Next, Sub/Function 配对"""
import re

bas_path = r"c:\Users\Administrator\Documents\这是什么\JK-temp\语料与文本\四大名著\通用分析\splittxt3\split_txt_v3.bas"

with open(bas_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

print(f"总行数: {len(lines)}")
print("=" * 60)

# 1. 检查结构配对
def check_structure():
    stack = []
    issues = []
    
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        
        # 跳过注释行
        if stripped.startswith("'"):
            continue
        
        # If ... Then 单行（不需要 End If）
        if re.match(r'^If\s+.+\s+Then\s+.+', stripped) and not stripped.endswith("Then") and "_" not in stripped:
            # 单行 If 语句，不计数
            continue
        
        # If 开头
        if re.match(r'^If\s+', stripped) and stripped.endswith("Then"):
            stack.append(('If', i))
        elif re.match(r'^ElseIf\s+', stripped):
            if not stack or stack[-1][0] != 'If':
                issues.append(f"行{i}: ElseIf 没有匹配的 If")
        elif re.match(r'^Else$', stripped):
            if not stack or stack[-1][0] != 'If':
                issues.append(f"行{i}: Else 没有匹配的 If")
        elif re.match(r'^End\s+If$', stripped):
            if not stack or stack[-1][0] != 'If':
                issues.append(f"行{i}: End If 没有匹配的 If")
            else:
                stack.pop()
        
        # For 循环
        if re.match(r'^For\s+', stripped):
            # 排除 For Each
            stack.append(('For', i))
        elif re.match(r'^Next\s+', stripped) or stripped == "Next":
            if not stack or stack[-1][0] != 'For':
                issues.append(f"行{i}: Next 没有匹配的 For")
            else:
                stack.pop()
        
        # Do 循环
        if re.match(r'^Do\s*$', stripped) or re.match(r'^Do\s+', stripped):
            stack.append(('Do', i))
        elif re.match(r'^Loop\s+', stripped) or stripped == "Loop":
            if not stack or stack[-1][0] != 'Do':
                issues.append(f"行{i}: Loop 没有匹配的 Do")
            else:
                stack.pop()
        
        # Select Case
        if re.match(r'^Select\s+Case\s+', stripped):
            stack.append(('Select', i))
        elif re.match(r'^End\s+Select$', stripped):
            if not stack or stack[-1][0] != 'Select':
                issues.append(f"行{i}: End Select 没有匹配的 Select")
            else:
                stack.pop()
        
        # Sub/Function
        if re.match(r'^(Public|Private)\s+Sub\s+', stripped):
            stack.append(('Sub', i, stripped))
        elif re.match(r'^(Public|Private)\s+Function\s+', stripped):
            stack.append(('Function', i, stripped))
        elif re.match(r'^End\s+Sub$', stripped):
            if not stack or stack[-1][0] not in ('Sub',):
                issues.append(f"行{i}: End Sub 没有匹配的 Sub")
            else:
                stack.pop()
        elif re.match(r'^End\s+Function$', stripped):
            if not stack or stack[-1][0] not in ('Function',):
                issues.append(f"行{i}: End Function 没有匹配的 Function")
            else:
                stack.pop()
    
    return issues, stack

issues, remaining = check_structure()

if issues:
    print("❌ 结构问题:")
    for issue in issues:
        print(f"  - {issue}")
else:
    print("✅ If/End If, For/Next, Do/Loop, Select/End Select, Sub/Function 全部配对正确")

if remaining:
    print(f"\n⚠ 未闭合的结构 ({len(remaining)} 个):")
    for item in remaining:
        print(f"  - 行{item[1]}: {item[0]} {' - ' + item[2] if len(item) > 2 else ''}")

# 2. 检查变量声明（粗略检查）
print("\n" + "=" * 60)
print("变量声明检查（粗略）:")

# 找出所有 Dim 声明
dim_vars = set()
for i, line in enumerate(lines, 1):
    stripped = line.strip()
    if stripped.startswith("Dim "):
        # 提取变量名
        parts = re.findall(r'Dim\s+(\w+)', stripped)
        for v in parts:
            dim_vars.add(v.lower())

print(f"  Dim 声明的变量数: {len(dim_vars)}")

# 检查常见的未定义变量模式（简单启发式）
# 这里只是抽查一些关键变量
key_vars = ['lines', 'linecount', 'ch_count', 'dedup_count', 'dedup_indices', 
            'g_dedupstrategy', 'g_sortstrategy', 'g_titlededup', 'g_volumemode',
            'flattenmap', 'flatmap', 'topnums', 'topcounts']

print("\n  关键变量检查:")
for v in key_vars:
    if v in dim_vars:
        print(f"    ✅ {v}")
    else:
        # 可能是全局变量，检查全局声明
        found_global = False
        for line in lines[:100]:  # 全局变量通常在文件开头
            if re.search(rf'(Private|Public|Global)\s+{re.escape(v)}\b', line, re.IGNORECASE):
                found_global = True
                break
        if found_global:
            print(f"    ✅ {v} (全局)")
        else:
            print(f"    ⚠  {v} (未找到Dim声明，可能是全局或参数)")

# 3. 检查 For Each 循环变量是否为 Variant
print("\n" + "=" * 60)
print("For Each 循环变量类型检查:")

for_each_issues = []
for i, line in enumerate(lines, 1):
    stripped = line.strip()
    m = re.match(r'^For\s+Each\s+(\w+)\s+In\s+', stripped)
    if m:
        var_name = m.group(1)
        # 查找该变量的 Dim 声明
        var_declared = False
        var_is_variant = False
        for j in range(max(0, i-50), i):
            decl = lines[j].strip()
            if re.search(rf'Dim\s+{re.escape(var_name)}\s+As\s+Variant', decl, re.IGNORECASE):
                var_declared = True
                var_is_variant = True
                break
            elif re.search(rf'Dim\s+{re.escape(var_name)}\s+As\s+', decl, re.IGNORECASE):
                var_declared = True
                var_is_variant = False
                break
        
        if var_declared and not var_is_variant:
            for_each_issues.append(f"行{i}: For Each {var_name} 不是 Variant 类型")

if for_each_issues:
    print("❌ 问题:")
    for issue in for_each_issues:
        print(f"  - {issue}")
else:
    print("✅ 所有 For Each 循环变量均为 Variant 类型")

print("\n" + "=" * 60)
print("✅ 静态验证完成")
