# ColorTxt 字体下载与设置全过程

> **文档用途**：记录给 ColorTxt（彩读）添加思源黑体、设为默认字体、增加字重调节功能的完整过程。
> 后期如需重做，按本文档顺序操作即可；恢复 GitHub 原版后也可照此重开。
> **项目路径**：`c:\Users\Administrator\Documents\这是什么\JK-temp\彩读分析\.temp\ColorTxt`
> **整理日期**：2026-09-21

---

## 一、背景与目标

| 项目 | 说明 |
|---|---|
| 应用技术栈 | Electron + Vue 3 + electron-vite，阅读正文使用 **Monaco Editor** 渲染 |
| 原版情况 | 仅内置「京華老宋体」（`KingHwa_OldSong_3.0.ttf`），字体选择器中有系统字体近似预设，但没有思源黑体 |
| 改造目标 | ① 内置思源黑体 7 个字重；② 设为阅读默认字体；③ 设置面板可切换字重；④ 字重设置持久化、跨窗口保留 |
| 改造原则 | 字体文件随安装包打包（`@font-face`），不依赖用户系统是否安装字体，全平台可用 |

---

## 二、思源黑体字重对照表

思源黑体（Source Han Sans SC / Noto Sans CJK SC）一个字体家族包含 7 个独立字重文件，每个文件在 CSS 中用不同的 `font-weight` 数值区分：

| 序号 | 字体文件 | CSS font-weight | 显示名 |
|---|---|---|---|
| 1 | SourceHanSansSC-ExtraLight.otf | 200 | ExtraLight 特细 |
| 2 | SourceHanSansSC-Light.otf | 300 | Light 细体 |
| 3 | SourceHanSansSC-Normal.otf | 350 | Normal 常规 |
| 4 | SourceHanSansSC-Regular.otf | 400 | Regular 标准 |
| 5 | SourceHanSansSC-Medium.otf | 500 | Medium 中等 |
| 6 | SourceHanSansSC-Bold.otf | 700 | Bold 粗体 |
| 7 | SourceHanSansSC-Heavy.otf | 900 | Heavy 特粗 |

> **注意**：350 是非标准 CSS 字重值（介于 300 和 400 之间），对应思源黑体官方的 Normal 字重。Monaco 与浏览器均支持数字字重，可正常命中对应字形。

---

## 三、实施全过程（共 5 步）

### 步骤 1：放入字体文件

把 7 个 OTF 文件复制到渲染层资源目录：

```
src/renderer/src/assets/
├── SourceHanSansSC-ExtraLight.otf
├── SourceHanSansSC-Light.otf
├── SourceHanSansSC-Normal.otf
├── SourceHanSansSC-Regular.otf
├── SourceHanSansSC-Medium.otf
├── SourceHanSansSC-Bold.otf
└── SourceHanSansSC-Heavy.otf
```

**关键点**：

- 放在 `src/renderer/src/assets/` 下，Vite 构建时自动处理路径与打包；
- 字体文件约 8～10 MB/个，7 个字重会增大安装包体积，但可保证离线可用；
- 必须用 **OTF 原文件**，不要用网络字体 CDN（Electron 内容安全策略 CSP 会拦截，且离线不可用）。

### 步骤 2：在全局样式注册 @font-face

在 [src/renderer/src/style.css](./.temp/ColorTxt/src/renderer/src/style.css) 顶部（原京華老宋体 `@font-face` 之后）注册 7 个同名字体家族：

```css
/* 内置思源黑体（Source Han Sans SC）——覆盖 7 个字重 */
@font-face {
  font-family: "Source Han Sans SC";
  src: url("./assets/SourceHanSansSC-ExtraLight.otf") format("opentype");
  font-weight: 200;
  font-style: normal;
  font-display: swap;
}
/* …其余 6 个结构完全相同，只换字体文件名与 font-weight：
   Light=300 / Normal=350 / Regular=400 / Medium=500 / Bold=700 / Heavy=900 */
```

**关键点**：

- 7 个 `@font-face` 的 `font-family` **必须同名**（都是 `"Source Han Sans SC"`），仅靠 `font-weight` 区分，浏览器才会按字重自动选文件；
- `font-display: swap`：字体加载前先用替代字体显示，加载完再切换，避免首屏白屏；
- `format("opentype")` 对应 `.otf`（若是 `.ttf` 则写 `format("truetype")`）。

### 步骤 3：在字体选择器预设中登记

在 [src/renderer/src/utils/presetFontDefinitions.ts](./.temp/ColorTxt/src/renderer/src/utils/presetFontDefinitions.ts) 中把思源黑体加为内置预设项（id：`sourcehan`）：

```ts
/** 预设 id 联合类型中加入 */
type PresetFontId = "kingsong" | "sourcehan" | /* …其余系统字体 */;

/** 预设 CSS 字体栈：思源黑体为内置字体，直接用家族名，无需系统回退列表 */
const PRESET_CSS_STACKS = {
  sourcehan: { all: ["Source Han Sans SC"] },
};

/** 字体选择器中显示的名称（全平台统一显示「思源黑体」）*/
const PRESET_DISPLAY_NAMES = {
  sourcehan: { darwin: "思源黑体", win32: "思源黑体", other: "思源黑体" },
};
```

**关键点**：

- 京華老宋体与思源黑体属于**内置字体**（`@font-face` 打包），字体栈只有家族名本身；
- 其他预设（如宋体、黑体）是**系统字体近似替代**，字体栈需要列多个平台名称做回退；
- `getPresetCssStack("sourcehan")` 是后续设默认字体用的工具函数，返回 `'"Source Han Sans SC"'`。

### 步骤 4：设为阅读默认字体

在 [src/renderer/src/monaco/readerEditorOptions.ts](./.temp/ColorTxt/src/renderer/src/monaco/readerEditorOptions.ts) 修改默认字体常量：

```ts
// 修改前：默认是京華老宋体
// 修改后：
export const READER_EDITOR_DEFAULT_FONT_FAMILY = getPresetCssStack("sourcehan");
```

**关键点**：

- 该常量是 Monaco 阅读编辑器的初始 `fontFamily`，新用户/重置设置后默认就是思源黑体；
- 已经使用过应用的用户，其保存的设置里仍记录旧字体，需在设置面板手动选一次思源黑体（或清空设置）。

### 步骤 5：增加字重调节功能（主界面）

#### 5.1 定义字重常量 —— src/renderer/src/constants/appUi.ts

```ts
/** 默认字重 */
export const defaultReaderFontWeight = 400;

/** 思源黑体内置 7 个字重（CSS font-weight 值）*/
export const SOURCE_HAN_SANS_WEIGHTS = [200, 300, 350, 400, 500, 700, 900] as const;

/** 字重下拉显示名 */
export const SOURCE_HAN_SANS_WEIGHT_LABELS: Record<number, string> = {
  200: "ExtraLight 特细",
  300: "Light 细体",
  350: "Normal 常规",
  400: "Regular 标准",
  500: "Medium 中等",
  700: "Bold 粗体",
  900: "Heavy 特粗",
};

/** 归一化字重：必须是内置字重之一，否则回退 400（防止存档里出现非法值）*/
export function normalizeReaderFontWeight(weight: unknown): number {
  if (typeof weight !== "number" || !Number.isFinite(weight)) {
    return defaultReaderFontWeight;
  }
  return SOURCE_HAN_SANS_WEIGHTS.includes(weight)
    ? weight
    : defaultReaderFontWeight;
}
```

#### 5.2 字重下拉 UI —— src/renderer/src/components/SettingsReadingPanel.vue

在「阅读」→「字体」区域，当选中**思源黑体**时显示字重下拉框（7 个选项）：

- 新增 prop：`draftFontWeight?: number`（用 `withDefaults` 给默认值 `defaultReaderFontWeight`，保证找书窗口不传该 prop 时不报错）；
- 新增 emit：`update:draftFontWeight`，用 `v-model:draft-font-weight` 双向绑定；
- 下拉数据遍历 `SOURCE_HAN_SANS_WEIGHTS`，显示文本用 `sourceHanSansWeightLabel()`。

#### 5.3 设置面板接线 —— src/renderer/src/components/SettingsPanel.vue

- `SettingsApplyPayload` 类型新增 `fontWeight: number` 字段；
- 组件 props 新增 `readerFontWeight: number`；
- 草稿 `draftFontWeight`：初始化、`syncDraftFromProps()` 同步、`resetReadingDraft()` 重置、`onConfirm()` 提交，四处都要加。

#### 5.4 应用层状态 —— src/renderer/src/App.vue

```ts
const readerFontWeight = ref(defaultReaderFontWeight);
```

- 传给 `useAppPersistence()` 参与持久化；
- `applySettings()` 中接收并归一化：`normalizeReaderFontWeight(payload.fontWeight)`；
- `applyReaderAppearanceFromSettings()` 中调用 `readerRef.value?.setFontWeight(readerFontWeight.value)`；
- 模板把 `:reader-font-weight="readerFontWeight"` 传给设置面板。

#### 5.5 Monaco 编辑器生效 —— src/renderer/src/components/ReaderMain.vue

核心规则：**只有字体栈含思源黑体时才应用数字字重，其他字体一律 normal**：

```ts
let currentFontWeight = defaultReaderFontWeight;

function effectiveFontWeight(): string {
  return currentFontFamily.includes("Source Han Sans SC")
    ? String(currentFontWeight)
    : "normal";
}

/** 对外暴露的字重设置方法 */
function setFontWeight(weight: number) {
  const e = editor.value;
  if (!e) return;
  currentFontWeight = weight;
  e.updateOptions({ fontWeight: effectiveFontWeight() });
}
```

在创建编辑器、更新字体（`setFontFamily`）等所有 `updateOptions` 的位置，fontWeight 都要用 `effectiveFontWeight()`，不能写死。

**防首屏闪烁处理**（切到思源黑体时）：

```ts
if (currentFontFamily.includes("Source Han Sans SC")) {
  void document.fonts
    ?.load(`${currentFontWeight} ${fontSize}px "Source Han Sans SC"`)
    .then(() => {
      e.updateOptions({ fontFamily: currentFontFamily, fontWeight: effectiveFontWeight() });
    });
}
```

先通过 Font Loading API 预加载对应字重字形，加载完再更新编辑器，避免大字重文件首次渲染时出现回退字体闪烁。

#### 5.6 持久化（重启/同步不丢失）

| 文件 | 改动 |
|---|---|
| src/renderer/src/composables/useAppPersistence.ts | 保存时写入 `fontWeight: deps.readerFontWeight.value`；读取时用 `normalizeReaderFontWeight()` 校验恢复 |
| src/renderer/src/services/settingsPersistMerge.ts | 合并键白名单加入 `"fontWeight"` |
| src/renderer/src/stores/cacheStore.ts | 缓存数据类型加 `fontWeight?: number`；合并时数字且有限才采纳 |

---

## 四、涉及文件总清单

| # | 文件 | 改动类型 | 作用 |
|---|---|---|---|
| 1 | src/renderer/src/assets/SourceHanSansSC-*.otf（7个） | 新增 | 7 个字重字体文件 |
| 2 | src/renderer/src/style.css | 修改 | 注册 7 个 @font-face |
| 3 | src/renderer/src/utils/presetFontDefinitions.ts | 修改 | 登记 sourcehan 预设 |
| 4 | src/renderer/src/monaco/readerEditorOptions.ts | 修改 | 默认字体改为思源黑体 |
| 5 | src/renderer/src/constants/appUi.ts | 修改 | 字重常量、标签、归一化函数 |
| 6 | src/renderer/src/components/SettingsReadingPanel.vue | 修改 | 字重下拉 UI |
| 7 | src/renderer/src/components/SettingsPanel.vue | 修改 | 设置面板草稿/提交接线 |
| 8 | src/renderer/src/App.vue | 修改 | 字重状态与应用 |
| 9 | src/renderer/src/components/ReaderMain.vue | 修改 | Monaco setFontWeight 生效逻辑 |
| 10 | src/renderer/src/composables/useAppPersistence.ts | 修改 | 字重持久化 |
| 11 | src/renderer/src/services/settingsPersistMerge.ts | 修改 | 持久化合并白名单 |
| 12 | src/renderer/src/stores/cacheStore.ts | 修改 | 缓存数据字重字段 |

---

## 五、验证方法

1. **类型检查**：项目根目录执行 `npm run typecheck`，必须 0 错误；
2. **启动应用**：`npm run dev`，打开任意 TXT 小说；
3. **默认字体验证**：正文应直接以思源黑体 Regular（400）显示；
4. **字重切换验证**：设置 → 阅读 → 字体选中「思源黑体」→ 字重下拉依次切换 7 档，正文字形应实时变细/变粗；
5. **其他字体不受影响验证**：切到京華老宋体或系统字体，字重应固定 normal，不报错；
6. **持久化验证**：关闭并重新打开应用，字重保持上次选择；
7. **DevTools 核对**：找书窗口/主窗口按 F12，Computed 样式中 `font-family` 含 `Source Han Sans SC`。

---

## 六、恢复与重开指引

### 6.1 想放弃全部修改、回到官方原版

```powershell
# 在项目根目录（含 .git 的目录）执行
git status --short          # 先查看将被影响的文件
git checkout -- src/renderer/src/style.css `
                  src/renderer/src/utils/presetFontDefinitions.ts `
                  src/renderer/src/monaco/readerEditorOptions.ts `
                  src/renderer/src/constants/appUi.ts `
                  src/renderer/src/components `
                  src/renderer/src/composables/useAppPersistence.ts `
                  src/renderer/src/services/settingsPersistMerge.ts `
                  src/renderer/src/stores/cacheStore.ts
```

再手动删除 7 个 `SourceHanSansSC-*.otf`（未被 git 跟踪的新文件），然后执行 `npm run typecheck` 确认，最后 `npm run dev` 重开。

### 6.2 只想重开字体功能（保留其他改动）

按本文档「三、实施全过程」5 个步骤顺序重做即可，每完成一步跑一次 `npm run typecheck`。

### 6.3 改了主进程/preload 后必须重启

- 修改 **渲染层**（`.vue`、`style.css`、assets）：Vite 热更新自动生效；
- 修改 **主进程 / preload / shared**：必须停掉 `npm run dev` 重新启动，否则界面调用的是旧接口（这也是之前导出功能报错的根因之一）。

---

## 七、注意事项与踩坑记录

1. **@font-face 同名不同重**：7 个声明 `font-family` 必须完全一致，拼错一个字就会变成两个独立字体家族，字重切换失效；
2. **fontWeight 仅对思源黑体生效**：Monaco 对不含多字重的字体传数字可能无效，统一通过 `effectiveFontWeight()` 回退 `"normal"`；
3. **字体路径必须相对 CSS 文件**：`url("./assets/xxx.otf")` 是相对 `style.css` 所在目录，不要从项目根目录开始写；
4. **旧用户设置覆盖默认值**：改了默认字体常量只影响新设置，老用户存档里的字体不会自动变；
5. **字重值必须归一化**：存档可能被手动改坏或来自旧版本，读取时一律过 `normalizeReaderFontWeight()`；
6. **构建体积**：7 个全字符集 OTF 体积较大，如追求安装包瘦身，可后期用字体子集化工具（如 `fonttools subset`）按常用汉字裁剪。
