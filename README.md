<div align="center">

# 🚀 LumenRoute AI

### 电商多智能体执行引擎

**拖拽素材 → AI 自动分析 → 选择商业目标 → 一键生成**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)](https://reactjs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.2-3178C6?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind-3.3-06B6D4?logo=tailwindcss&logoColor=white)](https://tailwindcss.com/)

[核心理念](#-核心理念) · [快速开始](#-快速开始) · [业务流程](#-业务流程) · [技术架构](#-技术架构) · [API](#-api-接口)

</div>

---

## 💡 核心理念

**极简无参化** — 用户不应面对任何技术参数。

传统 AI 工具要求用户理解尺寸（1024×1024）、质量（auto/low/high）、格式（png/jpeg/webp）、时长（3s/5s/8s）、种子数……这些全部由后端默认值或 AI 分析结果隐式决定。

**LumenRoute AI 只暴露一种交互：选择目标。**

| 传统流程 | LumenRoute 流程 |
|----------|----------------|
| 上传 → 配参数 → 写提示词 → 选模型 → 生成 | 上传 → 选目标 → 生成 |
| 用户需要理解 10+ 个技术参数 | 用户只需点击 1 次 |
| 对话驱动，多轮交互 | 任务驱动，一次闭环 |

---

## ✨ 特性

- **🎯 零参数交互**：上传素材后，AI 自动分析并推荐商业目标模板
- **📦 任务驱动架构**：一次上传 = 一个任务 = 一条生命周期
- **🖼️ 图片智能生成**：电商主图 / 产品详情 / 社交媒体 / 广告Banner / 节日主题
- **🎬 视频智能生成**：爆款分析 → 分镜拆解 → 一键生成
- **🔌 多 Provider 中转**：统一 API 管理 Seedance 2.0、OpenAI 等生成服务
- **📊 素材库管理**：所有生成结果统一归档，支持搜索和筛选
- **🏠 本地优先**：Docker 一键部署，数据完全自主

---

## 🎬 业务流程

### 图片流程

```
拖拽图片到上传区
    ↓
AI 自动分析图片内容
    ↓
展示预设目标卡片（电商主图 / 产品详情 / 社交媒体 / 广告Banner / 节日主题）
    ↓
勾选目标 → 点击「一键生成」
    ↓
并行生成 → 展示结果网格 → 下载
```

### 视频流程

```
拖拽视频到上传区
    ↓
AI 爆款分析（Hook / Pacing / Visual Style / Audio）
    ↓
自动拆解分镜（5-8 个镜头，含 Seedance 提示词）
    ↓
可编辑分镜 → 点击「一键生成视频」
    ↓
轮询生成 → 视频播放器 → 下载
```

---

## 🚀 快速开始

### 一键启动（Docker）

```bash
git clone https://github.com/zhaomuyuan357-creator/mediagateway.git
cd mediagateway
./setup.sh
```

| 服务 | 地址 | 说明 |
|------|------|------|
| 前端 | http://localhost:3000 | 工作台界面 |
| 后端 API | http://localhost:3001 | REST API |
| API 文档 | http://localhost:3001/docs | Swagger 交互文档 |

### 本地开发

```bash
# 后端
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # 填入你的 API Key
python run.py

# 前端
cd frontend
npm install
npm run dev
```

---

## 🏗️ 技术架构

```
mediagateway/
├── backend/                      # FastAPI 后端
│   └── src/
│       ├── api/routes.py         # 路由（任务提交、状态查询、素材管理）
│       ├── providers/            # Provider 适配器（Seedance / OpenAI）
│       ├── services/             # 业务逻辑（图片分析、视频分析、分镜拆解）
│       ├── models/               # 数据库模型
│       └── db/database.py        # SQLite / PostgreSQL
│
├── frontend/                     # React 前端（重构后）
│   └── src/
│       ├── pages/
│       │   ├── Login.tsx         # 登录页（渐变光晕背景）
│       │   ├── TaskWorkspace.tsx # 主工作台（组装 4 个核心组件）
│       │   ├── Gallery.tsx       # 素材库
│       │   └── Settings.tsx      # API 中转站管理
│       ├── components/
│       │   └── workspace/
│       │       ├── UploadZone.tsx     # 拖拽上传区
│       │       ├── GoalCardGrid.tsx   # 目标卡片网格
│       │       ├── ActionPanel.tsx    # 操作控制面板
│       │       └── ResultDisplay.tsx  # 结果展示
│       ├── lib/
│       │   ├── store.ts          # Zustand 状态树（4 字段极简设计）
│       │   ├── api.ts            # API 客户端（submitTask + pollTask）
│       │   └── mockTaskService.ts # 开发环境 Mock 服务
│       └── components/ui/        # shadcn/ui 基础组件
│
└── docker-compose.yml
```

### 前端状态模型（极简 4 字段）

```typescript
interface TaskStore {
  selectedFile: File          // 用户上传的素材
  selectedTemplate: Template  // 选择的商业目标
  taskStatus: TaskStatus      // 'pending' | 'processing' | 'success' | 'failed'
  taskResult: Result          // 生成结果（image_urls / video_url）
}
```

### API 接口

```typescript
// 提交任务（入参仅 fileUrl + templateId）
POST /v1/tasks
{ fileUrl: string, templateId: string }
→ { task_id: string }

// 轮询状态
GET /v1/tasks/{task_id}
→ { task_id, status, result?, error? }
```

---

## 🛠️ 技术栈

| 层 | 技术 |
|----|------|
| 前端框架 | React 18 + TypeScript 5.2 |
| 构建工具 | Vite 5.4 |
| 状态管理 | Zustand 5（极简 4 字段 store） |
| UI 组件 | shadcn/ui + Tailwind CSS 3.3 |
| 后端框架 | FastAPI + Python 3.11 |
| 数据库 | SQLite（本地）/ PostgreSQL（Docker） |
| 部署 | Docker Compose |

---

## 📸 界面预览

### 登录页 — 渐变光晕背景
深色 `bg-slate-950` 底色 + 蓝紫模糊光晕 + 毛玻璃登录卡片

### 工作台 — 任务驱动
```
┌──────────────────────────────────────┐
│  LumenRoute AI                       │
├──────────────────────────────────────┤
│  ┌────────────────────────────────┐  │
│  │     拖拽图片或视频到此处        │  │  ← UploadZone
│  └────────────────────────────────┘  │
│                                      │
│  选择商业目标                         │
│  ┌──┐ ┌──┐ ┌──┐ ┌──┐ ┌──┐          │
│  │电商│ │产品│ │社交│ │广告│ │节日│  │  ← GoalCardGrid
│  └──┘ └──┘ └──┘ └──┘ └──┘          │
│                                      │
│       ┌────────────────┐             │
│       │   一键生成      │             │  ← ActionPanel
│       └────────────────┘             │
│                                      │
│  生成结果（4 张）                     │
│  ┌──┐ ┌──┐ ┌──┐ ┌──┐               │  ← ResultDisplay
│  └──┘ └──┘ └──┘ └──┘               │
└──────────────────────────────────────┘
```

---

## 🤝 参与贡献

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/xxx`)
3. 提交改动 (`git commit -m 'feat: add xxx'`)
4. 推送分支 (`git push origin feature/xxx`)
5. 提交 Pull Request

---

## 📝 开源协议

本项目基于 [MIT License](./LICENSE) 开源。

---

<div align="center">

**LumenRoute AI** — 让电商 AI 创作回归简单

[⬆ 回到顶部](#-lumenroute-ai)

</div>
