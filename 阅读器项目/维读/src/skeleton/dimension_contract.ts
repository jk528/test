import {
  DIMENSION_CATEGORIES,
  type DimensionCategory,
  type DimensionValue,
  type DimensionMetadata,
  type ReadContext,
  type DimensionResult,
  type ValidationResult,
} from './dimension_types.js';

export interface DimensionContract {
  readonly id: string;
  readonly category: DimensionCategory;
  readonly values: DimensionValue[];
  readonly defaultValue: string;
  readonly metadata: DimensionMetadata;
  readonly examplePrompts: string[];
  readonly contractVersion: string;

  validate(): ValidationResult;
  execute(value: string, context: ReadContext): Promise<DimensionResult>;
}

export abstract class BaseDimension implements DimensionContract {
  abstract readonly id: string;
  abstract readonly category: DimensionCategory;
  abstract readonly values: DimensionValue[];
  abstract readonly defaultValue: string;
  abstract readonly metadata: DimensionMetadata;
  abstract readonly examplePrompts: string[];
  abstract readonly contractVersion: string;

  validate(): ValidationResult {
    const errors: string[] = [];

    if (!this.id || typeof this.id !== 'string') {
      errors.push('id 必须是非空字符串');
    }
    if (!/^[a-z][a-z0-9_]*$/.test(this.id)) {
      errors.push('id 必须为小写字母+下划线格式');
    }
    if (this.id.length > 30) {
      errors.push('id 长度不超过 30 字符');
    }

    if (!DIMENSION_CATEGORIES.includes(this.category)) {
      errors.push(`category 必须是 ${DIMENSION_CATEGORIES.join('/')} 之一`);
    }

    if (!Array.isArray(this.values) || this.values.length === 0) {
      errors.push('values 必须包含至少一个取值');
    }
    for (const v of this.values) {
      if (!v.id || !v.label) {
        errors.push(`取值 ${JSON.stringify(v)} 缺少 id 或 label`);
      }
    }

    if (!this.values.some((v) => v.id === this.defaultValue)) {
      errors.push(`defaultValue "${this.defaultValue}" 不在取值列表中`);
    }

    if (!this.metadata || !this.metadata.name || !this.metadata.description) {
      errors.push('metadata 必须包含 name 和 description');
    }

    if (!Array.isArray(this.examplePrompts) || this.examplePrompts.length === 0) {
      errors.push('examplePrompts 必须包含至少一条示例提示词');
    }

    if (!this.contractVersion || !/^\d+\.\d+\.\d+/.test(this.contractVersion)) {
      errors.push('contractVersion 必须是语义化版本号');
    }

    return { valid: errors.length === 0, errors };
  }

  abstract execute(value: string, context: ReadContext): Promise<DimensionResult>;
}
