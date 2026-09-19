---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: 'd8d04609-5708-476b-97f9-8425dcd7785a'
  PropagateID: 'd8d04609-5708-476b-97f9-8425dcd7785a'
  ReservedCode1: 'a4a865ba-1e7d-499e-9502-ada1fbfde761'
  ReservedCode2: 'a4a865ba-1e7d-499e-9502-ada1fbfde761'
---

# Qoder 注册登录方式与移动端绑定逻辑研究

> 对象：阿里巴巴 Qoder（Agentic 编程平台，2025 年 8 月发布）｜ 调研日期：2026-09-19
> 信息来源：阿里云帮助中心（help.aliyun.com）、Qoder CN 官方文档站（docs.qoder.cn / docs.qoder.cn/mobile/app/remote-control）、社区项目（avaritiachaos/qoder-proxy）、第三方教程
> 核心结论：Qoder 分**国际版**与**国内版**，国内版有两条产品线（原灵码线 / 全家桶线），账号体系不同；移动端绑定分「账号级绑定」与「会话级配对」两层。

---

## 一、产品线与账号体系总览

| 产品线 | 账号体系 | 购买/管理入口 | CLI 命令 | CLI 认证方式 |
|---|---|---|---|---|
| Qoder（国际版） | Qoder 账号（qoder.com） | qoder.com | `qodercli` | OAuth（`qodercli login`），凭证目录 `~/.qoder` |
| Qoder CN（原灵码，原通义灵码 Lingma） | **阿里云账号** | 阿里云控制台 qoder.console.aliyun.com | `qoderclicn`（全家桶 CLI 复用） | 见下文 |
| Qoder CN（全家桶） | **Qoder CN 账号**（qoder.com.cn 注册，手机号验证码） | qoder.com.cn | `qoderclicn` | PAT（Personal Access Token），凭证目录 `~/.qoderworkcn` |

补充：Qoder CN 系列于 2026 年 5 月 20 日由「通义灵码」更名而来。产品家族含 Desktop IDE、JetBrains 插件、CLI、QoderWork CN（办公助手）、QoderWake CN（数字员工）、Cloud Agents CN（云端 Agent）、Mobile App、网页版、眼镜版。

### 两套账号的关系（官方 FAQ 原文要点）

- 两套账号**通过手机号验证码登录打通**——同一手机号可分别登录阿里云官网和 qoder.com.cn，无需额外配置
- 但两条产品线的**订阅和 Credits 相互独立、不互通**（原灵码的 Credits 只在 Desktop / JetBrains 插件 / VSCode 插件生效；全家桶的 Credits 在 Desktop / JetBrains / QoderWork / QoderWake / CLI / Mobile 全线共享）
- Qoder CN 与 Qoder 国际版的 Credits **不等价、不可换算**
- 判断买的哪条线：订单 commodityCode 含 `lingma_` 前缀 → 原灵码线；含「全家桶」→ qoder.com.cn 线

---

## 二、注册登录方式

### 2.1 国际版（qoder.com）

| 方式 | 说明 |
|---|---|
| GitHub 一键注册/登录 | OAuth 关联 |
| Google 一键注册/登录 | OAuth 关联 |
| 邮箱 + 密码 | 常规注册 |
| CLI | `qodercli login` 走 OAuth 浏览器授权，登录一次后自动认证，无需配置 Token |

新用户默认 14 天 Pro 试用 + 300 Credits。

### 2.2 国内版（两条线）

**Qoder CN（原灵码线）——阿里云账号登录**

- 支持阿里云主账号（密码/扫码）与 RAM 用户（仅企业标准版/专属版，主账号分配席位）
- 个人版不支持 RAM 子账号：Credits 绑定在主账号上，子账号登录后 Credits 为 0
- 购买需阿里云账号实名认证

**Qoder CN（全家桶线）——Qoder CN 账号登录**

- 在 qoder.com.cn 用手机号验证码注册/登录
- 订单底层仍通过阿里云交易系统完成（开发票时用同一手机号对应的阿里云账号）

### 2.3 各客户端登录实现

| 客户端 | 登录方式 | 备注 |
|---|---|---|
| Desktop IDE / JetBrains 插件 | 浏览器跳转登录页（原灵码线跳阿里云登录页；全家桶线跳 qoder.com.cn），完成后回跳 IDE | 多个 IDE 客户端**登录状态同步，只需登录一次** |
| IDE（远程环境：Remote SSH / WSL / Docker / VS Code Web IDE / Open VSX） | **AK/SK 登录**：控制台创建 AccessKey 后，在 IDE 命令面板（`Ctrl+Shift+P`）搜 Qoder CN → 分步输入 AccessKey ID / Secret → 选择身份 | 适用于打不开浏览器登录页的场景；Visual Studio 端暂不支持 AK/SK |
| CLI（国内 `qoderclicn`） | **PAT**：创建入口 `qoder.com.cn/account/integrations`，环境变量 `QODERCN_PERSONAL_ACCESS_TOKEN` | 凭证目录 `~/.qoderworkcn` |
| CLI（国际 `qodercli`） | OAuth（`qodercli login`），无需配置 Token | 凭证目录 `~/.qoder` |

### 2.4 登录异常排查要点（来自官方 FAQ）

| 现象 | 原因/处理 |
|---|---|
| 「暂无 Qoder 使用权限」 | 登录账号与购买账号不一致；或企业成员未分配席位；或买了全家桶却用阿里云账号登录（反之亦然） |
| 刚买套餐仍显示「体验版/Community」 | 客户端状态未刷新：完全退出账号 → 关 IDE → 重开 → 重登 |
| 「您已达到配额使用上限」 | 退登重登刷新状态 → 升级客户端 → 检查订单是否待付款 → 确认产品线匹配 |

---

## 三、手机端与客户端绑定逻辑

### 3.1 移动端载体

| 终端 | 载体 | 说明 |
|---|---|---|
| 手机 App | **Qoder CN Mobile**（包名 `com.qoder.mobile.cn`） | App Store（id6768317705）/ 应用宝可下；Android/iOS |
| 网页版 | 浏览器 PWA | 远程控制 + 云端任务 |
| 眼镜版 | 千问 AI 眼镜 / Rokid 乐奇眼镜 | 2026 年 4 月 30 日上线 |

移动端核心能力：远程控制电脑上的任务、任务看板（运行中/已就绪/已归档一屏掌控）、关键操作审批、Plan 模式方案审核、7×24 跟进长任务。

### 3.2 账号级绑定（基础前提）

手机 App 与电脑端**登录相同账号**，这是远程控制的前置条件。绑定后 App 可见该账号下全部任务：

```
运行中（电脑/CLI 正在跑的会话） + 已就绪 + 已归档
```

全家桶线 Credits 在 Mobile 端同样消耗（与 Desktop/CLI 全线共享额度）。

### 3.3 会话级绑定（CLI 远程控制配对）

```
电脑端：项目目录启动 Qoder CLI 并完成登录
  → 输入 /remote-control 命令
  → 终端生成动态二维码
    （第三方教程描述：每 30 秒自动刷新，过期即失效——防截图重放）
手机端：App 右上角「+」→「扫码接入现有会话」→ 扫码
  → 手机端加载当前 CLI 会话的完整状态
```

**绑定后的运行模型**：

- **会话仍在电脑上持续运行**，App 只做实时同步与远程介入——查看进度、审批高风险操作、回答 Agent 提问、追加指令
- 双向实时同步（任务流、确认弹窗、文件变更状态在手机端还原）
- 断开连接后本地服务终止
- **守护进程模式**（remote-control daemon）：支持手机主动发起任务，而不仅是接管现有会话
- 官方定位：远程控制「不是替代电脑端开发环境」，而是衔接离场后的关键节点（审批/确认/推进）

### 3.4 云端任务（不依赖电脑在线的另一条路）

- 任务委派给 **Cloud Agents** 在云端隔离沙箱中长时异步执行，关闭客户端任务继续
- 执行过程与产物通过事件流实时回传到 App
- 适合「人不在电脑前、任务又不依赖本地环境」的场景；与远程控制互补——远程控制绑的是**本机会话**，云端任务绑的是**云端实例**

### 3.5 移动端使用限制

- 手机与电脑需网络可达（第三方教程提到局域网场景；公网远程需内网穿透或官方云端通道）
- 未登录（或登录不同账号）无法生成二维码或连接失败

---

## 四、对自动化的参考价值

结合个人 API 直连自动化经验，几个值得注意的技术细节：

1. **CLI 凭证落盘位置明确**：CN 线 `~/.qoderworkcn`，国际线 `~/.qoder`——与逆向 Trae 系列的 token 提取思路一致，可直接检查认证文件形态
2. **CN 线 PAT 是官方暴露的稳定凭证**（`qoder.com.cn/account/integrations` 创建），社区项目 `avaritiachaos/qoder-proxy` 已验证「PAT + `qoderclicn` → 本地 OpenAI/Anthropic 兼容接口」的链路（仅限个人账号本机研究用途，该项目明确禁止公网部署与共享）
3. **官方有「每日领取 100 Credits」活动**（docs.qoder.cn/events/100credits）——如评估是否纳入签到体系，此入口值得优先调研接口形态
4. **全家桶线额度全线共享**意味着移动端操作也消耗额度；原灵码线额度仅在 IDE 三件套生效，Mobile/QoderWork/CLI 用不到
5. AK/SK 登录的存在说明其鉴权体系与阿里云 RAM 体系有交集——原灵码线部分接口可能复用阿里云 STS/签名逻辑

---

## 五、信息来源

| 来源 | 内容 |
|---|---|
| help.aliyun.com/zh/lingma/faq | 两套账号关系、Credits 互通性、登录异常排查 |
| help.aliyun.com/zh/lingma（个人版登录） | 账号登录 / AK/SK 登录步骤、多 IDE 登录状态同步 |
| docs.qoder.cn/mobile/app/remote-control | 移动端远程控制能力（同账号登录、审批、Plan 审核） |
| docs.qoder.cn 产品页 | 产品家族构成（Mobile 2026-04-30 上线、眼镜版等） |
| github.com/avaritiachaos/qoder-proxy | CLI 认证方式（CN=PAT / Global=OAuth）、凭证目录、PAT 创建入口 |
| 知乎「Qoder 移动端上线」教程、php.cn 百科条目 | `/remote-control` 扫码配对流程、二维码 30 秒刷新细节（第三方描述，未经官方文档直接确认） |
| 百度百科 Qoder 词条 | 产品时间线（团队版 2025-12、QoderWork 2026-01、移动端 2026-04-30） |

> AI生成