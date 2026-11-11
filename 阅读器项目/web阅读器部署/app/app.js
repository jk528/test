/* 微阅读 · 零依赖网页阅读器
 * 数据：/data/library.json + /data/<book>/toc.json + /data/<book>/vol-N.json
 * 本地存储：rw.settings / rw.progress / rw.annotations / rw.lastBook
 */
(function () {
  'use strict';

  const BASE = location.pathname.replace(/\/[^/]*$/, '/');
  const LS = {
    settings: 'rw.settings',
    progress: 'rw.progress',
    annotations: 'rw.annotations',
    lastBook: 'rw.lastBook',
  };
  const DEFAULT_SETTINGS = { fontSize: 18, weight: 400, leading: 1.85, theme: 'paper' };

  const $ = (id) => document.getElementById(id);
  const el = {
    shelf: $('shelf'), reader: $('reader'), grid: $('book-grid'), count: $('shelf-count'),
    continueCard: $('continue-card'), continueTitle: $('continue-title'),
    continueSub: $('continue-sub'), continueBar: $('continue-bar'), continueBtn: $('continue-btn'),
    backBtn: $('back-btn'), tocBtn: $('toc-btn'), setBtn: $('set-btn'),
    content: $('content'), article: $('article'),
    bookName: $('book-name'), chapterName: $('chapter-name'),
    prevBtn: $('prev-btn'), nextBtn: $('next-btn'),
    chapterProgress: $('chapter-progress'), readBar: $('read-bar'), readPercent: $('read-percent'),
    drawer: $('drawer'), mask: $('mask'), tocList: $('toc-list'), markList: $('mark-list'),
    markCount: $('mark-count'), drawerClose: $('drawer-close'),
    settings: $('settings'), fontLabel: $('font-size-label'),
    fontMinus: $('font-minus'), fontPlus: $('font-plus'),
    weightSeg: $('weight-seg'), leadingSeg: $('leading-seg'), themeSeg: $('theme-seg'),
    selectBar: $('select-bar'), markBtn: $('mark-btn'), copyBtn: $('copy-btn'), toast: $('toast'),
  };

  const state = {
    library: [],
    book: null,
    toc: [],
    chapter: 0,
    volumes: new Map(),
    settings: readLS(LS.settings, DEFAULT_SETTINGS),
    progress: readLS(LS.progress, {}),
    annotations: readLS(LS.annotations, []),
    pendingSelection: '',
    saveTimer: 0,
    toastTimer: 0,
  };

  function readLS(key, fallback) {
    try {
      const raw = localStorage.getItem(key);
      return raw ? { ...fallback, ...JSON.parse(raw) } : fallback;
    } catch (e) { return fallback; }
  }
  function readLSArray(key) {
    try { return JSON.parse(localStorage.getItem(key) || '[]'); } catch (e) { return []; }
  }
  function writeLS(key, value) {
    try { localStorage.setItem(key, JSON.stringify(value)); } catch (e) { /* 隐私模式下忽略 */ }
  }

  function toast(text) {
    el.toast.textContent = text;
    el.toast.classList.remove('hidden');
    clearTimeout(state.toastTimer);
    state.toastTimer = setTimeout(() => el.toast.classList.add('hidden'), 1800);
  }

  function progressOf(bookId) {
    return state.progress[bookId] || null;
  }
  function bookPercent(bookId) {
    const p = progressOf(bookId);
    if (!p) return 0;
    const total = (state.library.find((b) => b.id === bookId) || {}).total || 1;
    return Math.min(1, (p.chapter + (p.ratio || 0)) / total);
  }

  /* ---------------- 设置 ---------------- */
  function applySettings() {
    const s = state.settings;
    const root = document.documentElement;
    root.style.setProperty('--font-size', s.fontSize + 'px');
    root.style.setProperty('--weight', String(s.weight));
    root.style.setProperty('--leading', String(s.leading));
    root.dataset.theme = s.theme;

    el.fontLabel.textContent = s.fontSize;
    el.weightSeg.querySelectorAll('button').forEach((b) => {
      b.classList.toggle('active', Number(b.dataset.weight) === s.weight);
    });
    el.leadingSeg.querySelectorAll('button').forEach((b) => {
      b.classList.toggle('active', Number(b.dataset.leading) === s.leading);
    });
    el.themeSeg.querySelectorAll('button').forEach((b) => {
      b.classList.toggle('active', b.dataset.theme === s.theme);
    });
  }

  el.fontMinus.addEventListener('click', () => {
    state.settings.fontSize = Math.max(14, state.settings.fontSize - 1);
    applySettings(); writeLS(LS.settings, state.settings);
  });
  el.fontPlus.addEventListener('click', () => {
    state.settings.fontSize = Math.min(30, state.settings.fontSize + 1);
    applySettings(); writeLS(LS.settings, state.settings);
  });
  el.weightSeg.addEventListener('click', (e) => {
    const btn = e.target.closest('button');
    if (!btn) return;
    state.settings.weight = Number(btn.dataset.weight);
    applySettings(); writeLS(LS.settings, state.settings);
  });
  el.leadingSeg.addEventListener('click', (e) => {
    const btn = e.target.closest('button');
    if (!btn) return;
    state.settings.leading = Number(btn.dataset.leading);
    applySettings(); writeLS(LS.settings, state.settings);
  });
  el.themeSeg.addEventListener('click', (e) => {
    const btn = e.target.closest('button');
    if (!btn) return;
    state.settings.theme = btn.dataset.theme;
    applySettings(); writeLS(LS.settings, state.settings);
  });

  /* ---------------- 书架 ---------------- */
  async function loadLibrary() {
    const res = await fetch(BASE + 'data/library.json', { cache: 'no-store' });
    if (!res.ok) throw new Error('library.json ' + res.status);
    const lib = await res.json();
    state.library = lib.books || [];
    renderShelf();
  }

  function renderShelf() {
    el.count.textContent = state.library.length + ' 本';
    el.grid.innerHTML = '';

    state.library.forEach((book) => {
      const card = document.createElement('div');
      card.className = 'book';
      const pct = Math.round(bookPercent(book.id) * 100);
      card.innerHTML =
        '<div class="cover" style="background:linear-gradient(155deg,' + book.cover.from + ',' + book.cover.to + ')">' +
          '<div class="cover-title">' + esc(book.title) + '</div>' +
          '<div class="cover-author">' + esc(book.author) + '</div>' +
        '</div>' +
        '<div class="meta">' +
          '<strong>' + esc(book.title) + '</strong>' +
          '<span>' + esc(book.author) + ' · ' + book.total + ' 回</span>' +
          '<div class="bar"><i style="width:' + pct + '%"></i></div>' +
        '</div>';
      card.addEventListener('click', () => openBook(book.id));
      el.grid.appendChild(card);
    });

    // 继续阅读
    let latest = null;
    state.library.forEach((b) => {
      const p = progressOf(b.id);
      if (p && (!latest || p.ts > latest.ts)) latest = { book: b, ...p };
    });
    if (!latest) {
      el.continueCard.classList.add('hidden');
    } else {
      const pct = Math.round(bookPercent(latest.id) * 1000) / 10;
      el.continueCard.classList.remove('hidden');
      el.continueTitle.textContent = latest.book.title;
      el.continueSub.textContent = '读到 ' + (latest.chapter + 1) + ' / ' + latest.book.total + ' 回 · ' + pct + '%';
      el.continueBar.style.width = pct + '%';
      el.continueBtn.onclick = () => openBook(latest.id, latest.chapter, latest.ratio);
    }
  }

  /* ---------------- 打开书籍 ---------------- */
  async function openBook(bookId, chapter, ratio) {
    const book = state.library.find((b) => b.id === bookId);
    if (!book) return;
    state.book = book;
    state.volumes.clear();

    el.bookName.textContent = book.title;
    try {
      const res = await fetch(BASE + 'data/' + book.id + '/toc.json', { cache: 'force-cache' });
      if (!res.ok) throw new Error('toc ' + res.status);
      state.toc = await res.json();
    } catch (err) {
      toast('目录加载失败：' + err.message);
      return;
    }

    el.shelf.classList.remove('active');
    el.reader.classList.add('active');
    if (typeof chapter === 'number') {
      await renderChapter(chapter, ratio);
    } else {
      const p = progressOf(book.id);
      await renderChapter(p ? p.chapter : 0, p ? p.ratio : 0);
    }
    location.hash = '#/read/' + book.id + '/' + state.chapter;
  }

  function showShelf() {
    saveProgress();
    el.reader.classList.remove('active');
    el.shelf.classList.add('active');
    closePanels();
    history.replaceState(null, '', location.pathname);
    renderShelf();
  }

  async function ensureVolume(volIndex) {
    if (state.volumes.has(volIndex)) return state.volumes.get(volIndex);
    const res = await fetch(BASE + 'data/' + state.book.id + '/vol-' + volIndex + '.json', { cache: 'force-cache' });
    if (!res.ok) throw new Error('vol ' + volIndex + ' ' + res.status);
    const data = await res.json();
    state.volumes.set(volIndex, data);
    return data;
  }

  async function renderChapter(index, ratio) {
    const book = state.book;
    if (!book) return;
    index = Math.max(0, Math.min(book.total - 1, index));
    const per = book.perVolume || 20;
    const volIndex = Math.floor(index / per);

    let chapterData;
    try {
      const vol = await ensureVolume(volIndex);
      chapterData = vol[index - volIndex * per];
    } catch (err) {
      toast('正文加载失败：' + err.message);
      return;
    }
    if (!chapterData) { toast('章节不存在'); return; }

    const prevScroll = saveProgress(true);
    const keepRatio = typeof ratio === 'number' ? ratio : (index === state.chapter ? prevScroll : 0);

    state.chapter = index;
    el.chapterName.textContent = chapterData.title;

    const html = ['<h1>' + esc(chapterData.title) + '</h1>'];
    chapterData.paragraphs.forEach((p) => {
      const cls = /^(——|·|-|＊|\*)/.test(p) ? ' class="no-indent"' : '';
      html.push('<p' + cls + '>' + esc(p) + '</p>');
    });
    el.article.innerHTML = html.join('');
    applyHighlights();
    updateProgressBar();
    renderToc();

    const max = Math.max(1, el.content.scrollHeight - el.content.clientHeight);
    el.content.scrollTop = Math.max(0, Math.min(1, keepRatio || 0)) * max;
    el.prevBtn.disabled = index === 0;
    el.nextBtn.disabled = index === book.total - 1;
    location.hash = '#/read/' + book.id + '/' + index;
  }

  function updateProgressBar() {
    const book = state.book;
    const total = book.total;
    const ratio = currentScrollRatio();
    const pct = ((state.chapter + ratio) / total) * 100;
    el.chapterProgress.textContent = '第 ' + (state.chapter + 1) + ' / ' + total + ' 章';
    el.readPercent.textContent = pct.toFixed(1) + '%';
    el.readBar.style.width = Math.min(100, pct) + '%';
  }

  function currentScrollRatio() {
    const max = el.content.scrollHeight - el.content.clientHeight;
    return max > 8 ? Math.max(0, Math.min(1, el.content.scrollTop / max)) : 0;
  }

  function saveProgress(silent) {
    if (!state.book) return 0;
    const ratio = currentScrollRatio();
    const id = state.book.id;
    state.progress[id] = { chapter: state.chapter, ratio: ratio, ts: Date.now() };
    writeLS(LS.progress, state.progress);
    writeLS(LS.lastBook, id);
    if (!silent) updateProgressBar();
    return ratio;
  }

  function scheduleSave() {
    clearTimeout(state.saveTimer);
    state.saveTimer = setTimeout(() => saveProgress(true), 400);
  }

  /* ---------------- 目录 / 划线 ---------------- */
  function renderToc() {
    if (!state.book) return;
    const per = state.book.perVolume || 20;
    const read = progressOf(state.book.id);
    const frag = document.createDocumentFragment();
    state.toc.forEach((ch, i) => {
      if (i % per === 0) {
        const label = document.createElement('div');
        label.className = 'toc-vol';
        label.textContent = '第 ' + (i + 1) + '–' + Math.min(i + per, state.toc.length) + ' 回';
        frag.appendChild(label);
      }
      const btn = document.createElement('button');
      btn.className = 'toc-item';
      if (i === state.chapter) btn.classList.add('current');
      if (read && i < read.chapter) btn.classList.add('read');
      btn.innerHTML = '<span>' + esc(ch.title) + '</span>';
      btn.onclick = () => { closePanels(); renderChapter(i, 0); };
      frag.appendChild(btn);
    });
    el.tocList.innerHTML = '';
    el.tocList.appendChild(frag);
  }

  function renderMarks() {
    if (!state.book) return;
    const list = state.annotations
      .filter((a) => a.book === state.book.id)
      .sort((a, b) => b.ts - a.ts);
    el.markCount.textContent = String(list.length);
    el.markList.innerHTML = '';

    if (!list.length) {
      el.markList.innerHTML = '<p class="mark-empty">还没有划线。<br>在正文中选中文字后点「划线」。</p>';
      return;
    }
    list.forEach((a) => {
      const card = document.createElement('div');
      card.className = 'mark-card';
      card.innerHTML =
        '<p>' + esc(a.text) + '</p>' +
        '<div class="mark-actions">' +
          '<small>第 ' + (a.chapter + 1) + ' 章</small>' +
          '<span>' +
            '<button data-act="go">跳转</button>' +
            '<button data-act="del">删除</button>' +
          '</span>' +
        '</div>';
      card.querySelector('[data-act="go"]').onclick = async () => {
        closePanels();
        await renderChapter(a.chapter, 0);
        const node = el.article.querySelector('mark[data-id="' + a.id + '"]');
        if (node) node.scrollIntoView({ block: 'center' });
      };
      card.querySelector('[data-act="del"]').onclick = () => removeAnnotation(a.id);
      el.markList.appendChild(card);
    });
  }

  function openDrawer(tab) {
    el.drawer.classList.add('open');
    el.mask.classList.add('show');
    el.settings.classList.remove('open');
    switchTab(tab || 'toc');
    renderMarks();
  }

  function switchTab(tab) {
    el.drawer.querySelectorAll('.tab').forEach((t) => {
      t.classList.toggle('active', t.dataset.tab === tab);
    });
    el.tocList.classList.toggle('hidden', tab !== 'toc');
    el.markList.classList.toggle('hidden', tab !== 'marks');
  }

  el.drawer.querySelectorAll('.tab').forEach((t) => {
    t.addEventListener('click', () => switchTab(t.dataset.tab));
  });

  function closePanels() {
    el.drawer.classList.remove('open');
    el.settings.classList.remove('open');
    el.mask.classList.remove('show');
    el.selectBar.classList.add('hidden');
  }

  /* ---------------- 划线 ---------------- */
  function applyHighlights() {
    if (!state.book) return;
    const list = state.annotations.filter(
      (a) => a.book === state.book.id && a.chapter === state.chapter
    );
    list.forEach((a) => wrapFirst(a.text, a.id));
  }

  function wrapFirst(text, id) {
    if (!text) return;
    const walker = document.createTreeWalker(el.article, NodeFilter.SHOW_TEXT, {
      acceptNode(node) {
        if (!node.nodeValue.trim()) return NodeFilter.FILTER_REJECT;
        if (node.parentElement.closest('mark')) return NodeFilter.FILTER_REJECT;
        return NodeFilter.FILTER_ACCEPT;
      },
    });
    while (walker.nextNode()) {
      const node = walker.currentNode;
      const idx = node.nodeValue.indexOf(text);
      if (idx === -1) continue;
      const range = document.createRange();
      range.setStart(node, idx);
      range.setEnd(node, idx + text.length);
      const mark = document.createElement('mark');
      mark.className = 'hl';
      mark.dataset.id = id;
      try {
        range.surroundContents(mark);
      } catch (e) { return; }
      return;
    }
  }

  function addAnnotation(text) {
    const clean = text.replace(/\s+/g, ' ').trim();
    if (clean.length < 1) return;
    const dup = state.annotations.some(
      (a) => a.book === state.book.id && a.chapter === state.chapter && a.text === clean
    );
    if (dup) { toast('这句已经划过了'); return; }
    state.annotations.push({
      id: 'a' + Date.now().toString(36) + Math.random().toString(36).slice(2, 6),
      book: state.book.id,
      chapter: state.chapter,
      text: clean,
      ts: Date.now(),
    });
    writeLS(LS.annotations, state.annotations);
    el.article.innerHTML = el.article.innerHTML;
    applyHighlights();
    renderMarks();
    toast('已划线');
  }

  function removeAnnotation(id) {
    state.annotations = state.annotations.filter((a) => a.id !== id);
    writeLS(LS.annotations, state.annotations);
    el.article.querySelectorAll('mark[data-id="' + id + '"]').forEach((m) => {
      const parent = m.parentNode;
      while (m.firstChild) parent.insertBefore(m.firstChild, m);
      parent.removeChild(m);
    });
    renderMarks();
    toast('已删除划线');
  }

  /* ---------------- 选区操作 ---------------- */
  function hideSelectBar() {
    el.selectBar.classList.add('hidden');
  }

  function handleSelection() {
    const sel = window.getSelection();
    if (!sel || sel.isCollapsed) { hideSelectBar(); return; }
    const text = sel.toString();
    if (!text.trim()) { hideSelectBar(); return; }
    const range = sel.getRangeAt(0);
    if (!el.article.contains(range.commonAncestorContainer)) { hideSelectBar(); return; }

    state.pendingSelection = text;
    const rect = range.getBoundingClientRect();
    const barW = 150;
    const left = Math.max(10, Math.min(window.innerWidth - barW - 10, rect.left + rect.width / 2 - barW / 2));
    const top = rect.top > 64 ? rect.top - 48 : rect.bottom + 12;
    el.selectBar.style.left = left + 'px';
    el.selectBar.style.top = top + 'px';
    el.selectBar.classList.remove('hidden');
  }

  el.markBtn.addEventListener('click', () => {
    addAnnotation(state.pendingSelection);
    hideSelectBar();
    window.getSelection().removeAllRanges();
  });

  el.copyBtn.addEventListener('click', async () => {
    try { await navigator.clipboard.writeText(state.pendingSelection); toast('已复制'); }
    catch (e) { toast('复制失败，请手动选择'); }
    hideSelectBar();
  });

  el.article.addEventListener('click', (e) => {
    const mark = e.target.closest('mark.hl');
    if (mark) {
      if (confirm('删除这条划线？')) removeAnnotation(mark.dataset.id);
      return;
    }
    if (window.getSelection().toString()) return;
    el.reader.classList.toggle('chrome-hidden');
    closePanels();
  });

  /* ---------------- 事件绑定 ---------------- */
  el.backBtn.addEventListener('click', showShelf);
  el.tocBtn.addEventListener('click', () => openDrawer('toc'));
  el.setBtn.addEventListener('click', () => {
    const open = el.settings.classList.toggle('open');
    el.drawer.classList.remove('open');
    el.mask.classList.toggle('show', open);
  });
  el.drawerClose.addEventListener('click', closePanels);
  el.mask.addEventListener('click', closePanels);
  el.prevBtn.addEventListener('click', () => renderChapter(state.chapter - 1, 0));
  el.nextBtn.addEventListener('click', () => renderChapter(state.chapter + 1, 0));

  el.content.addEventListener('scroll', () => { updateProgressBar(); scheduleSave(); });
  document.addEventListener('mouseup', () => setTimeout(handleSelection, 10));
  document.addEventListener('touchend', () => setTimeout(handleSelection, 10));
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') { closePanels(); hideSelectBar(); }
  });
  window.addEventListener('beforeunload', () => saveProgress(true));
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'hidden') saveProgress(true);
  });

  function esc(str) {
    return String(str).replace(/[&<>"']/g, (c) => (
      { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
    ));
  }

  /* ---------------- 启动 ---------------- */
  async function boot() {
    applySettings();
    try {
      await loadLibrary();
    } catch (err) {
      el.grid.innerHTML = '<p class="mark-empty">书库加载失败：' + esc(err.message) + '</p>';
      return;
    }

    const m = location.hash.match(/^#\/read\/([\w-]+)(?:\/(\d+))?/);
    if (m) {
      const chapter = m[2] ? parseInt(m[2], 10) : undefined;
      await openBook(m[1], chapter);
    }
  }

  state.annotations = readLSArray(LS.annotations);
  boot();
})();
