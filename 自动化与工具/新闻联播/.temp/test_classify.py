# -*- coding: utf-8 -*-
import sys, os, json
sys.path.insert(0, r"C:\Users\Administrator\Documents\这是什么\JK-temp\自动化与工具\新闻联播\流程\最新版本\代码")
from gen_report_final import generate_part67

items = [
    {"idx": "1", "title": "测试1", "url": "https://tv.cctv.com/a.shtml", "category": "国际新闻",
     "elements": {"time": "2026-10-06", "location": "纽约", "subject": "联合国秘书长古特雷斯",
                  "event": "呼吁停火", "cause": "缓解人道危机", "method": "公开呼吁"}},
    {"idx": "2", "title": "测试2", "url": "https://tv.cctv.com/b.shtml", "category": "国内",
     "elements": {"time": "2026-10-06", "location": "北京", "subject": "中共中央总书记、国家主席、中央军委主席习近平",
                  "event": "出席会议", "cause": "部署工作", "method": "主持会议"}},
    {"idx": "3", "title": "测试3", "url": "https://tv.cctv.com/c.shtml", "category": "国内",
     "elements": {"time": "2026-10-06", "location": "全国", "subject": "交通运输部",
                  "event": "发布数据", "cause": "保障出行", "method": "统计发布"}},
    {"idx": "4", "title": "测试4", "url": "https://tv.cctv.com/d.shtml", "category": "国际新闻",
     "elements": {"time": "2026-10-06", "location": "俄罗斯", "subject": "俄罗斯外交部发言人扎哈罗娃",
                  "event": "发表评论", "cause": "回应制裁", "method": "公开表态"}},
    {"idx": "5", "title": "测试5", "url": "https://tv.cctv.com/e.shtml", "category": "国际新闻",
     "elements": {"time": "2026-10-06", "location": "也门", "subject": "也门冲突双方",
                  "event": "交火持续", "cause": "—", "method": "军事行动"}},
    {"idx": "6", "title": "测试6", "url": "https://tv.cctv.com/f.shtml", "category": "社会",
     "elements": {"time": "2026-10-06", "location": "天津", "subject": "南开大学图书馆",
                  "event": "专题展览", "cause": "传承文化", "method": "办展"}},
    {"idx": "7", "title": "测试7", "url": "https://tv.cctv.com/g.shtml", "category": "国际新闻",
     "elements": {"time": "2026-10-06", "location": "开罗", "subject": "埃及总统塞西",
                  "event": "会晤代表", "cause": "协调立场", "method": "举行会晤"}},
    {"idx": "8", "title": "国内联播快讯", "url": "https://tv.cctv.com/h.shtml", "category": "快讯目录",
     "is_placeholder": True, "elements": {"location": "—", "subject": "—", "event": "播报国内联播快讯", "cause": "—", "method": "目录播报"}},
]
out = generate_part67(items, "2026年10月06日", "20261006")
for line in out.split("\n"):
    if line.startswith("|") and "序号" not in line and "----" not in line:
        print(line)
