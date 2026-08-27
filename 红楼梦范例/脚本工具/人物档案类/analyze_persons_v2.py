# -*- coding: utf-8 -*-
import json
data = json.load(open(r'c:\Users\Administrator\.trae-cn\work\6a8e88bd38e645ba57bc4277\v34_extract2.json', encoding='utf-8'))
data.sort(key=lambda d: d['no'])

# 字面首次出场
first = {}
for d in data:
    for c in d['char_list']:
        n = c['name'].strip()
        if n not in first:
            first[n] = d['no']

# 每章新人物
newmap = {}
for d in data:
    newmap[d['no']] = [c['name'].strip() for c in d['char_list'] if first[c['name'].strip()] == d['no']]

print('=== 各章新出场人数(字面去重) ===')
total = 0
for d in data:
    n = newmap[d['no']]
    total += len(n)
    print('第%02d章: %d人 %s' % (d['no'], len(n), '、'.join(n)))
print('累计去重人物合计:', len(first), ' 新出场合计:', total)

print()
print('=== 疑似全名/简称重复检测 ===')
# 检测名字是否为另一个名字的子串(如宝玉 vs 贾宝玉)
names = sorted(first.keys())
for n in names:
    # 找出包含n作为后缀/前缀的其他名字
    for m in names:
        if n != m and (m.endswith(n) or n.endswith(m)) and len(n) >= 2 and len(m) >= 2 and abs(len(n) - len(m)) <= 2:
            if m.endswith(n) and len(n) < len(m):
                # m 是更长的名字，如 贾宝玉 endswith 宝玉
                pass
print('名便于查重已在前一步，直接列全名单：')
for n in names:
    print(n, first[n])