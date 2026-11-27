# -*- coding: utf-8 -*-
"""单文件引文锚定自检（三国演义版）：与 03_质检脚本_参数化.ps1 的 Norm/锚定逻辑一致。
用法: python 称呼学_锚定自检_三国.py <稿件.md>
自动从同父级向上查找 三国演义_拆分 与 名词列锦章节。
"""
import sys, os, glob, re

def norm(s):
    out = []
    for ch in s:
        c = ord(ch)
        if c < 0x20: continue
        if c in (0x20, 0x3000, 0xA0): continue
        if c in (0xAD, 0x180E, 0xFEFF): continue
        if 0x200B <= c <= 0x200F or 0x202A <= c <= 0x202E or 0x2060 <= c <= 0x2064: continue
        if 0xE000 <= c <= 0xF8FF or 0xFE00 <= c <= 0xFE0F: continue
        if 0x21 <= c <= 0x2F or 0x3A <= c <= 0x40 or 0x5B <= c <= 0x60 or 0x7B <= c <= 0x7E: continue
        if 0x2010 <= c <= 0x2027 or c == 0xB7: continue
        if 0x3001 <= c <= 0x303F: continue
        if 0xFF01 <= c <= 0xFF0F or 0xFF1A <= c <= 0xFF20 or 0xFF3B <= c <= 0xFF40 or 0xFF5B <= c <= 0xFF65: continue
        out.append(ch)
    return ''.join(out)

def find_up(start, name):
    p = start
    while p and p != os.path.dirname(p):
        if os.path.isdir(os.path.join(p, name)):
            return os.path.join(p, name)
        p = os.path.dirname(p)
    return None

md = sys.argv[1]
num = re.match(r'(\d{3})_', os.path.basename(md)).group(1)
proj = os.path.dirname(os.path.abspath(md))
split = find_up(proj, '三国演义_拆分')
nieq = find_up(proj, '名词列锦章节')

def read(p):
    with open(p, encoding='utf-8') as f:
        return f.read()

s0 = ''
if split:
    for p in glob.glob(os.path.join(split, num + '_*.txt')):
        s0 = norm(read(p)); break
n0 = ''
if nieq:
    for p in glob.glob(os.path.join(nieq, num + '_*.md')):
        n0 = norm(read(p)); break

with open(md, encoding='utf-8') as f:
    c = f.read()

qs = re.findall(r'「([^「」]+)」', c)
miss = []
total = 0
for i, q in enumerate(qs, 1):
    for seg in re.split(r'……|＋|——|—', q):
        nf = norm(seg)
        if len(nf) < 12: continue
        total += 1
        if s0 and nf in s0: continue
        if n0 and nf in n0: continue
        miss.append((i, seg[:30]))

chars = len(c)
h3 = sum(1 for l in c.splitlines() if l.startswith('### '))
print('文件:', os.path.basename(md))
print('字符数:', chars, '| 「」:', len(qs), '| 校验片段:', total, '| 未锚定:', len(miss))
print('### 段数:', h3)
for i, seg in miss:
    print('  [Q%d] %s' % (i, seg))
sys.exit(1 if miss else 0)
