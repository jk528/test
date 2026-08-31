# Espanso 使用说明

> 参考来源：[Espanso Hub](https://hub.espanso.org/)、[Espanso Hub GitHub 仓库](https://github.com/espanso/hub)、[Espanso 官方文档](https://espanso.org/docs/)

Espanso 是一款用 Rust 编写的跨平台文本扩展工具。它会在你打字时检测预设的**关键词（trigger）**，并将其自动替换为预设的文本、代码片段，甚至执行自定义脚本，从而显著提升日常输入效率。

---

## 目录

- 一、核心概念
- 二、配置目录结构
- 三、创建自定义匹配
- 四、基础匹配进阶
- 五、动态匹配与扩展（Extensions）
- 六、变量高级语法
- 七、Shell 与脚本扩展
- 八、包管理（Espanso Hub）
- 九、Hub 精选包推荐
- 十、实用快捷键
- 十一、常用命令速查
- 十二、编辑器集成与调试
- 十三、上手验证

---

## 一、核心概念

### 1. Match（匹配规则）

Espanso 的核心是 **Match**——一条把"触发词"和"替换内容"关联起来的规则。最基本的形式是：你输入一个关键词，Espanso 在你打字时把它替换掉。

- 触发词（trigger）：一个简单的字符串，如 `:date`、`:br`、`>>up` 都是合法的触发词。
- 替换内容（replace）：触发词被替换成的文本。

Espanso 自带的匹配规则很少，以给你最大的灵活性。你可以通过两种方式扩展它的能力：**创建自定义匹配**，或**安装包（packages）**。

> 提示：espanso 的 match 不仅限于文本替换。它把一个"因"关联到一个"果"——因可以是输入关键词、搜索栏选择、快捷键；果可以是插入文本、插入图片、执行脚本等。

### 2. Package（包）

包让你能**复用他人创建的代码片段**，或把自己的片段**分享给全世界**。借助官方包仓库 [Espanso Hub](https://hub.espanso.org/) 和内置的包管理器，使用起来非常简单。包本质上就是带元数据的普通 YAML 配置文件。

---

## 二、配置目录结构

Espanso 采用基于文件的配置方式（遵循 Unix 哲学），所有配置文件都放在 `espanso` 目录中，位置取决于操作系统：

| 系统 | 路径 |
| --- | --- |
| Windows | `%APPDATA%\espanso`（如 `C:\Users\用户名\AppData\Roaming\espanso`） |
| macOS | `$HOME/Library/Application Support/espanso` |
| Linux | `$XDG_CONFIG_HOME/espanso`（如 `/home/用户名/.config/espanso`） |

> 下文用 `$CONFIG` 指代此配置目录。快速查看路径的命令：`espanso path`

全新安装后，`$CONFIG` 目录结构如下：

```
$CONFIG/
  config/
    default.yml
  match/
    base.yml
```

两个子目录的用途：

- **`match/` 目录定义 Espanso 该做什么（WHAT）**——即所有自定义片段和动作。`match/base.yml` 是开始添加匹配规则的地方。当片段变多时，可以拆分到多个文件，例如新建 `match/emails.yml` 专门放写邮件用的片段。
- **`config/` 目录定义 Espanso 该如何展开（HOW）**——即所有参数和选项。`config/default.yml` 定义对所有应用生效的默认选项；也可为特定应用创建配置，如 `config/slack.yml` 让 Slack 使用不同设置。

所有文件都使用 YAML 格式。

### 应用级配置与引用

你可以把片段按用途拆分，并通过 `extra_includes` 在特定应用配置中引用，例如：

`$CONFIG/config/vscode.yml`

```yaml
# 仅当窗口标题包含 "Visual Studio Code" 时生效
filter_title: "Visual Studio Code"

# 额外引入的匹配文件（相对当前文件路径）
extra_includes:
  - "../match/_code_snippets.yml"
```

这样在 VSCode 中就能同时使用 `_code_snippets.yml` 所引入的 JS、CSS 片段。

---

## 三、创建自定义匹配

以写邮件结尾为例，希望输入 `:br` 时自动展开为署名。

用文本编辑器打开 `$CONFIG/match/base.yml`，在 `matches:` 下添加一条规则：

```yaml
matches:
  # 简单文本替换
  - trigger: ":espanso"
    replace: "Hi there!"

  - trigger: ":br"
    replace: "Best Regards,\nJon Snow"
```

保存后 Espanso 会自动检测变更并重新加载配置。现在在任意位置输入 `:br`，即可看到 `Best Regards, Jon Snow` 出现。

> **重要**：必须保持 YAML 缩进，建议用空格而非 Tab。

### 快速编辑命令

在终端运行：

```bash
espanso edit
```

会用系统默认编辑器（Unix 默认 Nano，Windows 默认记事本）打开配置，可自定义。

---

## 四、基础匹配进阶

### 1. 静态匹配与多行

最基本的匹配是"触发词 → 替换文本"的静态对。多行替换可用 `\n` 换行符，或使用 YAML 块标量 `|`（保留换行）与 `>`（折叠换行为空格）。

```yaml
matches:
  # 使用 \n 换行
  - trigger: ":br"
    replace: "Best Regards,\nJon Snow"

  # 使用 | 保留换行
  - trigger: ":poem"
    replace: |
      exactly as you see
      will appear these three
      lines of poetry

  # 使用 > 折叠换行
  - trigger: ":line"
    replace: >
      this is really a
      single line of text
```

> 提示：包含 `\n`、`\t`，或以 YAML 特殊字符（`' " [] {} > | * & ! % # ` @`）开头的字符串**必须加引号**。

### 2. 单词触发（word trigger）

把 `word: true` 加给匹配，可让触发词只在**作为独立单词**（前后是空格、逗号、换行等分隔符）时才展开，适合做拼写纠错：

```yaml
matches:
  # 只替换独立单词 ther，不误伤 other
  - trigger: "ther"
    replace: "there"
    word: true
```

| 输入前 | 输入后 |
| --- | --- |
| Is ther anyone else? | Is there anyone else? |
| I have other interests | I have other interests（不触发） |

相关的 `left_word: true` 与 `right_word: true` 分别约束匹配只发生在单词开头或结尾。可通过配置项 `word_separators` 自定义哪些字符算分隔符。

### 3. 大小写传播与特殊字符

`propagate_case: true` 让替换结果继承触发词的大小写：

```yaml
matches:
  # alh→although, Alh→Although, ALH→ALTHOUGH
  - trigger: "alh"
    replace: "although"
    propagate_case: true
    word: true
```

多词替换默认只大写首词；要每个单词都大写，加 `uppercase_style: capitalize_words`。

`replace` 还支持十六进制与 Unicode 转义：`"\xC4"`、`"\u0105"`、`"\U00000105"`，例如 `"\u20ac"` 等价于 `€`。

### 4. 光标提示

在替换文本中插入 `$|$` 可控制展开后**光标的位置**：

```yaml
matches:
  # 展开后光标停在 <div> 与 </div> 之间
  - trigger: ":div"
    replace: "<div>$|$</div>"
```

> 注意：每条匹配只能有一个光标提示，多余会被忽略。在支持自动缩进的编辑器中使用多行展开时可能产生意外结果。

### 5. 匹配消歧

多条匹配共用同一个触发词时，Espanso 会弹出**选择对话框**让你挑选：

```yaml
matches:
  # 三条匹配共用同一个触发词，输入 :quote 后弹出选择框
  - trigger: ":quote"
    replace: "Every moment is a fresh beginning."
  - trigger: ":quote"
    replace: "Everything you can imagine is real."
  - trigger: ":quote"
    replace: "Whatever you do, do it well."
```

### 6. 搜索标签与多触发词

用 `label` 覆盖搜索栏中显示的描述，用 `search_terms` 添加额外搜索关键词：

```yaml
matches:
  # label 覆盖搜索栏显示，search_terms 补充搜索关键词
  - trigger: ":tomorrow"
    replace: "{{mytime}}"
    label: "插入明天的日期"
    search_terms: ["date", "明天"]
    vars:
      # 日期变量：%v 为日期格式，86400 秒 = 明天
      - name: mytime
        type: date
        params:
          format: "%v"
          offset: 86400
```

用 `triggers`（复数）为一个匹配指定多个触发词：

```yaml
matches:
  # 一个匹配绑定多个触发词：输入 hello 或 hi 都展开为 world
  - triggers: [hello, hi]
    replace: world
```

### 7. 富文本、图片与嵌套匹配

富文本可用 `markdown` 或 `html` 字段输出；图片用 `image_path` 展开；嵌套匹配用 `type: match` 引用其他匹配的输出：

```yaml
matches:
  # 富文本
  - trigger: ":rich"
    markdown: "This *text* is **very rich**!"

  # 图片展开（用 $CONFIG 避免硬编码路径）
  - trigger: ":cat"
    image_path: "$CONFIG/images/cat.png"

  # 嵌套匹配：引用 :one 的输出
  - trigger: ":one"
    replace: "nested"
  - trigger: ":nested"
    replace: "This is a {{output}} match"
    vars:
      - name: output
        type: match
        params:
          trigger: ":one"
```

---

## 五、动态匹配与扩展（Extensions）

静态匹配无法生成**动态变化**的内容。Espanso 用**变量（variable）**承载**扩展（extension）**的输出：

- 在 `replace` 中用 `{{变量名}}` 注入变量；
- 在 `vars:` 中声明变量的 `name`、`type`（即扩展类型）与 `params`（参数）。

```yaml
matches:
  # 声明动态匹配：用 {{mytime}} 注入变量
  - trigger: ":now"
    replace: "It's {{mytime}}"
    vars:
      # 定义变量 mytime，类型为 date（日期扩展）
      - name: mytime
        type: date
        params:
          # 时间格式：%H 小时，%M 分钟
          format: "%H:%M"
```

输入 `:now` 会展开为 `It's 09:33` 之类的时间。

### 1. 日期扩展（date）

- `format`：指定输出格式，遵循 [chrono 的 strftime 格式](https://docs.rs/chrono/latest/chrono/format/strftime/index.html)。
- `offset`：相对当前时间的偏移（单位秒），正数表示未来，负数表示过去。
- `locale`：强制区域（BCP47 格式，如 `en-US`）。
- `tz`：时区（IANA 名称，如 `America/New_York`），v2.3.0 起支持，无效时回退本地时间。

```yaml
matches:
  # 当前时间
  - trigger: ":now"
    replace: "It's {{mytime}}"
    vars:
      - name: mytime
        type: date
        params:
          format: "%H:%M"

  # 明天（+86400 秒）
  - trigger: ":tomorrow"
    replace: "{{mytime}}"
    vars:
      - name: mytime
        type: date
        params:
          format: "%x"
          offset: 86400

  # 昨天（-86400 秒）
  - trigger: ":yesterday"
    replace: "{{mytime}}"
    vars:
      - name: mytime
        type: date
        params:
          format: "%x"
          offset: -86400

  # 强制美式格式与时区
  - trigger: ":today"
    replace: "{{mytime}}"
    vars:
      - name: mytime
        type: date
        params:
          format: "%x"
          locale: "en-US"
          tz: "America/New_York"
```

### 2. 选择扩展（choice）

弹出选择对话框，从列表中挑选一个值。用 `label` + `id` 可让"显示文本"与"最终插入值"不同：

```yaml
matches:
  # 输入 :quote 弹出选择对话框
  - trigger: ":quote"
    replace: "{{output}}"
    vars:
      - name: output
        type: choice
        params:
          values:
            # label 为显示文本，id 为最终插入的值
            - label: "Every moment is a fresh beginning."
              id: "bar"
            - label: "Everything you can imagine is real."
              id: "foo"
```

> 若只是想"同一触发词选不同替换"，用第四节的**匹配消歧**即可；choice 更适合脚本等需要动态取值的高级场景。

### 3. 随机扩展（random）

从 `choices` 中随机选取一个，适合避免重复：

```yaml
matches:
  # 输入 :quote 时从 choices 中随机选取一个
  - trigger: ":quote"
    replace: "{{output}}"
    vars:
      - name: output
        type: random
        params:
          choices:
            - "Every moment is a fresh beginning."
            - "Everything you can imagine is real."
            - "Whatever you do, do it well."
```

### 4. 剪贴板扩展（clipboard）

把当前剪贴板内容插入匹配：

```yaml
matches:
  # 输入 :a 时读取剪贴板内容拼成 HTML 链接
  - trigger: ":a"
    # $|$ 让光标停在 <a> 标签之间
    replace: "<a href='{{clipb}}'>$|$</a>"
    vars:
      # clipboard 扩展：读取当前剪贴板
      - name: clipb
        type: clipboard
```

复制一个链接后输入 `:a`，即可得到 `<a href='你复制的链接'></a>`，光标停在标签中间。

### 5. 回显扩展（echo）

创建固定值的变量，特别适合定义**全局变量**：

```yaml
# 全局变量：定义后可在所有匹配中复用
global_vars:
  # echo 扩展：返回固定值 "John"
  - name: myname
    type: echo
    params:
      echo: "John"

matches:
  # 输入 :greet 展开为 Hello John
  - trigger: ":greet"
    replace: "Hello {{myname}}"
```

### 6. 表单扩展（form）

`type: form` 可构建交互式表单，用 `layout` 定义结构、`fields` 定义字段（如 `type: list` 下拉框），表单字段值通过 `{{form1.field}}` 注入。详情见[官方文档](https://espanso.org/docs/matches/extensions/)。

---

## 六、变量高级语法

变量不仅能插入替换文本，还能**互相组合**形成复杂工作流。以下为变量注入、求值顺序与环境变量传递等高级用法。

### 1. 变量注入

把变量的值插入替换文本的动作叫**变量注入**。注入不仅能发生在 `replace` 里，也能发生在**其他变量的参数里**——即用一个扩展的输出作为另一个扩展的输入：

```yaml
matches:
  # 输入 :now 输出当前时间
  - trigger: ":now"
    replace: "It's {{mytime}}"
    vars:
      # 第一个变量：执行 shell 命令，输出 "%H:%M"
      - name: shellcmd
        type: shell
        params:
          cmd: "echo \"%H:%M\""
      # 第二个变量：把 shellcmd 的输出作为 format 参数注入
      - name: mytime
        type: date
        params:
          format: "{{shellcmd}}"
```

> 变量注入**只作用于 `params` 字段**，不能用于 `name` 或 `type`。

### 2. 禁用变量注入

Espanso 会把所有花括号内容当作变量注入，必要时可用两种方式关闭：

**转义花括号**（多行字符串中无需双重转义反斜杠）：

```yaml
matches:
  # 转义花括号，让 {{var}} 按字面量输出
  - trigger: ":hello"
    replace: |
      hello \{\{var\}\}
```

**使用 `inject_vars: false`**：

```yaml
matches:
  # 输出 hello {{var}}（字面量，不展开）
  - trigger: ":hello"
    replace: "hello {{output}}"
    vars:
      - name: output
        type: echo
        # inject_vars: false 关闭参数中的变量注入
        inject_vars: false
        params:
          echo: "{{var}}"
```

### 3. 全局变量

在 `matches:` 之前定义的 `global_vars` 可在多个匹配中复用，也能注入到局部变量的参数里，甚至注入到其他全局变量里：

```yaml
# 全局变量：跨匹配共享
global_vars:
  - name: firstname
    type: echo
    params:
      echo: "Jon"
  - name: lastname
    type: echo
    params:
      echo: "Snow"
  # 全局变量可注入其他全局变量
  - name: fullname
    type: echo
    params:
      echo: "{{firstname}} {{lastname}}"

matches:
  # 输入 :hello 展开为 hello Jon Snow
  - trigger: ":hello"
    replace: "hello {{fullname}}"
```

### 4. 求值顺序

- **局部变量**按声明顺序**串行求值**（先声明的先求值）。
- **全局变量**默认**无固定顺序**——Espanso 采用基于依赖约束的解析算法：若变量 A 注入到了 B 的 `params` 中，则 B 必须先于 A 求值；否则顺序不保证。

若要**强制全局变量的求值顺序**，有两种方式：

**方式一：重声明为 `type: global` 的局部变量**（放入 `vars:` 中，随局部变量串行求值）：

```yaml
global_vars:
  - name: three
    type: shell
    params:
      cmd: "echo three"

matches:
  - trigger: ":hello"
    replace: "hello {{one}} {{two}} {{three}}"
    vars:
      # 局部变量按声明顺序串行求值
      - name: one
        type: shell
        params:
          cmd: "echo one"
      - name: two
        type: shell
        params:
          cmd: "echo two"
      # 把全局变量 three 重声明为 type: global 的局部变量
      # 从而强制它在 one、two 之后求值
      - name: three
        type: global
```

**方式二：使用 `depends_on` 显式声明依赖**（接受需要先行求值的变量名列表）：

```yaml
global_vars:
  - name: one
    type: shell
    params:
      cmd: "echo one"
  # depends_on 声明 two 依赖 one，保证 one 先求值
  - name: two
    type: shell
    depends_on: ["one"]
    params:
      cmd: "echo two"
```

### 5. 通过环境变量传递（Shell/Script 的替代方案）

除字符串注入外，Shell 与 Script 扩展还会把**当前作用域的所有变量**以环境变量形式传入。命名规则：变量 `myname` → `ESPANSO_MYNAME`，`form1.name` → `ESPANSO_FORM1_NAME`。

| 平台 / Shell | 读取环境变量语法 |
| --- | --- |
| Linux / macOS（bash 类） | `$ESPANSO_MYNAME` |
| Windows PowerShell | `$env:ESPANSO_MYNAME` |
| Windows 命令提示符 | `%ESPANSO_MYNAME%` |
| Windows WSL | `$ESPANSO_MYNAME` |

示例（bash 反转字符串）：

```yaml
matches:
  - trigger: ":reversed"
    replace: "Reversed {{myshell}}"
    vars:
      # 先求值 myname，值为 John
      - name: myname
        type: echo
        params:
          echo: "John"
      # shell 读取环境变量 ESPANSO_MYNAME 并反转
      - name: myshell
        type: shell
        params:
          cmd: "echo $ESPANSO_MYNAME | rev"
```

Python 脚本内读取：

```python
import os
# 通过环境变量读取 espanso 变量 myvar 的值
myvar = os.environ['ESPANSO_MYVAR']
```

> 注意：使用环境变量传递时，Espanso **无法自动检测依赖**。若依赖的是全局变量或定义顺序不满足要求，必须用 `depends_on` 显式声明依赖（如上节所示）。

---

## 七、Shell 与脚本扩展

当内置扩展不够用时，**Shell 扩展**执行 shell 命令，**Script 扩展**调用任意语言脚本，把输出注入匹配。

### 1. Shell 扩展

默认在 Windows 用 PowerShell、Linux 用 bash，可用 `shell` 参数切换：

```yaml
matches:
  # 获取公网 IP
  - trigger: ":ip"
    replace: "{{output}}"
    vars:
      - name: output
        type: shell
        params:
          cmd: "curl 'https://api.ipify.org'"

  # Windows 下用 WSL 执行 Linux 命令
  - trigger: ":localip"
    replace: "{{output}}"
    vars:
      - name: output
        type: shell
        params:
          cmd: "ip a | grep 'inet 192' | awk '{ print $2 }'"
          shell: wsl
```

`shell` 参数可选值：

| 平台 | 可选 shell |
| --- | --- |
| Windows | `cmd`、`powershell`、`pwsh`、`wsl`、`nu` |
| macOS | `sh`、`bash`、`pwsh`、`nu` |
| Linux | `sh`、`bash`、`pwsh`、`nu` |

> Windows 的 `cmd` 不支持多行内联代码。

其他参数：

- `trim: false`：默认会去掉输出末尾多余的换行/空格，设为 `false` 则保留。
- `debug: true`：把实际执行的命令、返回码与错误信息写入日志，配合 `espanso log` 查看。

### 2. Script 扩展

通过 `args` 指定解释器与脚本路径，支持任意语言。最佳实践是把脚本放在 `$CONFIG/scripts/` 目录，并用 `%CONFIG%` 通配符引用路径，便于多机同步：

```yaml
matches:
  # 输入 :pyscript 时运行 Python 脚本并插入其输出
  - trigger: ":pyscript"
    replace: "{{output}}"
    vars:
      - name: output
        type: script
        params:
          args:
            - python                        # 解释器
            - "%CONFIG%/scripts/script.py"  # 脚本路径（%CONFIG% 通配配置目录）
            - parameter_1                   # 传给脚本的参数
```

> 性能提醒：脚本有执行耗时，应尽量使用快速运行的脚本，避免展开卡顿。

### 3. 内联脚本

脚本可**内联**写在匹配里（如 `python -c`），省去维护脚本文件，且可直接使用 `{{变量}}`；缺点是难以调试，且 Windows 有 8191 字符上限：

```yaml
matches:
  # 输入 :fruits 时内联运行 Python 代码
  - trigger: ":fruits"
    replace: "{{output}}"
    vars:
      - name: output
        type: script
        params:
          args:
            - python   # 解释器
            - -c       # 从参数读取内联代码
            - |
              fruits = ["apple", "banana", "cherry"]
              for x in fruits:
                  print(x)
```

跨匹配共享脚本，可用 `echo` 全局变量或 YAML 锚点（`&` / `*`）：

```yaml
# YAML 锚点：用 &script1 定义，*script1 引用，复用同一段脚本
anchors:
  script1: &script1 |
    fruits = ["apple", "banana", "cherry"]
    for x in fruits:
        print(x)

matches:
  - trigger: ":test"
    replace: "{{output}}"
    vars:
      - name: output
        type: script
        params:
          # *script1 展开为上面定义的脚本内容
          args: [python, -c, *script1]
```

### 4. UTF-8 输出处理

部分脚本默认不返回 UTF-8，影响中文等外语字符。解决办法：

- Python：`sys.stdout.reconfigure(encoding='utf-8')`
- PowerShell：`[Console]::OutputEncoding = [System.Text.Encoding]::UTF8`
- Bash：`export LANG='zh_CN.UTF-8'`（换成你的 locale）

### 5. 环境变量

Shell / Script 扩展执行时，Espanso 会注入两个有用的环境变量：

- `CONFIG`：指向 espanso 配置目录的路径。
- 所有已求值匹配变量的值（见第六节）。

---

## 八、包管理（Espanso Hub）

[Espanso Hub](https://hub.espanso.org/) 是官方包仓库，上面的包都由 Espanso 团队人工审核过。在 [Hub 搜索页](https://hub.espanso.org/search) 浏览选择需要的包。

### 1. 安装包

```bash
espanso install <包名>
```

例如安装 [lorem](https://hub.espanso.org/lorem) 包：

```bash
espanso install lorem
```

安装特定版本：

```bash
espanso install <包名> --version <版本号>
# 示例
espanso install html-utils-package --version 0.1.0
```

强制重新安装（覆盖本地修改回到官方版本）：

```bash
espanso install lorem --force
```

安装示例：添加 emoji，输入 `:ok` 展开为 👍

```bash
espanso install basic-emojis
```

如果安装后没有自动重载，手动重启：

```bash
espanso restart
```

### 2. 卸载包

```bash
espanso uninstall <包名>
# 示例
espanso uninstall lorem
```

### 3. 查看已安装包

```bash
espanso package list
```

### 4. 更新包

更新单个包：

```bash
espanso package update <包名>
# 示例
espanso package update lorem
```

更新全部包：

```bash
espanso package update all
```

### 5. 查看包存储位置

```bash
espanso path packages
```

包存储在 `packages` 目录下，与你的 YAML 匹配文件放在一起。

---

## 九、Hub 精选包推荐

以下为 [Espanso Hub](https://hub.espanso.org/) 首页推荐的精选包，可按需安装：

| 包名 | 说明 | 安装命令 |
| --- | --- | --- |
| **math-symbols** | 基于 LaTeX 命名方案的数学符号 | `espanso install math-symbols` |
| **all-emojis** | 全部 emoji（含别名，来自 gemoji） | `espanso install all-emojis` |
| **html-utils-package** | 让 HTML5 编码更简单 | `espanso install html-utils-package` |
| **spanish-accent** | 西班牙语重音符号 | `espanso install spanish-accent` |
| **medical-docs** | 医疗文档辅助 | `espanso install medical-docs` |
| **lorem** | Lorem ipsum 句子与段落生成器 | `espanso install lorem` |
| **espanso-dice** | 用 espanso 随机函数模拟掷骰子 | `espanso install espanso-dice` |
| **shruggie** | 展开颜文字 `¯\_(ツ)_/¯` | `espanso install shruggie` |
| **greek-letters-improved** | 基于 LaTeX 命名的希腊字母 | `espanso install greek-letters-improved` |

更多包请在 [Hub 搜索页](https://hub.espanso.org/search) 探索。

---

## 十、实用快捷键

### 1. 搜索栏（Search Bar）

Espanso 自带强大的搜索栏，可快速查找并插入匹配规则。打开方式：

- 按 `ALT+SPACE`（macOS 为 `Option+Space`）。
- 点击任务栏图标，选择"Open Search bar"（Linux 不可用）。
- 自定义搜索触发词后在任意位置输入。

> 在搜索栏开头输入 `>` 可显示 espanso 的控制与报告命令。

### 2. Backspace 撤销

如果不小心触发了展开，**立即按 `BACKSPACE`** 即可撤销展开并恢复触发词。

在 `config/default.yml` 中可关闭此行为：

```yaml
# 关闭 Backspace 撤销功能（默认开启）
undo_backspace: false
```

### 3. 切换开关

想临时禁用 Espanso 以避免误展开，可通过任务栏图标菜单切换开关，也可自定义切换快捷键。

---

## 十一、常用命令速查

| 命令 | 作用 |
| --- | --- |
| `espanso status` | 查看 espanso 是否运行 |
| `espanso start` | 启动 espanso（Linux） |
| `espanso restart` | 重启 espanso（重载配置） |
| `espanso path` | 查看配置目录路径 |
| `espanso path packages` | 查看包存储路径 |
| `espanso edit` | 用默认编辑器打开配置 |
| `espanso log` | 查看日志（配合 shell 的 `debug: true`） |
| `espanso install <包名>` | 安装包 |
| `espanso install <包名> --version <版本>` | 安装指定版本 |
| `espanso install <包名> --force` | 强制重装 |
| `espanso uninstall <包名>` | 卸载包 |
| `espanso package list` | 列出已安装包 |
| `espanso package update <包名>` | 更新单个包 |
| `espanso package update all` | 更新全部包 |

---

## 十二、编辑器集成与调试

配置文件可用任何文本编辑器编写，推荐以下几款：

### 1. EspansoEdit

[EspansoEdit](https://espanso.org/docs/tools/#espansoedit) 是一款专为 espanso 设计的免费编辑器与工具，功能丰富。

### 2. VSCode / VSCodium

VSCode 与开源版 VSCodium 支持通过 **Schema** 在输入时高效地高亮语法错误，避免保存后 espanso 才报错。

安装 Red Hat YAML [扩展](https://marketplace.visualstudio.com/items?itemName=redhat.vscode-yaml) 后，在 `espanso/config` 文件顶部添加：

```yaml
# yaml-language-server: $schema=https://raw.githubusercontent.com/espanso/espanso/dev/schemas/config.schema.json
```

在 `espanso/match` 文件顶部添加：

```yaml
# yaml-language-server: $schema=https://raw.githubusercontent.com/espanso/espanso/dev/schemas/match.schema.json
```

> 经验提示：在 VSCode/VSCodium 中使用 `clipboard` 后端体验最佳，可参考应用级配置示例设置 filter。

VSCode/VSCodium 自动补全片段集合见 [VSCode-Espanso-snippets](https://github.com/smeech/VSCode-Espanso-snippets)。

### 3. Neovim

通过 `mason` 和 `lspconfig` 安装 `yaml-language-server`（`yamlls`），并保留文件顶部的 `# yaml-language-server: $schema=...` 链接即可使用 schema。

### 4. 展开不生效的排查

若展开不生效（无替换、缺字符或只出现 `v`），可在触发词上加 `force_mode: clipboard` 或 `force_mode: keys` 测试注入机制：

```yaml
matches:
  # 调试：强制用按键注入，排查展开不生效的问题
  - trigger: ":x"
    replace: "testing"
    force_mode: keys
```

定位问题后，建议改为在 `default.yml` 中调整 `backend` 全局配置，或在应用级配置中单独设置，而不是每条匹配都加 `force_mode`。

---

## 十三、上手验证

1. 安装后 espanso 自动启动，Windows 任务栏出现 espanso 图标。
2. 打开任意输入应用（如记事本），输入 `:espanso`，应出现 `Hi there!`。
3. 若未生效：Windows 用户从开始菜单点击 espanso，或便携版运行 `START_ESPANSO.bat`；Linux 运行 `espanso start`；仍不行则重装。
4. 自定义一条 `:br` 规则并验证展开。
5. 用 `:now` 验证日期扩展的动态匹配。
6. 安装一个 Hub 包（如 `basic-emojis`）体验包管理。

---

## 参考链接

- [Espanso 官网与文档](https://espanso.org/docs/)
- [Espanso Hub 包仓库](https://hub.espanso.org/)
- [Hub GitHub 仓库](https://github.com/espanso/hub)
- [Hub 包搜索](https://hub.espanso.org/search)
- [Windows 安装指南](https://espanso.org/docs/install/win/)
- [入门教程](https://espanso.org/docs/get-started/)
- [匹配规则基础](https://espanso.org/docs/matches/basics/)
- [扩展（Extensions）](https://espanso.org/docs/matches/extensions/)
- [变量（Variables）](https://espanso.org/docs/matches/variables/)
- [包基础文档](https://espanso.org/docs/packages/basics/)
- [配置选项文档](https://espanso.org/docs/configuration/options/)
