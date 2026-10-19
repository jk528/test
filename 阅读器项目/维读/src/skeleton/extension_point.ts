import type { DimensionCategory, ValidationResult } from './dimension_types.js';

export interface ExtensionPoint {
  readonly id: string;
  readonly contractVersion: string;
  readonly layer: 'skeleton';
  readonly category: DimensionCategory;
  readonly registeredDimensions: string[];

  validate(contract: unknown): ValidationResult;
  register(dimensionId: string): void;
  unregister(dimensionId: string): void;
  discover(): string[];
}

export class BaseExtensionPoint implements ExtensionPoint {
  readonly layer = 'skeleton' as const;
  readonly registeredDimensions: string[] = [];

  constructor(
    readonly id: string,
    readonly contractVersion: string,
    readonly category: DimensionCategory,
  ) {}

  validate(contract: unknown): ValidationResult {
    const errors: string[] = [];
    if (!contract || typeof contract !== 'object') {
      return { valid: false, errors: ['契约必须是非空对象'] };
    }
    const c = contract as Record<string, unknown>;
    if (typeof c.id !== 'string' || c.id.length === 0) {
      errors.push('id 必须是非空字符串');
    }
    if (typeof c.contractVersion !== 'string') {
      errors.push('contractVersion 必须是字符串');
    }
    return { valid: errors.length === 0, errors };
  }

  register(dimensionId: string): void {
    if (this.registeredDimensions.includes(dimensionId)) {
      throw new Error(`维度 ${dimensionId} 已注册到扩展点 ${this.id}`);
    }
    this.registeredDimensions.push(dimensionId);
  }

  unregister(dimensionId: string): void {
    const idx = this.registeredDimensions.indexOf(dimensionId);
    if (idx === -1) {
      throw new Error(`维度 ${dimensionId} 未注册到扩展点 ${this.id}`);
    }
    this.registeredDimensions.splice(idx, 1);
  }

  discover(): string[] {
    return [...this.registeredDimensions];
  }
}

export const EXTENSION_POINT_IDS = {
  READING_DIMENSION: 'reading_dimension',
  ANALYSIS_DIMENSION: 'analysis_dimension',
  DISPLAY_DIMENSION: 'display_dimension',
  INTERACTION_DIMENSION: 'interaction_dimension',
} as const;

export const CONTRACT_VERSION = '1.0.0';

export function createDimensionExtensionPoints(): ExtensionPoint[] {
  return [
    new BaseExtensionPoint(EXTENSION_POINT_IDS.READING_DIMENSION, CONTRACT_VERSION, 'reading'),
    new BaseExtensionPoint(EXTENSION_POINT_IDS.ANALYSIS_DIMENSION, CONTRACT_VERSION, 'analysis'),
    new BaseExtensionPoint(EXTENSION_POINT_IDS.DISPLAY_DIMENSION, CONTRACT_VERSION, 'display'),
    new BaseExtensionPoint(EXTENSION_POINT_IDS.INTERACTION_DIMENSION, CONTRACT_VERSION, 'interaction'),
  ];
}