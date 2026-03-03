# 企业级AI知识库系统 - 整体方案设计

> 版本：v3.2 | 日期：2026-03-02 | 状态：待确认 | 变更：上传会话脱离LRU、Complete补偿事务、主路Reranker进程池解耦、辅路错峰发车、Cache改余弦相似度、废弃Token挤出改MMR、Chunk缝合与Embedding去重、Pandas沙箱数据脱敏

---

## 一、项目概述

### 1.1 系统定位

部署于企业本地服务器的AI知识库系统，提供个人文件管理、智能问答、知识检索功能。数据完全存储于内网，通过钉钉统一身份认证，通过外部AI API提供智能问答与文档索引能力。

### 1.2 核心设计原则

- **数据内网存储**：所有文件与业务数据不传输至外部
- **最小出网原则**：外网访问仅限钉钉认证域名与AI API（仅接收文本片段和纯文字问题）
- **权限最小化**：用户默认只能访问自己的数据，权限需显式授予
- **混合交互模式**：主界面为聊天窗口（AI问答 + 文件操作指令），侧边栏提供可折叠文件树浏览
- **API 版本化**：URL 前缀版本化（`/api/v1/*`），Phase 迭代中保持向后兼容，破坏性变更通过新版本号发布

---

## 二、系统架构

### 2.1 整体架构图

```
┌──────────────────────────────────────────────────────────┐
│                    企业内网 (Intranet)                      │
│                                                          │
│  浏览器/钉钉 ──▶ Nginx（IP白名单 + HTTPS + 限流）           │
│                      │                                   │
│                FastAPI 后端服务                             │
│           认证/文件/AI问答/权限/审计/组织同步                  │
│              │       │      │      │                     │
  │          Postgres  Redis×3 MinIO  Elasticsearch          │
  │          用户/权限  缓存/   文件    BM25全文+              │
  │          审计日志   安全/   存储    Vector混合检索          │
  │                    队列                                  │
│                                                          │
│  Celery Worker（分容器部署，按队列独立伸缩）：              │
│    worker-high:    Gotenberg预览转换 / Markdown→ES索引     │
│    worker-default: MarkItDown解析 / AI索引生成 / 钉钉同步   │
│    worker-low:     folder_summary汇总                      │
│                                                          │
│  React + TypeScript + Ant Design 前端                     │
│  聊天驱动UI / 侧边栏文件树 / 拖拽上传 / 在线预览 / 管理后台     │
└────────────────────────┬─────────────────────────────────┘
                         │ 仅以下流量出网（防火墙白名单）
           认证：login.dingtalk.com / api.dingtalk.com
           AI API：dashscope.aliyuncs.com / api.deepseek.com
```

### 2.2 技术栈选型

| 层级 | 技术选型 | 说明 |
|------|----------|------|
| 后端框架 | Python 3.12 + FastAPI | 异步高性能，AI生态丰富 |
| 前端框架 | React 18 + TypeScript + Ant Design 5 | 企业级UI组件 |
| 前端状态管理 | Zustand + React Query (TanStack Query) | Zustand 管理客户端状态（聊天会话/UI状态）；React Query 管理服务端缓存（文件列表/用户信息），自动处理加载/错误/缓存失效 |
| 前端构建 | Vite 6 | 开发热更新 <100ms，生产构建自动 Tree Shaking + Code Splitting |
| 关系数据库 | PostgreSQL 16 | 用户/权限/审计/元数据/索引树 |
| 搜索引擎 | Elasticsearch 8 | BM25全文检索 + dense_vector（HNSW）向量检索，同一请求内 RRF 混合打分 |
| 本地重排模型 | BGE-Reranker-Base（BAAI，~600MB） | Cross-Encoder 精筛，ProcessPoolExecutor 独立进程池推理避免阻塞异步循环，Top-20 → Top-3 |
| Embedding 模型 | 通义千问 text-embedding-v3（外部 API） | 文档语义块向量化（dims=1536），属受控出网（仅发送文档文本片段，不含文件名/用户信息）；速率限制纳入全局 AI API 限流（60次/分钟令牌桶）|
| 缓存/队列 | Redis 7 (3实例) | 缓存实例(allkeys-lru) + 安全实例(noeviction) + Celery队列实例(noeviction) |
| 文档解析 | MarkItDown (Microsoft) | Word/PDF/Excel/PPT → Markdown，本地运行 |
| 文件存储 | MinIO | S3兼容对象存储，加密存储原始文件 + Markdown副本 + 预览PDF |
| 异步任务 | Celery + Redis | 文件解析、索引生成、组织同步 |
| 文档转换 | Gotenberg | Word/Excel/PPT转PDF预览，Docker部署 |
| 容器化 | Docker + Docker Compose | 一键部署 |
| 反向代理 | Nginx | IP白名单、HTTPS、限流 |
| 外部AI | 通义千问 + DeepSeek API | 索引生成 + 兜底问答 |

### 2.3 AI API 路由与故障切换

| 功能场景 | 主供应商 | 备选供应商 | 说明 |
|----------|----------|------------|------|
| 索引生成（摘要/标签/分类） | 通义千问 | DeepSeek | 中文理解强，适合结构化提取 |
| Embedding 向量化 | 通义千问 text-embedding-v3 | 无备选（降级跳过 Vector 写入，仅保留 BM25） | 语义块向量化；失败时标记 `vector_ready=false`，Celery 定时重试 |
| 兜底问答（通用知识） | DeepSeek | 通义千问 | 推理能力强，适合开放问答 |
| 聊天指令解析（复杂歧义） | DeepSeek | 通义千问 | 仅本地规则匹配失败时触发 |

**故障切换**：主供应商超时30秒/5xx/429 → 自动切备选 → 备选也失败 → 降级（索引用规则提取Level 1标记待重试；问答提示暂不可用）。熔断：连续10次失败 → 熔断5分钟 → 探测恢复。

**成本感知路由**（仅兜底问答/指令解析，主备均可用时生效）：

```
weight = base_weight × (1 - budget_ratio × 0.3) × satisfaction_score

路由因素：Token单价差异 / 月度预算消耗比（>80%降权）/ 7天用户满意度
管理后台可设置月度预算上限，可关闭回退为固定主备模式
```

---

## 三、用户与权限体系

### 3.1 角色定义

| 角色 | 权限 |
|------|------|
| 超级管理员 | 管理所有用户账号和文件；配置权限（精确到文件夹级）；查看全平台审计日志；管理公共知识库和索引体系；系统配置 |
| 部门主管 | 查看+下载本部门成员文件（不可编辑他人文件）；管理个人文件空间；上传公共知识库（需管理员开启）；查看本部门操作日志（不可导出） |
| 普通用户 | 管理个人文件空间；访问被授权的他人文件夹（只读+下载）；访问公共知识库；查看自己的操作记录与问答历史 |

### 3.2 权限配置规则

权限由超级管理员配置，**单方面生效，无需文件所有者同意**。支持用户→文件夹级/部门级授权，跨部门授权。他人文件固定为查看+下载，不可配置为编辑。

### 3.3 AI检索权限边界

AI检索范围 = 用户自有文件 + 管理员授权的他人文件夹 + 公共知识库。严格保证检索结果不出现无权内容。

### 3.4 核心数据表设计

PostgreSQL核心表（省略通用审计字段 `created_at`/`updated_at`）：

#### 用户与组织

```sql
departments     -- 部门表（钉钉同步）
  id, dingtalk_dept_id(UNIQUE), name, parent_id(FK), path(LTREE), manager_user_id(FK), sort_order

users           -- 用户表
  id, dingtalk_user_id(UNIQUE), name, phone, department_id(FK),
  role(super_admin/dept_manager/user), status(active/disabled),
  password_hash,  -- 本地降级登录（可NULL）
  token_version   -- Token批量失效版本号
```

#### 文件与版本

```sql
folders         -- 文件夹表
  id, user_id(FK), parent_id(FK), name, folder_type(personal/public/shared),
  path(LTREE), deleted_at, UNIQUE(user_id, parent_id, name)

files           -- 文件表
  id, folder_id(FK), user_id(FK), filename(已消毒), original_name,
  file_type, file_size, sha256_hash, current_version,
  parse_status(pending/processing/normal/degraded/ocr_required/failed), deleted_at

file_versions   -- 文件版本表
  id, file_id(FK), version, file_size, sha256_hash,
  minio_original, minio_markdown, minio_preview, uploaded_at,
  UNIQUE(file_id, version)
```

#### 权限与索引

```sql
folder_permissions  -- 共享权限表
  id, grantee_user_id(FK), target_type(folder/department),
  target_folder_id(FK), target_dept_id(FK), granted_by(FK),
  permission_type(固定read_download)

index_tree          -- 索引树（AI问答知识地图）
  id, node_type, ref_id, parent_id(FK), path(LTREE),
  name, description, folder_summary, summary(≤200字),
  category_l1, category_l2, key_entities(TEXT[]), time_range(TSTZRANGE),
  admin_notes, health_score(0-100), index_level(1/2/3),
  CHECK(node_type IN ('department','user','folder','file')),
  CHECK(index_level IN (1,2,3)),
  CHECK(health_score BETWEEN 0 AND 100)

tags / file_tags    -- 标签多对多（支持跨文件夹横向检索）
```

#### 审计与对话

```sql
audit_logs      -- 审计日志
  id, user_id(FK), action(login/upload/download/preview/delete/permission_change/ai_query/ai_code_exec/org_sync),
  target_type, target_id, detail(JSONB), ip_address(INET), created_at

chat_messages   -- AI对话记录
  id, session_id, user_id(FK), role(user/assistant), content,
  citations(JSONB), satisfaction(thumbs_up/thumbs_down/saved/NULL),
  is_external_ai(BOOLEAN), created_at
```

#### 缓存与学习

```sql
index_cache     -- AI索引结果缓存（基于SHA-256去重，避免重复调用AI）
  id, sha256_hash(UNIQUE), summary, tags(TEXT[]),
  category_l1, category_l2, key_entities(TEXT[]),
  index_level, prompt_version,  -- 提示词/模型版本号，升级时可按版本批量失效
  created_at

cmd_templates   -- 指令解析模板（AI兜底解析结果的反馈学习）
  id, raw_input, pattern(泛化正则), action(move/create_folder/rename/delete),
  params_template(JSONB), hit_count, status(pending/approved/rejected),
  approved_by(FK), created_at
```

> **LTREE选型说明**：支持高效祖先查询（`@>`）、后代查询（`<@`）和路径匹配（`~`），适合深度 ≤ 10 层的文件夹树。

#### 关键数据库索引

```sql
-- 文件查询（用户文件列表、文件夹内文件、回收站）
CREATE INDEX idx_files_user_folder ON files(user_id, folder_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_files_deleted ON files(deleted_at) WHERE deleted_at IS NOT NULL;

-- 文件夹树查询
CREATE INDEX idx_folders_path ON folders USING GIST(path);
CREATE INDEX idx_folders_user_parent ON folders(user_id, parent_id) WHERE deleted_at IS NULL;

-- 索引树导航
CREATE INDEX idx_index_tree_path ON index_tree USING GIST(path);
CREATE INDEX idx_index_tree_parent ON index_tree(parent_id);
CREATE INDEX idx_index_tree_ref ON index_tree(node_type, ref_id);

-- 审计日志查询（按用户+时间、按操作类型+时间）
CREATE INDEX idx_audit_user_time ON audit_logs(user_id, created_at DESC);
CREATE INDEX idx_audit_action_time ON audit_logs(action, created_at DESC);

-- 对话记录
CREATE INDEX idx_chat_session ON chat_messages(session_id, created_at);
CREATE INDEX idx_chat_user ON chat_messages(user_id, created_at DESC);

-- 索引缓存去重
CREATE UNIQUE INDEX idx_index_cache_hash ON index_cache(sha256_hash);

-- 权限查询
CREATE INDEX idx_perms_grantee ON folder_permissions(grantee_user_id);
CREATE INDEX idx_perms_folder ON folder_permissions(target_folder_id);
```

---

## 四、核心功能

### 4.1 文件管理（聊天驱动）

#### 上传流程

**架构设计原则：前端直传 MinIO，后端零数据穿透**。历史方案中分片经由 FastAPI 中转再推送 MinIO，在多用户并发上传 100MB 文件时会消耗大量后端内存（10 用户并发 ≈ 1GB+ 缓冲）。v3.0 改为 MinIO 原生直传，FastAPI 仅参与签名协调，不参与数据传输。

**文件大小分路策略**：

| 文件大小 | 上传方式 | 说明 |
|----------|----------|------|
| < 20MB | 单次 PUT 直传 | 1 个预签名 PUT URL，1 次 HTTP 请求完成 |
| ≥ 20MB | Multipart 分片直传 | 5MB/片，MinIO 原生分片协议，支持断点续传 |

```
上传时序 A（小文件 < 20MB，单次直传）：

1. 前端 Web Worker：计算整体 SHA-256

2. POST /api/v1/upload/init
   后端执行（顺序严格）：
   a. 分布式防并发锁：SET NX "lock:upload:<user_id>:<sha256>" EX 3600
      命中同一哈希的并发请求直接返回 202 "处理中"，避免竞态
   b. 去重检测（最早期执行，此时尚未分配存储）：
      查 PG files 表：同哈希同文件夹 → 返回 409 + 提示"文件已存在，是否覆盖"
      同名不同哈希同文件夹 → 正常继续（将作为新版本处理）
   c. 生成 MinIO 预签名 PUT URL（TTL=30min）
      metadata 中携带 x-amz-meta-sha256: <sha256>（用于服务端校验）
   d. 返回：{ upload_mode: "single", presigned_url, file_id }

3. 前端直接 PUT 文件到预签名 URL（绕过后端，1 次请求）

4. POST /api/v1/upload/complete
   后端执行：
   a. 调用 MinIO StatObject → 读取对象 metadata 中的 x-amz-meta-sha256
      与步骤 1 的 SHA-256 比对，不一致则删除对象并返回 400
   b. 写入 PostgreSQL files / file_versions 记录
   c. 释放分布式锁
   d. 触发 Celery 异步解析任务
```

```
上传时序 B（大文件 ≥ 20MB，Multipart 分片直传）：

1. 前端 Web Worker（后台线程，不阻塞UI）：
   - 计算整体 SHA-256（避免主线程冻结，100MB 文件约 2-3 秒）
   - 将文件切割为 5MB 分片，生成分片列表

2. POST /api/v1/upload/init
   后端执行（顺序严格）：
   a. 分布式防并发锁：SET NX "lock:upload:<user_id>:<sha256>" EX 3600
   b. 去重检测：同哈希同文件夹 → 返回 409；同名不同哈希 → 继续
   c. 调用 MinIO CreateMultipartUpload，metadata 写入 x-amz-meta-sha256: <sha256>
      → 获取原生 upload_id
   d. 为前 N 片生成预签名 PUT URL（首批最多 10 片，TTL=30min）
   e. 将 upload_id + 分片总数 + 已完成分片集合存入 Redis
      （Key: upload:session:<upload_id>，TTL=48h）
   f. 返回：{ upload_mode: "multipart", upload_id, presigned_urls[], chunk_size }

3. 前端并发直传：
   - 每个分片通过预签名 URL 直接 PUT 到 MinIO（绕过后端）
   - 并发数限制：max 3 片同时传（避免占满内网带宽）
   - 单片超时 60 秒，失败自动重试（最多 3 次）
   - 每完成一批（10 片）后调用 POST /api/v1/upload/<upload_id>/presign
     获取下一批预签名 URL（滚动续签，始终保证 URL 在 30min 内有效）
   - 上传进度实时展示（已传分片数 / 总分片数）

4. 断点续传：
   - 上传中断后刷新页面，前端重新计算 SHA-256
   - GET /api/v1/upload/<upload_id>/status → 返回已完成分片列表
   - 前端跳过已完成分片，对剩余分片调用 /presign 获取新 URL 续传
   - Redis 中 upload:session TTL 为 48h，支持次日续传

5. POST /api/v1/upload/complete
   后端执行：
   a. 引入最终一致性补偿（Outbox 模式）：在 PG 记录 `pending_complete` 状态，防止应用崩溃导致 MinIO 幽灵文件
   b. 调用 MinIO CompleteMultipartUpload（服务端内部合并，零后端 IO）
   b. 调用 MinIO StatObject → 读取对象 metadata 中的 x-amz-meta-sha256
      与步骤 1 的 SHA-256 比对，不一致则 AbortMultipartUpload 并返回 400
      （避免分片传输中的静默数据损坏）
   c. 写入 PostgreSQL files / file_versions 记录
   d. 释放分布式锁
   e. 触发 Celery 异步解析任务（MarkItDown + AI索引 + ES写入）
```

**去重检测**（在 step 2.b 中执行，init 阶段最早期拦截，此时用户尚未传输任何数据）：
- 同哈希同文件夹 → 返回 409 + 提示"文件已存在，是否覆盖为新版本"；用户确认后后端解锁并继续
- 同名不同哈希同文件夹 → 自动作为新版本处理
- 跨用户不去重（隐私隔离），但 AI 索引可通过 `index_cache`（SHA-256）复用
- 同用户不同文件夹的同哈希文件 → 正常存储（用户可能有意分类放置）

**展示文件夹结构 + 智能推荐存放位置**，用户通过自然语言指令选择。

**后台异步处理**（Celery Worker，全程不阻塞上传响应，详见 4.3 节自动索引生成流程）：
- MarkItDown → Markdown 副本 → 按语义边界切割为 256-512 Token 语义块 → 写入 ES（BM25）
- 语义块批量调用通义千问 Embedding API → 生成向量 → 补写 ES `content_vector`（标记 `vector_ready=true`）
- 提取标题+目录+前500字 → 调用外部 AI → 生成摘要/标签/分类/关键实体
- 更新索引树节点（含 `index_cache` SHA-256 复用检查）+ 写入 ES 文档（含 `read_allow` ACL）
- 触发 folder_summary 增量汇总（60秒防抖 + Redis 分布式锁）

#### 分片孤儿回收（GC）

MinIO 中存在"已创建 Multipart 会话但从未 Complete 或 Abort"的孤儿分片，长期积累会浪费存储空间。

| 机制 | 实现 |
|------|------|
| MinIO 生命周期策略（首选） | 通过 `mc ilm add` 配置 Bucket 生命周期规则：未完成的 Multipart Upload 超过 **48小时** 自动中止并清理分片，无需业务代码介入 |
| Celery 兜底扫描 | 每日凌晨定时任务扫描 Redis 中 TTL 已过期但状态仍为 `processing` 的 upload_id，调用 MinIO AbortMultipartUpload 清理对应碎片 |

#### 聊天指令解析（本地规则优先 + AI兜底）

- **第一层**：本地正则模板匹配（"放到{folder}里"/"新建{name}文件夹"/"改名为{name}"/"删除{file}"），支持编辑距离模糊匹配，高置信度直接执行，低置信度确认
- **第二层**：规则失败时调用外部AI解析，返回结构化意图，确认后执行

**反馈学习**：AI解析结果经用户确认后，泛化为正则模板存入`cmd_templates`表（需管理员审核后启用）。同类模式 ≥ 5次/月时提醒管理员加入正式规则库。目标覆盖率：90% → 95%+。

#### 文件夹AI辅助索引

用户新建/重命名文件夹时，AI根据命名自动生成描述建议并通过聊天提问补充信息（如合同类型），自动建立文件夹索引（描述、标签、时间范围），用户可确认或修改。

#### 上传安全校验

| 校验项 | 规则 |
|--------|------|
| 类型白名单 | PDF/Word/Excel/PPT/图片(jpg/png/gif)/文本(txt/md/csv) |
| MIME校验 | 后端Magic Bytes校验真实类型，不信任前端Content-Type |
| 文件名消毒 | 移除路径分隔符/控制字符/特殊字符，截断≤255字符 |
| 大小限制 | 单文件 ≤ 100MB（Nginx + 后端双重校验） |
| 可执行文件 | 拒绝.exe/.bat/.sh等，Magic Bytes拦截伪装扩展名 |

> 反病毒扫描：初期不集成，后续可集成ClamAV异步扫描。

#### 支持的文件格式

| 格式 | 在线预览 | AI检索 | 解析质量 |
|------|----------|--------|----------|
| PDF | 直接预览 | ✅（扫描件标记`ocr_required`） | ⭐⭐~⭐⭐⭐ |
| Word/Excel/PPT | 转PDF预览 | ✅ | ⭐⭐⭐ |
| JPG/PNG/GIF | 直接预览 | ⚠️ Phase 6 OCR后支持 | - |
| TXT/MD/CSV | 直接预览 | ✅ | ⭐⭐⭐ |

#### 文件版本控制

- 同名文件上传同一文件夹 → 自动保留历史版本，保留最近10个版本
- MinIO路径：`files/{YYYY-MM}/{file_id}/v{n}/{original_filename}`（物理路径与业务逻辑解耦，详见 6.3 节）
- 回滚：复制旧版本为新v{n+1}（保留完整历史链），触发完整重索引
- 版本diff：Phase 1暂不支持

#### 文件删除与级联

**软删除 + 30天回收站**：

- **立即**：从ES/索引树/标签关联中移除，触发folder_summary重汇总，对话引用标注"[来源已删除]"
- **30天后**：定时任务彻底清除MinIO三路径对象 + PG元数据

#### 公共知识库管理

- **上传**：管理员直接发布；部门主管上传需审核
- **维护**：标记更新频率，过期文档标黄提醒，可标记"归档"（常规检索不显示，可选包含）
- **分类**：管理员维护一级/二级分类体系，AI自动推荐分类

#### 大文件处理策略

| 任务 | 超时 | 失败策略 |
|------|------|----------|
| MarkItDown解析 | 5分钟 | 重试3次 → 降级纯文本入ES，标记`degraded` |
| Gotenberg转PDF | 3分钟 | 重试2次 → 降级为"下载查看" |
| AI索引生成 | 3分钟 | 异步重试，降级用规则基础索引 |
| 组织架构同步 | 30分钟 | 记录日志，下次定时重执行 |

**扫描件PDF自动检测**：MarkItDown 解析完成后执行文本密度检查——若 PDF 文件大小 >1MB 但解析产出文本 <200 字符，判定为扫描件/图片型 PDF，自动标记 `parse_status=ocr_required`。该状态下文件不进入 ES 全文索引，AI 检索时跳过该文件内容。前端在文件列表和预览页对 `ocr_required` 状态的文件显示警告提示："该文件疑似扫描件，文本内容无法被检索，OCR 识别功能将在后续版本支持"。管理后台可按此状态筛选，便于批量管理。

**渐进式索引**：首次仅发送标题+目录+前500字生成初级索引；检索命中率低时再发送更多内容生成增强索引。Markdown副本不出网，仅发送提取的文本片段。

**AI索引缓存**：基于SHA-256指纹查询`index_cache`表，命中直接复用（0 Token），未命中则调用AI后写入缓存。适用场景：跨用户相同文件、版本回滚、跨文件夹重复上传。缓存与 `prompt_version` 绑定，AI模型或提示词升级时通过更新版本号触发旧版本缓存批量失效（不删除，标记为过期后由定时任务重索引）；孤立记录（文件已删除）由定时任务清理。

#### folder_summary 频率控制

| 策略 | 规则 |
|------|------|
| 增量汇总（默认） | 仅发送变更差异 + 现有summary，Token O(delta) |
| 全量重建 | 每周定时（仅有增量汇总过的文件夹）或变动 >30% 且 ≥3文件 |
| 防抖 | 60秒内有新变动重置计时器 |
| 冷却 | 同一文件夹每小时最多2次；冷却期内的变更累积记录到 Redis 脏标记（Key: `folder:dirty:<folder_id>`），冷却期结束后自动补发一次汇总 |
| 优先级 | Celery低优先级队列`queue=low` |
| 限流 | 受全局AI API 60次/分钟配额约束 |

#### AI索引批量合并

批量上传时，60秒防抖窗口内同一文件夹的待索引文件合并为一次AI请求（≤5个/批，>5个按5个分批间隔2秒）。约束：同文件夹同索引级别、单次≤4000 Token、缓存命中跳过、失败回退单个请求。Token节省约30%。

### 4.2 AI问答（混合检索 + 索引树导航）

> **术语说明**：索引树导航 = Deep RAG 模式 = 知识地图导航；文件夹全局说明 = folder_summary；RRF = Reciprocal Rank Fusion（倒数排名融合）

#### 设计理念

传统 RAG 将文档切成碎片做向量检索，丢失结构和逻辑关联。本方案采用**"ES 原生混合检索（BM25 + Vector RRF）→ 本地 Reranker 精筛 → 索引树导航 → 渐进式深度阅读"**架构，通过三个关键决策大幅提升效率与降低成本：

- **关键决策一：ES 底座收敛**：向量检索与 BM25 全文检索统一至 Elasticsearch 8.x，利用其原生 `dense_vector` + HNSW 在**同一查询请求**内完成混合打分（RRF），彻底避免了跨两个数据库（PG + ES）协调的网络开销和代码复杂度。`pgvector` 扩展从技术栈中移除。
- **关键决策二：本地 Reranker 截断上下文**：ES 混合检索粗筛 Top-20 候选文档片段后，在本地后端运行轻量级 Cross-Encoder 重排模型（`BGE-Reranker-Base`，约 600MB，CPU 可运行），对 20 个片段精准打分，仅将 Top-3（约 1000 Token）交给外部大模型处理，相比直接发送 3000 Token 节省约 67% 的输入成本，并大幅提升回答准确度。
- **关键决策三：并线路由与错峰发车**：用户提问时主路（混合检索）优先执行，辅路（索引树 AI 导航）通过 `asyncio.sleep(0.3)` **延迟启动**。由于主路极快（200-300ms），若在 300ms 内达成置信度 ≥ 0.85 的判定，直接取消辅路的 LLM 请求。此举在不影响端到端感知延迟的前提下，大幅节省外部 API 的 Token 和带宽浪费。

#### 架构设计

```
用户提问 → 意图分类（纯本地规则，零延迟）
         ├─ 简单查找（置信度高）→ 上下文预算截断为 2000 Token → 快速通道
         └─ 复杂推理（多跳/对比/聚合）→ 完整通道（10000 Token 预算）
                              ↓
          会话状态管理（维护上下文约束 + 多轮澄清 + 实体追踪槽）
                              ↓
           Skill 路由（personal / shared / public_kb，可并发触发）
                              ↓
         ┌────────────────────┴──────────────────────┐
         │  主路（并行）                               │  辅路（并行）
         │  ES 混合检索                                │  索引树 AI 导航
         │  BM25 + Vector → RRF 融合 → Top-20          │  本地预过滤 → AI 规划路径
         │  权限过滤（read_allow term）                 │  folder_summary 路由
         └────────────────┬───────────────────────────┘
                          │  主路置信度 ≥ 0.85 → 取消辅路延迟启动
                          ↓
             本地 Reranker（BGE-Reranker-Base）
             进程池 CPU 推理防阻塞，Top-20 片段 → 精准打分 → Top-3（~1000 Token）
                          ↓
                    早停判断：信息足够？
              是↙                      ↘否
              │             Token 预算检查
              │        接近上限↙        ↘充足
              │      相邻块缝合合并    渐进式深度阅读
              │      挤出上下文     （按语义块渐进加载）
              └──────────────────────────┘
                          ↓
                答案综合层（标注引用来源 + 置信度）
                          ↓
            置信度高 → 直接输出答案（SSE 流式）
            置信度低 → 触发外部 AI 兜底（仅发送脱敏问题）
```

#### 索引树导航机制（辅路：Deep RAG 模式）

索引树导航作为辅路运行，在主路（ES 混合检索）置信度不足时介入，提供知识地图式的精确路由能力。

```
第 0 步：本地预过滤（零AI成本，与主路并行执行）
  - jieba分词 → 同义词扩展（复用 synonyms.txt）→ 文件夹名/标签/描述文本匹配
  - 只注入匹配度>0的文件夹；未匹配文件夹折叠为"其他N个文件夹"概要
  - 效果：20个文件夹预过滤后通常只注入3-5个

第 1 步：注入顶层索引（200-800 Token）→ AI输出结构化JSON（目标文件夹ID列表），
         禁止AI输出推理过程，强制JSON格式降低输出Token消耗
第 2 步：注入子层索引（按需）→ AI判断哪些文件最可能含答案
第 3 步：执行ES混合检索（带文件ID过滤，缩小检索范围）
  第 4 步：多轮迭代，最多 3 轮（与 Token 优化策略中的早停上限一致）；不足时返回第1步或扩展关键词
```

#### Skill体系定义

| Skill | 功能 | 检索范围 |
|-------|------|----------|
| skill_personal_search | 个人文件空间检索 | 用户自己上传的文件 |
| skill_shared_search | 共享文件检索 | 被授权的共享文件夹 |
| skill_public_kb_search | 公共知识库检索 | 管理员维护的公共文档 |
| skill_deep_read | 渐进式深度阅读 | 单文件，按章节/页渐进加载 |
| skill_query_table | Excel/CSV查询：脱敏表头+类型给AI生成Pandas代码 → 后端沙箱执行 → 返回结果 | 用户有权访问的表格文件 |
| skill_compare | 多文件对比 | 指定的多个文件 |
| skill_summarize | 文件/文件夹摘要 | 指定范围内文件 |
| skill_timeline | 时间维度检索 | 用户有权访问的文件 |

#### skill_query_table 安全沙箱设计

```
1. 沙箱隔离
   - 方案A（推荐）：预热容器池（Docker Compose 中长驻 sandbox 服务，维护2个 warm 容器）
     - 容器预装 Python + pandas + numpy，启动后 idle 等待任务
     - 每次执行通过 HTTP API 提交代码 → 容器内 worker 执行 → 返回结果
     - 容器无网络（`network_mode: none`）、只读根文件系统、tmpfs 临时目录
     - 执行完毕重置 worker 状态（不销毁容器），避免冷启动延迟
   - 方案B（备选）：RestrictedPython + 白名单 AST 检查，仅允许 pandas/numpy
     ⚠ RestrictedPython 历史上存在通过 __class__.__mro__ 等属性链绕过限制的漏洞，
       单独使用不足以保障安全，必须配合静态 AST 白名单检查才可作为替代方案
   - 禁止：import os/sys/subprocess/socket/shutil

2. 执行约束
   - 超时：30秒强制SIGKILL（防止AI生成的死循环代码占用资源）；内存：256MB
   - CPU：Docker Compose 配置 `cpus: 0.5`（限制单个沙箱容器最多使用0.5核）
   - 输入：最大100万行×100列；输出：最大1000行

3. 代码审计
   - 静态分析拒绝：eval()、exec()、__import__()、open()、globals()、locals()
   - 记录完整执行代码和结果到审计日志

4. 数据隔离
   - 每次执行创建独立临时目录，完毕立即销毁
   - DataFrame仅在内存中存在，不落盘
```

**表结构缓存与查询模板复用**：

| 优化策略 | 说明 | Token节省 |
|----------|------|-----------|
| 表结构指纹缓存 | 缓存列名+数据类型+脱敏样本行(3行)+行列数到Redis（Key: `table:schema:<file_id>:<version>`，TTL 24h） | ~100-300/次 |
| 查询模板参数化 | 首次生成Pandas代码后提取参数化模板，后续同类查询直接填参数执行，不再调AI | ~500-1000/次 |
| 代码结果缓存 | 缓存AI生成代码（Key: `table:code:<file_id>:<query_intent_fingerprint>`，TTL 24h） | 命中时100% |
| 列名同义词映射 | 提取"销售额=营收=revenue"等列名同义词，归一化后提升模板命中率 | 间接+10-15% |
| 模板匹配 | 动词+归一化列名+聚合方式做意图指纹匹配，企业报表场景命中率50-70% | - |

#### 检索策略总览

| 检索层级 | 引擎/模型 | 适用场景 | 延迟 | Token消耗 |
|----------|-----------|----------|------|-----------|
| Query Embedding | 通义千问 text-embedding-v3（外部API） | 用户问题向量化（Vector KNN 前置步骤） | ~200-400ms（网络 RTT） | 极低（问题文本，<100 Token） |
| ES 混合检索（主路） | Elasticsearch 8（BM25 + Vector RRF） | 所有查询的第一道防线：精确关键词、语义模糊、同义表达 | 低（<200ms，ES 本地） | 零（ES查询） |
| 本地 Reranker（精筛） | BGE-Reranker-Base（本地CPU推理） | Top-20 候选 → Top-3 精准截断，消除 Lost-in-Middle 效应 | 低（~100ms） | 零（本地模型） |
| 索引树导航（辅路） | PostgreSQL + LLM（JSON输出） | 延迟 300ms 启动，主路置信度不足时：复杂多跳、全局概括 | 中 | 低（200-800 Token） |
| 表格查询 | skill_query_table（Pandas沙箱） | Excel/CSV 数值过滤、聚合计算 | 中 | 极低 |
| 渐进式深度阅读 | Markdown语义块按需加载 | 精确定位后补全上下文，BM25/Reranker仍不足时 | 按需 | 按需（语义块粒度） |

> **端到端延迟预估（简单查找场景）**：Query Embedding ~300ms + ES 检索 ~150ms + Reranker ~100ms + LLM 首字节 ~1500ms ≈ **首字节 ≤ 2.1 秒**，符合 9.0 节 AI 问答 ≤5 秒（首字节 ≤2 秒）指标。

**混合检索（RRF）原理**：

```
ES 同一查询请求内并行执行：
  ① BM25 关键词匹配 → 返回文档排名列表（rank_bm25）
  ② dense_vector KNN（HNSW）→ 语义相似度排名（rank_knn）；vector_ready=false 的文档跳过 KNN
  RRF 融合得分 = Σ 1 / (k + rank_i)，k=60（ES 默认）
  融合后 Top-20 → 送入本地 Reranker → Top-3 → 送外部 LLM
```

**主路置信度计算**：

置信度基于本地 Reranker 输出分（Cross-Encoder logit，范围约 -10~10，经 sigmoid 归一化至 0-1）：

```
confidence = sigmoid(reranker_score_top1)

阈值规则：
  confidence ≥ 0.85 → 主路直接输出，取消辅路延迟启动
  0.60 ≤ confidence < 0.85 → 主路输出但同时等待辅路结果，取更高分
  confidence < 0.60 → 主路不足，辅路接管（或触发外部 AI 兜底）

说明：Reranker 输出分与文档库规模无关（Cross-Encoder 是句对打分），
      不受 ES _score 绝对值漂移影响，适合作为稳定阈值基准。
```

**BM25 不足时的场景处理**：

| 场景 | 短板 | 处理方案 |
|------|------|----------|
| 否定排除 | 只能检索含X的文档 | 索引树辅路全集视野遍历 |
| 数值比较/极值 | 无法做数值运算 | 加载多文件关键数值后比较 |
| 同义词/语义模糊 | 词汇不匹配 | ES Vector（KNN）语义补充 + Reranker 精筛 |
| 多跳推理 | 单跳无法建推理链 | 索引树辅路分步检索，每步驱动下一步 |
| 全局概括 | 片段无法覆盖全局 | 索引树了解全貌，按需加载 folder_summary |
| 表格计算 | 无法过滤聚合 | skill_query_table Pandas执行 |

#### Token 优化策略

**总体优化目标**：相比 v2.x 方案的 7000+ Token 上下文塞入，v3.0 通过 Reranker 精筛 + 语义切块 + 动态预算，将典型场景的外部 LLM 输入控制在 **2000-4000 Token**，节省约 50-70%。

```
1. 意图复杂度分类（本地规则，零延迟）→ 动态上下文预算：

   简单查找（如"张三的报销单在哪"）：
     预算上限 2000 Token（System 400 + 历史 500 + 检索结果 1100）
     跳过索引树导航，主路命中即输出

   中等复杂（如"找出2024年Q4的所有合同"）：
     预算上限 6000 Token（System 600 + 历史 1000 + 索引树 1500 + 检索结果 2900）

   复杂推理（如跨文件对比/多跳推理/全局汇总）：
     预算上限 10000 Token（System 800 + 历史 1500 + 索引树 2500 + 检索结果 5200）

2. ES 混合检索结果截断（Reranker 精筛后）：
   - ES 粗筛 Top-20 片段（本地处理，无Token消耗）
   - 本地 Reranker 精筛 → Top-3（约 800-1200 Token，依文档类型）
   - 普通文本/Markdown 每片：±5行上下文，硬上限 300 Token
   - 法律/合同文档每片：±10行，硬上限 500 Token

3. 渐进式深度阅读（语义切块，取代按##章节整章塞入）：
   - 索引时将 Markdown 切割为语义块（Chunk Size 256-512 Token）
     切块策略：优先按段落边界（空行），其次按句子边界，保留±1个句子上下文
   - 深度阅读时按语义块粒度按需加载，而非整个 ## 章节
   - Token预估 ≤ 300 → 加载整个语义块；> 300 → 仅加载命中句子±3行
   - 自动校准：维护最近100次请求的滑动窗口，按文档语言（中/英/混合）
     分别计算实际 char/token 比率（通过 AI API usage.prompt_tokens 校准）

4. 早停：每轮 Reranker 精筛后评估置信度，足够则立停，最多 3 轮（不再允许5轮）

5. Chunk 冗余消除（去重与缝合）：
   - **更新免生成**：在上传/更新时，引入 Redis Chunk Embedding 缓存（Key=MD5），微调文件仅对修改的 Chunk 重新调用外部 API。
   - **查询缝合**：对 Reranker 选出的 Top-K 进行相邻索引检测（`chunk_index` 相差 ≤1），代码级缝合合并，消除 ±1 个句子的上下文重叠（Overlap）。
   - **MMR 去重**：废弃耗时极高的“大模型中间摘要挤出”策略，改用本地余弦距离进行 MMR（Maximal Marginal Relevance）去重，零成本剔除相似冗余片段。
   清空原始片段继续检索

6. AI 导航路径强制 JSON 输出（仅 LLM 路由决策，不允许推理说明）：
   强制格式：{"target_folders": ["id1", "id2"], "search_keywords": ["kw1"]}
   减少约 200-400 Token 的推理输出消耗

7. 输出 Token 上限约束（max_tokens 参数硬限，减少无效冗余输出）：

   简单查找：max_tokens=300（定位类问题无需长篇回答）
   中等复杂：max_tokens=800
   复杂推理：max_tokens=2000
   通用知识兜底：max_tokens=1500（保持现有值）
```

**Reranker 部署规格**：

| 项目 | 规格 |
|------|------|
| 模型 | BAAI/bge-reranker-base（中英双语，约 600MB） |
| 运行环境 | ProcessPoolExecutor 独立进程池推理（避免阻塞 FastAPI 异步循环），CPU 推理 |
| 推理延迟 | 20 条候选 ~80-120ms（4核CPU） |
| 内存占用 | 约 1.2GB（含模型权重 + 推理缓冲） |
| 服务器影响 | 推荐配置 32GB 内存下可忽略不计 |

#### 数据安全边界

```
永远不出网：文件完整内容 / 用户操作日志 / 用户身份信息 / 文件名

受控出网：
  - AI索引生成：从Markdown副本提取标题/目录/摘要文本（不含文件名/用户信息）
  - Embedding 向量化：语义块纯文本片段（不含文件名/用户信息）→ 通义千问 text-embedding-v3
  - 外部AI兜底：仅发送脱敏的纯文字问题，不含任何文件内容
  - 系统提示词（不含业务数据）
```

#### 满意度反馈与多轮上下文管理

- 每条回答底部：满意 / 不满意 / 保存问题；管理员可查看全平台不满意问题汇总
- 双层存储：redis-cache（活跃会话，30分钟TTL） + PostgreSQL（对话摘要，90天）
- 对话历史压缩（含实体追踪）：
  - **实体追踪槽**：每轮提取关键实体（文件名/人名/数字/日期）存入独立追踪列表，不随压缩丢失，始终注入上下文
  - **最近3轮**：保留原文
  - **第4轮起**：规则压缩（保留问题原文 + 回答中的引用来源 + 关键数据点，~40-60 Token/轮）
  - **超15轮**：调用AI生成一次性摘要（指令要求保留所有实体和数据点）
  - **超20轮**：提示开新对话
  - 此为 V1 策略，后续需根据真实对话日志分析调整

#### AI 兜底问答触发逻辑

意图识别由纯本地规则驱动（零AI成本、零延迟）：

```
路径A（文件相关）：命中业务词汇/文件名/上下文已处于检索状态
  → Deep RAG检索 → 置信度高则输出，低则提示用户是否需要通用AI解答

路径B（通用知识）：命中编程语言名+通识句式，或不含业务词汇
  → 直接调用外部AI（输入≤2000/输出≤1500，无状态，用户每小时上限20次）

路径C（意图模糊）：以上均无法判定
  → 反问用户，根据回答走A或B
```

#### 高频答案缓存（Answer Cache）

仅适用公共知识库（个人文件内容不同，不可复用）：
- 缓存键构建：jieba分词 → 去停用词 → 保留否定词（不/没/无/未） → 提取年份/日期标识 → 词干排序 → SHA-256哈希
- 防误命中机制：直接复用系统第一步生成的 Query Embedding，计算**问题向量的余弦相似度（Cosine Similarity）**。相比 Jaccard 相似度（只看字面词重合，容易导致"张三报销单"和"李四报销单"误命中串话），余弦相似度能精准捕获语义意图，且不产生任何额外开销。
  （命中相似度阈值设定为 0.92）
- TTL：24小时；容量：1000条LRU；公共文件更新时主动失效
- 预期节省：高频场景减少20-40%的AI调用

---

### 4.3 索引体系设计

索引分**自动生成**和**手动管理**两个层面，文件夹层级构建主索引树，标签作为跨文件夹的横向检索通道。

#### 索引架构

```
组织根节点
├─ [部门] 销售部/              ← 管理员手动设置
│  ├─ [用户] 张三/             ← 管理员手动设置
│  │  ├─ [文件夹] 2024年Q3合同/ ← AI辅助+用户确认
│  │  │  ├─ 华东区代理协议.pdf  ← 自动生成
│  │  │  └─ 采购合同.docx      ← 自动生成
│  │  └─ [文件夹] 报销单据/
│
├─ [公共知识库]/               ← 管理员手动设置
│  └─ [文件夹] 公司制度/
│
└─ 横向标签索引（跨文件夹检索通道）
   ├─ #合同 → [华东区代理协议.pdf, 采购合同.docx, ...]
   └─ #2024Q3 → [2024年Q3合同/*, ...]
```

#### 索引节点数据结构

| 字段 | 类型 | 来源 | 说明 |
|------|------|------|------|
| name | 文本 | 系统自动 | 文件/文件夹名称 |
| description | 文本 | AI生成/管理员编辑 | 一句话摘要 |
| folder_summary | 长文本 | Celery异步汇总 | 主题范围+时间跨度+文件类型分布（文件增删时自动重新汇总） |
| tags | 标签数组 | AI自动+管理员补充 | 跨文件夹横向检索 |
| category_l1/l2 | 枚举/文本 | AI自动分类 | 一/二级分类 |
| key_entities | 文本数组 | AI自动提取 | 人名/公司名/金额/日期/编号 |
| time_range | 日期范围 | AI提取/用户设置 | 文档涉及的时间范围 |
| summary | 长文本 | AI生成 | 文档摘要（仅文件级，200字以内） |
| admin_notes | 长文本 | 管理员手动 | 仅部门/公共知识库文件夹 |
| health_score | 数值 | 系统计算 | 索引健康度（0-100） |

#### 自动索引生成流程

```
文件上传 → Celery Worker异步处理
  第1步：规则提取（零成本）
    - 文件名/元数据解析（Level 1 基础索引）
    - Markdown副本 → 按段落/句子边界切割为语义块（256-512 Token）
    - 语义块写入 ES（BM25 content 字段，`vector_ready=false`）
      此时文件已可被 BM25 关键词检索；Vector KNN 尚不可用（明确标记，查询侧感知）
  第2步：AI增强（渐进式出网）
    - 首次请求（~500 Token）：标题+目录+前500字 → 摘要+标签+一/二级分类（通义千问）
    - 语义块批量调用通义千问 text-embedding-v3（≤20块/批，批间间隔200ms）
      → 生成 dims=1536 向量 → 补写 ES content_vector → 更新 `vector_ready=true`
      → Embedding 失败时标记 `vector_ready=false`，Celery 定时任务（每小时）扫描重试
    - 置信度低时追加（~1500 Token）：各章节首段 → 增强摘要+关键实体
  第3步：索引入库 - 更新PostgreSQL + 标签索引 + 健康度评分
    - 检查 index_cache（SHA-256）：命中则直接复用摘要/标签，跳过第2步首次请求（0 Token）
  第4步：文件夹全局说明汇总（Celery异步）- 聚合文件夹内所有文件信息 → 调AI生成folder_summary
```

#### 管理员手动索引管理

超级管理员可编辑：部门根文件夹、用户根文件夹、公共知识库各文件夹的描述/分类/标签/适用人群/更新频率/备注。

#### 索引健康度评估

| 评估维度 | 权重 | 评分规则 |
|----------|------|----------|
| 描述完整度 | 30% | ≥10字满分，空为0 |
| 标签覆盖度 | 20% | ≥3个满分，0个为0 |
| 分类准确度 | 15% | 一/二级分类均存在满分 |
| 关键实体 | 15% | ≥2个满分 |
| 摘要质量 | 20% | ≥50字满分，空为0 |

- **≥80分**：良好（绿色）
- **50-79分**：可用建议优化（黄色）
- **<50分**：质量差（红色），AI自动跳过索引导航，直接用 `skill_deep_read` 全文阅读

#### 场景化索引策略

| 场景 | 典型文件 | 索引深度 | 最佳实践 |
|------|----------|----------|----------|
| 结构化档案 | 合同、简历、发票 | 高 - 硬性字段 | 必须提取姓名/日期/编号/金额存入key_entities |
| 模糊知识库 | 技术文档、培训材料 | 极高 - 标签增强 | TAR：预设分类+多维标签+同义词覆盖 |
| 大规模长文档 | 书籍、长篇报告 | 中 - 章节摘要 | 章节标题+关键词+摘要，检索时渐进加载 |
| 表格数据 | Excel、CSV | 中 - 列名索引 | 提取列名/数据范围/行数，标注"可做数据分析" |

#### 分级索引构建

| 级别 | 信息密度 | 生成方式 | Token消耗 |
|------|----------|----------|-----------|
| Level 1 基础型 | 文件名+类型+大小+日期 | 纯规则 | 0 |
| Level 2 结构型 | +章节结构+实体+分类 | 规则+AI首次请求 | ~500/文件 |
| Level 3 语义增强型 | +详细摘要+多维标签+实体关系 | AI追加请求 | ~2000/文件 |

默认所有文件 Level 1，文本类自动升 Level 2，管理员可手动升 Level 3。

#### Elasticsearch 索引设计

**索引 Mapping**：

```json
{
  "index": "documents",
  "settings": {
    "number_of_shards": 1,
    "number_of_replicas": 0,
    "analysis": {
      "analyzer": {
        "ik_smart_synonym": {
          "type": "custom",
          "tokenizer": "ik_smart",
          "filter": ["synonym_filter"]
        }
      },
      "filter": {
        "synonym_filter": {
          "type": "synonym_graph",
          "synonyms_path": "analysis/synonyms.txt"
        }
      }
    }
  },
  "mappings": {
    "properties": {
      "file_id":              { "type": "keyword" },
      "user_id":              { "type": "keyword" },
      "folder_id":            { "type": "keyword" },
      "is_public":            { "type": "boolean" },
      "read_allow":           { "type": "keyword" },
      "filename":        { "type": "text", "analyzer": "ik_max_word", "search_analyzer": "ik_smart" },
      "content":         { "type": "text", "analyzer": "ik_max_word", "search_analyzer": "ik_smart_synonym" },
      "file_type":       { "type": "keyword" },
      "tags":            { "type": "keyword" },
      "category_l1":     { "type": "keyword" },
      "category_l2":     { "type": "keyword" },
      "created_at":      { "type": "date" },
      "updated_at":      { "type": "date" },
      "parse_status":    { "type": "keyword" },
      "vector_ready":    { "type": "boolean" },
      "content_vector":  {
        "type": "dense_vector",
        "dims": 1536,
        "index": true,
        "similarity": "cosine"
      }
    }
  }
}
```

**设计决策**：

| 决策项 | 选择 | 理由 |
|--------|------|------|
| 中文分词 | IK（ik_max_word索引+ik_smart检索） | 最大化覆盖率，检索时提高精确度 |
| 同义词 | 自定义synonyms.txt | 支持"裁员赔偿=经济补偿金"等业务同义词 |
| 向量检索 | dense_vector（dims=1536）+ HNSW | 与 BM25 在同一请求内 RRF 融合，无需跨库协调；文档写入时由 Celery Worker 调用通义千问 text-embedding-v3 生成向量并写入 |
| 向量就绪状态 | `vector_ready` boolean 字段 | Embedding 写入前为 `false`，写入完成后置 `true`。KNN 检索时追加过滤条件 `filter: { term: { vector_ready: true } }`，避免未就绪文档参与向量检索产生零命中噪声 |
| 分片数 | 1主分片，0副本 | 单节点，文档<100万时足够 |
| 权限过滤 | 文档级ACL同步至ES | 每个文档存储 `read_allow: [user_id_1, user_id_2, ...]` 字段，包含文件所有者 + 被授权用户 + 部门成员等所有可读用户的 ID。权限变更时由 Celery 异步任务批量更新相关文档的 `read_allow` 字段（通过 `_update_by_query` 批量操作）。查询时仅需 `term: { read_allow: "当前user_id" }` 或 `term: { is_public: true }` 即可完成权限过滤，无需应用层展开文件夹 ID 列表，彻底避免 `max_clause_count` 限制。写入延迟通过 Celery 高优先级队列控制在秒级 |
| 解析状态 | parse_status字段（normal/degraded/ocr_required） | 降级解析文件可在结果中提示质量受限；`ocr_required`标识扫描件，前端显示警告 |

**IK 分词器 Docker 集成与词典维护**：

| 事项 | 方案 |
|------|------|
| Docker集成 | 自定义Dockerfile在构建阶段安装IK（版本号必须与ES完全一致） |
| 自定义词典 | `custom_dict.dic` 和 `synonyms.txt` 通过Docker Compose volume挂载至 `config/analysis/` |
| 词典热更新 | 配置 `remote_ext_dict` 指向后端词典HTTP端点，管理员编辑后自动生效，无需重启ES |
| 版本锁定 | ES镜像和IK插件版本号写死，升级时同步更新 |
| 同义词自动扩展 | 语义重写时自动将同义词对写入 `synonym_candidates` 表 → 管理员审核确认 → 热更新生效；≥10次/月的高频词对优先提醒审核 |

### 4.4 审计日志

管理员可查看以下操作记录：

| 日志类型 | 记录内容 |
|----------|----------|
| 登录日志 | 用户、时间、IP、登录方式、成功/失败 |
| 文件上传 | 用户、时间、文件名、大小、路径、哈希 |
| 文件下载 | 用户、时间、文件名、来源路径 |
| 文件预览 | 用户、时间、文件名 |
| 文件删除 | 用户、时间、文件名、路径、删除类型 |
| 权限变更 | 操作人、时间、被授权用户、授权内容 |
| AI问答 | 用户、时间、问题内容、是否调用外部AI、满意度 |
| AI代码执行 | 用户、时间、生成代码、执行结果、耗时 |
| 组织同步 | 时间、同步来源、变更摘要 |

**日志保留策略**：PostgreSQL 在线保留 6 个月，超期按月归档为 CSV 存入 MinIO `archives/audit-logs/`，归档保留 3 年。每月 1 日凌晨自动归档并清理已归档记录。管理员可按时间/类型/用户筛选导出 CSV。

---

## 五、认证与组织同步

### 5.1 钉钉混合模式SSO

```
正常流程（钉钉可用）：
浏览器 → /login → 生成 state 存 Redis(TTL=5min) → 跳转钉钉授权页
→ 用户扫码 → 回调 /oauth/callback?code&state → 校验 state（防 CSRF）
→ code 换 accessToken → 获取 userId + 部门 → 匹配/创建本地用户 → 签发 JWT

降级流程（钉钉不可用）：
浏览器 → /login → 账号密码表单 → bcrypt 验证 → 签发 JWT
```

### 5.2 组织架构同步策略

| 同步方式 | 触发时机 | 说明 |
|----------|----------|------|
| 全量同步 | 每天凌晨2点 | 拉取完整部门树和用户列表 |
| 增量回调 | 钉钉事件推送 | 处理入职/离职/调岗/部门变更 |
| 手动同步 | 管理员触发 | 紧急情况使用 |

**同步内容**：部门ID/名称/层级关系、用户ID/姓名/手机号/所属部门

### 5.2.1 用户离职数据处理策略

```
检测到用户离职 →
  立即：禁用账号 + 失效所有 JWT（更新 token_version） + 清除 Redis 会话

  文件处理（延迟，留处理窗口）：
  - 7天内：文件保留原位，标记"离职用户文件"；管理员/部门主管可查看下载转移；AI检索排除
  - 管理员可操作：转移文件 / 归档 / 删除（软删除→30天回收站→清理）
  - 90天未处理：自动归档，后台标黄提醒；不自动删除
```

> 设计原则：离职数据默认保留，需管理员显式操作才删除。

### 5.3 钉钉事件回调安全验证

端点 `POST /webhook/dingtalk` 验签流程：
1. 读取 Header 中 `timestamp` 和 `sign`
2. `stringToSign = timestamp + "\n" + appSecret`
3. `signature = Base64(HMAC-SHA256(stringToSign, appSecret))`
4. 校验 signature 一致 + 时间差 ≤ 60秒（防重放），否则返回 403

> appSecret 存环境变量，不写入代码。

---

## 六、部署架构

### 6.1 服务器要求

> 部署于企业自有服务器或私有虚拟化平台，不依赖公有云。

| 资源 | 最低 | 推荐 |
|------|------|------|
| CPU | 8核 | 16核 |
| 内存 | 16GB | 32GB |
| 系统盘 | 100GB SSD | 200GB SSD |
| 数据盘 | 500GB | 1TB+ |
| 网络 | 百兆内网 | 千兆内网 |
| OS | Ubuntu 22.04 LTS | Ubuntu 22.04 LTS |

### 6.2 Docker Compose 服务组成

```yaml
services:
  nginx          # 反向代理，IP白名单，HTTPS
  frontend       # React 前端（Nginx 静态托管）
  backend        # FastAPI 后端
  worker         # Celery 异步任务
  postgresql     # 关系数据库
  redis-cache    # 缓存（预览URL/AI会话/权限快照，allkeys-lru）
  redis-security # 会话存储（Token/上传会话状态，noeviction防驱逐）
  redis-security # 安全数据（Token黑名单/token_version，noeviction）
  redis-celery   # Celery 任务队列（noeviction）
  minio          # 文件对象存储
  elasticsearch  # 全文搜索引擎
  gotenberg      # 文档转换（LibreOffice Headless）
  sandbox        # skill_query_table 沙箱容器池（无网络、只读数据卷）
  flower         # Celery监控（仅内网）
```

### 6.3 MinIO 存储

单节点部署，适用于初期规模（≤500GB、30并发）。

**存储路径**（`documents` bucket）：

```
├── files/{YYYY-MM}/{file_id}/v{n}/{original_filename}     # 原始文件（下载/预览源）
├── markdown/{YYYY-MM}/{file_id}/v{n}/{original_name}.md   # Markdown副本（ES索引/AI问答源）
└── previews/{YYYY-MM}/{file_id}/v{n}/preview.pdf          # 预览PDF（Gotenberg转换）
```

> **路径解耦设计**：物理存储路径中不包含 `user_id`，文件归属关系完全由 PostgreSQL `files.user_id` 字段管理。好处：① 文件转移（如员工离职交接）只需更新 PG 记录的 `user_id`，O(1) 操作，无需移动 MinIO 对象；② 路径按月份分区（`YYYY-MM`），便于归档和生命周期管理；③ `file_id` 全局唯一，天然避免路径冲突。

**数据保障**：
- 数据目录挂载宿主机 `/data/minio`，Docker 重启不丢
- 每日 `mc mirror` 同步至备份磁盘，保留7天
- 扩容路径：迁移至 MinIO 分布式模式（4节点 Erasure Coding）

> 单节点无硬件容灾，宕机期间不可用。高可用需求需分布式部署或阿里云OSS。

### 6.4 网络访问控制

```nginx
geo $allowed_ip {
    default         0;
    10.0.0.0/8      1;
    172.16.0.0/12   1;
    192.168.0.0/16  1;
}
```

### 6.5 外网防火墙白名单

| 目标域名 | 端口 | 用途 | 数据说明 |
|----------|------|------|----------|
| login.dingtalk.com | 443 | 钉钉授权页 | 无业务数据 |
| api.dingtalk.com | 443 | 用户身份与组织 | 仅用户ID/姓名/部门 |
| dashscope.aliyuncs.com | 443 | 通义千问 API（索引生成 + Embedding 向量化） | 文档语义块纯文本片段/摘要片段，不含文件名/用户信息/完整文件 |
| api.deepseek.com | 443 | DeepSeek API | 仅纯文字问题 |

---

## 七、数据安全设计

### 7.1 存储加密

| 数据类型 | 加密方案 |
|----------|----------|
| 文件内容 | MinIO SSE-S3（AES-256），覆盖三类对象 |
| 数据库密码 | bcrypt，salt rounds ≥ 12 |
| 用户Token | JWT RS256，密钥对存环境变量 |
| 传输 | TLS 1.2+ |

### 7.2 Token 生命周期管理

| 场景 | 策略 |
|------|------|
| Access Token | 2小时，剩余 < 15分钟时前端静默刷新 |
| Refresh Token | 7天，HttpOnly Cookie |
| 主动登出 | Refresh Token JTI 写入 Redis 黑名单 |
| 密码修改/权限变更 | 更新 `token_version` 批量失效该用户所有 Token |
| 密钥轮换 | RS256 非对称，新旧密钥过渡期滚动更新 |

**密钥轮换（JWKS 机制）**：

```
密钥存储：密钥对存储于文件系统（/data/keys/），环境变量指定路径，不硬编码
密钥标识：每个密钥对分配唯一 kid（Key ID），JWT Header 携带 kid 字段
验证流程：后端维护密钥列表（当前 + 上一个），验证时按 JWT Header 中的 kid 匹配对应公钥

轮换周期：90天自动轮换（Celery 定时任务触发）
  1. 生成新 RS256 密钥对，分配新 kid
  2. 新密钥立即用于签发，旧密钥保留验证
  3. 7天过渡期后删除旧密钥（旧 Token 自然过期或续签为新 kid）
  4. 记录轮换事件到审计日志

紧急轮换：管理员手动触发，过渡期=0，立即删除旧密钥，所有旧 Token 失效
```

### 7.3 敏感信息管理

- 密钥/API Key/密码通过环境变量注入，`.env` 不入版本控制
- 生产环境建议 Docker Secrets 或密钥管理服务

### 7.3.1 CORS 策略

同源部署（Nginx 统一代理，`/api/*` 和 `/*` 路径区分），无需 CORS。分域部署时需配置 `CORSMiddleware`。

### 7.3.2 MinIO 预签名 URL 安全约束

| 约束项 | 策略 |
|--------|------|
| TTL | 15 分钟 |
| 鉴权 | 生成前校验用户权限 |
| 缓存隔离 | Key = `preview:url:<user_id>:<file_id>`，按用户隔离 |
| 审计 | 每次生成记录审计日志 |
| HTTPS | 强制 HTTPS 链接 |

### 7.4 Redis 会话与缓存策略

| Key 类型 | 命名规范 | TTL | Redis 实例 |
|----------|----------|-----|-----------|
| Token 黑名单 | `blacklist:jti:<jti>` | Refresh Token 剩余有效期 | redis-security |
| token_version | `user:tv:<user_id>` | 永久 | redis-security |
| AI 对话会话 | `chat:session:<session_id>` | 30分钟（活跃续期） | redis-cache |
| 钉钉 Token | `dingtalk:apptoken` | 与钉钉一致 | redis-cache |
| 预览 URL | `preview:url:<user_id>:<file_id>` | 15分钟 | redis-cache |
| 权限快照 | `perm:folders:<user_id>` | 5分钟（权限变更时主动失效） | redis-cache |
| folder脏标记 | `folder:dirty:<folder_id>` | 2小时 | redis-cache |
| 分片上传会话 | `upload:session:<upload_id>` | 24小时 | redis-security |
| ES权限同步锁 | `es:acl_sync:<folder_id>` | 5分钟 | redis-cache |

**Redis 多实例隔离**（替代 `SELECT` 多 DB，因 Redis 驱逐策略为实例级别，多 DB 无法独立配置）：

| 实例 | Docker 服务名 | 用途 | 驱逐策略 | 内存上限 |
|------|---------------|------|----------|----------|
| redis-cache | `redis-cache` | 缓存（预览URL、AI会话、权限快照） | `allkeys-lru` | 512MB |
| redis-security | `redis-security` | 会话（钉钉Token、JWT会话、大文件分片状态） | `noeviction` | 256MB |
| redis-security | `redis-security` | 安全数据（Token黑名单、token_version） | `noeviction` | 256MB |
| redis-celery | `redis-celery` | Celery 任务队列 | `noeviction` | 256MB |

Key 命名规范统一使用前缀命名空间（如 `cache:preview:*`、`security:blacklist:*`），便于监控和调试。

### 7.5 应用层限流策略

| 接口 | 维度 | 规则 | 实现 |
|------|------|------|------|
| AI 问答 | 用户级 | 10次/分钟 | Redis 滑动窗口 |
| 文件上传 | 用户级 | 50次/小时（按文件计，非分片计），≤100MB/个 | Redis 计数器 |
| 文件下载/预览 | 用户级 | 30次/分钟 | Redis 滑动窗口 |
| 外部 AI API | 全局 | 60次/分钟 | Redis 令牌桶 |
| 登录 | IP级 | 10次/5分钟，超限锁定15分钟 | Redis 计数器 |

被限流返回 HTTP 429 + `Retry-After` 头。

### 7.6 统一错误码体系

#### 错误响应格式

```json
{
  "error": {
    "code": "KB-FILE-003",
    "message": "文件类型不在白名单中",
    "detail": "不支持 .exe 文件上传，允许类型：PDF/Word/Excel/PPT/图片/文本",
    "request_id": "req_abc123"
  }
}
```

#### 错误码编码规则

格式：`KB-{MODULE}-{SEQ}`，MODULE 为模块缩写（3-5字母），SEQ 为3位数字序号。

| 模块 | 前缀 | 错误码范围 | 说明 |
|------|------|-----------|------|
| 认证 | `KB-AUTH` | 001-099 | 登录/Token/权限验证 |
| 文件 | `KB-FILE` | 001-099 | 上传/下载/删除/版本 |
| AI问答 | `KB-AI` | 001-099 | 检索/问答/沙箱执行 |
| 索引 | `KB-IDX` | 001-099 | 索引生成/更新/健康度 |
| 权限 | `KB-PERM` | 001-099 | 权限配置/共享/访问控制 |
| 组织 | `KB-ORG` | 001-099 | 钉钉同步/部门/用户管理 |
| 系统 | `KB-SYS` | 001-099 | 限流/服务不可用/配置 |

#### 核心错误码清单

| 错误码 | HTTP状态 | 说明 |
|--------|----------|------|
| KB-AUTH-001 | 401 | Token 过期或无效 |
| KB-AUTH-002 | 401 | Token 已被吊销（token_version 不匹配） |
| KB-AUTH-003 | 403 | 无权访问该资源 |
| KB-AUTH-004 | 401 | 钉钉授权失败 |
| KB-AUTH-005 | 401 | 本地登录密码错误 |
| KB-AUTH-006 | 403 | 账号已禁用（离职/停用） |
| KB-FILE-001 | 400 | 文件大小超限（>100MB） |
| KB-FILE-002 | 400 | MIME 类型与扩展名不匹配 |
| KB-FILE-003 | 400 | 文件类型不在白名单中 |
| KB-FILE-004 | 404 | 文件不存在或已删除 |
| KB-FILE-005 | 409 | 文件夹名称冲突 |
| KB-FILE-006 | 500 | 文件解析失败（MarkItDown） |
| KB-FILE-007 | 500 | 预览转换失败（Gotenberg） |
| KB-AI-001 | 503 | AI 服务暂不可用（主备均熔断） |
| KB-AI-002 | 504 | AI 请求超时 |
| KB-AI-003 | 500 | 沙箱代码执行失败 |
| KB-AI-004 | 400 | 问题内容为空或超长 |
| KB-AI-005 | 429 | AI 问答频率超限 |
| KB-PERM-001 | 403 | 无权访问该文件夹 |
| KB-PERM-002 | 400 | 权限配置参数无效 |
| KB-SYS-001 | 429 | 请求频率超限 |
| KB-SYS-002 | 503 | 服务维护中 |
| KB-SYS-003 | 500 | 内部服务错误 |

> 前端根据错误码前缀做统一拦截（如 `KB-AUTH-*` 触发重新登录流程），根据 `message` 做用户提示。`request_id` 用于运维排查，由 Nginx 生成并贯穿请求链路。

---

## 八、前端构建与部署

### 8.1 前端技术栈

| 技术 | 选型 | 说明 |
|------|------|------|
| 构建工具 | Vite 6 | 开发 HMR <100ms，生产构建基于 Rollup |
| UI 框架 | Ant Design 5 | 企业级组件，按需引入（通过 Tree Shaking 自动优化） |
| 状态管理 | Zustand | 轻量（<1KB），管理聊天会话/UI状态/用户偏好 |
| 服务端缓存 | React Query (TanStack Query v5) | 文件列表/用户信息/权限数据的缓存、自动刷新、乐观更新 |
| 路由 | React Router v6 | 懒加载路由，按功能模块拆分 |
| HTTP 客户端 | Axios | 统一拦截器处理 Token 刷新、错误码映射、请求重试 |
| 代码规范 | ESLint + Prettier | 统一代码风格 |

### 8.2 构建优化策略

```
产物结构（build/）：
├── index.html
├── assets/
│   ├── vendor-[hash].js      # 第三方依赖（React/Ant Design/Zustand）
│   ├── app-[hash].js         # 应用主包
│   ├── chat-[hash].js        # 聊天模块（懒加载）
│   ├── admin-[hash].js       # 管理后台（懒加载）
│   ├── preview-[hash].js     # 文件预览模块（懒加载）
│   └── *.css                 # CSS 按模块拆分
└── favicon.ico

优化措施：
  - Code Splitting：React.lazy + Suspense 按路由拆分（聊天/文件/管理后台/预览）
  - Vendor 分包：manualChunks 将 react/antd/zustand 拆为独立 vendor chunk
  - Tree Shaking：Ant Design 5 原生 ESM 支持，无需 babel-plugin-import
  - 资源压缩：Vite 默认 esbuild minify（JS），cssnano（CSS）
  - Gzip/Brotli：Nginx 配置 gzip_static on，构建时生成 .gz/.br 预压缩文件
  - 长缓存：文件名含 content hash，Nginx 配置 Cache-Control: max-age=31536000
```

### 8.3 前端部署方式

采用 Docker 多阶段构建，前端产物由独立 Nginx 容器静态托管：

```dockerfile
# Stage 1: Build
FROM node:20-alpine AS builder
WORKDIR /app
COPY package.json pnpm-lock.yaml ./
RUN corepack enable && pnpm install --frozen-lockfile
COPY . .
RUN pnpm build

# Stage 2: Serve
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
```

前端 Nginx 仅负责静态文件，上游 Nginx（主反向代理）统一路由：
- `/*` → frontend 容器（静态资源）
- `/api/v1/*` → backend 容器（FastAPI）
- SPA 路由：前端 Nginx 配置 `try_files $uri $uri/ /index.html`

---

## 九、性能指标

| 指标 | 目标值 | 实现方案 |
|------|--------|----------|
| 并发用户 | ≥ 30 | FastAPI 异步 + Nginx 限流 + Redis 缓存 |
| 文件检索 | ≤ 3秒 | ES + 预索引 |
| AI问答（单轮） | ≤ 5秒 | SSE 流式，首字节 ≤ 2秒 |
| 上传大小 | ≤ 100MB/个 | 5MB分片上传 + 断点续传 |
| 预览加载 | ≤ 5秒 | 上传时异步预转换 PDF |
| MarkItDown 解析 | ≤ 60秒/文件 | Word/Excel/PPT 通常 ≤ 10秒 |

### 9.1 并发瓶颈分析

| 瓶颈点 | 应对策略 |
|--------|----------|
| 外部 AI API | 全局限流 + `httpx.AsyncClient` 连接池，超限排队 |
| Celery Worker | 分容器部署，按队列独立伸缩（初始配置）：worker-high 2进程（Gotenberg I/O密集）、worker-default 2进程（MarkItDown+AI索引）、worker-low 1进程（folder_summary）。各容器独立 `-Q` 参数，可通过 `docker compose up --scale worker-default=2` 水平扩展。监控队列积压指标，根据实际负载调整 |
| Gotenberg | `--libreoffice-max-queue-size=2`，同时转换限 2 个 |
| PostgreSQL | FastAPI `asyncpg` 连接池 max_size=20，Worker 同步池 max_size=8 |
| MinIO 带宽 | Nginx 限单用户上传并发 3，分片上传（5MB/片）降低单次传输压力，千兆内网可支撑 |

### 9.2 SSE 流式输出策略

| 场景 | 处理策略 |
|------|----------|
| 网络断开 | EventSource 自动重连，后端分配唯一 ID 支持断点续传 |
| AI 长思考 | 每 5 秒心跳，前端 15 秒无事件判定超时 |
| 用户取消 | 关闭 SSE → 后端取消 AI 请求，释放资源 |
| 多标签页 | session_id 隔离，同用户最多 3 个并行问答 |

### 9.3 监控与告警

轻量方案：Docker 健康检查 + Flower + 应用内采集 + 日志告警，后续可升级 Prometheus + Grafana。

**关键告警阈值**：

| 类别 | 指标 | 阈值 |
|------|------|------|
| 磁盘 | 数据盘使用率 | > 80% 警告，> 90% 严重 |
| 磁盘 | MinIO 剩余空间 | < 50GB |
| Celery | 队列积压 | > 50 任务持续 5 分钟 |
| Celery | 任务失败率 | > 10%（1小时内） |
| ES | 索引失败 | 连续 5 个失败 |
| AI API | 调用错误率 | > 20%（30分钟内） |
| AI API | 熔断状态变化 | 任何变化 |
| 服务 | 容器状态 | 非 healthy > 1 分钟 |
| PG | 连接池使用率 | > 80% |
| PG | 慢查询 | > 5 秒 |
| Redis | 内存使用率 | > 80% |

**告警分发**：指标写入 PG metrics 表（保留7天）→ 管理后台通知 + 严重告警推钉钉群机器人，同类告警 5 分钟去重。

### 9.4 备份恢复

**RPO ≤ 24小时，RTO ≤ 4小时**

| 数据类型 | 方式 | 频率 | 保留 |
|----------|------|------|------|
| PostgreSQL | `pg_dump` | 每日 3:00 | 7天 |
| MinIO | `mc mirror` | 每日 4:00 | 7天 |
| ES | Snapshot API | 每日 3:30 | 7天 |
| Redis | RDB BGSAVE | 每小时 | 24个快照 |
| 配置文件 | Git 版本控制 | - | 永久 |

---

## 十、项目开发阶段规划

```
Phase 1 - 基础设施与认证（约2.5周）
├── Docker Compose 环境 + 数据库模型（LTREE）+ Alembic 迁移
├── 钉钉SSO + 本地降级认证 + JWT JWKS密钥轮换
├── 限流中间件 + Nginx IP白名单/HTTPS
├── 错误码体系基础框架 + 统一错误响应格式
└── 测试：认证 + JWT + 限流

Phase 2 - 文件管理系统（约3.5周）
├── [后端] MinIO 分片直传（预签名URL + 分布式防并发锁 + 断点续传 + 分片GC）
├── [后端] 文件安全校验 + 去重 + 版本控制 + 软删除级联
├── [后端] MarkItDown 解析管线 + 语义切块（256-512 Token）+ ES 写入（BM25 + Embedding 批量写 Vector）
├── [后端] Gotenberg 预览转换                              ┐ 后端/前端可并行
├── [前端] 聊天UI框架 + 文件树组件 + Web Worker 直传进度    ┘
├── [全栈] 聊天指令引擎 + 聊天驱动上传 + AI辅助文件夹索引
├── folder_summary 防抖 + Celery 分队列优先级
└── 测试：文件CRUD + 安全 + 解析 + ES BM25 + Vector 写入

Phase 3 - 权限体系（约2周）
├── [后端] 个人空间隔离 + 文件夹级权限 + 部门主管权限     ┐ 可并行
├── [前端] 权限管理界面 + 文件共享交互                    ┘
├── 权限审计 + 离职数据处理
└── 测试：权限隔离 + 跨用户控制 + 离职流程

Phase 4 - AI问答系统（约3.5周）
├── [后端] AI API 路由与故障切换（熔断）                  ┐
├── [后端] ES Vector 索引 + BM25+Vector RRF 混合检索       │
├── [后端] 本地 BGE-Reranker-Base 集成（Top-20 → Top-3）   ├ 后端AI/前端聊天可并行
├── [后端] 索引体系 + 并线路由（主路/辅路）+ skill_query_table │
├── [前端] 聊天问答界面 + SSE流式展示 + 引用标注           ┘
├── 渐进式深度阅读（语义块粒度）+ 动态Token预算 + 早停 + Token挤出
├── 多轮对话 + 意图路由 + 满意度反馈
└── 测试：ES 混合检索 + Reranker 精度 + RAG + 沙箱安全 + 故障切换

Phase 5 - 管理后台（约2周）
├── [前端] 用户权限管理 + 索引管理 + 公共知识库           ┐ 各管理页面可并行
├── [前端] 审计日志 + 问答反馈 + 监控面板                 ┘
└── 测试：E2E + 权限边界

Phase 6 - 综合测试与上线（约2周）
├── 全链路集成测试 + 30并发压测
├── 安全审计 + 灾难恢复演练 + 部署文档

人力假设：2-3人团队（1后端+1前端+1全栈/兼测试）
标注 [后端]/[前端] 的任务可分配不同开发者并行推进
```

> 每个 Phase 测试通过后方可进入下一阶段。

*文档由Brainstorm Agent生成 | v3.1*
