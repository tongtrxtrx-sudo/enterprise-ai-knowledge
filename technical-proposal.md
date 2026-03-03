---
企业级AI知识库系统 - 极简方案（30人小公司版）
 > 版本：v2.1 | 日期：2026-03-03 | 状态：待确认 | 基于 v2.0 的在线编辑与出网策略修订
---
一、项目概述
1.1 系统定位
部署于企业本地服务器的AI知识库系统，提供个人文件管理、智能问答、知识检索功能。数据完全存储于内网，账号密码登录，通过外部AI API提供智能问答与文档索引能力。
1.2 核心设计原则
- 数据内网存储：所有文件与业务数据不传输至外部
- 最小出网原则：外网访问仅限AI API（仅接收文本片段和纯文字问题）
- 权限最小化：用户默认只能访问自己的数据，权限需显式授予
- 混合交互模式：主界面为聊天窗口，侧边栏提供文件树浏览
- 极简部署：单台服务器 Docker Compose 一键启动，运维零门槛
1.3 相比 v3.2 的简化说明
| 去掉的模块                  | 原因                                                               |
| --------------------------- | ------------------------------------------------------------------ |
| 本地 BGE-Reranker 模型      | 30人并发极低，pgvector RRF 已够用，省去 600MB 模型 + 进程池复杂度 |
| Gotenberg 文档预览          | 改为直接下载，去掉 LibreOffice 容器                                |
| 钉钉 SSO + 组织同步         | 改为本地账号密码，管理员手动创建用户，去掉 OAuth 全链路            |
| Elasticsearch               | 改用 pgvector + tsvector，省去 2-4GB 内存，去掉独立容器            |
| Redis 安全实例              | Token 黑名单改存 PostgreSQL，持久化更可靠，去掉第二个 Redis        |
| MinIO 分片直传/断点续传     | 改为后端中转直传（≤10MB），去掉预签名URL体系                       |
| Celery Worker 容器          | 10MB 文件处理 ~10-15s，改用 FastAPI Background Tasks，够用即止     |
| 前端 SHA-256 Web Worker     | 改为后端上传后计算，前端零感知，简化上传流程                       |
| skill_query_table 沙箱      | 去掉 Pandas 沙箱容器池                                             |
| 成本感知路由/熔断器         | 改为简单重试（3次），主备固定切换                                  |
| JWKS 密钥轮换               | 改为 HS256 固定密钥，环境变量管理                                  |
| Outbox 补偿事务             | 去掉，接受极低概率的幽灵文件风险                                   |
| folder_summary 自动触发     | 改为按需触发（用户手动刷新），去掉防抖/定时逻辑                    |
| Answer Cache jieba 双重验证 | 改为精确字符串匹配缓存（exact match），去掉 jieba + Embedding 验证 |
| 指令模板反馈学习            | 去掉，纯规则匹配 + AI兜底                                          |
---
二、系统架构
2.1 整体架构图
 ┌──────────────────────────────────────────────────────┐
│               企业内网 (Intranet)                   │
│                                                  │
│  浏览器 ──▶ Nginx（IP白名单 + HTTPS + 限流）     │
│                    │                             │
│             FastAPI 后端服务                       │
│        认证 / 文件 / AI问答 / 权限 / 审计          │
│        Background Tasks（文件解析/索引生成）        │
│           │              │         │         │
│        Postgres + pgvector  MinIO  Redis           │
│        用户/权限/Token黑名单  文件   缓存         │
│        审计/全文/向量检索                        │
│                                                  │
│  React + TypeScript + Ant Design 前端              │
│        │                                         │
│    ONLYOFFICE Document Server（在线编辑）          │
└──────────────────┬───────────────────────────────┘
                    │ 仅以下流量出网
        AI API：dashscope.aliyuncs.com（通义千问）
                    api.deepseek.com
2.2 技术栈选型
| 层级           | 技术选型                              | 说明                                          |
| -------------- | ------------------------------------- | --------------------------------------------- |
| 后端框架       | Python 3.12 + FastAPI                 | 异步高性能，AI生态丰富                        |
| 前端框架       | React 18 + TypeScript + Ant Design 5  | 企业级UI组件                                  |
| 前端状态管理   | Zustand + React Query                 | 轻量，够用                                    |
| 前端构建       | Vite 6                                | 热更新快，构建自动优化                        |
| 关系数据库     | PostgreSQL 16 + pgvector + zhparser   | 用户/权限/审计/元数据/全文检索/向量检索 一体化 |
| Embedding 模型 | 通义千问 text-embedding-v3（外部API） | 文档向量化（dims=1536）                       |
| 缓存           | Redis 7（单实例，allkeys-lru，512MB） | 会话缓存/权限快照/对话上下文                  |
| 文档解析       | MarkItDown (Microsoft)                | Word/PDF/Excel/PPT → Markdown，本地运行       |
| 文件存储       | MinIO                                 | S3兼容对象存储                                |
| 异步任务       | FastAPI Background Tasks              | 文件解析、索引生成，10MB文件 ~15s，无需队列   |
| 在线编辑器     | ONLYOFFICE Document Server             | DOC/DOCX/XLS/XLSX/PPT/PPTX 在线编辑           |
| 容器化         | Docker + Docker Compose               | 一键部署                                      |
| 反向代理       | Nginx                                 | IP白名单、HTTPS、限流                         |
| 外部AI         | 通义千问 + DeepSeek API               | 索引生成 + 问答                               |
2.3 AI API 路由
| 功能场景                   | 供应商                         | 说明                                  |
| -------------------------- | ------------------------------ | ------------------------------------- |
| 索引生成（摘要/标签/分类） | 通义千问（主）→ DeepSeek（备） | 失败重试3次后切备                     |
| Embedding 向量化           | 通义千问 text-embedding-v3     | 失败标记 vector_ready=false，定时重试 |
| 问答                       | DeepSeek（主）→ 通义千问（备） | 失败重试3次后切备                     |
故障处理：主供应商超时30s / 5xx / 429 → 重试3次 → 切备选 → 备选也失败 → 降级提示用户暂不可用。无熔断器，简单计数重试。
出网内容边界：外发外部 API 仅包含问题文本、检索摘要片段和必要上下文，已做脱敏与最小化处理，不发送完整文件内容和用户敏感身份字段。
---
三、用户与权限体系
3.1 角色定义
| 角色       | 权限                                                                           |
| ---------- | ------------------------------------------------------------------------------ |
| 超级管理员 | 管理所有用户账号和文件；配置权限；查看全平台审计日志；管理公共知识库；系统配置 |
| 部门主管   | 查看+下载+编辑本部门成员文件；管理个人文件空间；上传公共知识库（需管理员开启） |
| 普通用户   | 管理个人文件空间；访问被授权的他人文件夹（查看/下载/可编辑）；访问公共知识库 |
3.2 权限配置规则
权限由超级管理员配置，单方面生效。支持用户→文件夹级/部门级授权。共享文件默认可编辑，可按需改为只读。
3.3 AI检索权限边界
AI检索范围 = 用户自有文件 + 管理员授权的他人文件夹 + 被共享文件（取决于权限） + 公共知识库。严格保证检索结果不出现无权内容。
3.4 核心数据表设计
-- 用户与部门（手动管理，无钉钉同步）
departments
  id, name, parent_id(FK), manager_user_id(FK), sort_order, created_at
users
  id, username(UNIQUE), name, department_id(FK),
  role(super_admin/dept_manager/user), status(active/disabled),
  password_hash,        -- bcrypt
  token_version,        -- Token批量失效版本号
  created_at, updated_at
-- 文件与版本（去掉 LTREE，改用 parent_id 递归查询）
folders
  id, user_id(FK), parent_id(FK), name,
  folder_type(personal/public/shared),
  deleted_at, created_at,
  UNIQUE(user_id, parent_id, name)
files
  id, folder_id(FK), user_id(FK), filename, original_name,
  file_type, file_size, sha256_hash, current_version,
  parse_status(pending/processing/normal/degraded/ocr_required/failed),
  deleted_at, created_at, updated_at
file_versions
  id, file_id(FK), version, file_size, sha256_hash,
  minio_original, minio_markdown, uploaded_at,
  UNIQUE(file_id, version)
-- 权限
folder_permissions
  id, grantee_user_id(FK), target_folder_id(FK),
  allow_edit BOOLEAN DEFAULT true,
  granted_by(FK), created_at
-- 编辑会话（在线编辑回调一致性控制）
doc_edit_session
  id, file_id(FK), file_version_id(FK), user_id(FK),
  edit_token TEXT UNIQUE, status(active/closed/expired), expires_at,
  created_at, updated_at
-- 索引树（简化版，去掉 LTREE/health_score 等）
index_tree
  id, node_type(folder/file), ref_id,
  parent_id(FK), name, description,
  folder_summary, summary,
  category_l1, category_l2,
  key_entities(TEXT[]), time_range(TSTZRANGE),
  tags(TEXT[]),
  index_level(1/2/3),
  created_at, updated_at
-- 审计与对话
audit_logs
  id, user_id(FK), action, target_type, target_id,
  detail(JSONB), ip_address(INET), created_at
chat_messages
  id, session_id, user_id(FK), role(user/assistant),
  content, citations(JSONB),
  satisfaction(thumbs_up/thumbs_down/NULL),
  created_at
-- AI索引缓存（相同文件内容复用）
index_cache
  id, sha256_hash(UNIQUE), summary, tags(TEXT[]),
  category_l1, category_l2, key_entities(TEXT[]),
  index_level, prompt_version, created_at
关键索引
CREATE INDEX idx_files_user_folder ON files(user_id, folder_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_files_deleted ON files(deleted_at) WHERE deleted_at IS NOT NULL;
CREATE INDEX idx_folders_user_parent ON folders(user_id, parent_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_audit_user_time ON audit_logs(user_id, created_at DESC);
CREATE INDEX idx_chat_session ON chat_messages(session_id, created_at);
CREATE INDEX idx_perms_grantee ON folder_permissions(grantee_user_id);
CREATE UNIQUE INDEX idx_index_cache_hash ON index_cache(sha256_hash);
-- Token 黑名单（替代 redis-security，重启不丢失）
token_blacklist
  jti         TEXT PRIMARY KEY,
  expires_at  TIMESTAMPTZ NOT NULL
CREATE INDEX idx_token_blacklist_expires ON token_blacklist(expires_at);
-- 定时清理：DELETE FROM token_blacklist WHERE expires_at < NOW()
-- 文档检索（替代 Elasticsearch）
doc_chunks
  id              BIGSERIAL PRIMARY KEY,
  file_id         UUID NOT NULL REFERENCES files(id) ON DELETE CASCADE,
  user_id         UUID NOT NULL,
  folder_id       UUID NOT NULL,
  is_public       BOOLEAN NOT NULL DEFAULT false,
  read_allow      UUID[],           -- 有权限的用户ID列表（权限过滤）
  chunk_index     INTEGER NOT NULL,
  content         TEXT NOT NULL,
  content_tsv     TSVECTOR,         -- 全文检索（zhparser中文分词）
  content_vector  VECTOR(1536),     -- 语义向量（pgvector HNSW）
  file_type       TEXT,
  tags            TEXT[],
  category_l1     TEXT,
  category_l2     TEXT,
  vector_ready    BOOLEAN NOT NULL DEFAULT false,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
-- 全文检索索引（GIN）
CREATE INDEX idx_chunks_tsv ON doc_chunks USING GIN(content_tsv);
-- 向量检索索引（HNSW，cosine相似度）
CREATE INDEX idx_chunks_vector ON doc_chunks USING hnsw(content_vector vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);
-- 权限过滤索引
CREATE INDEX idx_chunks_file ON doc_chunks(file_id);
CREATE INDEX idx_chunks_user ON doc_chunks(user_id);
CREATE INDEX idx_chunks_read_allow ON doc_chunks USING GIN(read_allow);
---
四、核心功能
4.1 文件管理
上传流程（后端中转，极简版）
1. POST /api/v1/upload（multipart/form-data，单次请求完成上传）
   后端：
   a. 大小校验：> 10MB 立即拒绝（413）
   b. Magic Bytes 校验真实类型
   c. 文件名消毒
   d. 后端计算 SHA-256
   e. 去重检测：同哈希同文件夹 → 返回 409（提示已存在）
              同名不同哈希 → 自动作为新版本
   f. 写入 MinIO
   g. 创建 files 记录（parse_status=processing）
   h. 触发 Background Task（异步，不阻塞响应）
   i. 立即返回成功 + file_id
（注：后端中转，单文件 ≤ 10MB，30人场景并发极低，无需分片直传，无需前端预处理）
后台异步处理（FastAPI Background Tasks）
MarkItDown → Markdown 副本 → 语义切块（256-512 Token）
→ 写入 doc_chunks（content + content_tsv）
→ 语义块批量调用通义千问 Embedding → 更新 content_vector（vector_ready=true）
→ 提取标题+目录+前500字 → 调用通义千问 → 生成摘要/标签/分类/关键实体
→ 写入 index_tree + index_cache（SHA-256去重）
处理时间估算：10MB 文件全流程 ~10-15s，用户可继续操作，状态栏轮询进度。
在线编辑（ONLYOFFICE）
1. POST /api/v1/files/{file_id}/edit/start
   - 服务端校验：登录、文件类型、文件版本、编辑权限（owner/admin/dept_manager/shared）
   - 返回编辑会话信息（token/回调地址/文档加载配置）
2. 前端唤起 ONLYOFFICE 编辑器（iframe）
3. 回调处理：
   - ONLYOFFICE 返回 status=2/6 时下载新文件版本
   - 写入 MinIO 新版本对象
   - 更新 file_versions 与 files.current_version
   - 触发异步重索引（与上传流程一致）
4. 回调返回 {error:0} 成功后端保存，前端提示保存完成
说明：编辑保存一律按新版本落库，保留最近10个版本；保存失败写入错误日志并允许手动重试。
上传安全校验
| 校验项     | 规则                                              |
| ---------- | ------------------------------------------------- |
| 类型白名单 | PDF/Word/Excel/PPT/图片(jpg/png)/文本(txt/md/csv) |
| MIME校验   | 后端 Magic Bytes 校验，不信任前端 Content-Type    |
| 文件名消毒 | 移除路径分隔符/控制字符，截断 ≤ 255 字符          |
| 大小限制   | 单文件 ≤ 10MB（Nginx + 后端双重校验）             |
| 可执行文件 | 拒绝 .exe/.bat/.sh，Magic Bytes 拦截              |
支持的文件格式
| 格式           | 下载 | AI检索                        |
| -------------- | ---- | ----------------------------- |
| PDF            | ✅   | ✅（扫描件标记 ocr_required） |
| Word/DOC/DOCX  | ✅   | ✅                            |
| Excel/XLS/XLSX | ✅   | ✅（内容索引）                |
| PPT/PPTX       | ✅   | ✅                            |
| TXT/MD/CSV     | ✅   | ✅                            |
| JPG/PNG        | ✅   | ❌ 暂不支持                   |
文件版本控制
- 同名文件上传同一文件夹 → 自动保留历史版本，保留最近10个版本
- MinIO 路径：files/{YYYY-MM}/{file_id}/v{n}/{original_filename}
- 回滚：复制旧版本为新 v{n+1}，触发重索引
文件删除
软删除 + 30天回收站：
- 立即：从 doc_chunks / 索引树 / 标签中移除
- 30天后：定时任务彻底清除 MinIO 对象 + PG 元数据
聊天指令解析
- 第一层：本地正则匹配（"放到{folder}里" / "新建{name}文件夹" / "改名为{name}" / "删除{file}"），高置信度直接执行，低置信度二次确认
- 第二层：规则失败时调用 DeepSeek 解析，返回结构化意图，确认后执行
4.2 AI问答（混合检索）
架构设计
用户提问
    │
    ▼
意图分类（本地规则，零延迟）
    ├─ 文件相关 → 混合检索通道
    ├─ 通用知识 → 直接调外部AI（无需检索）
    └─ 意图模糊 → 反问用户
    │
    ▼（文件相关路径）
Query Embedding（通义千问 API，~300ms）
    │
    ▼
pgvector 混合检索（tsvector BM25 + HNSW 向量 RRF，~100ms）
权限过滤（WHERE user_id = ? OR is_public = true OR ? = ANY(read_allow)）→ Top-10
    │
    ▼
答案综合（标注引用来源）→ SSE 流式输出
置信度低 → 触发外部AI兜底（仅发送脱敏问题）
注：pgvector SQL WITH 子查询手动实现 RRF，Top-5 送给 LLM（约 1500-2000 Token），对30人场景效果完全够用。
检索策略
| 检索层          | 引擎                              | 延迟     |
| --------------- | --------------------------------- | -------- |
| Query Embedding | 通义千问 text-embedding-v3        | ~300ms   |
| PG 混合检索     | tsvector GIN + pgvector HNSW RRF  | ~100ms   |
| LLM 答案生成    | DeepSeek / 通义千问               | SSE 流式 |
端到端延迟预估：300ms + 100ms + LLM 首字节 ~1500ms ≈ 首字节 ≤ 2 秒
Skill 体系
| Skill                  | 功能                                 |
| ---------------------- | ------------------------------------ |
| skill_personal_search  | 个人文件空间检索                     |
| skill_shared_search    | 共享文件检索                         |
| skill_public_kb_search | 公共知识库检索                       |
| skill_deep_read        | 渐进式深度阅读（单文件按语义块加载） |
| skill_compare          | 多文件对比                           |
| skill_summarize        | 文件/文件夹摘要                      |
Token 控制策略
意图复杂度分类（本地规则）→ 动态上下文预算：
简单查找：预算 2000 Token（System 400 + 历史 500 + 检索结果 1100）
中等复杂：预算 5000 Token（System 600 + 历史 1000 + 检索结果 3400）
复杂推理：预算 8000 Token（System 800 + 历史 1500 + 检索结果 5700）
输出 Token 上限：
  简单查找：max_tokens=300
  中等复杂：max_tokens=800
  复杂推理：max_tokens=2000
数据安全边界
仅以下内容可出网：问题文本、检索命中片段、脱敏摘要与上下文（不含完整文件内容）
必须不出网：文件完整内容 / 用户身份标识 / 文件名 / 原始日志明细
受控出网：
  - AI索引生成：标题/目录/摘要文本片段（不含文件名/用户信息）
  - Embedding 向量化：语义块纯文本片段
  - 外部AI问答：脱敏的纯文字问题和检索片段，不含完整文件内容与敏感字段
多轮上下文管理
- 双层存储：Redis（活跃会话，30分钟TTL）+ PostgreSQL（对话摘要，90天）
- 最近3轮保留原文，第4轮起规则压缩（保留问题 + 引用来源 + 关键数据点）
- 超15轮：调用AI生成摘要；超20轮：提示开新对话
高频答案缓存
仅适用公共知识库，精确字符串匹配：
- 缓存键：问题字符串 trim 后直接 SHA-256
- 命中条件：完全相同的问题字符串（exact match）
- TTL：1小时；容量：200条 LRU；公共文件更新时主动失效
4.3 索引体系
分级索引
| 级别               | 信息密度              | 生成方式        | Token消耗  |
| ------------------ | --------------------- | --------------- | ---------- |
| Level 1 基础型     | 文件名+类型+大小+日期 | 纯规则          | 0          |
| Level 2 结构型     | +章节+实体+分类+摘要  | 规则+AI首次请求 | ~500/文件  |
| Level 3 语义增强型 | +详细摘要+多维标签    | AI追加请求      | ~2000/文件 |
默认文本类自动升 Level 2，管理员可手动升 Level 3。
pgvector + tsvector 检索设计
-- RRF 混合检索 SQL 示例（BM25 + 向量，k=60 融合）
WITH
  bm25 AS (
    SELECT id, file_id, content,
           ts_rank(content_tsv, query) AS score,
           ROW_NUMBER() OVER (ORDER BY ts_rank(content_tsv, query) DESC) AS rn
    FROM doc_chunks, plainto_tsquery('zhparser', :query_text) query
    WHERE content_tsv @@ query
      AND (user_id = :uid OR is_public = true OR :uid = ANY(read_allow))
    LIMIT 20
  ),
  vec AS (
    SELECT id, file_id, content,
           1 - (content_vector <=> :query_vector) AS score,
           ROW_NUMBER() OVER (ORDER BY content_vector <=> :query_vector) AS rn
    FROM doc_chunks
    WHERE vector_ready = true
      AND (user_id = :uid OR is_public = true OR :uid = ANY(read_allow))
    ORDER BY content_vector <=> :query_vector
    LIMIT 20
  ),
  rrf AS (
    SELECT COALESCE(b.id, v.id) AS id,
           COALESCE(b.content, v.content) AS content,
           COALESCE(b.file_id, v.file_id) AS file_id,
           (COALESCE(1.0/(60+b.rn), 0) + COALESCE(1.0/(60+v.rn), 0)) AS rrf_score
    FROM bm25 b FULL OUTER JOIN vec v ON b.id = v.id
  )
SELECT * FROM rrf ORDER BY rrf_score DESC LIMIT 10;
4.4 审计日志
| 日志类型 | 记录内容                             |
| -------- | ------------------------------------ |
| 登录日志 | 用户、时间、IP、成功/失败            |
| 文件上传 | 用户、时间、文件名、大小、路径       |
| 文件下载 | 用户、时间、文件名                   |
| 文件删除 | 用户、时间、文件名、路径             |
| 文件编辑 | 用户、时间、文件名、版本、回调状态   |
| 权限变更 | 操作人、时间、被授权用户、授权内容   |
| AI问答   | 用户、时间、问题内容、是否调用外部AI |
日志保留：PostgreSQL 在线保留6个月，超期归档为 CSV 存入 MinIO，保留3年。
---
五、认证体系
5.1 本地账号密码登录
浏览器 → POST /api/v1/auth/login
后端：bcrypt 验证密码 → 签发 JWT（HS256）→ 返回 access_token + refresh_token
- Access Token：2小时，剩余 < 15分钟前端静默刷新
- Refresh Token：7天，HttpOnly Cookie
- 主动登出：Refresh Token JTI 写入 PostgreSQL token_blacklist（重启不丢失）
- 密码修改/权限变更：更新 token_version 批量失效该用户所有 Token
- 黑名单清理：定时任务每日清除 expires_at < NOW() 的记录
5.2 用户管理
- 管理员后台创建/禁用用户，分配部门和角色
- 初始密码由管理员设置，用户首次登录强制修改
- 离职处理：禁用账号 → 失效所有 JWT → 文件保留7天供管理员处理 → 90天后归档
---
六、部署架构
6.1 服务器要求
| 资源   | 最低             | 推荐             |
| ------ | ---------------- | ---------------- |
| CPU    | 2核              | 4核              |
| 内存   | 4GB              | 8GB              |
| 系统盘 | 50GB SSD         | 100GB SSD        |
| 数据盘 | 200GB            | 500GB            |
| OS     | Ubuntu 22.04 LTS | Ubuntu 22.04 LTS |
6.2 Docker Compose 服务组成
services:
  nginx          # 反向代理，IP白名单，HTTPS
  frontend       # React 前端（Nginx 静态托管）
  backend        # FastAPI 后端（含 Background Tasks）
  postgresql     # PostgreSQL 16 + pgvector + zhparser
  redis          # 单实例缓存（allkeys-lru，512MB）
  minio          # 文件对象存储
  onlyoffice     # ONLYOFFICE Document Server（在线编辑）
内存估算（8GB服务器）：
| 服务           | 估算内存                 |
| -------------- | ------------------------ |
| PostgreSQL     | 512MB-1GB（含pgvector）  |
| FastAPI 后端   | 256MB（含 MarkItDown）   |
| Redis × 1      | 512MB                    |
| MinIO          | 256MB                    |
| Nginx + 前端   | 128MB                    |
| ONLYOFFICE     | 800MB-1.2GB（按文档规模与并发变化） |
| 合计           | ~2.5-3.4GB，余量充足     |
6.3 MinIO 存储路径
documents bucket：
├── files/{YYYY-MM}/{file_id}/v{n}/{original_filename}     # 原始文件
└── markdown/{YYYY-MM}/{file_id}/v{n}/{original_name}.md   # Markdown副本
6.4 网络访问控制
geo $allowed_ip {
    default         0;
    10.0.0.0/8      1;
    172.16.0.0/12   1;
    192.168.0.0/16  1;
}
6.5 外网防火墙白名单
| 目标域名               | 端口 | 用途                             |
| ---------------------- | ---- | -------------------------------- |
| dashscope.aliyuncs.com | 443  | 通义千问 API（索引 + Embedding） |
| api.deepseek.com       | 443  | DeepSeek API（问答）             |
---
七、数据安全设计
7.1 存储加密
| 数据类型   | 加密方案                  |
| ---------- | ------------------------- |
| 文件内容   | MinIO SSE-S3（AES-256）   |
| 数据库密码 | bcrypt，salt rounds ≥ 12  |
| 用户Token  | JWT HS256，密钥存环境变量 |
| 传输       | TLS 1.2+                  |
7.2 Redis Key 规范
| Key 类型     | 命名                      | TTL    | 说明                 |
| ------------ | ------------------------- | ------ | -------------------- |
| AI 对话会话  | chat:session:<session_id> | 30分钟 | 活跃会话上下文       |
| 权限快照     | perm:folders:<user_id>    | 5分钟  | 用户权限列表缓存     |
| Answer Cache | answer:<query_sha256>     | 1小时  | 公共知识库精确匹配   |
注：Token 黑名单和 token_version 均存储于 PostgreSQL，不再使用 Redis。
7.3 限流策略
| 接口        | 维度   | 规则                       |
| ----------- | ------ | -------------------------- |
| AI 问答     | 用户级 | 10次/分钟                  |
| 文件上传    | 用户级 | 20次/小时                  |
| 文件下载    | 用户级 | 30次/分钟                  |
| 外部 AI API | 全局   | 60次/分钟                  |
| 登录        | IP级   | 10次/5分钟，超限锁定15分钟 |
7.4 统一错误响应
{
  error: {
    code: KB-FILE-003,
    message: 文件类型不在白名单中,
    detail: 不支持 .exe 文件上传,
    request_id: req_abc123
  }
}
---
八、前端设计
8.1 技术栈
| 技术     | 选型                  |
| -------- | --------------------- |
| 构建工具 | Vite 6                |
| UI 框架  | Ant Design 5          |
| 状态管理 | Zustand + React Query |
| 路由     | React Router v6       |
| HTTP     | Axios（统一拦截器）   |
8.2 主要页面
- 聊天页：主界面，支持 AI 问答 + 文件操作指令，SSE 流式回复
- 文件管理页：侧边栏文件树，拖拽上传，下载，软删除/回收站
- 管理后台：用户管理、部门管理、权限配置、审计日志、公共知识库
- 个人设置：修改密码、查看个人操作记录
---
九、性能指标
| 指标            | 目标值     |
| --------------- | ---------- |
| 并发用户        | ≥ 30       |
| 文件检索        | ≤ 3秒      |
| AI问答首字节    | ≤ 2秒      |
| 上传大小        | ≤ 10MB/个  |
| MarkItDown 解析 | ≤ 15秒/文件 |
9.1 备份恢复
RPO ≤ 24小时，RTO ≤ 4小时
| 数据类型   | 方式       | 频率      | 保留     |
| ---------- | ---------- | --------- | -------- |
| PostgreSQL | pg_dump    | 每日 3:00 | 7天      |
| MinIO      | mc mirror  | 每日 4:00 | 7天      |
| Redis      | RDB BGSAVE | 每小时    | 24个快照 |
注：去掉 Elasticsearch，无需 ES Snapshot 备份。
---
十、开发阶段规划
Phase 1 - 基础设施与认证（约1.5周）
├── Docker Compose 环境（7容器）+ 数据库模型 + Alembic 迁移
├── 本地账号密码登录 + JWT + 用户/部门/角色管理
├── Token 黑名单（PostgreSQL）+ 限流中间件 + Nginx IP白名单/HTTPS
└── 测试：认证 + JWT + 限流
Phase 2 - 文件管理系统（约2.5周）
├── [后端] 文件上传（后端中转，≤10MB）+ 安全校验 + 去重 + 版本控制
├── [后端] MarkItDown 解析 + 语义切块 + pgvector/tsvector 写入（Background Tasks）
├── [后端] Embedding 批量写入 + 软删除级联
├── [前端] 聊天UI框架 + 文件树 + 上传进度           ← 可并行
├── [全栈] 聊天指令引擎（规则匹配 + AI兜底）
└── 测试：文件CRUD + 安全 + 解析 + 向量写入
Phase 3 - 权限体系（约1周）
├── 个人空间隔离 + 文件夹级权限 + 部门主管权限
├── 权限管理界面 + doc_chunks read_allow 同步
└── 测试：权限隔离 + 跨用户控制
Phase 4 - AI问答系统（约2.5周）
├── [后端] AI API路由 + 简单重试 + 故障切换
├── [后端] pgvector BM25+Vector RRF 混合检索 + 权限过滤
├── [后端] 意图分类 + Skill路由 + 索引树导航
├── [前端] 聊天问答 + SSE流式 + 引用标注           ← 可并行
├── 多轮对话 + 满意度反馈 + Answer Cache（精确匹配）
└── 测试：混合检索精度 + RAG + 故障切换
Phase 5 - 管理后台（约1周）
├── 用户/部门管理 + 索引管理 + 公共知识库
├── 审计日志 + 问答反馈 + 监控面板
└── 测试：E2E + 权限边界
Phase 6 - 综合测试与上线（约0.5周）
├── 全链路集成测试 + 压测
└── 部署文档 + 运维手册
总计：约9周（2个多月）
人力假设：2人（1后端+1前端/全栈）
---
文档由 Brainstorm Agent 生成 | 极简版 v2.1 | 基于 v2.0 进一步修订
---
与 v1.0 相比核心变化：
- 容器数量：9个 → 7个（新增 ONLYOFFICE，去掉 Elasticsearch / Celery Worker / redis-security）
- 内存需求：~5-6GB → ~2.5-3.4GB（8GB 服务器足够，含在线编辑器开销）
- 开发周期：约12周 → 约9周
- 文件上传限制：100MB → 10MB
- 异步任务：Celery + Redis 队列 → FastAPI Background Tasks（零额外依赖）
- 全文+向量检索：Elasticsearch → PostgreSQL pgvector + tsvector（统一存储，备份更简单）
- Token 黑名单：Redis（重启丢失）→ PostgreSQL（持久化，更可靠）
- Answer Cache：jieba + Embedding 双重验证 → 精确字符串匹配（零额外依赖）
- folder_summary：防抖+定时自动触发 → 按需触发（节省 API 费用）
