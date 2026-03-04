# 上线执行文档 (Go-Live Guide)

本文档用于指导 Enterprise AI Knowledge Base v2.1 在生产环境上线。

## 1. 目标与范围

- 目标：将当前 `master` 的稳定版本部署到生产环境，并完成上线后可用性验证。
- 范围：后端 API、前端页面、数据库、对象存储、缓存、在线编辑服务、反向代理。

## 2. 版本信息

- 推荐上线提交：`c22fc86`
- 分支：`master`

## 3. 上线前准备

### 3.1 环境与账号

- 准备生产服务器与网络访问策略（80/443、数据库、对象存储、ONLYOFFICE）。
- 准备仓库拉取权限、容器镜像拉取权限。
- 准备管理员初始账号信息（用户名、强密码、部门）。

### 3.2 配置文件

- 基于 `.env.production.example` 创建 `.env.production`。
- 必填并替换为真实值：
  - `JWT_SECRET`
  - `POSTGRES_PASSWORD`
  - `MINIO_ROOT_USER`
  - `MINIO_ROOT_PASSWORD`
  - `ONLYOFFICE_JWT_SECRET`
- 确保以下配置满足生产要求：
  - `APP_ENV=production`
  - `ONLYOFFICE_JWT_ENABLED=true`
  - `REFRESH_COOKIE_SECURE=true`

### 3.3 预检

- 按 `docs/runbooks/pre-launch-checklist.md` 完成全部检查项。
- 确认备份与恢复脚本可执行。

## 4. 部署步骤

在项目根目录执行：

```bash
docker compose --env-file .env.production -f infra/docker-compose.yml up -d --build
```

检查服务状态：

```bash
docker compose --env-file .env.production -f infra/docker-compose.yml ps
```

期望：`nginx/frontend/backend/postgres/redis/minio/onlyoffice` 全部 `healthy` 或 `Up`。

## 5. 初始化管理员

在后端容器中执行：

```bash
docker compose --env-file .env.production -f infra/docker-compose.yml exec -T backend \
  sh -lc "BOOTSTRAP_ADMIN_USERNAME=admin BOOTSTRAP_ADMIN_PASSWORD='<STRONG_PASSWORD>' python /app/scripts/bootstrap_admin.py"
```

说明：
- 首次执行会创建管理员；重复执行会更新同名管理员信息（用于密码轮换）。

## 6. 上线后冒烟验证

### 6.1 基础健康检查

```bash
curl -sS "http://127.0.0.1:8080/health"
```

应返回 `service_name` 与 `version` 字段。

### 6.2 认证与管理接口

1) 登录获取 token
2) 使用 token 调用：
- `/api/admin/users`
- `/api/admin/departments`
- `/api/admin/audit-states`

应返回 200 且结构正确。

### 6.3 核心业务流

- 上传文件：`POST /api/uploads`
- 查看版本：`GET /api/uploads/{id}/versions`
- 启动编辑：`POST /api/files/{id}/edit/start`
- 对话流式：`POST /api/chat/stream`

应满足：
- 上传成功返回 `upload_id`
- 版本接口返回版本列表
- 编辑启动返回 `session_token`
- SSE 能持续返回 chunk 并以 done 结束

### 6.4 前端检查

- 打开 `http://127.0.0.1:8080`
- 确认默认中文界面可访问聊天、文件管理、管理页
- 确认语言切换可在中英文之间切换

## 7. 回滚方案

当出现严重问题（接口大面积 5xx、登录失效、编辑回调异常）时：

1. 回滚到上一稳定提交并重新部署：

```bash
git checkout <previous-stable-sha>
docker compose --env-file .env.production -f infra/docker-compose.yml up -d --build
```

2. 验证健康检查与关键接口恢复。
3. 如数据异常，按备份恢复 runbook 执行恢复。

## 8. 观测与告警建议

- 监控以下关键指标：
  - `/health` 可用率
  - 登录成功率与 401 比例
  - 上传成功率与 4xx/5xx 比例
  - SSE 请求时延与中断率
  - 编辑回调成功率
- 关键日志建议聚合：
  - 认证失败日志
  - 上传与解析状态变化日志
  - 权限拒绝日志
  - 编辑回调冲突与版本冲突日志

## 9. 常见问题

- 问：前端页面能打开但功能不可用。
  - 查：是否已完成管理员初始化；token 是否有效；后端是否与最新代码一致。
- 问：上传成功但版本接口 403。
  - 查：上传记录 owner 是否正确写入；当前用户是否有可见权限。
- 问：编辑启动返回 404。
  - 查：文件记录与上传记录映射是否创建成功，目标 ID 是否存在。

## 10. 相关文档

- `docs/runbooks/pre-launch-checklist.md`
- `docs/runbooks/deployment-v2.1.md`
- `docs/runbooks/incident-response.md`
- `docs/release-notes-v2.1.md`
