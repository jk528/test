# OfficeAce 专家智能体清单

> 数据来源：OfficeAce 本地专家注册表 `user-experts.json`（用户目录 `users/<uid>/user-experts.json`）
> 统计范围：`visibility = public` 的全部专家智能体，共 **58 位**，分属 **7 大类别**
> 每个专家均支持 `@专家名` 唤起，默认模型 `deepseek-v4.1-flash`，提供方 `huawei-maas`

---

## 一、总览

| 序号 | 类别（category） | 类别名称 | 专家数量 |
|------|------------------|----------|----------|
| 1 | product | 产品研发 | 18 |
| 2 | marketing-growth | 市场增长与商业化 | 12 |
| 3 | office | 办公协作 | 8 |
| 4 | insight | 洞察研究 | 7 |
| 5 | learning-education | 学习教育 | 6 |
| 6 | business | 商业业务 | 4 |
| 7 | finance | 金融财经 | 3 |
| | | **合计** | **58** |

---

## 二、产品研发（product，18 位）

| 专家名称 | 智能体 ID | 岗位分工 | 核心能力 | 关联技能 |
|----------|-----------|----------|----------|----------|
| 软件研发负责人 | expert-software-rd-lead | 统一需求、架构、测试到发布的标准，善于组织合适的技术专家，把业务目标转化为边界清晰、可以验收的软件成果。 | 研发管理、交付验收、技术决策、范围管控 | task-implement、handoff、caveman、docx-craft |
| 产品与架构师 | expert-product-architect | 擅长在"做什么"与"如何实现"之间作出关键取舍，把用户任务转化为清晰的产品范围、用户流程、验收标准和技术架构。 | 产品范围、技术架构、验收标准、关键取舍 | market-researcher、zoom-out、excalidraw-diagram |
| 客户端工程师 | expert-client-engineer | 精通 Web、移动端与小程序的客户端实现，按目标平台选择合适技术，交付交互流畅、异常可控、性能可靠的界面。 | 客户端实现、交互状态、响应式、可访问性 | frontend-dev、impeccable、responsiveness-check、wechat-miniprogram、react-native-dev、flutter-dev |
| 服务端工程师 | expert-server-engineer | 深耕服务端逻辑、数据库、权限与第三方集成，重视数据一致性、安全与可维护性，让每个接口都经得起验证。 | 服务端逻辑、数据一致性、接口设计、安全 | fullstack-dev、mcp-builder、setup-pre-commit、api-gateway |
| 质量工程师 | expert-quality-engineer | 用测试、调试与代码审查验证软件是否真正满足需求，如实呈现覆盖范围与未验证事项，绝不把"未发现问题"说成"没有问题"。 | 测试、调试、代码审查、风险识别 | tdd、diagnose、skill-vetter、web-performance-audit |
| 发布工程师 | expert-release-engineer | 打理代码仓库、持续集成与部署环境的每一处细节，确保软件安全发布、随时可观察、出问题能快速回滚。 | 持续集成、部署、回滚、上线检查 | vercel-deploy、web-deploy、github |
| 产品设计负责人 | expert-product-design-lead | 善于把商业目标、人群与技术限制折算成设计决策，将研究、交互、视觉与原型整合成体验一致的产品。 | 设计整合、产品体验、设计目标、验证建议 | task-implement、handoff |
| 用户研究员 | expert-user-researcher | 识别目标用户、关键任务与使用障碍，把真实场景中的行为变成产品决策可以依赖的证据。 | 用户识别、任务场景、用户分群、证据基础 | market-researcher、browser-use、material-organizer、summarize、xlsx-craft |
| 产品策略师 | expert-product-strategist | 把用户研究与商业目标转化为产品定位、优先级和验收标准，想清楚首版不做什么，让团队少走弯路。 | 产品定位、功能范围、优先级、成功指标 | idea-validator、docx-craft |
| 交互设计师 | expert-interaction-designer | 打理产品导航、用户流程与页面结构，关注每一步状态变化与异常出口，让用户始终知道自己在哪、下一步去哪。 | 产品导航、用户流程、页面结构、状态设计 | impeccable、excalidraw-diagram |
| 视觉与设计系统专家 | expert-visual-design-system | 把控色彩、字体与组件的视觉方向，用设计系统确保信息层级清晰、品牌一致、人人可用。 | 色彩字体、版式、组件、品牌一致 | awesome-design-md、brand-guidelines、canvas-design、pptx-craft |
| 原型与体验验证工程师 | expert-prototype-validation-engineer | 把设计方案变成可运行、可测试的前端原型，逐一检查响应式、性能与目标完成度，让设计在动起来之后接受检验。 | 前端原型、响应式、性能、目标完成度 | frontend-dev、landing-page-generator、product-showcase-site、tdesign-miniprogram、github、responsiveness-check、web-performance-audit |
| 华为云插件 | expert-huaweicloud-devkit | 让 AI 智能体掌握华为云全流程操作——构建、部署、运维全程受控，助您轻松安全上云。 | 华为云 ECS/CCE、VPC/安全组、RDS/GaussDB、OBS、FunctionGraph/APIG、ModelArts、IAM、成本与配额、故障排查、安全合规 | huaweicloud-core、huaweicloud-safety、huaweicloud-cli-and-auth、huaweicloud-capability-discovery、huaweicloud-api-and-sdk、huaweicloud-troubleshooting、huawei-getting-started、huawei-voucher、huawei-ecs、huawei-obs、huawei-vpc、huawei-iam、huawei-iac、huawei-rds、huawei-gaussdb、huawei-functiongraph、huawei-apig、huawei-cce、huawei-smn-dms、huawei-modelarts、huawei-cloud-eye、huawei-cts、huawei-dew、huawei-billing、huawei-cbr、huawei-waf-aad、huawei-dds-dcs、huawei-deployment、huawei-sandbox、huaweicloud-devkit-status |
| 华为云服务器助手 | expert-huaweicloud-ops | 华为云基础设施全生命周期运维伙伴：查询诊断、变更操作、运维配置、架构编排；ECS/FlexusX/FlexusL/CCI 四类实例自动识别并分族路由，26 个专属 skill 覆盖计算、网络、存储、监控告警、计费询价、远程运维、容器与 IaC。 | ECS/FlexusX/FlexusL 生命周期、SSH 免密登录、安全组与 DNS 管理、云盘与快照运维、监控告警、计费与询价、COC 远程脚本、CCI 容器实例、OBS 对象存储、Terraform IaC | huawei-cloud-computing-query、huawei-cloud-ecs-lifecycle、huawei-cloud-ecs-alert、huawei-cloud-ecs-passwordless-login、huawei-cloud-ces-ecs-monitoring、huawei-cloud-monitoring-query、huawei-cloud-network-query、huawei-cloud-network-ops、huawei-cloud-storage-query、huawei-cloud-storage-ops、huawei-cloud-billing-scout、huawei-cloud-business-tf-support、huawei-cloud-obs-bucket-create、huawei-cloud-obs-upload、huawei-cloud-obs-stats、huawei-cloud-obs-website-host、huawei-cloud-iam-query、huawei-cloud-cci-instance-management、huawei-cloud-functiongraph-function-create、huawei-cloud-functiongraph-trigger-create、huawei-cloud-flexus-l-server-manage、huawei-cloud-flexus-l-server-ops、huawei-cloud-flexus-l-server-scripts-excute、huawei-cloud-terraform-generator、huawei-cloud-terraform-installer、huawei-cloud-find-skills |
| 产品专家 | expert-product | 在商业指标与技术成本之间持续寻找最高杠杆的解法，坚信产品的护城河源于对用户痛苦的诚实回应。 | 产品设计、需求分析、场景分析、商业化设计、用户体验 | — |
| 架构专家 | expert-architecture | 视每一个架构决策为可逆性、成本与演化能力的三角博弈，坚信好的架构是在约束条件下演化出来的。 | 架构设计、技术规划、系统设计、可演化性分析、技术选型 | — |
| 开发工程师 | expert-development | 在需求评审时追问边界条件，在代码审查时死磕可维护性，笃信程序员的最高修养是让自己写的代码能被三个月后的陌生人轻松接住。 | 代码开发、架构实现、边界条件分析、代码审查、可维护性优化 | — |
| 项目经理 | expert-project-manager | 对进度永远保持一种健康的焦虑，对范围蔓延保持一种近乎生理性的警觉，坚持项目成功的标准不是准时上线。 | 项目管理、进度跟踪、风险管控、干系人沟通、范围管理 | — |

---

## 三、市场增长与商业化（marketing-growth，12 位）

| 专家名称 | 智能体 ID | 岗位分工 | 核心能力 | 关联技能 |
|----------|-----------|----------|----------|----------|
| 市场营销总监 | expert-marketing-director | 善于理解商业目标、产品特点与预算约束，把市场洞察、定位、内容与增长行动组织成一套步调一致的营销方案。 | 营销策略、定位、预算管理、方案整合 | task-implement、handoff |
| 市场与受众洞察专家 | expert-market-audience-insight | 专注研究目标用户、需求场景与市场趋势，从竞争表达和渠道信号中提炼证据，让每一次营销决策都有据可依。 | 用户研究、市场趋势、竞争表达、渠道信号 | market-researcher、admapix、ecomseer |
| 品牌与营销策略师 | expert-brand-marketing-strategist | 善于从市场洞察中提炼品牌定位与价值主张，定下发布策略与传播主题，让后续内容与创意有章可循。 | 品牌定位、价值主张、传播主题、渠道策略 | marketing-skills、Marketing_Mode、brand-guidelines、pptx-craft |
| 内容与渠道主编 | expert-content-channel-editor | 建立统一的内容叙事，产出核心内容并改编成适合不同渠道的版本，让每一次发布都整齐划一、可直接使用。 | 内容叙事、渠道改编、文案、发布 | content-factory、content-ops、Copywriting、content-repurposer、wechat-article-pro、humanizer、email-craft |
| 创意与营销体验制作人 | expert-creative-experience-producer | 把营销策略转化为主视觉、宣传视频与落地页，让视觉与页面共同讲述同一个故事，服务理解与转化。 | 主视觉、宣传视频、落地页、产品展示 | promo-creator-skills、nano-banana-pro、canvas-design、remotion-video-toolkit、landing-page-generator、product-showcase-site |
| 增长与营销分析师 | expert-growth-marketing-analyst | 设计、运行并复盘增长实验，追踪曝光、点击、转化与渠道成本，用数据回答增长从哪里来、到哪里去。 | 增长实验、转化分析、渠道成本、收入归因 | growth-engine、conversion-ops、revenue-intelligence、seo-ops、xlsx-craft |
| 产品商业化负责人 | expert-product-commercialization-lead | 擅长把产品能力与用户需求转化为可验证的商业路径，在市场、定价、渠道与销售方式之间帮您作出明确选择。 | 商业路径、定价、进入市场、风险识别 | task-implement、handoff |
| 市场机会分析师 | expert-market-opportunity-analyst | 专门判断机会的真伪：问题是否真实且重要、用户是否愿意改变、市场有没有进入空间、竞争压力有多大。 | 市场机会、问题强度、竞争格局、假设验证 | market-researcher、qcc-company、perplexity |
| 商业模式策略师 | expert-business-model-strategist | 设计目标客户、价值主张与收入来源，比较不同商业路径的成立条件，帮您找到可以验证的盈利模式。 | 商业模式、价值主张、收入来源、路径比较 | idea-validator、Marketing_Mode、the-entrepreneurship-handbook |
| 定价与财务分析师 | expert-pricing-finance-analyst | 设计套餐与价格体系，搭建成本结构和单位经济模型，测算收入、毛利与现金需求，让每个数字都经得起推敲。 | 套餐定价、单位经济、毛利测算、敏感性分析 | finance-ops、Financial_Analysis_Agent、Financial_Calculator_Pro、Financial_Due_Diligence_Analyzer、xlsx-craft |
| 上市与销售增长专家 | expert-launch-sales-growth | 选定首批客户与市场切入点，设计增长实验和销售剧本，把产品准备、市场传播与销售转化串成一条线。 | 首批客户、渠道切入、销售剧本、销售管道 | marketing-skills、growth-engine、conversion-ops、sales-playbook、sales-pipeline、revenue-intelligence |
| 商业交付与签约专家 | expert-commercial-delivery-signing | 把产品价值与商业方案转化为销售提案、演示材料与签约文件，让每一次交付都专业得体、直击决策。 | 销售提案、演示材料、签约材料、权限边界 | product-showcase-site、landing-page-generator、Copywriting、tencent-esign-contract、fadada-document-sign、docx-craft、pptx-craft、email-craft |

---

## 四、办公协作（office，8 位）

| 专家名称 | 智能体 ID | 岗位分工 | 核心能力 | 关联技能 |
|----------|-----------|----------|----------|----------|
| 文档专家 | expert-document | 精通各类文件格式转换与内容提取，面对混乱的文档需求，总能给出精确到页码的解决方案。 | 文档编写、格式转换、内容提取、排版设计、多格式处理 | official-doc-formatter、xlsx-craft |
| 策划助理 | expert-planning | 擅长将天马行空的想法进行落地，让创意不至于飘在空中。 | 创意策划、方案输出、逻辑拆解、执行规划、创意落地 | lidan-writing-framework |
| PPT专家 | expert-ppt | 坚信逻辑是骨架、数据是血肉、设计是衣裳，目标是让你在台上讲得更精彩。 | PPT设计、逻辑梳理、视觉设计、演讲辅助、数据可视化 | pptx-craft、xlsx-craft |
| 会议助手 | expert-meeting | 从发起邀约到待办追踪全程包办，一旦会议跑题，会温和提醒回归议程。 | 会议组织、议程管理、待办追踪、时间控制、纪要整理 | meeting-autopilot-pro、openai-whisper-cn、email-craft |
| 纪要专员 | expert-meeting-notes | 能把多方混杂的语音讨论，提炼为决策、待办、信息项的清晰记录，绝不遗漏关键结论。 | 纪要整理、决策提炼、待办提取、结构化输出、信息归档 | openai-whisper-cn、official-doc-formatter、meeting-autopilot-pro |
| 速记文员 | expert-transcription | 无条件还原对话，交付干净利落的逐字稿，不增不减。 | 语音转文字、逐字稿、极速转录、多人对话区分、原文还原 | openai-whisper-cn、official-doc-formatter |
| 项目助理 | expert-project-assistant | 用文档和邮件编织信息同步网，确保任何变更都有迹可循、有人可找。 | 进度跟踪、信息同步、变更管理、文档整理、邮件沟通 | meeting-autopilot-pro、email-craft、official-doc-formatter |
| 法务助理 | expert-legal | 善于将复杂的法律事务转化为清晰的标准化回复，一旦发现潜在风险，会立即停止生成回复并将问题转交专业法律顾问。 | 合同审查、法律风险识别、标准化回复、法规查询、风险转介 | canned-responses-review |

---

## 五、洞察研究（insight，7 位）

| 专家名称 | 智能体 ID | 岗位分工 | 核心能力 | 关联技能 |
|----------|-----------|----------|----------|----------|
| 用户研究专家 | expert-user-research | 善于从访谈噪音中萃取真实需求与痛点，并将其转译成可落地的洞察与用户画像。 | 用户访谈、需求分析、用户画像、同理心地图、定性研究 | daily-briefing、xlsx-craft、pptx-craft、deepresearch |
| 市场洞察分析师 | expert-market-insight | 外部情报与内部数据的侦探，擅长拼接碎片信息，用数据透视出异常信号和增长机会。 | 市场分析、竞品研究、数据分析、增长机会识别、情报收集 | — |
| 首席研究官 | expert-chief-researcher | 擅长把宽泛的问题转化为清晰的研究框架，组织市场、学术、数据与情报专家协同作答，诚实标注每一步的不确定性。 | 研究框架、证据区分、决策支持、不确定性评估 | task-implement、handoff |
| 市场与情报研究员 | expert-market-intelligence-researcher | 善于从公开网页、新闻与行业资料中打捞关键情报，拼出市场边界、用户需求与竞争格局的完整图景。 | 市场研究、竞争格局、情报收集、来源核查 | perplexity、tavily、web-search-exa、market-researcher、qcc-company、admapix |
| 学术与证据研究员 | expert-academic-evidence-researcher | 专注发现和精读相关论文，提取研究问题、方法与实验结果，审查每一条证据的来源与论证链条，绝不夸大一分。 | 论文阅读、证据审查、事实核查、论证链条 | arxiv-watcher、arxiv-reader、paper-quick-reader、academic-translation、citation-manager、jiaozhen-factcheck |
| 数据洞察分析师 | expert-data-insight-analyst | 擅长整理研究数据与业务表格，从趋势、分布与异常中识别变量关系，交付条理清晰、可供复核的洞察。 | 数据分析、趋势识别、异常检测、可审计性 | xlsx-craft、Financial_Analysis_Agent |
| 洞察与报告编辑 | expert-insight-report-editor | 把市场、学术与数据研究编织成结构清晰的洞察报告，统一术语、核对证据、标明限制，让每个结论都能追溯来源。 | 报告结构、术语统一、来源追溯、证据组织 | material-organizer、summarize、markitdown-skill、humanizer、docx-craft、pptx-craft |

---

## 六、学习教育（learning-education，6 位）

| 专家名称 | 智能体 ID | 岗位分工 | 核心能力 | 关联技能 |
|----------|-----------|----------|----------|----------|
| 首席备考教练 | expert-chief-exam-coach | 根据考试目标、剩余时间与当前水平制定可执行的备考方案，让学习者随时清楚今天该学什么、掌握得怎么样。 | 备考规划、掌握评估、复习安排、动态调整 | task-implement、handoff |
| 学习规划师 | expert-study-planner | 根据目标、期限与可用时间制定阶段、每周和每日计划，为每一步设好完成标准，让学习节奏始终在轨道上。 | 阶段规划、每周计划、每日计划、完成标准 | study-planner、xlsx-craft、email-craft |
| 启发式学科导师 | expert-heuristic-subject-tutor | 擅长把概念讲透、把例题拆开、把误区点破，引导学习者自己想通解题思路，而不只是给出一个答案。 | 概念讲解、例题拆解、误区辨析、知识迁移 | notebooklm-studio、knowledge-framework-builder、pptx-craft |
| 学习材料设计师 | expert-study-material-designer | 把教材、网页和笔记整理成知识框架与主题笔记，理清概念关系与易混淆点，让复习材料一目了然、拿来即用。 | 知识框架、主题笔记、概念关系、复习材料 | material-organizer、markitdown-skill、summarize、docx-craft |
| 测评与记忆训练师 | expert-assessment-memory-trainer | 围绕考试范围生成诊断题、模拟题与抽认卡，从错因分析中锁定薄弱环节，让每一次练习都练在刀刃上。 | 诊断题、练习题、模拟题、错因分析 | education、tutor-skills |
| 英语专项教练 | expert-english-coach | 精读英语文章、拆解词汇与语法，按考试标准逐句批改作文并给出升档建议，让每一篇练习都有的放矢。 | 英语精读、词汇语法、作文批改、升档建议 | english-intensive-reader、english-exam-writing-reviewer |

---

## 七、商业业务（business，4 位）

| 专家名称 | 智能体 ID | 岗位分工 | 核心能力 | 关联技能 |
|----------|-----------|----------|----------|----------|
| 运营专家 | expert-operations | 不迷信最佳实践，只信A/B测试和复盘里暴露出的用户真实选择，把每一次活动都当成一次可量化的假设检验。 | 运营策划、数据分析、A/B测试、增长策略、复盘优化 | — |
| 商务拓展助理 | expert-bd | 先于合作方察觉沉默成本，先于合同条款预判执行阻力，把BD的核心能力定义为"让对方赢的同时，公司也稳赚"。 | 商务拓展、合作谈判、价值挖掘、风险预判、利益分析 | — |
| 售前工程师 | expert-presales | 演示时说的每一句话都要能经受住PoC的拷打，笃信最好的售前不是把产品吹上天，而是客户在签单前就清楚这个系统的所有能力边界。 | 技术演示、PoC执行、需求理解、方案设计、信任建立 | — |
| 商务助理 | expert-business | 擅长将商业诉求包装成精美得体的方案文件与标准商务信函，一切为了促成合作。 | 商务写作、方案包装、信函撰写、形象设计、沟通协调 | email-craft、pptx-craft |

---

## 八、金融财经（finance，3 位）

| 专家名称 | 智能体 ID | 岗位分工 | 核心能力 | 关联技能 |
|----------|-----------|----------|----------|----------|
| 投研专家 | expert-investment-research | 常年潜伏在财报脚注和供应链的隐秘角落，只为捕捉那个能让估值逻辑彻底翻盘的预期差。 | 财务分析、估值建模、供应链分析、预期差识别、行业研究 | — |
| 商业尽调顾问 | expert-commercial-dd | 在交易风险排查领域有15年经验的商业尽调顾问，曾服务于顶级PE和跨境并购案。 | 商业尽调、风险识别、财务分析、跨境并购、尽职调查 | — |
| 客户风险分析专家 | expert-customer-risk-analysis | 负责客户风险分类全流程作业。读取客户历史信息后，依据客户类型选择评估路径——运营商客户优先用知识图谱，互联网等一般企业走财报解析+信用风控模型，金融/政府机构用外部评级+转换逻辑。财报自含解析，外部工商/股权/诉讼/舆情/评级信息通过 web-search 采集公开信息与风评，保留来源 URL 与采集时间；不依赖外部 MCP 连接器。同一数据和规则下结果稳定，能用规则、公式、图谱确定的内容不由模型自由猜测。完整生成正式 Word 报告后一次性交付，需确认项在报告"人工确认项"章节集中列出。 | 客户风险分类、财报分析、外部信息提炼、风险评级、知识图谱应用 | customer-risk-classification、financial-report-analysis、finance-data-processing、docx-craft、xlsx-craft、perplexity、tavily、web-search-exa |

---

## 九、补充说明

1. **唤起方式**：在对话中输入 `@专家名称` 即可唤起对应专家智能体，例如 `@法务助理`、`@PPT专家`。
2. **分类口径**：类别取自注册表 `category` 字段，包含 `product`、`marketing-growth`、`office`、`insight`、`learning-education`、`business`、`finance` 七类。
3. **关联技能**：列出该专家预置的技能（skill），标 `—` 表示注册表中该专家暂未预置技能，主要依靠通用能力作答。
4. **非专家智能体**：除上述 58 位公开专家外，系统还存在 `agent_office`（通用助手）、`agent_agentteam` / `agent_agentteams`（团队协作载体）、`agent_assistant`、`agent_default` 等非专家角色的运行单元，不属于本清单的"专家智能体"统计范围。
5. **本清单为只读汇总**，不影响任何专家配置；如需新增/停用专家，请通过 OfficeAce 客户端界面操作。