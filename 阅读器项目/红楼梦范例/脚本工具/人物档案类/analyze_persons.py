# -*- coding: utf-8 -*-
import json
data = json.load(open(r'c:\Users\Administrator\.trae-cn\work\6a8e88bd38e645ba57bc4277\v34_extract2.json', encoding='utf-8'))
data.sort(key=lambda d: d['no'])
print('总章数', len(data))
total_new = 0
for d in data:
    new = [c['name'] for c in d['char_list'] if '初登场' in c['status']]
    if d['no'] == 1:
        new = [c['name'] for c in d['char_list']]
    total_new += len(new)
    if not new:
        print('第%d章: 0个新人物(共%d人)' % (d['no'], d['chars']))
    elif len(new) <= 2:
        print('第%d章: %d个新人物 -> %s' % (d['no'], len(new), new))
print('初登场累计(含ch1全量)', total_new)
seen = set()
for d in data:
    for c in d['char_list']:
        seen.add(c['name'])
print('去重名称总数(按name字面去重)', len(seen))