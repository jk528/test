# -*- coding: utf-8 -*-
"""
detect_duplication.py — 行级 shingling 重复检测脚本（方案 D）

用法:
    python detect_duplication.py <src_dir> [--k 5] [--confirm 0.8] [--suspect 0.5] [--out 重复报告.md]

对应 spec 5.2 / design 接口族一（detect_duplicates / generate_shingles / jaccard_similarity / locate_duplicate_spans）。
对原文档库只读，输出仅限 _工具\ 目录。
"""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, FrozenSet, List, Set, Tuple


Shingle = int


@dataclass(frozen=True)
class DuplicateSpan:
    a_start: int
    a_end: int
    b_start: int
    b_end: int
    preview: str


@dataclass
class DuplicationResult:
    path_a: str
    path_b: str
    jaccard: float
    status: str
    dup_lines: int
    spans: List[DuplicateSpan] = field(default_factory=list)


_HEADER_RE = re.compile(r"^#{1,6}\s*")
_TABLE_SEP_RE = re.compile(r"^\|?[\s:|-]+\|?$")


def normalize_line(line: str) -> str:
    """归一化单行：去首尾空白；统一空行；忽略 # 数量差异；忽略纯表格分隔行差异。"""
    s = line.strip()
    if s == "":
        return ""
    if s.startswith("#"):
        s = _HEADER_RE.sub("# ", s)
    if _TABLE_SEP_RE.match(s):
        return "|---|"
    return s


def generate_shingles(lines: List[str], k: int) -> FrozenSet[Shingle]:
    """将文档按行划分为连续 k 行的 shingle 集合，返回不可变无重复 frozenset。"""
    if k < 1:
        raise ValueError(f"k 必须 >= 1，当前 k={k}")
    norm = [normalize_line(ln) for ln in lines]
    n = len(norm)
    if n < k:
        return frozenset()
    out: Set[Shingle] = set()
    for i in range(n - k + 1):
        chunk = "\n".join(norm[i:i + k])
        out.add(int(hashlib.md5(chunk.encode("utf-8")).hexdigest(), 16))
    return frozenset(out)


def jaccard_similarity(set_a: FrozenSet[Shingle], set_b: FrozenSet[Shingle]) -> float:
    """计算 |A∩B| / |A∪B|；空集并集时返回 0.0。"""
    if not set_a and not set_b:
        return 0.0
    inter = len(set_a & set_b)
    union = len(set_a | set_b)
    if union == 0:
        return 0.0
    return inter / union


def locate_duplicate_spans(
    lines_a: List[str],
    lines_b: List[str],
    k: int,
    shared_shingles: Set[Shingle],
) -> List[DuplicateSpan]:
    """将命中 shingle 回溯到原行号，合并相邻行号为连续段落区间。"""
    norm_a = [normalize_line(ln) for ln in lines_a]
    norm_b = [normalize_line(ln) for ln in lines_b]
    hit_a: List[int] = []
    for i in range(len(norm_a) - k + 1):
        chunk = "\n".join(norm_a[i:i + k])
        h = int(hashlib.md5(chunk.encode("utf-8")).hexdigest(), 16)
        if h in shared_shingles:
            hit_a.append(i)
    hit_b: List[int] = []
    for j in range(len(norm_b) - k + 1):
        chunk = "\n".join(norm_b[j:j + k])
        h = int(hashlib.md5(chunk.encode("utf-8")).hexdigest(), 16)
        if h in shared_shingles:
            hit_b.append(j)

    def merge_ranges(starts: List[int]) -> List[Tuple[int, int]]:
        if not starts:
            return []
        starts = sorted(set(starts))
        ranges: List[Tuple[int, int]] = []
        rs = starts[0]
        re_ = starts[0]
        for s in starts[1:]:
            if s <= re_ + k:
                re_ = max(re_, s)
            else:
                ranges.append((rs, re_ + k - 1))
                rs = s
                re_ = s
        ranges.append((rs, re_ + k - 1))
        return ranges

    ra = merge_ranges(hit_a)
    rb = merge_ranges(hit_b)
    spans: List[DuplicateSpan] = []
    for (a_s, a_e), (b_s, b_e) in zip(ra, rb):
        preview_lines = lines_a[a_s:a_e + 1][:3]
        preview = " / ".join(preview_lines).strip()
        if len(preview) > 60:
            preview = preview[:60] + "..."
        spans.append(DuplicateSpan(a_start=a_s + 1, a_end=a_e + 1,
                                   b_start=b_s + 1, b_end=b_e + 1,
                                   preview=preview))
    return spans


def _read_md_lines(path: Path) -> List[str]:
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read().splitlines()


def detect_duplicates(
    src_dir: str,
    k: int = 5,
    confirm_threshold: float = 0.8,
    suspect_threshold: float = 0.5,
    output_path: str | None = None,
) -> List[DuplicationResult]:
    """主入口：扫描 src_dir 下全部 MD，输出重复报告。对原文档库只读。"""
    if k < 1:
        raise ValueError("k 必须 >= 1")
    if not (0 < suspect_threshold < confirm_threshold <= 1):
        raise ValueError("需满足 0 < suspect_threshold < confirm_threshold <= 1")

    src = Path(src_dir)
    md_files = sorted([p for p in src.rglob("*.md")
                       if "精简" not in p.parts])
    results: List[DuplicationResult] = []

    docs: List[Tuple[str, List[str], FrozenSet[Shingle]]] = []
    for p in md_files:
        lines = _read_md_lines(p)
        sh = generate_shingles(lines, k)
        docs.append((p.name, lines, sh))

    for i in range(len(docs)):
        for j in range(i + 1, len(docs)):
            na, la, sa = docs[i]
            nb, lb, sb = docs[j]
            if not sa or not sb:
                continue
            sim = jaccard_similarity(sa, sb)
            if sim < suspect_threshold:
                continue
            if sim >= confirm_threshold:
                status = "CONFIRMED"
            else:
                status = "SUSPECT（待人工确认）"
            shared = set(sa & sb)
            spans = locate_duplicate_spans(la, lb, k, shared)
            dup_lines = sum(s.a_end - s.a_start + 1 for s in spans)
            results.append(DuplicationResult(
                path_a=na, path_b=nb, jaccard=round(sim, 3),
                status=status, dup_lines=dup_lines, spans=spans,
            ))

    results.sort(key=lambda r: r.jaccard, reverse=True)

    if output_path:
        _write_report(results, output_path, k, confirm_threshold, suspect_threshold)
    return results


def _write_report(
    results: List[DuplicationResult],
    output_path: str,
    k: int,
    confirm_threshold: float,
    suspect_threshold: float,
) -> None:
    lines: List[str] = []
    lines.append("# 重复检测报告（方案 D）")
    lines.append("")
    lines.append(f"> 检测方法：行级 shingling（k={k}）")
    lines.append(f"> 确认阈值：{confirm_threshold}（≥ 该值标记 CONFIRMED）")
    lines.append(f"> 疑似阈值：{suspect_threshold}（介于两阈值之间标记 SUSPECT，待人工确认）")
    lines.append(f"> 检测文档对数：{len(results)}（仅列出相似度 ≥ 疑似阈值的对）")
    lines.append("")
    lines.append("---")
    lines.append("")
    if not results:
        lines.append("未检测到重复段落。")
    for idx, r in enumerate(results, 1):
        lines.append(f"## {idx}. {r.path_a}  ⟷  {r.path_b}")
        lines.append("")
        lines.append(f"- **Jaccard 相似度**：{r.jaccard}")
        lines.append(f"- **状态**：{r.status}")
        lines.append(f"- **重复行数**：{r.dup_lines}")
        lines.append(f"- **重复片段定位**：")
        lines.append("")
        if r.spans:
            lines.append("| A 行号 | B 行号 | 片段预览 |")
            lines.append("|--------|--------|----------|")
            for s in r.spans:
                lines.append(f"| {s.a_start}-{s.a_end} | {s.b_start}-{s.b_end} | {s.preview} |")
        else:
            lines.append("（无连续片段）")
        lines.append("")
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main() -> int:
    ap = argparse.ArgumentParser(description="行级 shingling 重复检测（方案 D）")
    ap.add_argument("src_dir", help="待扫描的 MD 根目录")
    ap.add_argument("--k", type=int, default=5, help="shingle 窗口大小（默认 5）")
    ap.add_argument("--confirm", type=float, default=0.8, help="确认阈值（默认 0.8）")
    ap.add_argument("--suspect", type=float, default=0.5, help="疑似阈值（默认 0.5）")
    ap.add_argument("--out", default=None, help="报告输出路径")
    args = ap.parse_args()

    out = args.out or os.path.join(args.src_dir, "精简", "_工具", "重复报告.md")
    t0 = time.time()
    results = detect_duplicates(args.src_dir, args.k, args.confirm, args.suspect, out)
    dt = time.time() - t0
    confirmed = sum(1 for r in results if r.status == "CONFIRMED")
    suspect = len(results) - confirmed
    print(f"检测完成：共 {len(results)} 对（CONFIRMED {confirmed} / SUSPECT {suspect}），耗时 {dt:.2f}s")
    print(f"报告已写入：{out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())