export interface BackendCapabilities {
  setShape: boolean;
  sidecar: boolean;
  sessionFetch: boolean;
  stickyScroll: boolean;
}

export interface Decoration {
  type: 'highlight' | 'glyph' | 'viewzone' | 'inline';
  startLine: number;
  endLine?: number;
  className?: string;
  color?: string;
  tooltip?: string;
  data?: unknown;
}

export interface Selection {
  startLine: number;
  endLine: number;
  text: string;
}

export interface Viewport {
  firstVisibleLine: number;
  lastVisibleLine: number;
}

export interface Document {
  id: string;
  text: string;
  lineCount: number;
  chapters?: Chapter[];
}

export interface Chapter {
  index: number;
  title: string;
  startLine: number;
  endLine: number;
}

export interface Annotation {
  id: string;
  documentId: string;
  type: 'bookmark' | 'note' | 'highlight';
  startLine: number;
  endLine: number;
  content: string;
  timestamp: number;
}

export interface AnalysisTask {
  engine: string;
  method: string;
  params: Record<string, unknown>;
}

export interface AnalysisResult {
  engine: string;
  method: string;
  data: unknown;
  duration: number;
}

export interface ReaderBackendAdapter {
  readonly capabilities: BackendCapabilities;

  renderDecorations(decorations: Decoration[]): void;
  renderText(text: string): void;
  clearDecorations(): void;

  onSelectionChange(callback: (sel: Selection) => void): () => void;
  onScroll(callback: (vp: Viewport) => void): () => void;
  onChapterChange(callback: (chapter: number) => void): () => void;

  openFile(path: string): Promise<Document>;
  saveAnnotation(ann: Annotation): Promise<void>;
  getAnnotations(documentId: string): Promise<Annotation[]>;

  callAnalysisEngine(task: AnalysisTask): Promise<AnalysisResult>;
}

export const DEFAULT_CAPABILITIES: BackendCapabilities = {
  setShape: false,
  sidecar: false,
  sessionFetch: false,
  stickyScroll: false,
};