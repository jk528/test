# -*- coding: utf-8 -*-
import io, os, re, glob

XYJ = r"C:\Users\Administrator\Documents\这是什么\JK-temp\输入法相关\.temp\xyj_baimiao"
OUT = r"C:\Users\Administrator\Documents\这是什么\JK-temp\输入法相关\.temp\_check_xyj.txt"

FRAMEWORK = {
    "结果先行","动作承载","物件承载","数字对比","引语承载","名词列锦",
    "事实并置","特写","预叙","重复升级","第三拍转向","回声照应","蒙太奇并置",
    "长短句换挡","独句落点","情绪延迟","引语留白",
    "显示而非讲述","叙述距离","轻描归因","陌生化","反讽与距离",
    "动作收尾","条件收尾","问题收尾",
}

L = []
all_files = sorted(glob.glob(os.path.join(XYJ, "*.md")))
grand_missing = 0
for p in all_files:
    s = io.open(p, encoding="utf-8", newline="").read()
    name = os.path.basename(p)
    # 违规检查
    bad_h2 = re.findall(r"(?m)^##\s+\S.*$", s)
    bad_grp = re.findall(r"(?m)^#{1,4}\s*第[一二三四五六七八九十百\d]+批.*$", s)
    bad_title = re.findall(r"(?m)^#\s+\S.*$", s)
    heads = re.findall(r"(?m)^###\s*第\s*(\d+)\s*回[　 ].*$", s)
    nums = [int(x) for x in heads]
    L.append("--- %s  回数=%d  回号=%s" % (name, len(nums), nums))
    if bad_h2:    L.append("    !! 出现 ## 级标题: %s" % bad_h2[:2])
    if bad_grp:   L.append("    !! 出现分组标题: %s" % bad_grp[:2])
    if bad_title: L.append("    !! 出现文件总标题: %s" % bad_title[:2])
    if nums != sorted(nums):
        L.append("    !! 回号非升序")

    blocks = re.split(r"(?m)(?=^###\s*第)", s)
    for b in blocks:
        m = re.match(r"###\s*第\s*(\d+)\s*回", b)
        if not m:
            continue
        n = int(m.group(1))
        frags = re.findall(r"(?m)^(\d+)\.\s+\*\*([^*]+?)\*\*", b)
        fnames = []
        for _, f in frags:
            for part in re.split(r"[/／]", f):
                core = re.sub(r"（[^）]*）", "", part).strip()
                if core:
                    fnames.append(core)
                for mm in re.findall(r"（([^）]+)）", part):
                    fnames.append(mm.strip())
        mh = re.search(r"(?m)^\*\*本回命中\*\*[:：]?\s*(.+?)\s*$", b)
        hits = []
        if mh:
            hits = [x.strip() for x in re.split(r"[、,，;；]", mh.group(1)) if x.strip()]
        miss = [h for h in hits if h not in fnames]
        extra = [f for f in set(fnames) if f not in hits]
        unknown = [h for h in hits if h not in FRAMEWORK]
        seq  = [int(i) for i, _ in frags]
        seq_ok = seq == list(range(1, len(seq) + 1))
        flag = []
        if miss:    flag.append("缺片段:%s" % miss)
        if extra:   flag.append("越界:%s" % extra)
        if unknown: flag.append("非框架手法:%s" % unknown)
        if not seq_ok: flag.append("编号不连续:%s" % seq)
        if not mh:  flag.append("无命中行")
        L.append("   第%-4d回 片段=%-3d(条) 命中=%-3d  %s" % (n, len(frags), len(hits), "OK" if not flag else " | ".join(flag)))
        if miss:
            grand_missing += 1

L.append("=" * 50)
L.append("存在缺片段的回数 = %d" % grand_missing)
io.open(OUT, "w", encoding="utf-8", newline="").write("\n".join(L))
print("OK")
