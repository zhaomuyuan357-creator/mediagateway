# Chat 界面重构 — 项目拆分

> 基于 CHAT_REDESIGN.md 决策记录

---

## 阶段总览

```
Phase 1: 数据层 ──→ Phase 2: 后端 API ──→ Phase 3: 前端 Chat 框架
                                                  ↓
Phase 6: 素材库 ←── Phase 5: 视频对话 ←── Phase 4: 图片对话
                                                  ↓
                                          Phase 7: 打磨与优化
```

---

## Phase 1：数据层（数据库 + 模型）

**目标**：新增对话和消息的数据库表，为后续 API 和前端打基础。

### 任务清单

- [ ] **1.1** 新增 `Conversation` 模型
  - 字段：id, type（video/image）, title, created_at, updated_at
  - 文件：`backend/src/models/conversation.py`

- [ ] **1.2** 新增 `Message` 模型
  - 字段：id, conversation_id(FK), role（user/assistant）, content, message_type（text/image/video/storyboard/analysis）, metadata(JSON), created_at
  - 文件：`backend/src/models/message.py`

- [ ] **1.3** 更新 `__init__.py` 导出新模型

- [ ] **1.4** 更新 `database.py` 的 `init_db()` 添加迁移逻辑

- [ ] **1.5** 更新 `main.py` 的静态文件挂载（确认 storage 路径）

---

## Phase 2：后端 API

**目标**：提供对话 CRUD、消息管理、AI 分析等 API 端点。

### 任务清单

- [x] **2.1** 对话 CRUD API
  - `POST /v1/conversations` — 创建对话（传入 type）
  - `GET /v1/conversations` — 列表
  - `GET /v1/conversations/{id}` — 详情（含消息）
  - `DELETE /v1/conversations/{id}` — 删除
  - `PATCH /v1/conversations/{id}` — 更新标题

- [x] **2.2** 消息 API
  - `POST /v1/conversations/{id}/messages` — 发送消息（文字 + 附件）
  - `GET /v1/conversations/{id}/messages` — 获取消息列表
  - 支持 multipart/form-data 上传图片/视频文件

- [x] **2.3** 图片分析 API
  - `POST /v1/ai/analyze-image` — 上传图片 + 意图 → 返回多条提示词
  - 使用 Qwen3-VL-Plus 分析产品图片
  - 输出：多条不同用途的英文提示词（主图、详情页、社交媒体等）

- [x] **2.4** 视频分析 API
  - `POST /v1/ai/analyze-video` — 上传视频/URL + 意图 → 返回爆款分析 + 分镜
  - 使用 Qwen3-VL-Plus 分析视频关键帧
  - 输出：爆款分析（核心维度）+ 分镜列表（含 Seedance 提示词）

- [x] **2.5** 图片生成 API（改造现有）
  - `POST /v1/image/generations/with-reference` — 支持参考图输入
  - `POST /v1/image/generations/batch` — 支持批量生成（多条提示词）

- [x] **2.6** 视频生成 API（改造现有）
  - `POST /v1/video/generations/from-storyboard` — 从分镜列表生成单个视频
  - 保留现有的异步轮询机制

- [x] **2.7** Pydantic schemas
  - 新增 Conversation、Message、ImageAnalysis、VideoAnalysis 的请求/响应模型
  - 文件：`backend/src/api/schemas.py`

- [x] **2.8** 更新 `routes.py` 注册新路由

### 新增文件
- `backend/src/services/image_analyzer.py` — 图片分析服务（Qwen3-VL-Plus）
- `backend/src/services/video_analyzer.py` — 视频分析服务（爆款分析 + 分镜）

---

## Phase 3：前端 Chat 框架

**目标**：搭建 Chat 页面的基础骨架 — 对话列表 + 对话区 + 消息渲染。

### 任务清单

- [ ] **3.1** 安装新依赖
  - `npm install zustand`（可选，轻量状态管理）
  - 其他需要的 shadcn/ui 组件

- [ ] **3.2** 对话列表组件（左侧栏）
  - 新建对话按钮（弹出选择：视频/图片）
  - 对话列表（标题、时间、类型标识）
  - 选中高亮、删除按钮
  - 文件：`frontend/src/components/ConversationList.tsx`

- [ ] **3.3** 消息渲染组件（右侧对话区）
  - 用户消息：文字 + 图片/视频附件预览
  - AI 消息：文字 + 结构化卡片
  - 消息类型渲染器：
    - `TextMessage` — 纯文字
    - `ImageMessage` — 图片展示 + 下载/引用按钮
    - `VideoMessage` — 视频播放器 + 下载/引用按钮
    - `AnalysisMessage` — 爆款分析卡片
    - `StoryboardMessage` — 分镜列表卡片（可编辑）
    - `ConfirmationCard` — 生成前确认卡片
  - 文件：`frontend/src/components/messages/` 目录

- [ ] **3.4** 输入区域组件
  - 文字输入框 + 发送按钮
  - 附件上传按钮（图片/视频，根据对话类型变化）
  - 参数面板入口按钮
  - 文件：`frontend/src/components/ChatInput.tsx`

- [ ] **3.5** 参数面板组件
  - 图片对话：比例、画质、格式、数量
  - 视频对话：比例、时长、Seed
  - 支持展开/收起
  - 文件：`frontend/src/components/ParameterPanel.tsx`

- [ ] **3.6** Chat 页面组装
  - 左侧 ConversationList + 右侧消息区 + 底部 ChatInput
  - 对话切换、新建、删除的状态管理
  - 文件：`frontend/src/pages/Chat.tsx`

- [ ] **3.7** 更新 App.tsx 路由
  - `/` → Chat 页面
  - `/gallery` → 素材库
  - `/usage` → 用量统计
  - `/settings` → 设置
  - 移除 Playground 和 Storyboard 路由

- [ ] **3.8** 更新 API 客户端
  - 新增对话、消息、AI 分析相关的 API 方法
  - 文件：`frontend/src/lib/api.ts`

---

## Phase 4：图片对话功能

**目标**：实现完整的图片对话流程 — 上传产品图 → AI 分析 → 确认 → 生成。

### 任务清单

- [x] **4.1** 图片上传与预览
  - 支持拖拽上传 + 粘贴上传 + 点击上传
  - 图片预览缩略图

- [x] **4.2** AI 图片分析流程
  - 发送图片 + 意图文字 → 调用分析 API
  - 渲染分析结果：多条提示词卡片
  - 每条提示词可编辑、可勾选

- [x] **4.3** 确认卡片组件
  - 显示参考图缩略图
  - 显示选中的提示词（可编辑）
  - 参数（比例、画质）可临时修改
  - 确认生成 / 重新分析 按钮

- [x] **4.4** 图片生成与结果展示
  - 调用生成 API（支持参考图 + 批量）
  - 轮询状态，渲染生成结果
  - 结果图片支持下载、引用到下一条消息

- [x] **4.5** 引用机制
  - 点击对话里的图片 → 附加到输入区
  - 输入区显示附件预览，可移除

---

## Phase 5：视频对话功能

**目标**：实现完整的视频对话流程 — 上传视频 → AI 分析 → 审核分镜 → 生成。

### 任务清单

- [ ] **5.1** 视频上传与 URL 输入
  - 支持文件上传 + URL 粘贴
  - 视频预览播放器

- [ ] **5.2** AI 视频分析流程
  - 发送视频 + 意图文字 → 调用分析 API
  - 渲染分析结果（同一条消息）：
    - 爆款分析区块（核心维度，中文）
    - 分镜拆解区块（编号、描述、提示词、时长）

- [ ] **5.3** 分镜编辑组件
  - 每个分镜的提示词可展开编辑
  - 分镜数量可调整（增加/删除）
  - 分镜顺序可拖拽调整

- [ ] **5.4** 视频确认与生成
  - 确认按钮 → 调用生成 API
  - 轮询状态，显示生成进度
  - 完成后渲染视频播放器 + 下载按钮

- [ ] **5.5** 追问扩展分析
  - 用户可追问"帮我从 XX 角度再分析一下"
  - AI 基于同一视频的已有分析，补充新维度

---

## Phase 6：素材库（改造 Gallery）

**目标**：将现有 Gallery 改造为全局素材库。

### 任务清单

- [ ] **6.1** 素材库 API
  - `GET /v1/materials` — 查询所有素材（图片+视频），支持筛选、搜索、分页
  - 参数：type, date_from, date_to, conversation_id, keyword

- [ ] **6.2** 前端布局改造
  - 按时间线排列（默认）
  - 按对话分组查看（切换视图）
  - 瀑布流/网格切换

- [ ] **6.3** 筛选与搜索
  - 类型筛选（图片/视频）
  - 日期范围选择
  - 对话来源筛选
  - 关键词搜索（提示词）

- [ ] **6.4** 素材详情弹窗
  - 大图/视频预览
  - 显示：提示词、参数、来源对话、生成时间
  - 操作：下载、删除、引用到新对话

---

## Phase 7：打磨与优化

**目标**：细节优化、体验打磨。

### 任务清单

- [x] **7.1** 导航栏更新
  - 新的导航结构：Chat / 素材库 / 用量统计 / 设置
  - 移除旧的 Playground / Storyboard 导航
  - 移动端汉堡菜单（响应式导航）

- [x] **7.2** 响应式适配
  - 移动端对话列表可折叠（侧边栏 toggle 按钮）
  - 小屏幕下消息卡片自适应（响应式间距/字号）
  - 移动端选择对话后自动收起侧边栏

- [x] **7.3** 加载状态优化
  - Gallery 骨架屏加载（Skeleton 组件）
  - Usage 骨架屏加载
  - 消息加载中文本提示
  - 文件上传错误横幅（5s 自动消失）

- [x] **7.4** 错误处理
  - ErrorBoundary 全局错误边界
  - Gallery/Usage 错误 UI + 重试按钮
  - 文件大小/格式校验（50MB 限制、类型检查）
  - 智能错误消息（网络/API Key/限流/通用）
  - API 请求重试机制（requestWithRetry）

- [x] **7.5** Usage 页面调整
  - 使用 api 客户端替代 raw fetch
  - 新增 getDetailedUsage/getPricing API 方法
  - 错误状态 UI + 重试
  - 响应式布局优化（移动端适配）

- [x] **7.6** 测试与验证
  - 构建通过（零错误）
  - 删除孤立的 Playground.tsx 和 Storyboard.tsx

---

## 文件变更清单（预估）

### 新增文件
```
backend/src/models/conversation.py
backend/src/models/message.py
backend/src/services/image_analyzer.py      ← Qwen3-VL-Plus 图片分析
backend/src/services/video_analyzer.py      ← Qwen3-VL-Plus 视频分析（改造现有 storyboard_analyzer）
frontend/src/pages/Chat.tsx
frontend/src/components/ConversationList.tsx
frontend/src/components/ChatInput.tsx
frontend/src/components/ParameterPanel.tsx
frontend/src/components/messages/TextMessage.tsx
frontend/src/components/messages/ImageMessage.tsx
frontend/src/components/messages/VideoMessage.tsx
frontend/src/components/messages/AnalysisMessage.tsx
frontend/src/components/messages/StoryboardMessage.tsx
frontend/src/components/messages/ConfirmationCard.tsx
frontend/src/components/MaterialGallery.tsx   ← 改造 Gallery
frontend/src/components/ErrorBoundary.tsx     ← 全局错误边界 (Phase 7)
frontend/src/components/ui/skeleton.tsx       ← 骨架屏组件 (Phase 7)
```

### 修改文件
```
backend/src/api/routes.py                    ← 新增对话/消息/AI分析路由
backend/src/api/schemas.py                   ← 新增请求/响应模型
backend/src/models/__init__.py               ← 导出新模型
backend/src/db/database.py                   ← 新增迁移逻辑
backend/src/providers/openai_image.py        ← 支持参考图（image edit）
backend/src/config.py                        ← Qwen3-VL-Plus 配置
frontend/src/App.tsx                         ← 更新路由
frontend/src/lib/api.ts                      ← 新增 API 方法
frontend/src/pages/Gallery.tsx               ← 改造为素材库
frontend/src/pages/Usage.tsx                 ← 移除费用预估
```

### 已移除/归档
```
frontend/src/pages/Playground.tsx            ← 功能移入 Chat，已删除 (Phase 7)
frontend/src/pages/Storyboard.tsx            ← 功能移入 Chat，已删除 (Phase 7)
```
