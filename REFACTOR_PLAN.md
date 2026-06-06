# MediaGateway 工程化重构计划

> 目标：从"多步交互的开发者工具"转向"面向电商老板的一键式极简业务系统"
> 日期：2026-06-06

---

## 一、重构总览

### 核心变更

```
旧架构                              新架构
─────────────────────────────────   ─────────────────────────────────
APIKey 表（静态 provider 配置）   →  APIProvider 表（动态中转站管理）
Generation 表（视频/图片分开追）  →  Task 表（统一任务追踪）
providers/seedance.py（硬编码）   →  provider_router.py（动态路由）
providers/openai_image.py         →  AsyncOpenAI 动态实例化
key_manager.py（加密 Key 管理）   →  APIProvider.encrypted_key
config.py 里写死 DashScope 配置   →  APIProvider 表里配置
```

### 架构对比

```
【旧】前端 → routes.py → key_manager.get_key() → create_provider("seedance", key) → 硬编码 Provider 类 → API

【新】前端 → routes.py → Task(pending) → execute_pipeline()
                              ↓
                    provider_router.resolve_provider(task_type)
                              ↓
                    加权轮询选 APIProvider → 取 model_mapping → 动态 AsyncOpenAI(base_url, api_key)
                              ↓
                    调用中转站 API → 更新 Task.result_url / status
```

---

## 二、数据模型设计

### 2.1 APIProvider 表（替代 APIKey）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK | 自增主键 |
| name | String | 中转站显示名称，如 "XX中转站-图片" |
| base_url | String | API 基础地址，如 `https://api.example.com/v1` |
| encrypted_key | String | 加密后的 API Key（复用 Fernet 加密） |
| model_mapping | JSON | `{"image": "dall-e-3", "video": "seedance-2.0-t2v", "analysis": "gpt-4o"}` |
| weight | Integer | 权重（≥1），用于加权轮询 |
| is_active | Boolean | 是否启用 |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

### 2.2 Task 表（替代 Generation）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK | 自增主键 |
| task_id | String UNIQUE | 对外 ID，如 `task_a1b2c3` |
| task_type | Enum | `image` / `video` / `analysis` |
| status | Enum | `pending` → `processing` → `success` / `failed` |
| provider_id | Integer FK | 实际执行的 APIProvider ID |
| provider_name | String | 冗余的中转站名称 |
| payload | JSON | 完整请求参数 |
| result_url | String | 结果 URL（图片/视频/分析 JSON） |
| error_msg | Text | 失败原因 |
| progress | String | 当前阶段，如 `analyzing` / `generating` |
| created_at | DateTime | 创建时间 |
| started_at | DateTime | 开始执行时间 |
| completed_at | DateTime | 完成时间 |

### 2.3 删除的表

| 旧表 | 替代方案 |
|------|----------|
| `api_keys` | `api_providers` |
| `generations` | `tasks` |

---

## 三、execute_pipeline 流水线设计

```
                    ┌─────────────────────────────────────────┐
                    │           execute_pipeline(task_id)      │
                    └─────────────────┬───────────────────────┘
                                      │
                          读取 Task.payload，判断 task_type
                                      │
                    ┌─────────────────┼─────────────────┐
                    ▼                 ▼                 ▼
              task_type=         task_type=         task_type=
               image              video            analysis
                    │                 │                 │
            payload 含           payload 含         直接执行
            参考图 URL？         参考视频 URL？          │
            ┌──┴──┐             ┌──┴──┐           调千问 VL
            是    否            是    否           返回结构化
            │     │             │     │           分析结果
            ▼     │             ▼     │                │
     千问 VL 分析  │      千问 VL 分析  │           更新 Task
     提取视觉特征  │      提取分镜结构  │           status=success
     组装 Prompt   │      组装 Prompt   │           result_url=JSON
            │     │             │     │
            └──┬──┘             └──┬──┘
               ▼                   ▼
        resolve_provider      resolve_provider
        (task_type="image")   (task_type="video")
               │                   │
        动态 AsyncOpenAI      动态 AsyncOpenAI
        调中转站生成图片       调中转站生成视频
               │                   │
        保存结果文件           轮询状态+下载视频
        更新 Task              更新 Task
```

### 3.1 短流水线（纯文本输入）

```
pending → processing → [调中转站 API] → success/failed
```

### 3.2 复合流水线（含参考图/视频）

```
pending → processing → [千问 VL 分析] → analyzing → [组装 Prompt] → [调中转站 API] → generating → success/failed
```

### 3.3 分析流水线

```
pending → processing → [千问 VL 分析] → success/failed
```

---

## 四、API 接口设计

### 4.1 中转站管理（APIProvider CRUD）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/v1/providers` | 创建中转站 |
| GET | `/v1/providers` | 列出所有中转站 |
| GET | `/v1/providers/{id}` | 获取单个中转站 |
| PATCH | `/v1/providers/{id}` | 更新中转站 |
| DELETE | `/v1/providers/{id}` | 删除中转站 |

### 4.2 任务管理（Task）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/v1/tasks` | 创建任务 → 返回 task_id → 后台自动执行 pipeline |
| GET | `/v1/tasks/{task_id}` | 查询任务状态（前端轮询用） |
| GET | `/v1/tasks` | 列出任务（支持分页、按 type/status 筛选） |
| DELETE | `/v1/tasks/{task_id}` | 删除任务 |

### 4.3 对话管理（保留）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/v1/conversations` | 创建对话 |
| GET | `/v1/conversations` | 列出对话 |
| GET | `/v1/conversations/{id}` | 对话详情 |
| PATCH | `/v1/conversations/{id}` | 更新对话 |
| DELETE | `/v1/conversations/{id}` | 删除对话 |
| POST | `/v1/conversations/{id}/messages` | 发送消息 |
| GET | `/v1/conversations/{id}/messages` | 列出消息 |

---

## 五、分工计划

### 阶段一：基础层（数据库 + 路由服务）

**已完成 ✅**

- [x] `models/api_provider.py` — APIProvider 模型
- [x] `models/task.py` — Task 模型
- [x] `models/__init__.py` — 更新导出
- [x] `db/database.py` — 注册新表
- [x] `services/provider_router.py` — 加权轮询 + 动态客户端
- [x] `api/schemas.py` — 新 schemas

### 阶段二：路由层重写

**已完成 ✅**

**负责文件：`backend/src/api/routes.py`**

需要做的事情：
1. [x] 删除所有旧路由（video/generations、image/generations、keys、providers、storyboard）
2. [x] 新增 APIProvider CRUD 路由（5 个端点）
3. [x] 新增 Task CRUD 路由（4 个端点）
4. [x] 保留 conversations/messages 路由（几乎不变）
5. [x] 保留 materials 路由（查询改为从 Task 表读取）

**依赖：阶段一完成**

### 阶段三：流水线实现

**已完成 ✅**

**负责文件：`backend/src/services/pipeline.py`（新建）**

需要做的事情：
1. [x] 编写 `execute_pipeline(task_id)` 主函数
2. [x] 实现短流水线：直接调中转站 API
3. [x] 实现复合流水线：千问 VL 分析 → 组装 Prompt → 调中转站 API
4. [x] 实现分析流水线：千问 VL 分析 → 返回结果
5. [x] 每个节点更新 Task 的 status / progress / result_url / error_msg

**依赖：阶段二完成**

### 阶段四：清理旧代码

**负责文件：删除 + 精简**

| 操作 | 文件 |
|------|------|
| 删除 | `providers/seedance.py` |
| 删除 | `providers/openai_image.py` |
| 删除 | `providers/sora.py`（如果还存在） |
| 删除 | `providers/runway.py`（如果还存在） |
| 删除 | `providers/kling.py`（如果还存在） |
| 删除 | `services/key_manager.py` |
| 删除 | `models/api_key.py` |
| 删除 | `models/generation.py` |
| 精简 | `providers/__init__.py`（只保留空壳或删除） |
| 精简 | `config.py`（移除 dashscope_* 配置项） |

**依赖：阶段三完成**

### 阶段五：改造 Analyzer 服务

**负责文件：**

| 文件 | 改动 |
|------|------|
| `services/storyboard_analyzer.py` | 改用 `provider_router.resolve_provider("analysis")` 获取千问客户端 |
| `services/image_analyzer.py` | 同上 |
| `services/video_analyzer.py` | 同上 |

**依赖：阶段四完成**

### 阶段六：前端适配

**负责文件：`frontend/src/lib/api.ts` + 页面组件**

需要做的事情：
1. api.ts 新增 `createTask()` / `getTask()` / `listTasks()` 方法
2. api.ts 新增 APIProvider CRUD 方法
3. Settings 页面改为中转站管理界面
4. 前端轮询改为调 `/v1/tasks/{task_id}`
5. 适配新的响应格式

**依赖：阶段二完成（后端 API 稳定后即可并行开发）**

---

## 六、文件变更汇总

### 新建

| 文件 | 阶段 | 说明 |
|------|------|------|
| ~~`services/pipeline.py`~~ | 三 | ✅ 已完成 |
| ~~`models/api_provider.py`~~ | 一 | ✅ 已完成 |
| ~~`models/task.py`~~ | 一 | ✅ 已完成 |
| ~~`services/provider_router.py`~~ | 一 | ✅ 已完成 |

### 重写

| 文件 | 阶段 | 说明 |
|------|------|------|
| ~~`api/routes.py`~~ | 二 | ✅ 已完成 |
| `api/schemas.py` | 一 | ✅ 已完成 |
| `models/__init__.py` | 一 | ✅ 已完成 |
| `db/database.py` | 一 | ✅ 已完成 |
| `config.py` | 四 | 移除硬编码配置 |
| `main.py` | 四 | 更新启动逻辑 |

### 删除

| 文件 | 阶段 | 原因 |
|------|------|------|
| `providers/seedance.py` | 四 | 被 provider_router 替代 |
| `providers/openai_image.py` | 四 | 同上 |
| `services/key_manager.py` | 四 | 被 APIProvider 表替代 |
| `models/api_key.py` | 四 | 同上 |
| `models/generation.py` | 四 | 被 Task 替代 |

### 改造

| 文件 | 阶段 | 改动 |
|------|------|------|
| `services/storyboard_analyzer.py` | 五 | 改用动态客户端 |
| `services/image_analyzer.py` | 五 | 同上 |
| `services/video_analyzer.py` | 五 | 同上 |
| `services/cost_calculator.py` | 四 | 适配新模型 |
| `services/video_storage.py` | 四 | 适配新模型 |

---

## 七、环境变量变更

### 移除（改由 APIProvider 表管理）

```env
# 以下配置不再需要写在 .env 里，改为在前端「中转站管理」页面配置
# SEEDANCE_API_KEY
# SEEDANCE_ENDPOINT_ID
# OPENAI_API_KEY
# DASHSCOPE_API_KEY
# DASHSCOPE_MODEL
```

### 保留

```env
DATABASE_URL=sqlite:///./storage/db.sqlite
STORAGE_PATH=./storage/videos
TEMP_PATH=./storage/temp
ENCRYPTION_KEY=change-this-key
SECRET_KEY=change-this-secret
```

---

## 八、执行建议

1. **阶段二 + 阶段六可并行**：后端 API 稳定后前端即可开始适配
2. **阶段三最关键**：pipeline.py 是整个重构的核心，需要充分测试
3. **阶段四一步到位**：旧文件删干净，避免残留引用导致 import 错误
4. **数据库迁移**：旧 SQLite 数据不保留，直接删 `db.sqlite` 重建表
