# 国内大模型 API 售卖平台合集

> 整理时间：2026年10月
> 适用范围：文本/多模态大模型 API 调用、企业采购、个人开发者选型
> 说明：价格与福利以各平台官网最新公告为准，本文档信息截至 2026年10月

**目录**：厂商直供平台 · 聚合分发平台 · 海外平台 · 选型建议

---

## 一、厂商直供平台

### 1. DeepSeek（深度求索）

| 项目 | 内容 |
|---|---|
| 官网/文档 | [api-docs.deepseek.com](https://api-docs.deepseek.com/zh-cn/quick_start/pricing/) |
| 主力模型 | deepseek-flash、deepseek-v4-pro、deepseek-chat、deepseek-reasoner |
| 计费模式 | 按量付费，**峰谷定价**（空闲时段更便宜） |
| 参考价格 | flash：输入约 1元/百万tokens（空闲），输出 1.2元；v4-pro：输入 4.5元，输出 3.96元（高峰） |
| 缓存命中 | 输入缓存命中时价格更低 |
| 新人福利 | 注册即用，无单独新人礼包，但峰谷定价本身即优惠 |

### 2. 火山方舟（字节跳动）

| 项目 | 内容 |
|---|---|
| 官网 | [volcengine.com/product/ark](https://www.volcengine.com/product/ark/) |
| 主力模型 | 豆包 Doubao 系列（Seed-2.1-pro、Seed-2.1-turbo、Seed-Evolving 等）、第三方模型托管 |
| 计费模式 | 按量付费 |
| 新人福利 | **注册即送免费推理额度**；协作奖励计划每日可领取单模型最高 **500万 Tokens** |
| 免费额度 | 豆包主力模型各 **50万 Tokens** |
| Managed Agents | 首次开通赠送 30小时 Agent 运行时 + 500次 web_search 调用 |

### 3. 百度千帆（文心一言）

| 项目 | 内容 |
|---|---|
| 官网 | [qianfan.cloud.baidu.com](https://qianfan.cloud.baidu.com/) |
| 主力模型 | ERNIE 系列（ERNIE-4.0、ERNIE-Speed、ERNIE-Lite、ERNIE-Tiny 等） |
| 计费模式 | 按量付费 + Token Plan 套餐 |
| 长期免费 | ERNIE-Speed / Lite / Tiny 系列（7款预置服务）**长期免费** |
| 新人福利 | 新用户 **100万 Tokens / 90天**；AI Studio 星河社区另送 100万 Tokens |
| Token Plan | 积分制套餐：首购 **五折**、续费 **六折**，与 Token 制并行 |

### 4. 阿里云百炼

| 项目 | 内容 |
|---|---|
| 官网 | [bailian.console.aliyun.com](https://bailian.console.aliyun.com/) |
| 主力模型 | 通义千问 Qwen 系列、智谱 GLM 系列、零一万物 Yi 系列等托管模型 |
| 计费模式 | 按量付费 + Token Plan 个人版/企业版 |
| 新人福利 | 首次开通自动发放**各模型新人专属免费额度** |
| Token Plan | 个人版四档：Mini / Lite / Pro / Max |
| 特色 | 仅华北2（北京）地域模型享有免费额度；未认证用户免费额度用完后需认证+充值 |

### 5. 腾讯混元

| 项目 | 内容 |
|---|---|
| 官网 | [cloud.tencent.com/product/hunyuan](https://cloud.tencent.com/product/hunyuan) |
| 平台 | TokenHub 大模型服务平台 |
| 主力模型 | Hunyuan 系列（Hunyuan-Turbo、Hunyuan-Lite 等） |
| 计费模式 | 按量付费 |
| 新人福利 | 首次开通即享 **100万 Tokens** 免费资源包（1年有效） |
| 完全免费 | **Hunyuan-Lite 完全免费** |
| 并发增购 | 默认5个并发，增购约 ¥800/并发/月 |

### 6. 智谱 AI（GLM）

| 项目 | 内容 |
|---|---|
| 官网 | [bigmodel.cn](https://www.bigmodel.cn/) |
| 主力模型 | GLM-5.3、GLM-5.2、GLM-4.5 等 |
| 计费模式 | 按量付费 |
| 特色 | GLM 系列推理模型在代码与 Agent 场景表现突出 |

### 7. 月之暗面 Kimi

| 项目 | 内容 |
|---|---|
| 官网 | [platform.moonshot.cn](https://platform.moonshot.cn/) |
| 主力模型 | Kimi K2.5、Kimi K3（3T 参数 MoE，256K 上下文） |
| 计费模式 | 按量付费 |
| 参考价格 | K2.5：输入 4元/M，输出 16元/M；K3：$3/M 输入，$15/M 输出（缓存 $0.3/M） |
| 特色 | 超长上下文、开源 Agent 模型，擅长编码与通用 Agent 任务 |

### 8. 讯飞星火

| 项目 | 内容 |
|---|---|
| 官网 | [xinghuo.xfyun.cn](https://xinghuo.xfyun.cn/sparkapi) |
| 主力模型 | Spark-X2.5-4B、Spark-X2.5-1.7B、科研大模型等 |
| 限时免费 | Spark-X2.5-4B **限时免费**；Spark-X2.5-1.7B **完全免费** |
| 科研大模型免费包 | 个人开发者 **200万 Tokens / 1年**；企业开发者 **500万 Tokens / 1年** |

### 9. MiniMax

| 项目 | 内容 |
|---|---|
| 官网 | [platform.minimaxi.com](https://platform.minimaxi.com/) |
| 主力模型 | MiniMax-M3、M3.1-Flash、M2.7 等 |
| 计费模式 | 按量付费 + Token Plan |
| 参考价格 | M3：输入 1元/M，输出 4元/M，缓存读取 0.1元/M；M3 512k 输入 12.6元（五折 6.3），输出 50.4元（五折 25.2） |
| 国际版 | M3.1-Flash：$0.15/M 输入，$0.60/M 输出 |
| 特色 | Agent 任务性价比极高，输入价格压至 1元/M |

### 10. 阶跃星辰 StepFun

| 项目 | 内容 |
|---|---|
| 官网 | [platform.stepfun.com](https://platform.stepfun.com/) |
| 主力模型 | step-5-preview 等 |
| 计费模式 | 按量付费 |
| 参考价格 | step-5-preview：输入 7元/M，缓存命中 0.35元/M，输出 20元/M |

### 11. 商汤日日新

| 项目 | 内容 |
|---|---|
| 官网 | [sensecore.cn](https://www.sensecore.cn/) |
| 主力模型 | SenseNova 系列 |
| 说明 | 企业级服务为主，需商务洽谈获取详细报价 |

### 12. 零一万物

| 项目 | 内容 |
|---|---|
| 官网 | [platform.lingyiwanwu.com](https://platform.lingyiwanwu.com/) |
| 主力模型 | Yi 系列（yi-large、yi-medium、yi-large-turbo 等） |
| 限时免费 | yi-large / yi-medium / yi-large-rag / yi-large-turbo 在阿里云百炼渠道**限时免费** |
| 免费额度 | yi-large：100万 Tokens |

---

## 二、聚合分发平台

### 1. 硅基流动 SiliconFlow

| 项目 | 内容 |
|---|---|
| 官网 | [siliconflow.cn](https://siliconflow.cn/) / [siliconflow.com](https://www.siliconflow.com/) |
| 模式 | 聚合多家模型（DeepSeek、Kimi、Qwen、GLM 等），统一 API 接口 |
| 计费 | 透明按需付费，无最低承诺 |
| 新人福利 | 注册即送 **$1 免费积分** |
| 特色 | 可一屏对比各模型价格，支持缓存命中优惠 |

### 2. 无问芯穹 Infinigence

| 项目 | 内容 |
|---|---|
| 官网 | [infini-ai.com](https://www.infini-ai.com/) / [docs.infini-ai.com](https://docs.infini-ai.com/) |
| 模式 | 聚合平台，提供 LLM API 与 GenStudio 体验中心 |
| 计费变更 | **2026年3月30日起基础版 LLM API 不再免费**，按 Token 后付费；网页端体验中心仍免费 |

---

## 三、海外聚合平台

### OpenRouter

| 项目 | 内容 |
|---|---|
| 官网 | [openrouter.ai](https://openrouter.ai/) |
| 模式 | 全球最大模型聚合平台，覆盖开源与闭源模型 |
| 免费模型 | Llama 3.3 70B、Qwen3 Coder、GPT-OSS 120B、NVIDIA Nemotron 3 Super 等 |
| 免费额度 | 无余额每日 **50次**；充值 $10+ 每日 **1000次** |
| 付费推理 | 按量付费，价格透明，支持缓存命中优惠 |

---

## 四、新人福利速查表

| 平台 | 新人福利 | 长期免费 |
|---|---|---|
| 火山方舟 | 注册送免费额度，每日领最高500万 Tokens | 豆包主力模型各50万 Tokens |
| 百度千帆 | 100万 Tokens / 90天 + AI Studio 100万 | ERNIE-Speed/Lite/Tiny 长期免费 |
| 阿里云百炼 | 各模型新人免费额度（自动发放） | 部分模型有免费额度 |
| 腾讯混元 | 100万 Tokens / 1年 | Hunyuan-Lite 完全免费 |
| 讯飞星火 | 科研大模型：个人200万/年，企业500万/年 | Spark-X2.5-1.7B 免费 |
| 硅基流动 | $1 免费积分 | 无 |
| 零一万物 | 阿里云渠道 yi-large 100万 Tokens | yi-large 等限时免费 |
| OpenRouter | 无新人礼包 | 多款开源模型每日免费额度 |

---

## 五、选型建议

| 场景 | 推荐平台 | 理由 |
|---|---|---|
| 极致性价比文本处理 | DeepSeek、MiniMax | 输入价格压至 1元/M，峰谷/缓存进一步降低成本 |
| 大厂生态整合 | 火山方舟、百度千帆、阿里云百炼、腾讯混元 | 与云服务深度绑定，SLA 有保障 |
| 超长上下文 / Agent | 月之暗面 Kimi、智谱 GLM | 256K 上下文、开源 Agent 模型 |
| 多模型统一接入 | 硅基流动、OpenRouter | 一个 API Key 调用多家模型，便于比价和切换 |
| 科研 / 教育 | 讯飞星火 | 科研大模型免费包额度高 |
| 企业私有化 / 合规 | 商汤、百度千帆、阿里云百炼 | 支持专有云部署与定制化服务 |

---

> **免责声明**：本文档价格与福利信息基于 2026年10月公开资料整理，大模型行业价格波动频繁，**实际使用前请务必以各平台官网最新公告为准**。部分平台可能需要企业认证或实名认证才能享受完整服务。
