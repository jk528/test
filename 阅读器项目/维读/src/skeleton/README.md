# 维读骨架层（skeleton/）

> 框架核心层，由维护者管理，禁止自动修改（spec 5.5.1）

## 目录结构

```
skeleton/
  ├─ dimension_types.ts      四类维度枚举与共享类型
  ├─ extension_point.ts      扩展点接口与基类
  ├─ dimension_contract.ts   维度契约接口与基类
  ├─ backend_adapter.ts      后端适配接口
  ├─ registry.ts             维度注册中心 + 契约校验器
  ├─ scheduler.ts            调度核心
  └─ isolation.ts            异常隔离
```

## 快速上手

```typescript
import { DimensionRegistry } from './skeleton/registry.js';
import { Scheduler } from './skeleton/scheduler.js';
import { BaseDimension } from './skeleton/dimension_contract.js';

// 1. 创建注册中心
const registry = new DimensionRegistry('1.0.0');

// 2. 定义维度（继承 BaseDimension）
class MyDimension extends BaseDimension { ... }

// 3. 注册维度
const result = registry.register(new MyDimension());

// 4. 创建调度器
const scheduler = new Scheduler(registry);

// 5. 调度执行
const result = await scheduler.dispatch({
  dimensions: [{ dimensionId: 'my_dim', value: 'some_value' }],
  context: { documentId: 'doc-1' },
});
```

## 骨架/内容分离约定

- `skeleton/`：骨架层，维护者管理，禁止自打磨写入
- `content/`：内容层，大模型自打磨可写入