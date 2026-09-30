# -*- coding: utf-8 -*-
"""
VBA 静态检查脚本
检测：
1. For 循环内部的 Dim 语句（WPS VBA 会报重复定义）
2. Option Explicit 下可能未定义的变量（粗检）
3. 同一过程内重复 Dim 同名变量
"""

import os
import re
import sys
from pathlib import Path

# ============================================================
# VBA 关键字 / 内置常量 / 内置函数 列表（用于排除误报）
# ============================================================

VBA_KEYWORDS = {
    # 语句/流程控制
    "and", "as", "assert", "b", "beep", "boolean", "byval", "byref",
    "call", "case", "class", "const", "currency", "cdecl", "date",
    "declare", "dim", "do", "double", "each", "else", "elseif", "empty",
    "end", "enum", "eqv", "erase", "error", "event", "exit", "false",
    "for", "friend", "function", "get", "gosub", "goto", "if",
    "imp", "implements", "in", "input", "integer", "is", "let",
    "like", "long", "loop", "lset", "me", "mid", "mod", "new",
    "next", "not", "nothing", "null", "on", "option", "optional",
    "or", "paramarray", "preserve", "private", "property", "public",
    "raiseevent", "redim", "rem", "resume", "return", "rset",
    "select", "set", "shared", "single", "static", "step", "stop",
    "string", "sub", "then", "to", "true", "type", "typeof",
    "until", "variant", "wend", "while", "with", "withevents",
    "xor", "byte",
    # 常用其他
    "attribute", "vbbinary", "vbtext", "vbusecurrentday",
    "explicit", "compare", "base", "binary",
    # On Error 相关
    "resume", "err",
    # WithEvents 等
    "default",
}

# Excel / VBA 常用常量前缀
VBA_CONSTANTS_PREFIX = {
    "xl", "vb", "vba", "mso", "wd", "ac", "ad", "cd", "da", "db",
    "form", "control",
}

# VBA 常用内置函数/方法
VBA_BUILTIN_FUNCTIONS = {
    # 数学函数
    "abs", "array", "asc", "atn", "cbool", "cbyte", "ccur", "cdate",
    "cdbl", "cdec", "cint", "clng", "clnglng", "clngptr", "csng",
    "cstr", "cvar", "cvdate", "cverr", "choose", "chr", "command",
    "cos", "createobject", "csng", "curdir", "cvar", "cvdate",
    "cverr", "date", "dateadd", "datediff", "datepart", "dateserial",
    "datevalue", "day", "ddb", "dir", "doevents", "environ", "eof",
    "error", "exp", "fileattr", "filecopy", "filedatetime", "filelen",
    "fix", "format", "formatcurrency", "formatdatetime", "formatnumber",
    "formatpercent", "freefile", "fv", "getobject", "hex", "hour",
    "iif", "input", "inputbox", "instr", "instrrev", "int", "ipmt",
    "irate", "isarray", "isdate", "isempty", "iserror", "ismissing",
    "isnull", "isnumeric", "isobject", "join", "lbound", "lcase",
    "left", "len", "lineinput", "load", "loc", "lof", "log", "ltrim",
    "mid", "minute", "mirr", "month", "monthname", "msgbox",
    "now", "nper", "npv", "oct", "partition", "pmt", "ppmt",
    "pv", "qbcolor", "rate", "replace", "rgb", "right", "rnd",
    "round", "rtrim", "second", "seek", "sgn", "shell", "sin",
    "sln", "space", "spc", "split", "sqr", "str", "strcomp",
    "strconv", "string", "strreverse", "switch", "syscmd", "tab",
    "tan", "timer", "timeserial", "timevalue", "trim", "typename",
    "ubound", "ucase", "unload", "val", "varptr", "vartype",
    "weekday", "weekdayname", "year",
    # 集合/对象
    "collection", "dictionary",
    # WorksheetFunction 常用
    "worksheetfunction",
    # 特殊
    "vba", "excel", "application", "worksheet", "worksheets",
    "workbook", "workbooks", "range", "cells", "rows", "columns",
    "activecell", "activesheet", "activeworkbook", "selection",
    "activesheet", "thisworkbook", "sheets",
    "err", "debug", "print",
    # 窗体相关
    "userforms", "userform", "controls", "designer",
    "vbcomponents", "vbproject", "codemodule",
    "vbp", "frm", "lbl", "txt", "chk", "fra", "btn",
    # 事件相关
    "click", "change", "initialize", "queryclose",
    # 常用属性
    "caption", "text", "value", "left", "top", "width", "height",
    "name", "font", "size", "bold", "backcolor", "forecolor",
    "visible", "enabled", "count", "item", "index",
    "add", "remove", "show", "hide", "unload", "setfocus",
    # With 块内常见
    "item",
}

# 常用 Excel 对象的方法/属性（粗排除用）
EXCEL_OBJECT_MEMBERS = {
    "cells", "range", "rows", "columns", "value", "value2", "text",
    "formula", "formular1c1", "numberformat", "interior", "font",
    "border", "borders", "color", "colorindex", "name", "parent",
    "count", "add", "item", "delete", "clear", "clearcontents",
    "copy", "paste", "pasteSpecial", "cut", "insert", "resize",
    "offset", "end", "xlup", "xldown", "xltoleft", "xltoright",
    "select", "activate", "activecell", "activesheet", "activeworkbook",
    "screenupdating", "calculation", "xlcalculationmanual",
    "xlcalculationautomatic", "displayalerts", "enableevents",
    "worksheets", "workbooks", "sheets", "range", "cells",
    "merge", "mergecells", "wraptext", "horizontalalignment",
    "verticalalignment", "autofit", "sort", "find", "replace",
    "pastespecial", "transpose", "array",
    "caption", "picture", "oleobjects", "shapes", "shape",
    "chart", "charts", "pivotcache", "pivottable", "pivotfield",
    "databodyrange", "listobject", "listobjects",
    "querytables", "querytable", "connection",
    "vbproject", "vbcomponents", "codemodule", "designer",
    "countoflines", "insertlines", "deletelines", "replaceline",
    "procofline", "proccountlines", "procstartline",
    "prockind", "vbext_pk_proc", "vbext_pk_get",
    "vbext_pk_let", "vbext_pk_set",
    "properties",
    # 常用集合成员
    "count", "item", "add", "remove", "newenum",
    # Error 相关
    "number", "description", "source", "helpfile", "helpcontext",
    "lastdllerror", "raise", "clear",
    # RGB
    "red", "green", "blue",
    # 文件系统
    "dir", "freefile", "open", "close", "input", "write",
    "print", "get", "put", "seek", "loc", "lof", "eof",
    # Misc
    "nothing", "empty", "null", "true", "false",
    "me", "with", "each", "step",
    "chr", "string", "space", "spc", "tab",
    "now", "date", "time", "timer",
    "format", "cstr", "clng", "cint", "cdbl", "cdate", "cbool",
    "len", "left", "right", "mid", "instr", "trim", "ltrim", "rtrim",
    "ucase", "lcase", "replace", "split", "join",
    "ubound", "lbound", "array", "erase", "redim",
    "msgbox", "inputbox", "debug",
    "iif", "switch", "choose",
    "abs", "int", "fix", "sgn", "sqr", "exp", "log",
    "sin", "cos", "tan", "atn",
    "rnd", "randomize",
    "shell", "environ",
    "typename", "vartype", "isarray", "isdate", "isempty",
    "isnull", "isnumeric", "isobject", "iserror", "ismissing",
    # 控件相关
    "commandbutton", "textbox", "label", "checkbox", "optionbutton",
    "listbox", "combobox", "frame", "image", "scrollbar", "spinbutton",
    "togglebutton", "tabstrip", "multipage", "refedit",
    "controls", "control",
    "setfocus", "zorder",
    "mouseicon", "mousepointer",
    "controlsource", "rowsource",
    "controltiptext", "tag",
    "accelerator", "accel",
    "wordwrap", "autosize",
    "multiline", "passwordchar",
    "scrollbars", "seltext", "sellength", "selstart",
    "style", "locked", "value",
    "columncount", "columnwidths", "boundcolumn",
    "listindex", "listcount", "list",
    # 窗体相关
    "startupposition", "show", "hide", "unload", "load",
    "vbmodeless", "vbmodal",
    "userforms",
    # 记录集相关
    "recordset", "recordsetclone", "bof", "eof", "movefirst",
    "movelast", "movenext", "moveprevious", "find", "seek",
    "fields", "field",
    # ADO
    "connection", "command", "recordset", "field", "fields",
    "parameters", "parameter", "errors", "error",
    "open", "close", "execute",
    # Dictionary
    "keys", "items", "exists", "add", "remove", "removeall",
    "comparemode", "count", "item", "key",
    # Collection
    "add", "count", "item", "remove",
}

def is_builtin_identifier(name: str) -> bool:
    """判断标识符是否为 VBA 内置/关键字/常量，返回 True 表示是内置的，不应报未定义"""
    lower = name.lower()
    # 关键字
    if lower in VBA_KEYWORDS:
        return True
    # 内置函数
    if lower in VBA_BUILTIN_FUNCTIONS:
        return True
    # Excel 对象成员
    if lower in EXCEL_OBJECT_MEMBERS:
        return True
    # 以 xl/vb/mso 等开头的常量
    for prefix in VBA_CONSTANTS_PREFIX:
        if lower.startswith(prefix):
            return True
    # 纯数字
    if lower.isdigit():
        return True
    return False


# ============================================================
# 行预处理
# ============================================================

def remove_vba_comment(line: str) -> str:
    """移除 VBA 行内注释（单引号开头的注释），保留字符串内的单引号"""
    in_str = False
    result = []
    i = 0
    while i < len(line):
        ch = line[i]
        if ch == '"':
            in_str = not in_str
            result.append(ch)
        elif ch == "'" and not in_str:
            break
        else:
            result.append(ch)
        i += 1
    return ''.join(result)


def is_continued_line(line: str) -> bool:
    """判断行是否以续行符 _ 结尾"""
    stripped = line.rstrip()
    no_comment = remove_vba_comment(stripped)
    return no_comment.rstrip().endswith("_")


def join_continued_lines(lines):
    """将续行合并为一行，返回 [(合并后文本, 起始行号)]"""
    result = []
    i = 0
    while i < len(lines):
        line_num = i + 1
        current = lines[i].rstrip("\r\n")
        while is_continued_line(current) and i + 1 < len(lines):
            i += 1
            next_line = lines[i].rstrip("\r\n")
            no_comment = remove_vba_comment(current)
            idx = no_comment.rfind("_")
            current = current[:idx] + " " + next_line.lstrip()
        result.append((current, line_num))
        i += 1
    return result


# ============================================================
# 变量声明提取
# ============================================================

DECL_PATTERN = re.compile(
    r'^\s*(Dim|Public|Private|Const|ReDim|Static|Global)\s+(.+)$',
    re.IGNORECASE
)

NON_VAR_DECL_AFTER = {
    'sub', 'function', 'property', 'type', 'enum', 'event',
    'declare', 'class',
}

VAR_NAME_PATTERN = re.compile(
    r'([A-Za-z_\u4e00-\u9fff][\w\u4e00-\u9fff]*)\s*(?:\([^)]*\))?\s*(?:As\s+\w+)?\s*(?:=\s*[^,]+)?',
    re.IGNORECASE
)

def extract_declared_vars(decl_line: str):
    """从一行声明语句中提取所有变量名列表（支持中文变量名）"""
    line = remove_vba_comment(decl_line)
    m = DECL_PATTERN.match(line)
    if not m:
        return []
    decl_keyword = m.group(1).lower()
    rest = m.group(2)
    
    # 排除过程定义：Public/Private/Global 后面跟 Sub/Function/Property 等
    if decl_keyword in ('public', 'private', 'global'):
        first_word = rest.strip().split()[0].lower() if rest.strip() else ''
        if first_word in NON_VAR_DECL_AFTER:
            return []
    
    # 处理多变量声明（用逗号分隔），注意不要切到字符串
    vars_text = rest
    parts = []
    in_str = False
    current = []
    for ch in vars_text:
        if ch == '"':
            in_str = not in_str
            current.append(ch)
        elif ch == ',' and not in_str:
            parts.append(''.join(current).strip())
            current = []
        else:
            current.append(ch)
    if current:
        parts.append(''.join(current).strip())
    
    var_names = []
    for part in parts:
        m2 = re.match(r'^([A-Za-z_\u4e00-\u9fff][\w\u4e00-\u9fff]*)', part)
        if m2:
            var_names.append(m2.group(1))
    return var_names


# ============================================================
# 过程识别
# ============================================================

PROC_START_PATTERN = re.compile(
    r'^\s*(?:Public\s+|Private\s+|Friend\s+|Static\s+)*'
    r'(Sub|Function|Property\s+(?:Get|Let|Set))\s+'
    r'([A-Za-z_\u4e00-\u9fff][\w\u4e00-\u9fff]*)\s*\(',
    re.IGNORECASE
)

PROC_END_PATTERN = re.compile(
    r'^\s*End\s+(Sub|Function|Property)\s*$',
    re.IGNORECASE
)

PARAM_PATTERN = re.compile(
    r'(?:ByVal\s+|ByRef\s+|Optional\s+)*'
    r'([A-Za-z_\u4e00-\u9fff][\w\u4e00-\u9fff]*)\s*(?:\([^)]*\))?\s*(?:As\s+\w+)?',
    re.IGNORECASE
)

def extract_param_names(proc_line: str):
    """从过程定义行提取参数名列表（支持中文）"""
    line = remove_vba_comment(proc_line)
    m = re.search(r'\((.*)\)', line)
    if not m:
        return []
    params_str = m.group(1)
    if not params_str.strip():
        return []
    parts = []
    in_str = False
    current = []
    for ch in params_str:
        if ch == '"':
            in_str = not in_str
            current.append(ch)
        elif ch == ',' and not in_str:
            parts.append(''.join(current).strip())
            current = []
        else:
            current.append(ch)
    if current:
        parts.append(''.join(current).strip())
    
    param_names = []
    for part in parts:
        m2 = PARAM_PATTERN.match(part.strip())
        if m2:
            param_names.append(m2.group(1))
    return param_names


# ============================================================
# For 循环识别
# ============================================================

FOR_START_PATTERN = re.compile(
    r'^\s*For\s+',
    re.IGNORECASE
)

FOR_EACH_PATTERN = re.compile(
    r'^\s*For\s+Each\s+',
    re.IGNORECASE
)

NEXT_PATTERN = re.compile(
    r'^\s*Next\b',
    re.IGNORECASE
)


def split_vba_statements(line: str):
    """按冒号分割 VBA 语句（字符串内的冒号不算）"""
    parts = []
    in_str = False
    current = []
    for ch in line:
        if ch == '"':
            in_str = not in_str
            current.append(ch)
        elif ch == ':' and not in_str:
            parts.append(''.join(current))
            current = []
        else:
            current.append(ch)
    if current:
        parts.append(''.join(current))
    return parts


def count_next_in_stmt(stmt: str):
    """统计 Next 语句中关闭的循环层数（Next i, j, k 返回 3）"""
    stripped = stmt.strip()
    m = re.match(r'^\s*Next\s*(.*)$', stripped, re.IGNORECASE)
    if not m:
        return 1
    rest = m.group(1).strip()
    if not rest:
        return 1
    count = rest.count(',') + 1
    return max(count, 1)


# ============================================================
# 标识符提取（用于未定义变量检测）
# ============================================================

IDENT_PATTERN = re.compile(r'[A-Za-z_\u4e00-\u9fff][\w\u4e00-\u9fff]*')


def extract_identifiers(line: str):
    """从一行代码中提取所有标识符（排除字符串内的，支持中文）"""
    line = remove_vba_comment(line)
    in_str = False
    result = []
    i = 0
    text = line
    while i < len(text):
        ch = text[i]
        if ch == '"':
            in_str = not in_str
            i += 1
            continue
        if in_str:
            i += 1
            continue
        if ch.isalpha() or ch == '_' or ('\u4e00' <= ch <= '\u9fff'):
            j = i
            while j < len(text):
                c = text[j]
                if c.isalnum() or c == '_' or ('\u4e00' <= c <= '\u9fff'):
                    j += 1
                else:
                    break
            ident = text[i:j]
            result.append((ident, i))
            i = j
        else:
            i += 1
    return result


# ============================================================
# 主检查器
# ============================================================

class VBAIssue:
    def __init__(self, issue_type: str, line_num: int, description: str):
        self.issue_type = issue_type
        self.line_num = line_num
        self.description = description
    
    def __repr__(self):
        return f"[行{self.line_num}] {self.issue_type}: {self.description}"


class VBAFileChecker:
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.filename = os.path.basename(filepath)
        self.issues = []
        self.lines = []
        self.has_option_explicit = False
    
    def add_issue(self, issue_type: str, line_num: int, description: str):
        self.issues.append(VBAIssue(issue_type, line_num, description))
    
    def check(self):
        """执行所有检查"""
        with open(self.filepath, 'r', encoding='utf-8', errors='replace') as f:
            raw_lines = f.readlines()
        self.lines = raw_lines
        
        # 检查 Option Explicit
        for i, line in enumerate(raw_lines):
            stripped = line.strip()
            if re.match(r'^Option\s+Explicit\s*$', stripped, re.IGNORECASE):
                self.has_option_explicit = True
                break
            if stripped and not stripped.startswith("'") and not stripped.startswith("Rem "):
                break
        
        # 合并续行
        merged = join_continued_lines(raw_lines)
        
        # ---- 检查1: For 循环内的 Dim 语句 ----
        self._check_dim_in_for(merged)
        
        # ---- 检查2 & 3: 过程级检查 ----
        self._check_proc_level(merged)
        
        return self.issues
    
    def _check_dim_in_for(self, merged_lines):
        """检查 For 循环内部的 Dim 语句"""
        for_depth = 0
        
        for line_text, line_num in merged_lines:
            no_comment = remove_vba_comment(line_text)
            if not no_comment.strip():
                continue
            
            statements = split_vba_statements(no_comment)
            
            for stmt in statements:
                stripped = stmt.strip()
                if not stripped:
                    continue
                
                is_for_start = False
                
                # 检查是否是 For 开始
                if FOR_START_PATTERN.match(stripped):
                    for_depth += 1
                    is_for_start = True
                
                # 检查 Next
                if NEXT_PATTERN.match(stripped):
                    next_count = count_next_in_stmt(stripped)
                    for _ in range(next_count):
                        if for_depth > 0:
                            for_depth -= 1
                
                # For 行本身跳过声明检测
                if is_for_start:
                    continue
                
                # 在 For 循环内部且是 Dim/Static/Const 等声明（排除 ReDim）
                if for_depth > 0:
                    is_redim = bool(re.match(r'^\s*ReDim\s+', stripped, re.IGNORECASE))
                    if is_redim:
                        continue
                    vars_in_decl = extract_declared_vars(stripped)
                    if vars_in_decl:
                        decl_type = stripped.split()[0]
                        for v in vars_in_decl:
                            self.add_issue(
                                "For循环内声明变量",
                                line_num,
                                f"在 For 循环内部使用 {decl_type} 声明变量 '{v}'，WPS VBA 可能报重复定义错误"
                            )
    
    def _check_proc_level(self, merged_lines):
        """过程级检查：重复 Dim 和未定义变量"""
        procs = []
        module_decls = set()
        
        current_proc = None
        in_proc = False
        
        for idx, (line_text, line_num) in enumerate(merged_lines):
            stripped = line_text.strip()
            if not stripped:
                continue
            
            # 检查过程开始
            m = PROC_START_PATTERN.match(stripped)
            if m and not in_proc:
                proc_name = m.group(2)
                params = extract_param_names(stripped)
                current_proc = {
                    'name': proc_name,
                    'start_idx': idx,
                    'start_line': line_num,
                    'params': params,
                    'decls': {},
                    'decl_order': [],
                }
                in_proc = True
                continue
            
            # 检查过程结束
            if PROC_END_PATTERN.match(stripped) and in_proc:
                current_proc['end_idx'] = idx
                current_proc['end_line'] = line_num
                procs.append(current_proc)
                current_proc = None
                in_proc = False
                continue
            
            # 模块级声明
            if not in_proc:
                if DECL_PATTERN.match(stripped):
                    vars_in_decl = extract_declared_vars(stripped)
                    for v in vars_in_decl:
                        module_decls.add(v.lower())
                continue
            
            # 过程内：收集声明
            if DECL_PATTERN.match(stripped):
                vars_in_decl = extract_declared_vars(stripped)
                is_redim = bool(re.match(r'^\s*ReDim\s+', stripped, re.IGNORECASE))
                for v in vars_in_decl:
                    v_lower = v.lower()
                    if not is_redim:
                        if v_lower in current_proc['decls']:
                            first_line = current_proc['decls'][v_lower]
                            self.add_issue(
                                "过程内重复声明",
                                line_num,
                                f"过程 '{current_proc['name']}' 内重复声明变量 '{v}'（首次声明在第 {first_line} 行）"
                            )
                        else:
                            current_proc['decls'][v_lower] = line_num
                            current_proc['decl_order'].append(v)
                    else:
                        if v_lower not in current_proc['decls']:
                            current_proc['decls'][v_lower] = line_num
                            current_proc['decl_order'].append(v)
        
        # ---- 检查3: Option Explicit 下未定义变量 ----
        if self.has_option_explicit:
            all_declared = set()
            all_declared.update(module_decls)
            for p in procs:
                all_declared.add(p['name'].lower())
            
            for proc in procs:
                proc_decls = set()
                for p in proc['params']:
                    proc_decls.add(p.lower())
                proc_decls.update(proc['decls'].keys())
                
                # 收集行标签
                line_labels = set()
                for idx in range(proc['start_idx'], proc['end_idx'] + 1):
                    lt, ln = merged_lines[idx]
                    lt_no_comment = remove_vba_comment(lt)
                    m_label = re.match(
                        r'^\s*([A-Za-z_\u4e00-\u9fff][\w\u4e00-\u9fff]*)\s*:\s*$',
                        lt_no_comment
                    )
                    if m_label:
                        line_labels.add(m_label.group(1).lower())
                
                visible = all_declared | proc_decls | line_labels
                
                # 扫描过程内每一行
                for idx in range(proc['start_idx'], proc['end_idx'] + 1):
                    line_text, line_num = merged_lines[idx]
                    stripped = line_text.strip()
                    if not stripped:
                        continue
                    
                    if DECL_PATTERN.match(stripped):
                        continue
                    if PROC_START_PATTERN.match(stripped):
                        continue
                    if PROC_END_PATTERN.match(stripped):
                        continue
                    if re.match(r'^\s*On\s+', stripped, re.IGNORECASE):
                        continue
                    if re.match(r'^\s*[A-Za-z_\u4e00-\u9fff][\w\u4e00-\u9fff]*\s*:\s*$', stripped):
                        continue
                    
                    idents = extract_identifiers(line_text)
                    
                    for ident, pos in idents:
                        ident_lower = ident.lower()
                        if is_builtin_identifier(ident):
                            continue
                        if ident_lower in visible:
                            continue
                        
                        # 过滤1：点号后面的属性/方法
                        before = line_text[:pos].rstrip()
                        if before and before[-1] == '.':
                            continue
                        
                        # 过滤2：方括号内（Evaluate 语法，如 [F2]）
                        before_bracket = line_text[:pos].rfind('[')
                        after_bracket = line_text[pos:].find(']')
                        if before_bracket >= 0 and after_bracket >= 0:
                            between = line_text[before_bracket+1:pos+after_bracket]
                            if '[' not in between and ']' not in between:
                                continue
                        
                        # 过滤3：命名参数（xxx:=）
                        after_text = line_text[pos+len(ident):].lstrip()
                        if after_text.startswith(':='):
                            continue
                        
                        # 过滤4：GoTo/Resume 后的行标签
                        before_stripped = before.rstrip()
                        m_last = re.search(
                            r'\b(GoTo|Resume|GoSub|On\s+Error\s+GoTo)\s*$',
                            before_stripped,
                            re.IGNORECASE
                        )
                        if m_last:
                            continue
                        
                        self.add_issue(
                            "可能未定义变量",
                            line_num,
                            f"过程 '{proc['name']}' 中使用标识符 '{ident}'，未在声明中找到（粗检，可能为外部调用/属性，请人工确认）"
                        )
        
        # 去重
        self._deduplicate_undefined()
    
    def _deduplicate_undefined(self):
        seen = set()
        new_issues = []
        for issue in self.issues:
            if issue.issue_type == "可能未定义变量":
                key = (issue.line_num, issue.description)
                if key not in seen:
                    seen.add(key)
                    new_issues.append(issue)
            else:
                new_issues.append(issue)
        self.issues = new_issues


# ============================================================
# 报告生成
# ============================================================

def generate_report(file_results: dict):
    """生成格式化报告"""
    lines = []
    lines.append("=" * 70)
    lines.append("VBA 静态检查报告")
    lines.append("=" * 70)
    lines.append("")
    
    total_issues = 0
    file_count = len(file_results)
    
    for filepath in sorted(file_results.keys()):
        issues = file_results[filepath]
        filename = os.path.basename(filepath)
        total_issues += len(issues)
        
        lines.append("-" * 70)
        lines.append(f"文件: {filename}")
        lines.append(f"路径: {filepath}")
        lines.append(f"问题数: {len(issues)}")
        lines.append("-" * 70)
        
        if not issues:
            lines.append("  （无问题）")
            lines.append("")
            continue
        
        by_type = {}
        for issue in issues:
            if issue.issue_type not in by_type:
                by_type[issue.issue_type] = []
            by_type[issue.issue_type].append(issue)
        
        for issue_type in sorted(by_type.keys()):
            type_issues = sorted(by_type[issue_type], key=lambda x: x.line_num)
            lines.append(f"")
            lines.append(f"  【{issue_type}】（共 {len(type_issues)} 处）")
            for issue in type_issues:
                lines.append(f"    行 {issue.line_num:>4d}: {issue.description}")
        
        lines.append("")
    
    lines.append("=" * 70)
    lines.append(f"检查完成：共扫描 {file_count} 个文件，发现 {total_issues} 个问题")
    lines.append("=" * 70)
    
    return "\n".join(lines)


# ============================================================
# 主函数
# ============================================================

def main():
    if len(sys.argv) > 1:
        scan_dir = sys.argv[1]
    else:
        scan_dir = r"C:\Users\Administrator\Documents\这是什么\JK-temp\自动化与工具\VBA转js\循环组合"
    
    if not os.path.isdir(scan_dir):
        print(f"错误：目录不存在 - {scan_dir}")
        sys.exit(1)
    
    bas_files = []
    for root, dirs, files in os.walk(scan_dir):
        for f in files:
            if f.lower().endswith('.bas'):
                bas_files.append(os.path.join(root, f))
    
    if not bas_files:
        print(f"在 {scan_dir} 下未找到 .bas 文件")
        sys.exit(0)
    
    print(f"找到 {len(bas_files)} 个 .bas 文件，开始检查...\n")
    
    results = {}
    for filepath in sorted(bas_files):
        checker = VBAFileChecker(filepath)
        issues = checker.check()
        results[filepath] = issues
    
    report = generate_report(results)
    print(report)
    
    report_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vba_lint_report.txt")
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"\n报告已保存至: {report_path}")


if __name__ == "__main__":
    main()
