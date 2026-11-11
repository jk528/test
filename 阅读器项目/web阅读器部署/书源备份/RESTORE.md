# 书源离线归档与恢复说明（RESTORE）

归档时间：2026-11-11　来源：`shuyuan.yiove.com` 书源分享站

## 一、目录内容

| 文件 | 说明 | 大小 |
| --- | --- | --- |
| `book-source-collection_20261111_383.json` | 全量书源，383 条标准 bookSource | 1,667,636 字节 |
| `latest.json` | 指向最新全量文件的软链接（Windows 侧为副本） | 同左 |
| `keep-22.json` | 精简保留清单，22 条（实测可用，20 条进 `✅精简` 分组） | 91,854 字节 |
| `RESTORE.md` | 本文件 | — |

服务器路径：`/opt/reader-backup/book-sources/`（目录 700、文件 600，仅 root 可读写）
本机路径：`C:\Users\Administrator\Desktop\JK-temp\阅读器项目\web阅读器部署\书源备份\`

订阅原始地址（UUID 永久链接，不保证长期有效）：
`https://shuyuan-api.yiove.com/import/book-source-collection/b8fd3e19-08dd-4f05-a7b4-d6cc909de8e6`

> 注意：网页域名 `https://shuyuan.yiove.com/import/...` 返回的是 SPA 壳（HTML），必须用 `shuyuan-api.yiove.com` 才能拿到 JSON。

## 二、导入回 hectorqin/reader

前提：reader 容器已启动，`/opt/reader/storage` 为数据卷。

### 1. 启动容器（仅重装时需要）

```bash
docker run -d --name reader --restart unless-stopped \
  -p 8080:8080 -e SPRING_PROFILES_ACTIVE=prod \
  -v /opt/reader/storage:/storage \
  hectorqin/reader:3.2.10-07270648
```

### 2. 调整用户书源上限（默认 100，导入 383 条会被截断）

停容器 → 编辑 `/opt/reader/storage/data/users.json`，把目标用户的 `"book_source_limit"` 改为 `500`（或更大）→ 起容器。
**改前先备份该文件**；若改后登录异常，改用管理员接口 `POST /reader3/resetPassword`（需 secureKey）重置口令再试。

### 3. 登录换 accessToken

```bash
TOKEN=$(curl -s -X POST 'http://127.0.0.1:8080/reader3/login' \
  -H 'Content-Type: application/json' \
  -d '{"username":"<用户名>","password":"<密码>","isLogin":true}' \
  | node -e 'let s="";process.stdin.on("data",d=>s+=d).on("end",()=>console.log(JSON.parse(s).data.accessToken))')
```

注意：`saveBookSources` **只带 secureKey 会报「请登录后使用」**，必须带 `accessToken`。

### 4. 导入

```bash
curl -sS -X POST "http://127.0.0.1:8080/reader3/saveBookSources?accessToken=$TOKEN" \
  -H 'Content-Type: application/json' \
  --data-binary @/opt/reader-backup/book-sources/latest.json
# 期望：{"isSuccess":true,"errorMsg":"","data":"新增383条书源，更新0条书源。"}
```

### 5. 校验条数

```bash
# getBookSources 必须是 GET（POST 空 body 会报错）
curl -s "http://127.0.0.1:8080/reader3/getBookSources?accessToken=$TOKEN" \
  | node -e 'let s="";process.stdin.on("data",d=>s+=d).on("end",()=>{
      const j=JSON.parse(s);console.log("total",j.data.length,
      "enabled",j.data.filter(x=>x.enabled!==false).length)})'
# 期望 total 383
```

也可直接核对落盘文件：`/opt/reader/storage/data/<用户>/bookSource.json`，条数应为 383。

### 6. 恢复精简分组（可选）

把 `keep-22.json` 里的 20 条（去掉 `溜达小说🎃`、`🔰 文墨中文` 两个慢源）的 `bookSourceGroup` 追加 `✅精简` 后 `saveBookSources` 回写，搜索时选该分组即为 20 源极速模式。

> **已知特性（v3.2.10 实测）**：`enabled=false` 对 `/reader3/searchBookMulti` **无效**（仍会扫描全部源），真正控制搜索范围的是 `bookSourceGroup` 参数。所以精简要靠分组，不能靠停用。

## 三、文件校验

```bash
# 服务器
cd /opt/reader-backup/book-sources
md5sum book-source-collection_20261111_383.json keep-22.json
node -e 'const a=require("/opt/reader-backup/book-sources/latest.json");console.log(a.length)'
```

```powershell
# 本机
Get-FileHash "C:\Users\Administrator\Desktop\JK-temp\阅读器项目\web阅读器部署\书源备份\latest.json" -Algorithm MD5
(Get-Content -Raw "C:\...\书源备份\latest.json" | ConvertFrom-Json).Count
```

## 四、风险与备份建议

1. **订阅地址是 UUID 永久链接，但不是承诺长期有效**：站点可能下线、改域名（历史上 `api.yiove.com` 已 NXDOMAIN）或删合集。本机副本是最重要的一层保险。
2. **`/opt/reader-backup` 不在自动备份范围**：建议至少做到以下之一
   - 每周 `tar czf /root/backup/reader-book-sources_$(date +%F).tgz -C /opt/reader-backup book-sources`，并随主机快照一起保留；
   - 上传到对象存储（OBS）或私有 Git 仓库（注意书源含第三方站点信息，按需加密）；
   - 每次改动书源后再导出一份带日期的 json，形成版本序列（文件名已带日期与条数）。
3. **数据质量**：383 条中 28 条 `bookSourceGroup` 为空（未分组，导入后可用），2 条 `bookSourceUrl` 不是 http(s) 形式（浏览器类源），均不影响导入。
