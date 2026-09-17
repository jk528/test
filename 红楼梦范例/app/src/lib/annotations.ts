// 标注·书签：M1 锚定「物理行」（与 V1.0 统一锚点模型的物理层一致）。
// M1 先用 localStorage 持久化（按书目路径隔离）；M5 迁移 SQLite 时保持同样字段。

export interface Bookmark {
  id: string;
  /** 0 基物理行号 */
  line: number;
  /** 备注（可空） */
  note: string;
  createdAt: number;
}

const PREFIX = "honglou.bookmarks.v1:";

function storageKey(bookKey: string): string {
  return PREFIX + bookKey;
}

/** 读取某书的全部书签（按行升序） */
export function loadBookmarks(bookKey: string): Bookmark[] {
  try {
    const raw = localStorage.getItem(storageKey(bookKey));
    if (!raw) return [];
    const arr = JSON.parse(raw) as Bookmark[];
    return arr.sort((a, b) => a.line - b.line);
  } catch {
    return [];
  }
}

function persist(bookKey: string, list: Bookmark[]): void {
  localStorage.setItem(storageKey(bookKey), JSON.stringify(list));
}

/** 添加书签（同一行重复添加则更新备注），返回最新列表 */
export function upsertBookmark(
  bookKey: string,
  line: number,
  note = ""
): Bookmark[] {
  const list = loadBookmarks(bookKey);
  const existing = list.find((b) => b.line === line);
  if (existing) {
    existing.note = note;
  } else {
    list.push({
      id: `${Date.now().toString(36)}-${line}`,
      line,
      note,
      createdAt: Date.now(),
    });
  }
  list.sort((a, b) => a.line - b.line);
  persist(bookKey, list);
  return list;
}

/** 删除某行书签（无则忽略），返回最新列表 */
export function removeBookmarkAt(bookKey: string, line: number): Bookmark[] {
  const list = loadBookmarks(bookKey).filter((b) => b.line !== line);
  persist(bookKey, list);
  return list;
}

/** 切换某行书签，返回 { list, active } */
export function toggleBookmark(
  bookKey: string,
  line: number
): { list: Bookmark[]; active: boolean } {
  const exists = loadBookmarks(bookKey).some((b) => b.line === line);
  if (exists) {
    return { list: removeBookmarkAt(bookKey, line), active: false };
  }
  return { list: upsertBookmark(bookKey, line), active: true };
}

export function isBookmarked(list: Bookmark[], line: number): boolean {
  return list.some((b) => b.line === line);
}
