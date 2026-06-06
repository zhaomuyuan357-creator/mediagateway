# LumenRoute AI 前端重构方案

> 日期: 2026-06-06
> 范围: 前端全面重构 — 废弃旧聊天界面，转向极简工作台 + 3D 登录页

---

## 一、核心设计原则

### 原则 1：极简无参化

用户不应面对任何技术参数。尺寸（1024x1024）、质量（auto/low/high）、格式（png/jpeg/webp）、时长（3s/5s/8s）、种子数等——这些全部由后端默认值或 AI 分析结果隐式决定。前端只暴露「选择目标」这一种交互。

### 原则 2：结果至上

用户关心的是「我的图片/视频出来了没有」，不是中间过程。所有中间状态（上传、分析、轮询）对用户透明化为一个进度指示器。最终结果（图片网格、视频播放器）占据视觉焦点。

### 原则 3：彻底废弃旧参数面板

`ParameterPanel.tsx`（292 行）、`ConfirmationCard.tsx` 中的 `ParamChip`/`ParamGroup`、`ChatInput.tsx` 中的模型选择器——这些组件连同它们的状态管理（`imageParams`、`videoParams`、`setImageParams`、`setVideoParams`）全部删除，不做迁移，不做兼容。新 store 中不存在任何参数相关字段。

### 原则 4：任务驱动替代对话驱动

旧架构以「对话（Conversation）」为核心单位，每轮对话包含多条消息。新架构以「任务（TaskSession）」为核心单位，一次上传 = 一个任务 = 一条生命周期。删除所有 Conversation/Message 相关的 API 方法和类型定义。

---

## 二、重构背景与目标

### 当前问题

| 文件 | 行数 | 问题 |
|------|------|------|
| `lib/store.ts` | 615 | 单一 store 混合 5 个关注点：对话 CRUD、消息 CRUD、输入状态、参数配置、分析/生成编排 |
| `pages/Chat.tsx` | 408 | 内联会话侧栏，与 App 级 Sidebar 重叠；三态渲染逻辑复杂 |
| `components/ChatInput.tsx` | 328 | 文字输入 + 文件上传 + 模型选择器（模型选择从未传递，纯装饰） |
| `components/ParameterPanel.tsx` | 292 | 尺寸/质量/格式/时长/种子等复杂参数面板，用户认知负担重 |
| `components/messages/*` | ~500 | 6 个聊天气泡组件，包裹在对话流中，无法独立复用 |

### 重构目标

1. **业务流极简化**：拖拽上传 → AI 自动分析 → 选择预设目标卡片 → 一键生成（全程无文字输入、无参数配置）
2. **状态管理重构**：基于 `TaskSession` 模型的 Zustand store，替代旧的对话/消息模型
3. **UI 大幅重设计**：ChatGPT 风格两栏布局 + 3D 动态登录页
4. **清理死代码**：删除 13 个废弃文件，移除未使用的 API 方法

---

## 二、新业务流程

### 图片流程

```
用户拖拽图片到上传区
    ↓
自动上传文件到后端，获取 URL
    ↓
创建 analysis 任务 (POST /v1/tasks)
    ↓
轮询任务状态 (GET /v1/tasks/{task_id})，等待分析完成
    ↓
解析 result_url JSON，提取 prompts 数组
    ↓
展示预设目标卡片：电商主图 / 产品详情页 / 社交媒体图 / 广告Banner / 节日活动主题图
    ↓
用户勾选目标卡片
    ↓
点击「一键生成」→ 为每个选中目标创建 image 任务
    ↓
并行轮询所有生成任务
    ↓
收集 image_urls，展示结果
```

### 视频流程

```
用户拖拽视频到上传区
    ↓
自动上传文件到后端，获取 URL
    ↓
创建 analysis 任务 (POST /v1/tasks)
    ↓
轮询任务状态，等待分析完成
    ↓
解析 result_url JSON，提取 viral_analysis + storyboard
    ↓
展示爆款分析维度卡片 + 分镜列表
    ↓
用户可编辑分镜（修改提示词、增删镜头）
    ↓
点击「一键生成视频」→ 创建 video 任务
    ↓
轮询任务（5 秒间隔，最长 10 分钟）
    ↓
展示视频结果 + 下载
```

---

## 三、新 UI 布局

### 工作台布局 (TaskWorkspace)

```
+------+------------------------------------------------------------+
|      |                                                            |
| [+]  |              LumenRoute AI                                 |
|      |                                                            |
| IMG  |  +------------------------------------------------------+|
| done |  |                                                      ||
|      |  |         拖拽上传区 (虚线边框, 大面积)                  ||
| VID  |  |                                                      ||
| proc |  |    [缩略图] [缩略图] [缩略图]                [x] [x]  ||
|      |  |                                                      ||
| IMG  |  +------------------------------------------------------+|
| fail |                                                            |
|      |  +--------+  +--------+  +--------+  +--------+  +------+|
|      |  |电商主图|  |产品详情|  |社交媒体|  |广告Banner|  |节日主题||
|      |  |  [x]   |  |  [ ]   |  |  [x]   |  |  [ ]   |  | [ ]  ||
|      |  +--------+  +--------+  +--------+  +--------+  +------+|
|      |                                                            |
|      |  +------------------------------------------------------+|
|      |  |            [  一键生成 (2 selected)  ]               ||
|      |  +------------------------------------------------------+|
|      |                                                            |
+------+------------------------------------------------------------+
 ~60px                         fluid
```

### 视频流程中间区域

```
      |  +------------------------------------------------------+|
      |  |  爆款视频分析                                        ||
      |  |  +------------------+  +------------------+           ||
      |  |  | Hook             |  | Pacing           |           ||
      |  |  | analysis text... |  | analysis text... |           ||
      |  |  +------------------+  +------------------+           ||
      |  |  +------------------+  +------------------+           ||
      |  |  | Visual Style     |  | Audio            |           ||
      |  |  | analysis text... |  | analysis text... |           ||
      |  |  +------------------+  +------------------+           ||
      |  +------------------------------------------------------+|
      |                                                            |
      |  +------------------------------------------------------+|
      |  |  分镜列表 (5 个镜头)                                 ||
      |  |  #1 [描述] 5s  ▼                                      ||
      |  |  #2 [描述] 3s  ▼                                      ||
      |  |  #3 [描述] 5s  ▼                                      ||
      |  +------------------------------------------------------+|
      |                                                            |
      |  +------------------------------------------------------+|
      |  |            [  一键生成视频  ]                         ||
      |  +------------------------------------------------------+|
```

### 登录页布局 (Login)

```
+---------------------------------------------------------------+
|                                                               |
|     (深色渐变光晕背景 — bg-slate-950 + 模糊色块)              |
|                                                               |
|              +--------------------+                           |
|              |   LumenRoute AI    |                           |
|              |                    |                           |
|              |  [ 登录 | 注册 ]   |                           |
|              |                    |                           |
|              |  邮箱: [________]  |                           |
|              |  密码: [________]  |                           |
|              |                    |                           |
|              |  [    提交    ]    |                           |
|              +--------------------+                           |
|                                                               |
+---------------------------------------------------------------+
```

---

## 四、新目录结构

```
src/
  App.tsx                          (修改路由 + 登录守卫)
  main.tsx                         (保留)
  index.css                        (保留)
  vite-env.d.ts                    (保留)

  lib/
    api.ts                         (修改: 添加 uploadFiles, 移除对话/消息 CRUD)
    store.ts                       (完全重写: TaskSession 模型)
    utils.ts                       (保留)

  pages/
    Login.tsx                      (新建: 3D 动态登录/注册页)
    TaskWorkspace.tsx              (新建: 替代 Chat.tsx)
    Gallery.tsx                    (保留)
    Settings.tsx                   (保留)
    Usage.tsx                      (保留)

  components/
    layout/
      AppShell.tsx                 (新建: 替代 Sidebar.tsx)
      TaskSidebar.tsx              (新建: ~60px 任务历史侧栏)

    upload/
      DropZone.tsx                 (新建: 大面积拖拽上传区)
      FilePreview.tsx              (新建: 缩略图预览条)

    cards/
      GoalCard.tsx                 (新建: 单个预设目标卡片)
      GoalCardGrid.tsx             (新建: 目标卡片网格)
      StoryboardCard.tsx           (新建: 视频分镜卡片)
      ViralAnalysisCard.tsx        (新建: 爆款分析维度卡片)

    task/
      TaskProgress.tsx             (新建: 任务进度指示器)
      GenerationResult.tsx         (新建: 生成结果展示)

    ui/                            (全部保留)
      button.tsx, card.tsx, badge.tsx, dialog.tsx, input.tsx,
      select.tsx, skeleton.tsx, slider.tsx, tabs.tsx, textarea.tsx

    ErrorBoundary.tsx              (保留)
    MaterialDetailModal.tsx        (保留)
```

---

## 五、新 Zustand Store 设计

### 类型定义

```typescript
type TaskStatus = 'pending' | 'uploading' | 'analyzing' | 'selecting' | 'generating' | 'success' | 'failed';
type MediaType = 'image' | 'video';

interface GoalPreset {
  id: string;
  purpose: string;        // "电商主图"
  purpose_en: string;     // "E-commerce Hero Image"
  prompt: string;         // 完整英文提示词
  prompt_cn: string;      // 中文描述
  selected: boolean;      // 用户勾选状态
}

interface StoryboardShot {
  shot_id: number;
  description_cn: string;
  camera_movement: string;
  duration: number;
  key_elements: string;
  seedance_prompt: string;
  keyframe_url?: string;
}

interface ViralDimension {
  dimension: string;
  analysis: string;
}

interface TaskSession {
  id: string;                        // 本地 UUID
  mediaType: MediaType;
  status: TaskStatus;

  // 上传状态
  files: File[];                     // 原始文件（用于预览）
  uploadedUrls: string[];            // 上传后的后端 URL

  // 分析状态
  analysisTaskId: string | null;     // 后端分析任务 ID

  // 分析结果
  goals: GoalPreset[];               // 图片: 预设目标卡片
  viralAnalysis: ViralDimension[];   // 视频: 爆款分析维度
  storyboard: StoryboardShot[];      // 视频: 分镜列表

  // 生成状态
  generationTaskIds: string[];       // 后端生成任务 ID 列表
  resultUrls: string[];              // 最终输出 URL

  // 元数据
  error: string | null;
  createdAt: string;
}
```

### Store 接口

```typescript
interface TaskStore {
  // 任务历史（侧栏）
  sessions: TaskSession[];
  activeSessionId: string | null;
  activeSession: () => TaskSession | undefined;

  // 会话生命周期
  createSession: (mediaType: MediaType, files: File[]) => Promise<void>;
  selectSession: (id: string) => void;
  deleteSession: (id: string) => void;
  resetSession: (id: string) => void;

  // 文件管理（当前会话内）
  addFiles: (files: File[]) => void;
  removeFile: (index: number) => void;
  clearFiles: () => void;

  // 目标选择（图片流程）
  toggleGoal: (goalId: string) => void;
  selectAllGoals: () => void;
  deselectAllGoals: () => void;

  // 分镜编辑（视频流程）
  updateShot: (shotId: number, updates: Partial<StoryboardShot>) => void;
  removeShot: (shotId: number) => void;
  addShot: () => void;

  // 核心动作
  startAnalysis: () => Promise<void>;
  startGeneration: () => Promise<void>;
}
```

### 核心动作流程

#### startAnalysis()

```
1. 获取 activeSession，验证 files 存在
2. session.status = 'uploading'
3. 调用 api.uploadFiles(files) 获取后端 URL
4. session.status = 'analyzing'
5. 调用 api.createTask({ task_type: 'analysis', payload: { image_url 或 video_url, ... } })
6. 调用 api.pollTask(taskId) 阻塞等待
7. 解析 JSON.parse(task.result_url)
8. 图片: session.goals = result.prompts.map(p => ({ ...p, selected: false }))
9. 视频: session.viralAnalysis = result.viral_analysis; session.storyboard = result.storyboard
10. session.status = 'selecting'
```

#### startGeneration()

```
1. 获取 activeSession，验证 goals/shots 已选中
2. session.status = 'generating'
3. 图片流程:
   a. 为每个选中 goal 创建 api.createTask({ task_type: 'image', payload: { prompt, reference_image_url, ... } })
   b. Promise.all(api.pollTask(...)) 并行轮询
   c. 收集 image_urls 到 session.resultUrls
4. 视频流程:
   a. 创建 api.createTask({ task_type: 'video', payload: { shots, ... } })
   b. api.pollTask(taskId, 120, 5000) 轮询（5 秒间隔）
   c. 解析 video_url 到 session.resultUrls
5. session.status = 'success'（或 'failed'）
```

---

## 六、API Client 修改

### 添加

```typescript
/**
 * 独立文件上传方法
 * 复用 sendMessage 的 FormData 模式，但只返回 URL
 */
async uploadFiles(files: File[]): Promise<{ urls: string[] }> {
  const formData = new FormData();
  files.forEach(file => formData.append('files', file));

  const response = await fetch(`${API_BASE_URL}/upload`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    throw new Error('文件上传失败');
  }

  return response.json();
}
```

> **注意**：若后端无 `/v1/upload` 独立端点，则复用 `POST /v1/conversations/{id}/messages` 的 FormData 模式，创建临时会话后提取 URL。

### 移除

- `createConversation()`, `listConversations()`, `getConversation()`, `deleteConversation()`
- `sendMessage()`, `getMessages()`
- 类型导出: `Conversation`, `Message`, `MessageRole`, `MessageType`, `ConversationType`

### 保留不变

- `createTask()`, `getTask()`, `listTasks()`, `deleteTask()`, `pollTask()` — 核心任务轮询
- Provider CRUD: `createProvider`, `listProviders`, `getProvider`, `updateProvider`, `deleteProvider`
- Material CRUD: `listMaterials`, `getMaterial`, `deleteMaterial`

---

## 七、登录页视觉方案（极简渐变光晕）

> **决策记录**：2026-06-06 放弃 Three.js / React Three Fiber 3D 方案。原因：WebGL 兼容性、性能开销、开发调试复杂度与项目极简原则不符。改用纯 CSS 渐变 + 模糊实现现代深色光晕效果。

### 技术方案

- 背景：`bg-slate-950` 深色底色
- 光晕：两个绝对定位的模糊色块（`bg-blue-900/20 blur-3xl`、`bg-purple-900/20 blur-3xl`），通过 `animate-pulse` 轻微呼吸动画
- 登录卡片：`backdrop-blur-md bg-slate-900/60 border border-slate-700/50` 毛玻璃质感
- 无任何额外依赖，纯 Tailwind CSS 实现

### Login.tsx

```tsx
function Login() {
  const [mode, setMode] = useState<'login' | 'register'>('login');

  return (
    <div className="relative w-screen h-screen bg-slate-950 overflow-hidden">
      {/* 渐变光晕背景 */}
      <div className="absolute -top-40 -left-40 w-96 h-96 bg-blue-900/20 rounded-full blur-3xl animate-pulse" />
      <div className="absolute -bottom-40 -right-40 w-96 h-96 bg-purple-900/20 rounded-full blur-3xl animate-pulse" />

      {/* 登录卡片 */}
      <div className="relative z-10 flex items-center justify-center w-full h-full">
        <div className="w-[380px] p-6 backdrop-blur-md bg-slate-900/60 border border-slate-700/50 rounded-2xl">
          <h1 className="text-2xl font-bold text-center text-white mb-6">LumenRoute AI</h1>
          {/* Tabs + Form ... */}
        </div>
      </div>
    </div>
  );
}
```

---

## 八、组件详细设计

### DropZone.tsx — 拖拽上传区

**功能**:
- 大面积虚线边框拖拽区域
- 支持拖拽文件、点击浏览、剪贴板粘贴
- 文件验证：50MB 大小限制，图片/视频类型检查
- 拖入文件后自动创建 TaskSession 并触发 startAnalysis

**逻辑来源**: 从 `ChatInput.tsx` 提取（handleDrop, handleDragOver, handlePaste, 文件验证）

```tsx
interface DropZoneProps {
  onFilesAccepted: (files: File[]) => void;
  disabled?: boolean;
}
```

### FilePreview.tsx — 文件缩略图预览

**功能**: 水平排列的缩略图条，每个缩略图带 X 按钮移除

**逻辑来源**: 从 `ChatInput.tsx` 的 attachment preview 部分提取

### GoalCard.tsx — 单个预设目标卡片

**功能**:
- 显示目的标签（如「电商主图」）+ 英文副标题
- 点击切换选中状态（高亮边框）
- 通过 `store.toggleGoal(goalId)` 更新状态

### GoalCardGrid.tsx — 目标卡片网格

**功能**: 水平排列 GoalCard 组件，显示「选择商业目标」标题 + 已选数量

### StoryboardCard.tsx — 视频分镜卡片

**功能**:
- 可展开/折叠的镜头列表
- 每个镜头显示：编号、描述、时长、Seedance 提示词
- 可编辑提示词、删除镜头、添加新镜头
- 「确认生成视频」按钮

**逻辑来源**: 从 `StoryboardMessage.tsx` 重构，去除聊天气泡包裹

### ViralAnalysisCard.tsx — 爆款分析维度卡片

**功能**: 网格展示 6 个分析维度（Hook、Pacing、Visual Style、Audio 等），每张卡片显示维度名 + 分析文本

**逻辑来源**: 从 `AnalysisMessage.tsx` 重构

### TaskProgress.tsx — 任务进度指示器

**功能**:
- 状态文本（"上传中..." / "分析中..." / "生成中..."）
- 旋转加载动画
- 视频生成时显示 "视频生成中，通常需要 2-5 分钟" + 计时器

### GenerationResult.tsx — 生成结果展示

**功能**:
- 图片: 网格展示生成的图片，每张带下载按钮 + 「存入素材库」
- 视频: 16:9 视频播放器 + 下载按钮

**逻辑来源**: 从 `ImageMessage.tsx` 和 `VideoMessage.tsx` 重构

---

## 九、AppShell + TaskSidebar 设计

### TaskSidebar.tsx (~60px)

```
+--------+
|  [+]   |  ← 新建任务按钮
|        |
| 🖼 ✓   |  ← 图片任务（绿色 = 成功）
| 🎬 ●   |  ← 视频任务（黄色 = 进行中）
| 🖼 ✗   |  ← 图片任务（红色 = 失败）
| 🎬 ○   |  ← 视频任务（蓝色 = 选择中）
|        |
|        |
|  ⚙    |  ← 设置入口
+--------+
```

- 每个任务项：图标(Image/Video) + 状态色点
- 点击切换 activeSession
- 底部：设置/Gallery 入口

### AppShell.tsx

- 替代现有 `Sidebar.tsx`
- 渲染 `TaskSidebar`（60px）+ 主内容区（fluid）
- 移动端：汉堡菜单 + 滑出 TaskSidebar

---

## 十、路由设计

```tsx
<Router>
  <Routes>
    <Route path="/login" element={<Login />} />
    <Route element={<AppShell />}>
      <Route path="/" element={<TaskWorkspace />} />
      <Route path="/gallery/*" element={<Gallery />} />
      <Route path="/settings" element={<Settings />} />
    </Route>
  </Routes>
</Router>
```

- `/login` 独立布局（全屏渐变光晕背景 + 居中毛玻璃卡片）
- 其他路由使用 AppShell 布局（TaskSidebar + 内容区）
- 登录守卫：未登录时重定向到 `/login`（初期可用 localStorage 简单实现）

---

## 十一、新增依赖

> 无新增依赖。登录页背景使用纯 Tailwind CSS 渐变 + 模糊实现，无需 Three.js。

---

## 十二、实施顺序

### Phase 1: 骨架路由 + 登录页

| 步骤 | 文件 | 操作 |
|------|------|------|
| 1.1 | `pages/Login.tsx` | 新建：渐变光晕背景 + 毛玻璃登录卡片 |
| 1.2 | `App.tsx` | 添加 `/login` 路由 |

### Phase 2: 登录页视觉完善（渐变光晕）

| 步骤 | 文件 | 操作 |
|------|------|------|
| 2.1 | `pages/Login.tsx` | 完善光晕动画、响应式布局、Tab 切换交互 |

### Phase 3: 工作台基础层

| 步骤 | 文件 | 操作 |
|------|------|------|
| 3.1 | `lib/store.ts` | 完全重写：TaskStore + TaskSession 模型 |
| 3.2 | `lib/api.ts` | 添加 uploadFiles，移除对话/消息 CRUD |

### Phase 4: 工作台组件

| 步骤 | 文件 | 操作 |
|------|------|------|
| 4.1 | `components/upload/DropZone.tsx` | 新建：拖拽上传区 |
| 4.2 | `components/upload/FilePreview.tsx` | 新建：缩略图预览 |
| 4.3 | `components/cards/GoalCard.tsx` | 新建：单个目标卡片 |
| 4.4 | `components/cards/GoalCardGrid.tsx` | 新建：目标卡片网格 |
| 4.5 | `components/cards/ViralAnalysisCard.tsx` | 新建：爆款分析维度 |
| 4.6 | `components/cards/StoryboardCard.tsx` | 新建：分镜卡片 |
| 4.7 | `components/task/TaskProgress.tsx` | 新建：进度指示器 |
| 4.8 | `components/task/GenerationResult.tsx` | 新建：结果展示 |

### Phase 5: 布局 + 主页面

| 步骤 | 文件 | 操作 |
|------|------|------|
| 5.1 | `components/layout/TaskSidebar.tsx` | 新建：60px 任务历史侧栏 |
| 5.2 | `components/layout/AppShell.tsx` | 新建：整体布局壳 |
| 5.3 | `pages/TaskWorkspace.tsx` | 新建：替代 Chat.tsx 的主工作区 |

### Phase 6: 路由收尾 + 清理

| 步骤 | 文件 | 操作 |
|------|------|------|
| 6.1 | `App.tsx` | 完善登录守卫 + 全部路由 |
| 6.2 | 旧文件 | 删除 13 个废弃文件（见删除清单） |

---

## 十三、删除清单

| 文件 | 原因 |
|------|------|
| `pages/Chat.tsx` | 被 TaskWorkspace.tsx 替代 |
| `components/ChatInput.tsx` | 文字输入不再需要，上传逻辑移至 DropZone |
| `components/ParameterPanel.tsx` | 参数面板完全废弃 |
| `components/ConversationList.tsx` | 未使用的死代码 |
| `components/Sidebar.tsx` | 被 AppShell.tsx 替代 |
| `components/messages/TextMessage.tsx` | 聊天气泡不再需要 |
| `components/messages/ImageMessage.tsx` | 逻辑移至 GenerationResult |
| `components/messages/VideoMessage.tsx` | 逻辑移至 GenerationResult |
| `components/messages/AnalysisMessage.tsx` | 逻辑移至 ViralAnalysisCard |
| `components/messages/StoryboardMessage.tsx` | 逻辑移至 StoryboardCard |
| `components/messages/ConfirmationCard.tsx` | 被 GoalCardGrid 替代 |
| `components/messages/index.ts` | 桶文件，随目录删除 |
| `lib/store.legacy.ts` | 临时兼容文件，完成后删除 |

---

## 十四、保留不变的文件

| 文件 | 说明 |
|------|------|
| `main.tsx` | 入口文件 |
| `index.css` | Tailwind CSS 变量 + shadcn/ui 主题 |
| `vite-env.d.ts` | Vite 类型声明 |
| `lib/utils.ts` | `cn()` 工具函数 |
| `components/ui/*` | 所有 shadcn/ui 基础组件 |
| `components/ErrorBoundary.tsx` | 错误边界 |
| `components/MaterialDetailModal.tsx` | 素材详情弹窗 |
| `pages/Gallery.tsx` | 素材库页面（需验证 import） |
| `pages/Settings.tsx` | API 中转站管理页面 |
| `pages/Usage.tsx` | 使用统计页面 |
| `vite.config.ts` | Vite 配置 |
| `tailwind.config.js` | Tailwind 配置 |
| `tsconfig.json` | TypeScript 配置 |

---

## 十五、风险和应对

| 风险 | 影响 | 应对方案 |
|------|------|----------|
| 后端无独立文件上传端点 | uploadFiles 无法直接调用 | 复用 sendMessage 的 FormData 模式，创建临时会话后提取 URL |
| Gallery.tsx 引用已删除的类型 | 编译报错 | 验证 import，必要时补充类型导出 |
| 视频生成轮询时间长（最长 10 分钟） | 用户体验差 | TaskProgress 显示计时器 + "通常需要 2-5 分钟" 提示 |
| ~~3D 模型文件缺失~~ | ~~MossBackground 无法渲染~~ | 已废弃 3D 方案，改用纯 CSS 渐变光晕 |
| 旧 store 被其他页面引用 | Gallery/Settings 编译失败 | Phase 3 中验证所有 import，必要时保留类型导出 |

---

## 十六、验证方式

### 编译验证

```bash
npm run type-check    # TypeScript 编译无错误
npm run build         # Vite 构建成功
```

### 功能验证

```bash
npm run dev           # 启动开发服务器
```

手动测试清单：

- [ ] `/login` 页面：渐变光晕背景正常显示，毛玻璃登录卡片居中，Tab 切换正常
- [ ] 拖拽图片 → 自动分析 → 展示目标卡片 → 勾选 → 一键生成 → 展示结果
- [ ] 拖拽视频 → 自动分析 → 展示爆款分析+分镜 → 编辑分镜 → 一键生成 → 播放视频
- [ ] 侧栏任务历史切换正常
- [ ] Gallery / Settings 页面正常访问
- [ ] 移动端响应式布局正常
