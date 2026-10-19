import type { DimensionContract } from './dimension_contract.js';
import type { DimensionRegistry } from './registry.js';
import type { ReadContext, DimensionResult, DimensionCategory } from './dimension_types.js';
import { IsolationBox, type IsolatedError } from './isolation.js';

export interface DispatchRequest {
  dimensions: DimensionDispatch[];
  context: ReadContext;
}

export interface DimensionDispatch {
  dimensionId: string;
  value: string;
}

export interface DispatchResult {
  results: DimensionResult[];
  errors: IsolatedError[];
  duration: number;
}

export interface SchedulerMessage {
  from: string;
  to: string;
  type: string;
  payload: unknown;
}

export class Scheduler {
  private registry: DimensionRegistry;
  private isolation: IsolationBox;
  private messageHandlers = new Map<string, (msg: SchedulerMessage) => void>();

  constructor(registry: DimensionRegistry) {
    this.registry = registry;
    this.isolation = new IsolationBox();
  }

  async dispatch(request: DispatchRequest): Promise<DispatchResult> {
    const startTime = Date.now();
    const results: DimensionResult[] = [];

    for (const dispatch of request.dimensions) {
      const dimension = this.registry.query(dispatch.dimensionId);
      if (!dimension) {
        const error: IsolatedError = {
          dimensionId: dispatch.dimensionId,
          error: new Error(`维度 "${dispatch.dimensionId}" 未注册`),
          timestamp: Date.now(),
        };
        this.isolation.getErrors();
        results.push({
          dimensionId: dispatch.dimensionId,
          value: dispatch.value,
          data: null,
        });
        continue;
      }

      if (!this.registry.isEnabled(dispatch.dimensionId)) {
        results.push({
          dimensionId: dispatch.dimensionId,
          value: dispatch.value,
          data: null,
        });
        continue;
      }

      const isolationResult = await this.isolation.runIsolated(
        dispatch.dimensionId,
        () => dimension.execute(dispatch.value, request.context),
      );

      if (isolationResult.success && isolationResult.result) {
        results.push(isolationResult.result);
      } else {
        results.push({
          dimensionId: dispatch.dimensionId,
          value: dispatch.value,
          data: null,
        });
      }
    }

    return {
      results,
      errors: this.isolation.getErrors(),
      duration: Date.now() - startTime,
    };
  }

  message(msg: SchedulerMessage): void {
    if (msg.from === msg.to) {
      throw new Error('禁止维度自调用');
    }
    const handler = this.messageHandlers.get(msg.to);
    if (handler) {
      handler(msg);
    }
  }

  registerMessageHandler(
    dimensionId: string,
    handler: (msg: SchedulerMessage) => void,
  ): void {
    this.messageHandlers.set(dimensionId, handler);
  }

  getIsolatedErrors(): IsolatedError[] {
    return this.isolation.getErrors();
  }

  clearErrors(): void {
    this.isolation.clearErrors();
  }
}