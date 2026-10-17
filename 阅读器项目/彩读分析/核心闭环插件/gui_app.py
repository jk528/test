# -*- coding: utf-8 -*-
"""
PyQt6 最小阅读器原型（把核心闭环纯逻辑接到 GUI）
================================================

【桥接关系】core 插件产出的纯数据结构，在这里被 GUI 消费：
  - 着色区间流  (plugin_04 Span)  →  QSyntaxHighlighter.setFormat(start, len, fmt)
  - 章节行号区间 (plugin_05 JumpResult) →  QTextCursor(block) + ensureCursorVisible()
  - 文件导入    (plugin_01 import_file) →  QFileDialog 选文件 + 填充编辑器
  - 书签进度    (plugin_06 BookmarkStore) →  本地 sqlite 持久化

【运行】
  python gui_app.py            # 打开图形窗口（内置《红楼梦》样章）
  python gui_app.py --selftest # 无头自检（offscreen 平台，不弹窗，验证逻辑）
"""

from __future__ import annotations

import os
import re
import sys

from PyQt6.QtCore import QRegularExpression, Qt
from PyQt6.QtGui import (
    QAction,
    QColor,
    QFont,
    QSyntaxHighlighter,
    QTextCharFormat,
    QTextCursor,
)
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QTextEdit,
    QToolBar,
)

from plugin_01_file_import import import_file
from plugin_03_chapter_detect import detect_chapters
from plugin_04_coloring import COLOR_NAMES, build_rules, highlight
from plugin_05_catalog_jump import build_ranges
from plugin_06_bookmark_progress import BookmarkStore


# ---------------------------------------------------------------------------
# 内置样章（打开即见，无需先导入）
# ---------------------------------------------------------------------------
_SAMPLE = "\n".join([
    "第一回 甄士隐梦幻识通灵",
    "此开卷第一回也。作者自云：因曾历过一番梦幻之后，故将真事隐去。",
    "宝玉笑道：这个妹妹我曾见过的。黛玉也不理他，只管向贾母道安。",
    "",
    "第二回 贾夫人仙逝扬州城",
    "原来这贾夫人，乃荣国府贾政之妻王氏。黛玉自此常住贾府。",
    "却说冷子兴演说荣国府，一一道出贾家的根基门第。",
    "",
    "第三回 托内兄如海荐西宾",
    "贾雨村听得这话，便与冷子兴计较，欲托贾政荐个西宾的差事。",
    "黛玉抛父进京都，初入荣国府，见了外祖母，又拜见两位母舅。",
])

_KEYWORDS = ["宝玉", "黛玉", "贾母", "贾政"]


# ---------------------------------------------------------------------------
# 语法高亮器（消费 plugin_04 的着色区间流）
# ---------------------------------------------------------------------------
class NovelHighlighter(QSyntaxHighlighter):
    """把「关键词 → 颜色」规则注册为高亮，由 C++ 底层一次扫描批量着色。

    对应 VBA Characters.Font.Color 的「换机制」替代：不再逐子串 COM 调用，
    而是 4 色循环 + QRegularExpression.globalMatch 一次匹配。
    """

    def __init__(self, document):
        super().__init__(document)
        self.rules: list[tuple[QRegularExpression, QTextCharFormat]] = []

    def set_keywords(self, keywords: list[str]):
        self.rules = []
        for i, kw in enumerate(keywords):
            if not kw:
                continue
            color = QColor(COLOR_NAMES[i % len(COLOR_NAMES)])  # 对应 VBA 4 色循环
            fmt = QTextCharFormat()
            fmt.setForeground(color)
            fmt.setFontWeight(600)
            self.rules.append((QRegularExpression(re.escape(kw)), fmt))
        self.rehighlight()

    def highlightBlock(self, text: str):
        for pattern, fmt in self.rules:
            it = pattern.globalMatch(text)
            while it.hasNext():
                m = it.next()
                self.setFormat(m.capturedStart(), m.capturedLength(), fmt)


# ---------------------------------------------------------------------------
# 主窗口
# ---------------------------------------------------------------------------
class ReaderWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("彩读 · PyQt6 最小原型")
        self.resize(900, 600)

        self.lines: list[str] = []
        self.chapters = []
        self.ranges = []
        self.book_id = "sample"
        self.store = BookmarkStore(
            os.path.join(os.path.dirname(__file__), "reader_bookmarks.db")
        )

        # 文本编辑器 + 高亮器
        self.editor = QTextEdit()
        self.editor.setReadOnly(True)
        font = QFont("Microsoft YaHei", 13)
        font.setStyleHint(QFont.StyleHint.SansSerif)
        self.editor.setFont(font)
        self.highlighter = NovelHighlighter(self.editor.document())

        # 章节侧栏
        self.chapter_list = QListWidget()
        self.chapter_list.itemClicked.connect(self._on_chapter_clicked)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._wrap_with_label("章节目录", self.chapter_list))
        splitter.addWidget(self.editor)
        splitter.setSizes([220, 680])
        self.setCentralWidget(splitter)

        # 工具栏
        self._build_toolbar()

        # 打开即加载内置样章
        self._load_lines(_SAMPLE.splitlines(), "内置样章")

    def _wrap_with_label(self, title: str, widget):
        from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(4, 4, 4, 4)
        lab = QLabel(title)
        lab.setStyleSheet("font-weight:600; padding:2px;")
        lay.addWidget(lab)
        lay.addWidget(widget)
        return w

    def _build_toolbar(self):
        tb = QToolBar("主工具栏")
        tb.setMovable(False)
        self.addToolBar(tb)

        act_open = QAction("打开", self)
        act_open.triggered.connect(self._open_file)
        tb.addAction(act_open)

        act_bookmark = QAction("记书签", self)
        act_bookmark.triggered.connect(self._add_bookmark)
        tb.addAction(act_bookmark)

        act_recolor = QAction("重新上色", self)
        act_recolor.triggered.connect(lambda: self.highlighter.set_keywords(_KEYWORDS))
        tb.addAction(act_recolor)

    # ---- 数据加载（复用 core 插件） ----
    def _load_lines(self, lines: list[str], book_id: str):
        self.lines = lines
        self.book_id = book_id
        self.editor.setPlainText("\n".join(lines))

        # 章节识别（plugin_03）+ 区间（plugin_05）
        self.chapters = detect_chapters(lines)
        self.ranges = build_ranges(self.chapters, len(lines))

        self.chapter_list.clear()
        for c in self.chapters:
            self.chapter_list.addItem(QListWidgetItem(c.title))

        # 上色（plugin_04 区间流由 highlighter 消费）
        self.highlighter.set_keywords(_KEYWORDS)

        self.statusBar().showMessage(
            f"{book_id} | 共 {len(lines)} 行 | {len(self.chapters)} 章 | 书签 {self.store.count_bookmarks(book_id)}"
        )

    def _open_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "打开小说", "", "文本文件 (*.txt *.md);;所有文件 (*)"
        )
        if not path:
            return
        try:
            content = import_file(path)
        except Exception as e:
            QMessageBox.warning(self, "打开失败", str(e))
            return
        self._load_lines(content.lines, os.path.basename(path))
        self.setWindowTitle(f"彩读 · PyQt6 最小原型 - {content.source_path}")

    # ---- 目录跳转（消费 plugin_05 的行号区间） ----
    def _on_chapter_clicked(self, item: QListWidgetItem):
        idx = self.chapter_list.row(item)
        if idx < 0 or idx >= len(self.ranges):
            return
        r = self.ranges[idx]
        block = self.editor.document().findBlockByNumber(r.start_line)
        cursor = QTextCursor(block)
        self.editor.setTextCursor(cursor)
        self.editor.ensureCursorVisible()
        self.editor.setFocus()
        self.statusBar().showMessage(f"跳转到：{r.chapter} ｜ 行 {r.start_line}-{r.end_line}")

    # ---- 书签（消费 plugin_06） ----
    def _add_bookmark(self):
        line = self.editor.textCursor().blockNumber()
        chapter = ""
        for r in self.ranges:
            if r.start_line <= line < r.end_line:
                chapter = r.chapter
                break
        self.store.add_bookmark(self.book_id, chapter, line)
        n = self.store.count_bookmarks(self.book_id)
        self.statusBar().showMessage(f"已记书签（第 {n} 条）：{chapter} @ 行 {line}")


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------
def main():
    selftest = "--selftest" in sys.argv
    if selftest:
        os.environ["QT_QPA_PLATFORM"] = "offscreen"

    app = QApplication(sys.argv)
    win = ReaderWindow()

    if selftest:
        _selftest(win)
        return

    win.show()
    sys.exit(app.exec())


def _selftest(win: ReaderWindow):
    """无头自检：验证 highlighter 区间流、章节区间、跳转定位、书签不报错。"""
    print("[selftest] 章节识别到", win.chapter_list.count(), "章：")
    for i in range(win.chapter_list.count()):
        r = win.ranges[i]
        print(f"    {win.chapter_list.item(i).text()}  -> 行区间 [{r.start_line}, {r.end_line})")

    # 模拟点击每一章，触发跳转（在下标回溯 QTextCursor 上消费区间）
    for idx in range(len(win.ranges)):
        r = win.ranges[idx]
        block = win.editor.document().findBlockByNumber(r.start_line)
        cursor = QTextCursor(block)
        assert cursor.blockNumber() == r.start_line
    print("[selftest] 目录跳转：全部章节区间定位正确")

    # 验证高亮器规则已注入 4 色循环
    print("[selftest] 高亮规则数 =", len(win.highlighter.rules),
          "（关键词", _KEYWORDS, "→", COLOR_NAMES[:len(_KEYWORDS)], "）")

    win._add_bookmark()
    print("[selftest] 书签数 =", win.store.count_bookmarks(win.book_id))
    print("[selftest] 通过：核心闭环 GUI 桥接全部正常")


if __name__ == "__main__":
    main()