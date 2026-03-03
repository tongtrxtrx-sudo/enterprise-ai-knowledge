# Enterprise AI Knowledge Base (v2.1)

企业级 AI 知识库项目，覆盖从运行时基座、后端能力、前端工作流到生产交付的完整链路。

## 项目概览

- 运行时：基于 Docker Compose 的 7 服务架构（nginx、frontend、backend、postgres、redis、minio、onlyoffice）
- 后端：认证、上传、解析索引、权限治理、在线编辑回调、AI 路由与 SSE 对话
- 前端：聊天页、文件管理、在线编辑、管理员页面
- 运维：备份恢复脚本、健康检查、部署与事故响应 runbook、烟雾压测

## 技术栈

- Backend: FastAPI, SQLAlchemy, PyJWT, MarkItDown
- Frontend: React, TypeScript, Vite, Vitest
- Infra: Docker Compose, Nginx, PostgreSQL, Redis, MinIO, ONLYOFFICE

## 目录结构

```text
.
|- backend/      # 后端服务与测试
|- frontend/     # 前端应用与测试
|- infra/        # docker-compose 与 nginx 配置
|- docs/         # 方案、场景、runbook、发布文档
|- tasks.json    # 任务执行状态
```

## 快速开始

### 1) 启动完整环境（推荐）

在项目根目录执行：

```bash
docker compose -f infra/docker-compose.yml up -d --build
```

默认访问入口：

- Nginx: `http://127.0.0.1:8080`
- Backend Health: `http://127.0.0.1:8000/health`
- MinIO Console: `http://127.0.0.1:9001`
- ONLYOFFICE: `http://127.0.0.1:8082`

### 2) 本地开发（可选）

后端：

```bash
cd backend
uv run --group dev pytest tests -q
```

前端：

```bash
cd frontend
npm install
npm test
npm run build
```

## 关键文档

- 发布说明：`docs/release-notes-v2.1.md`
- PR 描述样例：`docs/pr-description-v2.1.md`
- 部署 runbook：`docs/runbooks/deployment-v2.1.md`
- 事故响应：`docs/runbooks/incident-response.md`

## 版本

- 当前版本：`v2.1`

## English Version

For English documentation, see `README.en.md`.
