# -*- coding: utf-8 -*-
"""
VBA变量精确检查 - 找出真正未声明的变量
策略：
1. 提取所有全局变量（模块级Dim/Private/Public）
2. 逐过程提取 Dim/ReDim/Static 声明的变量
3. 提取过程参数（ByVal/ByRef/Optional）
4. 提取代码中的标识符引用，排除VBA关键字、内置函数、对象方法/属性
5. 对比：使用了但未在全局+局部+参数中声明的 = 疑似未声明
"""
import re

with open(r'c:\Users\Administrator\Documents\这是什么\JK-temp\语料与文本\四大名著\通用分析\splittxt3\split_txt_v3.bas', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 处理行连接符
combined_lines = []
combined_line_num = []
i = 0
while i < len(lines):
    line = lines[i].rstrip('\n').rstrip('\r')
    start_num = i + 1
    while line.rstrip().endswith('_'):
        line = line.rstrip().rstrip('_') + ' '
        i += 1
        if i < len(lines):
            line += lines[i].rstrip('\n').rstrip('\r')
        else:
            break
    combined_lines.append(line)
    combined_line_num.append(start_num)
    i += 1

# VBA关键字 + 内置函数 + 常量（小写）
vba_builtins = {
    # 语句关键字
    'if', 'then', 'else', 'elseif', 'end', 'for', 'next', 'do', 'loop',
    'while', 'wend', 'select', 'case', 'to', 'step', 'with', 'exit',
    'as', 'dim', 'redim', 'set', 'let', 'get', 'new', 'is', 'in', 'like',
    'not', 'and', 'or', 'xor', 'mod', 'imp', 'eqv',
    'sub', 'function', 'property', 'end sub', 'end function', 'end property',
    'call', 'byval', 'byref', 'optional', 'paramarray',
    'true', 'false', 'nothing', 'null', 'empty', 'me', 'nothing',
    'on', 'error', 'resume', 'goto', 'gosub', 'return',
    'each', 'static', 'preserve', 'erase',
    'type', 'enum', 'implements', 'friend',
    'open', 'close', 'print', 'write', 'input', 'put', 'get',
    'random', 'binary', 'output', 'append', 'input',
    'lock', 'unlock', 'seek',
    'const', 'declare', 'lib', 'alias',
    'option', 'explicit', 'base', 'compare', 'private', 'public',
    'class', 'module',
    'raiseevent', 'event',
    'stop', 'end',
    
    # 数据类型
    'string', 'long', 'integer', 'double', 'single', 'boolean', 'variant',
    'object', 'byte', 'currency', 'date', 'decimal',
    
    # 转换函数
    'clng', 'cint', 'cstr', 'cdbl', 'csng', 'cbool', 'cbyte', 'ccur',
    'cdate', 'cdec', 'cvar',
    'str', 'val', 'hex', 'oct', 'chr', 'asc', 'ascb', 'ascw', 'chrb', 'chrw',
    
    # 字符串函数
    'left', 'right', 'mid', 'len', 'lenb', 'trim', 'ltrim', 'rtrim',
    'ucase', 'lcase', 'replace', 'instr', 'instrb', 'instrrev',
    'split', 'join', 'filter',
    'string', 'space', 'strcomp', 'strconv',
    'format', 'formatcurrency', 'formatdatetime', 'formatnumber', 'formatpercent',
    
    # 数学函数
    'abs', 'sgn', 'sqr', 'int', 'fix', 'round',
    'rnd', 'randomize',
    'log', 'exp',
    'sin', 'cos', 'tan', 'atn',
    'sqr',
    
    # 日期时间
    'now', 'date', 'time', 'timer',
    'year', 'month', 'day', 'weekday', 'hour', 'minute', 'second',
    'datediff', 'dateadd', 'dateserial', 'datevalue',
    'timeserial', 'timevalue',
    'monthname', 'weekdayname',
    'datepart',
    
    # 数组
    'array', 'isarray', 'ubound', 'lbound',
    
    # 判断函数
    'isempty', 'isnull', 'isobject', 'isnumeric', 'isdate', 'isarray',
    'iserror', 'ismissing', 'isnull', 'isobject',
    
    # 文件IO
    'dir', 'freefile', 'eof', 'lof', 'loc', 'filelen',
    'kill', 'name', 'mkdir', 'rmdir', 'chdir', 'chdrive',
    'curdir', 'environ',
    
    # 交互
    'msgbox', 'inputbox',
    'shell', 'appactivate', 'sendkeys', 'beep',
    
    # 其他
    'iif', 'choose', 'switch',
    'command', 'curdir$', 'dir$', 'environ$',
    'error', 'err',
    'lbound', 'ubound',
    'typeof',
    
    # 常量
    'vbcrlf', 'vblf', 'vbcr', 'vbtab', 'vbnullstring', 'vbnull', 'vbempty',
    'vbexclamation', 'vbinformation', 'vbcritical', 'vbquestion',
    'vbokonly', 'vbokcancel', 'vbyesno', 'vbyesnocancel', 'vbretrycancel',
    'vbok', 'vbcancel', 'vbyes', 'vbno', 'vbretry', 'vbigore',
    'vbdefaultbutton1', 'vbdefaultbutton2', 'vbdefaultbutton3',
    'vbtextcompare', 'vbbinarycompare',
    'vbunicode',
    'vbnormalfocus', 'vbdefaultfocus', 'vbmodal', 'vbmodeless',
    'vbnormal', 'vbminimized', 'vbmaximized', 'vbhidetoolwindow',
    'vbgreen', 'vbred', 'vbyellow',
    'vbnullchar', 'vbtab', 'vbverticaltab', 'vbback', 'vbformfeed',
    
    # VBA对象/集合常用属性方法
    'count', 'item', 'add', 'remove', 'removeall', 'exists', 'keys', 'items',
    'comparemode',
    
    # FileSystemObject相关
    'filesystemobject', 'file', 'folder', 'files', 'folders',
    'getfile', 'getfolder', 'getfilename', 'getbasename', 'getextensionname',
    'getparentfoldername', 'buildpath', 'fileexists', 'folderexists',
    'driveexists', 'getdrive', 'drives',
    'createfolder', 'createTextFile', 'opentextfile',
    'copyfile', 'movefile', 'deletefile',
    'copyfolder', 'movefolder', 'deletefolder',
    'name', 'path', 'size', 'datecreated', 'datelastmodified', 'datelastaccessed',
    'attributes', 'type', 'shortname', 'shortpath',
    'readall', 'readline', 'read', 'write', 'writeline', 'writeblanklines',
    'skip', 'skipline', 'close', 'atendofstream', 'atendofline',
    'line', 'column',
    
    # Dictionary 相关
    'scripting.dictionary', 'dictionary',
    
    # RegExp 相关
    'regexp', 'pattern', 'global', 'ignorecase', 'multiline',
    'execute', 'test', 'replace', 'matches', 'match',
    'firstindex', 'length', 'value', 'submatches',
    
    # ADO Stream相关
    'adodb.stream', 'adodb',
    'open', 'close', 'read', 'write', 'readtext', 'writetext',
    'position', 'size', 'type', 'charset', 'eos',
    'loadfromfile', 'savetofile', 'copyto',
    'adtypetext', 'adtypebinary', 'admodereadwrite', 'admodeunknown',
    'adopenstatic',
    
    # Collection
    'collection',
    
    # 错误对象
    'err', 'number', 'description', 'source', 'helpcontext', 'helpfile',
    'lastdllerror', 'raise', 'clear',
    
    # 其他常见
    'debug', 'print',
    'application',
    'vba',
    'typename', 'vartype',
    'rgb',
    'load', 'unload',
    'show', 'hide',
    'enabled', 'visible', 'value', 'caption', 'text',
    'left', 'top', 'width', 'height',
    
    # 本项目的自定义函数/过程（从外部调用的也算"已定义"）
    # 这些会在全局函数列表中单独处理
}

def extract_declared_vars(line):
    """从一行Dim/ReDim/Static声明中提取变量名"""
    vars_found = set()
    
    # 匹配 Dim var1 As Type, var2() As Type 这种
    # 先移除注释
    code = line
    if "'" in code:
        quote_count = 0
        clean = ""
        for ch in code:
            if ch == '"':
                quote_count += 1
            if quote_count % 2 == 0 and ch == "'":
                break
            clean += ch
        code = clean
    
    code = code.strip()
    
    # 处理 Dim / ReDim / Static 开头
    decl_match = re.match(r'^(Dim|ReDim|Static|Private|Public)\s+', code)
    if decl_match:
        rest = code[decl_match.end():]
        
        # 处理逗号分隔的变量声明
        # 如: Dim a As Long, b As String, c() As Integer
        parts = re.split(r',\s*', rest)
        for part in parts:
            part = part.strip()
            # 提取变量名：第一个词，可能带括号
            m = re.match(r'(\w+)(\s*\(\s*\))?', part)
            if m:
                var_name = m.group(1)
                if var_name.lower() not in vba_builtins and len(var_name) > 1:
                    vars_found.add(var_name.lower())
    
    return vars_found


def extract_params(sig_line):
    """从过程签名中提取参数变量名"""
    params = set()
    # 找括号内的内容
    m = re.search(r'\((.*)\)', sig_line)
    if m:
        param_str = m.group(1)
        # 匹配 ByVal/ByRef/Optional varName 或直接 varName
        # 如: ByVal x As Long, Optional y As String = "default"
        # 移除 As 类型部分
        # 找每个参数的变量名
        param_parts = re.split(r',\s*', param_str)
        for pp in param_parts:
            pp = pp.strip()
            if not pp:
                continue
            # 移除 ByVal/ByRef/Optional 前缀
            pp = re.sub(r'^(ByVal|ByRef|Optional)\s+', '', pp, flags=re.IGNORECASE)
            # 提取第一个词（变量名）
            m2 = re.match(r'(\w+)', pp)
            if m2:
                var_name = m2.group(1)
                if var_name.lower() not in vba_builtins:
                    params.add(var_name.lower())
    return params


def extract_used_vars(line):
    """从一行代码中提取使用的变量名（排除点号后的属性/方法）"""
    # 移除字符串字面量和注释
    in_str = False
    in_comment = False
    clean_code = ""
    
    for ch in line:
        if in_comment:
            break
        if ch == '"':
            in_str = not in_str
            clean_code += ' '
        elif in_str:
            clean_code += ' '
        elif ch == "'":
            in_comment = True
            break
        else:
            clean_code += ch
    
    # 匹配标识符：前面不是点号，以字母/下划线开头
    # 使用负向断言
    tokens = re.findall(r'(?<!\.)\b([A-Za-z_][A-Za-z0-9_]*)\b', clean_code)
    
    result = set()
    for t in tokens:
        t_lower = t.lower()
        if t_lower in vba_builtins:
            continue
        if len(t) <= 1:  # 单字母忽略，误报太多
            continue
        result.add(t_lower)
    
    return result


# ===== 主逻辑 =====

# 1. 收集全局变量
global_vars = set()
in_global_section = True
proc_names = set()  # 所有过程/函数名

for idx, line in enumerate(combined_lines):
    stripped = line.strip()
    if stripped.startswith("'"):
        continue
    
    # 检测过程开始
    proc_match = re.match(r'^(Private|Public)\s+(Sub|Function)\s+(\w+)', stripped, re.IGNORECASE)
    if proc_match:
        proc_names.add(proc_match.group(3).lower())
        in_global_section = False
        continue
    
    if in_global_section:
        # 收集全局变量声明
        if re.match(r'^(Private|Public|Dim)\s+\w+', stripped, re.IGNORECASE):
            vars_from_line = extract_declared_vars(stripped)
            global_vars.update(vars_from_line)

print(f"=== 全局变量 ({len(global_vars)} 个) ===")
for v in sorted(global_vars):
    print(f"  {v}")

print(f"\n=== 过程/函数名 ({len(proc_names)} 个) ===")
for v in sorted(proc_names):
    print(f"  {v}")

# 2. 逐个过程检查
print("\n" + "=" * 60)
print("逐过程变量检查")
print("=" * 60)

current_proc_name = None
current_proc_start = 0
current_local_vars = set()
current_param_vars = set()
current_code_lines = []  # (line_num, code)

total_issues = []

for idx, line in enumerate(combined_lines):
    stripped = line.strip()
    line_num = combined_line_num[idx]
    
    # 检测过程开始
    proc_match = re.match(r'^(Private|Public)\s+(Sub|Function)\s+(\w+)', stripped, re.IGNORECASE)
    if proc_match:
        current_proc_name = proc_match.group(3)
        current_proc_start = line_num
        current_local_vars = set()
        current_code_lines = []
        current_param_vars = extract_params(stripped)
        continue
    
    # 检测过程结束
    if re.match(r'^End\s+(Sub|Function)\b', stripped, re.IGNORECASE):
        if current_proc_name:
            # 检查这个过程
            all_declared = global_vars | current_local_vars | current_param_vars | proc_names
            
            used_vars = set()
            for ln, code in current_code_lines:
                used_vars.update(extract_used_vars(code))
            
            undeclared = used_vars - all_declared
            
            # 过滤：可能是属性/方法名（通过点号调用的）
            # 已经在 extract_used_vars 中用 (?<!\.) 排除了
            
            # 再过滤：常见的对象属性名（即使在左边也可能是属性赋值）
            common_props = {
                'name', 'value', 'text', 'caption', 'index', 'tag',
                'left', 'top', 'width', 'height',
                'enabled', 'visible', 'locked',
                'count', 'item', 'keys', 'items',
                'path', 'size', 'type',
                'pattern', 'global', 'ignorecase',
                'number', 'description', 'source',
                'position', 'charset', 'eos',
                'datecreated', 'datelastmodified',
                'attributes', 'shortname',
                'firstindex', 'length', 'submatches',
                'comparemode',
            }
            undeclared = {v for v in undeclared if v not in common_props}
            
            # 过滤：本过程名（递归调用）
            undeclared.discard(current_proc_name.lower())
            
            # 过滤：太短的（1-2个字符大多是循环变量或临时变量，可能在别处声明）
            undeclared = {v for v in undeclared if len(v) > 2}
            
            # 过滤：纯数字（不会是变量名）
            undeclared = {v for v in undeclared if not v.isdigit()}
            
            if undeclared:
                issue = (current_proc_name, current_proc_start, line_num, sorted(undeclared))
                total_issues.append(issue)
                print(f"\n【{current_proc_name}】(行{current_proc_start}-{line_num})")
                print(f"  参数: {sorted(current_param_vars)}")
                print(f"  局部: {len(current_local_vars)} 个")
                print(f"  ⚠ 疑似未声明 ({len(undeclared)}):")
                for v in sorted(undeclared):
                    print(f"     - {v}")
            
            current_proc_name = None
            current_code_lines = []
        continue
    
    if current_proc_name is not None:
        current_code_lines.append((line_num, stripped))
        
        # 收集局部变量声明
        if re.match(r'^(Dim|ReDim|Static)\s+', stripped, re.IGNORECASE):
            vars_from_line = extract_declared_vars(stripped)
            current_local_vars.update(vars_from_line)

print(f"\n" + "=" * 60)
print(f"共发现 {len(total_issues)} 个过程有疑似未声明变量")
print("=" * 60)
