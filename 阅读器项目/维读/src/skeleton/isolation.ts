export interface IsolationResult<T> {
  success: boolean;
  result?: T;
  error?: IsolatedError;
}

export interface IsolatedError {
  dimensionId: string;
  error: Error;
  timestamp: number;
}

export class IsolationBox {
  private isolatedErrors: IsolatedError[] = [];
  private maxErrorLog: number;

  constructor(maxErrorLog: number = 100) {
    this.maxErrorLog = maxErrorLog;
  }

  async runIsolated<T>(
    dimensionId: string,
    fn: () => Promise<T>,
  ): Promise<IsolationResult<T>> {
    try {
      const result = await fn();
      return { success: true, result };
    } catch (err) {
      const error: IsolatedError = {
        dimensionId,
        error: err instanceof Error ? err : new Error(String(err)),
        timestamp: Date.now(),
      };
      this.isolatedErrors.push(error);
      if (this.isolatedErrors.length > this.maxErrorLog) {
        this.isolatedErrors.shift();
      }
      return { success: false, error };
    }
  }

  getErrors(): IsolatedError[] {
    return [...this.isolatedErrors];
  }

  getErrorsByDimension(dimensionId: string): IsolatedError[] {
    return this.isolatedErrors.filter((e) => e.dimensionId === dimensionId);
  }

  clearErrors(): void {
    this.isolatedErrors = [];
  }
}