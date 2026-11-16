# 华为云 CodeArts SSH 配置说明

## 一、基础信息

| 项目 | 内容 |
|------|------|
| 区域 | cn-north-4 |
| 仓库 | harmony-reader |
| 仓库 SSH 地址 | `git@codehub.devcloud.cn-north-4.huaweicloud.com:5f798e455ff0425dbf510ada7b012594/harmony-reader.git` |
| 仓库 HTTPS 地址 | `https://codehub.devcloud.cn-north-4.huaweicloud.com/5f798e455ff0425dbf510ada7b012594/harmony-reader.git` |
| SSH 公钥管理页面 | https://codehub.devcloud.cn-north-4.huaweicloud.com/my/sshkeys |
| 本地私钥路径 | `C:\Users\Administrator\.ssh\id_ed25519` |
| Git 用户名 | jk528528 |
| Git 邮箱 | jk528528@gitee.com |

---

## 二、本地 SSH 公钥（待添加到华为云）

```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAICt8INaeifxBRtWyO8yB1/vJ7oQ3HiOC+7uuixATayhL jk528528@gitee.com
```

---

## 三、添加公钥到华为云（操作步骤）

1. 打开 SSH 公钥管理页面：
   https://codehub.devcloud.cn-north-4.huaweicloud.com/my/sshkeys
2. 登录华为云账号（如未登录）
3. 点击 **"新增 SSH 密钥"** 按钮
4. **标题**：随意填写，例如 `my-pc`
5. **公钥**：粘贴上方公钥内容
6. 点击 **确定 / 保存**

---

## 四、克隆仓库

### 方式 A：SSH（推荐，添加公钥后使用）

```bash
git clone git@codehub.devcloud.cn-north-4.huaweicloud.com:5f798e455ff0425dbf510ada7b012594/harmony-reader.git
```

### 方式 B：HTTPS（需用户名 + 访问令牌）

```bash
git clone https://codehub.devcloud.cn-north-4.huaweicloud.com/5f798e455ff0425dbf510ada7b012594/harmony-reader.git
```

> 令牌申请位置：华为云控制台 → 我的凭证 → 访问密钥 / 数据加密密钥
> 或 CodeArts → 个人设置 → HTTPS 密码

---

## 五、后续同步命令

进入仓库目录后：

```bash
# 拉取远程最新代码
git pull

# 推送本地提交到远程
git push

# 查看远程仓库
git remote -v
```

---

## 六、常见问题

### 1. Permission denied (publickey)
- 原因：公钥未添加到华为云账号，或私钥路径不对
- 解决：按本文档第三节添加公钥；确认 `~/.ssh/id_ed25519` 存在

### 2. 连接超时 / 端口问题
若默认 22 端口不通，可在 `C:\Users\Administrator\.ssh\config` 中配置：

```
Host codehub.devcloud.cn-north-4.huaweicloud.com
    HostName codehub.devcloud.cn-north-4.huaweicloud.com
    PreferredAuthentications publickey
    IdentityFile ~/.ssh/id_ed25519
```

### 3. 验证 SSH 连接
```bash
ssh -T git@codehub.devcloud.cn-north-4.huaweicloud.com
```
成功会返回欢迎信息（非交互式仓库可能无回显，只要不报 Permission denied 即正常）。