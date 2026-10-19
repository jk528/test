import type { DimensionContract } from './dimension_contract.js';
import type { DimensionCategory, ValidationResult, SemVer } from './dimension_types.js';
import { isCompatible, parseSemVer } from './dimension_types.js';

export interface RegistryEntry {
  dimension: DimensionContract;
  enabled: boolean;
  registeredAt: number;
}

export interface RegistryEvent {
  type: 'registered' | 'unregistered' | 'enabled' | 'disabled';
  dimensionId: string;
  timestamp: number;
}

export type RegistryEventListener = (event: RegistryEvent) => void;

export class ContractValidator {
  validateMetadata(dimension: DimensionContract): ValidationResult {
    return dimension.validate();
  }

  validateValues(dimension: DimensionContract): ValidationResult {
    const errors: string[] = [];
    const valueIds = new Set<string>();
    for (const v of dimension.values) {
      if (valueIds.has(v.id)) {
        errors.push(`取值 "${v.id}" 重复`);
      }
      valueIds.add(v.id);
    }
    if (!valueIds.has(dimension.defaultValue)) {
      errors.push(`defaultValue "${dimension.defaultValue}" 不在取值列表中`);
    }
    return { valid: errors.length === 0, errors };
  }

  validateNoDuplicate(
    dimension: DimensionContract,
    existing: Map<string, RegistryEntry>,
  ): ValidationResult {
    if (existing.has(dimension.id)) {
      return {
        valid: false,
        errors: [`维度 "${dimension.id}" 已注册（DUPLICATE_DIMENSION）`],
      };
    }
    return { valid: true, errors: [] };
  }

  validateVersionCompatible(
    dimension: DimensionContract,
    requiredVersion: string,
  ): ValidationResult {
    if (!isCompatible(dimension.contractVersion, requiredVersion)) {
      return {
        valid: false,
        errors: [
          `契约版本不兼容: 维度 "${dimension.id}" 要求 ${requiredVersion}，实际 ${dimension.contractVersion}`,
        ],
      };
    }
    return { valid: true, errors: [] };
  }

  validateAll(
    dimension: DimensionContract,
    existing: Map<string, RegistryEntry>,
    requiredVersion: string,
  ): ValidationResult {
    const results = [
      this.validateMetadata(dimension),
      this.validateValues(dimension),
      this.validateNoDuplicate(dimension, existing),
      this.validateVersionCompatible(dimension, requiredVersion),
    ];
    const errors = results.flatMap((r) => r.errors);
    return { valid: errors.length === 0, errors };
  }
}

export class DimensionRegistry {
  private entries = new Map<string, RegistryEntry>();
  private byCategory = new Map<DimensionCategory, Set<string>>();
  private listeners = new Set<RegistryEventListener>();
  private validator = new ContractValidator();
  private requiredVersion: string;

  constructor(requiredVersion: string = '1.0.0') {
    this.requiredVersion = requiredVersion;
  }

  register(dimension: DimensionContract): ValidationResult {
    const result = this.validator.validateAll(
      dimension,
      this.entries,
      this.requiredVersion,
    );
    if (!result.valid) {
      return result;
    }

    const entry: RegistryEntry = {
      dimension,
      enabled: true,
      registeredAt: Date.now(),
    };
    this.entries.set(dimension.id, entry);

    let catSet = this.byCategory.get(dimension.category);
    if (!catSet) {
      catSet = new Set();
      this.byCategory.set(dimension.category, catSet);
    }
    catSet.add(dimension.id);

    this.emit({ type: 'registered', dimensionId: dimension.id, timestamp: entry.registeredAt });
    return { valid: true, errors: [] };
  }

  unregister(dimensionId: string): boolean {
    const entry = this.entries.get(dimensionId);
    if (!entry) return false;

    this.entries.delete(dimensionId);
    const catSet = this.byCategory.get(entry.dimension.category);
    catSet?.delete(dimensionId);

    this.emit({ type: 'unregistered', dimensionId, timestamp: Date.now() });
    return true;
  }

  query(dimensionId: string): DimensionContract | null {
    const entry = this.entries.get(dimensionId);
    return entry ? entry.dimension : null;
  }

  queryByCategory(category: DimensionCategory): DimensionContract[] {
    const catSet = this.byCategory.get(category);
    if (!catSet) return [];
    const result: DimensionContract[] = [];
    for (const id of catSet) {
      const entry = this.entries.get(id);
      if (entry && entry.enabled) {
        result.push(entry.dimension);
      }
    }
    return result;
  }

  discover(): DimensionContract[] {
    const result: DimensionContract[] = [];
    for (const entry of this.entries.values()) {
      if (entry.enabled) {
        result.push(entry.dimension);
      }
    }
    return result;
  }

  discoverByCategory(category: DimensionCategory): DimensionContract[] {
    return this.queryByCategory(category);
  }

  disable(dimensionId: string): boolean {
    const entry = this.entries.get(dimensionId);
    if (!entry || !entry.enabled) return false;
    entry.enabled = false;
    this.emit({ type: 'disabled', dimensionId, timestamp: Date.now() });
    return true;
  }

  enable(dimensionId: string): boolean {
    const entry = this.entries.get(dimensionId);
    if (!entry || entry.enabled) return false;
    entry.enabled = true;
    this.emit({ type: 'enabled', dimensionId, timestamp: Date.now() });
    return true;
  }

  isEnabled(dimensionId: string): boolean {
    const entry = this.entries.get(dimensionId);
    return entry ? entry.enabled : false;
  }

  observe(listener: RegistryEventListener): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  get size(): number {
    return this.entries.size;
  }

  clear(): void {
    this.entries.clear();
    this.byCategory.clear();
  }

  private emit(event: RegistryEvent): void {
    for (const listener of this.listeners) {
      try {
        listener(event);
      } catch {
        // 监听器异常不影响注册中心
      }
    }
  }
}