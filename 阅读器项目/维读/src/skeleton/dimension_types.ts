export type DimensionCategory = 'reading' | 'analysis' | 'display' | 'interaction';

export const DIMENSION_CATEGORIES: readonly DimensionCategory[] = [
  'reading',
  'analysis',
  'display',
  'interaction',
] as const;

export interface DimensionValue {
  id: string;
  label: string;
  description: string;
}

export interface DimensionMetadata {
  name: string;
  description: string;
  icon?: string;
}

export interface ReadContext {
  documentId: string;
  chapter?: number;
  selection?: {
    startLine: number;
    endLine: number;
    text: string;
  };
  history?: ParseHistoryEntry[];
}

export interface DimensionResult {
  dimensionId: string;
  value: string;
  data: unknown;
  decorations?: Decoration[];
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

export interface ParseHistoryEntry {
  prompt: string;
  config: unknown;
  adopted: boolean;
  timestamp: number;
}

export interface ValidationResult {
  valid: boolean;
  errors: string[];
}

export interface SemVer {
  major: number;
  minor: number;
  patch: number;
}

export function parseSemVer(version: string): SemVer {
  const match = version.match(/^(\d+)\.(\d+)\.(\d+)/);
  if (!match) {
    throw new Error(`无效的语义化版本号: ${version}`);
  }
  return {
    major: parseInt(match[1], 10),
    minor: parseInt(match[2], 10),
    patch: parseInt(match[3], 10),
  };
}

export function isCompatible(actual: string, required: string): boolean {
  const a = parseSemVer(actual);
  const r = parseSemVer(required);
  if (a.major !== r.major) return false;
  if (a.minor < r.minor) return false;
  return true;
}