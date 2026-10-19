import { describe, it, expect, beforeEach } from 'vitest';
import { DimensionRegistry } from '../skeleton/registry.js';
import { Scheduler } from '../skeleton/scheduler.js';
import { BaseDimension } from '../skeleton/dimension_contract.js';
import type {
  DimensionCategory,
  DimensionValue,
  DimensionMetadata,
  ReadContext,
  DimensionResult,
} from '../skeleton/dimension_types.js';

class TestReadingDimension extends BaseDimension {
  readonly id = 'test_reading';
  readonly category: DimensionCategory = 'reading';
  readonly values: DimensionValue[] = [
    { id: 'normal', label: '普通', description: '普通阅读' },
    { id: 'intensive', label: '精读', description: '精读模式' },
  ];
  readonly defaultValue = 'normal';
  readonly metadata: DimensionMetadata = {
    name: '测试阅读维度',
    description: '用于测试的阅读维度',
  };
  readonly examplePrompts = ['精读', '普通阅读'];
  readonly contractVersion = '1.0.0';

  async execute(value: string, context: ReadContext): Promise<DimensionResult> {
    return { dimensionId: this.id, value, data: { mode: value, docId: context.documentId } };
  }
}

class TestAnalysisDimension extends BaseDimension {
  readonly id = 'test_emotion';
  readonly category: DimensionCategory = 'analysis';
  readonly values: DimensionValue[] = [
    { id: 'on', label: '开启', description: '情感分析' },
    { id: 'off', label: '关闭', description: '不分析' },
  ];
  readonly defaultValue = 'off';
  readonly metadata: DimensionMetadata = {
    name: '测试情感维度',
    description: '用于测试的情感分析维度',
  };
  readonly examplePrompts = ['情感分析', '情感着色'];
  readonly contractVersion = '1.0.0';

  async execute(value: string, context: ReadContext): Promise<DimensionResult> {
    if (value === 'on') {
      return {
        dimensionId: this.id,
        value,
        data: { emotions: ['happy', 'sad'] },
        decorations: [{ type: 'highlight', startLine: 1, className: 'emotion-happy' }],
      };
    }
    return { dimensionId: this.id, value, data: null };
  }
}

class ErrorDimension extends BaseDimension {
  readonly id = 'test_error';
  readonly category: DimensionCategory = 'analysis';
  readonly values: DimensionValue[] = [
    { id: 'run', label: '运行', description: '会抛异常' },
  ];
  readonly defaultValue = 'run';
  readonly metadata: DimensionMetadata = {
    name: '测试异常维度',
    description: '用于测试异常隔离',
  };
  readonly examplePrompts = ['测试异常'];
  readonly contractVersion = '1.0.0';

  async execute(): Promise<DimensionResult> {
    throw new Error('维度执行异常');
  }
}

describe('Phase 0 端到端集成测试', () => {
  let registry: DimensionRegistry;
  let scheduler: Scheduler;

  beforeEach(() => {
    registry = new DimensionRegistry('1.0.0');
    scheduler = new Scheduler(registry);
  });

  it('注册示例维度 → 校验通过 → 调度执行', async () => {
    const reading = new TestReadingDimension();
    const emotion = new TestAnalysisDimension();

    const r1 = registry.register(reading);
    expect(r1.valid).toBe(true);

    const r2 = registry.register(emotion);
    expect(r2.valid).toBe(true);

    const context: ReadContext = { documentId: 'doc-1', chapter: 1 };
    const result = await scheduler.dispatch({
      dimensions: [
        { dimensionId: 'test_reading', value: 'intensive' },
        { dimensionId: 'test_emotion', value: 'on' },
      ],
      context,
    });

    expect(result.results).toHaveLength(2);
    expect(result.results[0].value).toBe('intensive');
    expect(result.results[1].data).toEqual({ emotions: ['happy', 'sad'] });
    expect(result.errors).toHaveLength(0);
  });

  it('异常维度被隔离，不影响其他维度', async () => {
    const reading = new TestReadingDimension();
    const errorDim = new ErrorDimension();

    registry.register(reading);
    registry.register(errorDim);

    const context: ReadContext = { documentId: 'doc-1' };
    const result = await scheduler.dispatch({
      dimensions: [
        { dimensionId: 'test_reading', value: 'normal' },
        { dimensionId: 'test_error', value: 'run' },
      ],
      context,
    });

    expect(result.results).toHaveLength(2);
    expect(result.results[0].value).toBe('normal');
    expect(result.results[1].data).toBeNull();
    expect(result.errors).toHaveLength(1);
    expect(result.errors[0].dimensionId).toBe('test_error');
  });

  it('重复注册被拒绝', () => {
    const reading1 = new TestReadingDimension();
    const reading2 = new TestReadingDimension();

    const r1 = registry.register(reading1);
    expect(r1.valid).toBe(true);

    const r2 = registry.register(reading2);
    expect(r2.valid).toBe(false);
    expect(r2.errors[0]).toContain('DUPLICATE_DIMENSION');
  });

  it('维度禁用后不参与调度', async () => {
    const emotion = new TestAnalysisDimension();
    registry.register(emotion);
    registry.disable('test_emotion');

    const context: ReadContext = { documentId: 'doc-1' };
    const result = await scheduler.dispatch({
      dimensions: [{ dimensionId: 'test_emotion', value: 'on' }],
      context,
    });

    expect(result.results[0].data).toBeNull();
  });

  it('注册表查询性能 ≤10ms', () => {
    const reading = new TestReadingDimension();
    registry.register(reading);

    const start = performance.now();
    for (let i = 0; i < 1000; i++) {
      registry.query('test_reading');
    }
    const elapsed = performance.now() - start;

    expect(elapsed).toBeLessThan(10);
  });

  it('维度间通信通过调度器中转', () => {
    const received: string[] = [];
    scheduler.registerMessageHandler('target_dim', (msg) => {
      received.push(msg.payload as string);
    });

    scheduler.message({
      from: 'source_dim',
      to: 'target_dim',
      type: 'notify',
      payload: 'hello',
    });

    expect(received).toEqual(['hello']);
  });

  it('禁止维度自调用', () => {
    expect(() => {
      scheduler.message({
        from: 'dim_a',
        to: 'dim_a',
        type: 'self',
        payload: null,
      });
    }).toThrow('禁止维度自调用');
  });
});