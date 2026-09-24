# -*- coding: utf-8 -*-
"""精确定点：在阅读区中央取 40x40 纯背景块，统计唯一色值与标准差（验证纹理噪点）。"""
from PIL import Image
import os, statistics

APP = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
p = os.path.join(APP, ".temp", "gui_beauty.png")
im = Image.open(p).convert("RGB")
W, H = im.size

# 阅读区大概在 x=100~900 之间（左侧 250 侧栏 + 阅读列）。取中央偏上无文字区。
# 先扫描找到"几乎纯色"的行（该行无文字像素 = 标准差很低）
def row_stats(y, x0, x1):
    vals = [im.getpixel((x, y)) for x in range(x0, x1)]
    rs = [v[0] for v in vals]
    return statistics.pstdev(rs), len(set(vals))

# 扫描 y 找纯背景行
best = None
for y in range(160, 600, 10):
    sd, uniq = row_stats(y, 300, 700)
    if best is None or sd < best[0]:
        best = (sd, uniq, y)
print(f"最低波动行: y={best[2]}, std={best[0]:.3f}, 唯一色={best[1]}")

# 在最佳行附近取 60x60 块
y0 = max(100, best[2] - 30)
vals = []
for y in range(y0, y0 + 60):
    for x in range(400, 460):
        vals.append(im.getpixel((x, y)))
uniq = set(vals)
print(f"\n60x60 块 (x400-460, y{y0}-{y0+60}):")
print(f"唯一色值数: {len(uniq)}")
print(f"色值样本: {sorted(uniq)[:8]}")
rs = [v[0] for v in vals]
print(f"R 标准差: {statistics.pstdev(rs):.3f}")
print(f"R 范围: {min(rs)}~{max(rs)}")

# 判定
if len(uniq) > 5:
    print("\n>>> 结论: 有纹理噪点（多色值微波动）")
elif len(uniq) <= 2:
    print("\n>>> 结论: 接近纯色（纹理可能未生效或过淡）")
else:
    print(f"\n>>> 结论: 轻微波动（{len(uniq)} 色），可能纹理较淡")
print("DONE")
