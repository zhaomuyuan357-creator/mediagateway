# MediaGateway 二开方案文档

## 一、项目概述

基于 [samagra14/mediagateway](https://github.com/samagra14/mediagateway) 进行二次开发，改造为**电商级 AI 视频/图片生产平台**。

### 原项目简介
原项目是一个视频生成模型的统一网关（类似 LiteLLM for Video），封装了 Sora、Runway、Kling 三个视频生成 API，提供统一的 REST 接口。

### 二开目标
1. **视频生成**：替换为字节跳动 Seedance 2.0（火山引擎 Ark API）
2. **图片生成**：新增 OpenAI gpt-image-1 生图能力
3. **分镜拆解**：新增参考视频 → AI 分镜 → 批量生成视频的流水线
4. **前端中文化**：界面全部改为中文

---

## 二、技术栈

| 层级 | 原项目 | 二开后 |
|------|--------|--------|
| 后端框架 | FastAPI + SQLAlchemy | 不变 |
| 前端框架 | React 18 + Vite + Tailwind | 不变 |
| 视频生成 | Sora / Runway / Kling | **Seedance 2.0**（火山引擎 Ark API） |
| 图片生成 | 无 | **OpenAI gpt-image-1** |
| 视频分析 | 无 | **千问 VL**（DashScope API） |
| 关键帧提取 | 无 | **ffmpeg** |
| 数据库 | SQLite | 不变（可扩展） |
| 部署 | Docker Compose | 不变 |

---

## 三、改动一：替换视频生成为 Seedance 2.0

### 3.1 删除旧 Provider

删除以下文件：
- `backend/src/providers/sora.py`
- `backend/src/providers/runway.py`
- `backend/src/providers/kling.py`

### 3.2 新增 Seedance Provider

**新建文件**：`backend/src/providers/seedance.py`

```
API 地址：https://ark.cn-beijing.volces.com/api/v3
认证方式：Bearer Token（火山引擎 Ark API Key）
流程：提交异步任务 → 轮询状态 → 获取视频 URL
```

实现要点：
- 继承 `VideoProvider` 抽象基类
- `name` → `"seedance"`
- `models` → `["seedance-2.0-t2v", "seedance-2.0-i2v"]`
  - `t2v`：文生视频
  - `i2v`：图生视频
- `generate_video()` → `POST /contents/generations/tasks`
- `check_status()` → `GET /contents/generations/tasks/{task_id}`
- 需要用户在火山引擎控制台创建推理接入点，获取 `endpoint_id`（格式 `ep-xxxxxxxxxxxx`）

### 3.3 更新配置

**修改文件**：`backend/src/config.py`

新增配置项：
```python
seedance_endpoint_id: str = ""  # 火山引擎 Ark 推理接入点 ID
```

### 3.4 更新费用计算

**修改文件**：`backend/src/services/cost_calculator.py`

```python
PRICING = {
    "seedance": {
        "seedance-2.0-t2v": {"per_second": 0.08, "base_cost": 0.0},
        "seedance-2.0-i2v": {"per_second": 0.10, "base_cost": 0.0},
    },
}
```

### 3.5 更新 Provider 注册表

**修改文件**：`backend/src/providers/__init__.py`

```python
PROVIDERS = {
    "seedance": SeedanceProvider,
}

MODEL_PROVIDER_MAP = {
    "seedance-2.0-t2v": "seedance",
    "seedance-2.0-i2v": "seedance",
}
```

---

## 四、改动二：新增 OpenAI 图片生成

### 4.1 新增 ImageProvider 抽象基类

**修改文件**：`backend/src/providers/base.py`

在现有 `VideoProvider` 旁边新增 `ImageProvider`：

```python
class ImageRequest(BaseModel):
    prompt: str
    size: Optional[str] = "1024x1024"       # 1024x1024 / 1536x1024 / 1024x1536
    quality: Optional[str] = "auto"          # low / medium / high / auto
    output_format: Optional[str] = "png"     # png / jpeg / webp
    n: Optional[int] = 1                     # 1-4 张

class ImageResponse(BaseModel):
    job_id: str
    status: str
    image_urls: Optional[list[str]] = None   # 支持多张
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class ImageProvider(ABC):
    """图片生成 Provider 基类"""
    # 与 VideoProvider 平级，接口类似
    # generate_image() / check_status() / validate_key()
```

### 4.2 新增 OpenAI Image Provider

**新建文件**：`backend/src/providers/openai_image.py`

```
API 地址：https://api.openai.com/v1/images/generations
认证方式：Bearer Token（OpenAI API Key）
特点：同步接口，不需要轮询，提交后直接返回结果
```

实现要点：
- `name` → `"openai-image"`
- `models` → `["gpt-image-1"]`
- `generate_image()` → `POST /v1/images/generations`
- 支持 `n=1~4`，一次生成多张
- 返回 `b64_json`，需要解码后存储为文件

### 4.3 新增图片生成 API 端点

**修改文件**：`backend/src/api/routes.py`

新增：
- `POST /v1/image/generations` — 提交图片生成
- `GET /v1/image/generations/{id}` — 查询状态
- `GET /v1/image/generations` — 列出记录
- `DELETE /v1/image/generations/{id}` — 删除记录

### 4.4 新增图片生成 Schema

**修改文件**：`backend/src/api/schemas.py`

```python
class ImageGenerationRequest(BaseModel):
    model: str = "gpt-image-1"
    prompt: str
    provider: Optional[str] = "openai-image"
    size: Optional[str] = "1024x1024"
    quality: Optional[str] = "auto"
    output_format: Optional[str] = "png"
    n: Optional[int] = Field(1, ge=1, le=4)

class ImageGenerationResponse(BaseModel):
    id: str
    object: str = "image.generation"
    created: int
    model: str
    provider: str
    status: str
    prompt: Optional[str] = None
    image: Optional[ImageObject] = None
    usage: Optional[UsageObject] = None
    error: Optional[str] = None
```

### 4.5 更新 DB 模型

**修改文件**：`backend/src/models/generation.py`

给 `Generation` 表新增 `type` 字段：
```python
type = Column(String, default="video")  # "video" 或 "image"
```

video_url 字段同时存储图片 URL，Gallery 统一查询。

### 4.6 更新 Provider 注册

```python
PROVIDERS = {
    "seedance": SeedanceProvider,
    "openai-image": OpenAIImageProvider,
}

MODEL_PROVIDER_MAP = {
    "seedance-2.0-t2v": "seedance",
    "seedance-2.0-i2v": "seedance",
    "gpt-image-1": "openai-image",
}
```

---

## 五、改动三：分镜拆解功能

### 5.1 功能流程

```
用户上传参考视频（文件或 URL）+ 可选文字描述
        │
        ▼
后端下载/接收视频到 storage/temp/
        │
        ▼
ffmpeg 提取 12 个关键帧（均匀采样或 I 帧提取）
        │
        ▼
关键帧 base64 + 用户描述 → 千问 VL (DashScope API)
"请分析这个视频，拆成9个分镜头，输出结构化JSON"
        │
        ▼
千问返回 9 个分镜：
  - 中文画面描述
  - 运镜方式（推/拉/摇/移/跟/升/降/固定）
  - 建议时长
  - 关键元素
  - Seedance 英文 prompt
        │
        ▼
系统为每个分镜生成 Seedance 优化的 prompt
        │
        ▼
返回给前端：9 个分镜卡片（关键帧预览 + prompt）
        │
        ▼
用户逐条预览、编辑 prompt（可选）
        │
        ▼
用户点击"批量生成视频"
        │
        ▼
9 个 prompt 依次提交给 Seedance 2.0
        │
        ▼
前端轮询每个分镜的生成状态
完成后展示 9 个独立视频片段
```

### 5.2 新增依赖

**修改文件**：`backend/requirements.txt`

```
ffmpeg-python==2.0.2
```

**修改文件**：`backend/Dockerfile`

```dockerfile
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*
```

### 5.3 新增分镜分析服务

**新建文件**：`backend/src/services/storyboard_analyzer.py`

核心类 `StoryboardAnalyzer`，负责：

1. **关键帧提取**（`extract_keyframes`）
   - 用 ffmpeg 从视频中均匀采样 12 帧
   - 输出 JPEG 格式的 base64 编码图片列表
   - ffmpeg 命令：`ffmpeg -i input.mp4 -vf "fps=1/{interval}" -frames:v 12 frame_%03d.jpg`

2. **千问 VL 分析**（`analyze_with_qwen`）
   - 调用 DashScope OpenAI 兼容接口
   - 地址：`https://dashscope.aliyuncs.com/compatible-mode/v1`
   - 模型：`qwen-vl-max`
   - 把 12 帧图片 + system prompt 发给千问
   - 要求输出 9 个分镜的结构化 JSON

3. **Seedance Prompt 生成**（`generate_seedance_prompt`）
   - 把千问返回的中文描述转换为 Seedance 优化的英文 prompt
   - 包含：运镜指令 + 画面描述 + 风格关键词

**发给千问的 System Prompt**：

```
你是一个专业的电商视频分镜师。请分析这些视频关键帧，将视频拆解为9个分镜头。

对每个分镜，请输出：
1. 画面描述（中文，详细描述画面内容）
2. 运镜方式（推/拉/摇/移/跟/升/降/固定/环绕）
3. 时长建议（2-5秒）
4. 关键元素（主体产品、背景环境、光线、色调、情绪）
5. Seedance英文prompt（适合AI视频生成引擎的英文描述，包含运镜、主体、环境、风格）

请严格输出JSON数组格式，不要包含其他文字：
[
  {
    "shot_id": 1,
    "description_cn": "画面中文描述",
    "camera_movement": "运镜方式",
    "duration": 3,
    "key_elements": "关键元素描述",
    "seedance_prompt": "English prompt for Seedance 2.0..."
  }
]
```

### 5.4 新增 API 端点

**修改文件**：`backend/src/api/routes.py`

| 端点 | 方法 | 说明 |
|------|------|------|
| `/v1/storyboard/analyze` | POST | 上传视频，触发分镜分析 |
| `/v1/storyboard/{id}` | GET | 查询分镜分析结果 |
| `/v1/storyboard/{id}/shots/{shot_id}` | PUT | 编辑某个分镜的 prompt |
| `/v1/storyboard/{id}/generate` | POST | 批量生成 9 个分镜视频 |

**POST /v1/storyboard/analyze** 请求：
```
Content-Type: multipart/form-data
- video: 视频文件（可选）
- video_url: 视频 URL（可选，二选一）
- user_prompt: 文字描述（可选）
```

响应：
```json
{
  "storyboard_id": "sb_a1b2c3d4",
  "status": "ready",
  "shots": [
    {
      "shot_id": 1,
      "description_cn": "产品特写，缓慢推近，展示材质细节",
      "camera_movement": "推",
      "duration": 3,
      "key_elements": "产品主体、浅色背景、柔和光线",
      "seedance_prompt": "Close-up shot of a product, slow push in...",
      "keyframe_url": "/storyboard/sb_a1b2c3d4/frame_001.jpg"
    }
    // ... 共 9 个
  ]
}
```

**POST /v1/storyboard/{id}/generate** 请求：
```json
{
  "shot_overrides": {
    3: "用户修改后的第3个分镜prompt",
    7: "用户修改后的第7个分镜prompt"
  }
}
```

响应：
```json
{
  "storyboard_id": "sb_a1b2c3d4",
  "generation_ids": ["gen_xxx1", "gen_xxx2", ..., "gen_xxx9"],
  "status": "generating"
}
```

### 5.5 新增 DB 模型

**新建文件**：`backend/src/models/storyboard.py`

```python
class Storyboard(Base):
    __tablename__ = "storyboards"

    id = Column(String, primary_key=True)           # sb_xxx
    source_video_url = Column(String)                # 原始视频 URL
    source_video_path = Column(String)               # 本地存储路径
    user_prompt = Column(String)                     # 用户补充描述
    shots = Column(JSON)                             # 9 个分镜的 JSON 数据
    status = Column(String)                          # analyzing / ready / generating / completed
    generation_ids = Column(JSON)                    # 关联的 9 个 generation ID
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
```

### 5.6 更新配置

**修改文件**：`backend/src/config.py`

```python
dashscope_api_key: str = ""                         # 千问 API Key
dashscope_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
dashscope_model: str = "qwen-vl-max"                # 视觉模型
```

---

## 六、前端改动

### 6.1 更新 API 客户端

**修改文件**：`frontend/src/lib/api.ts`

新增类型：
```typescript
interface Shot {
  shot_id: number
  description_cn: string
  camera_movement: string
  duration: number
  key_elements: string
  seedance_prompt: string
  keyframe_url?: string
}

interface Storyboard {
  storyboard_id: string
  shots: Shot[]
  status: string
  generation_ids?: string[]
}

interface ImageGenerationRequest {
  model: string
  prompt: string
  provider?: string
  size?: string
  quality?: string
  output_format?: string
  n?: number
}
```

新增方法：
```typescript
// 图片生成
createImageGeneration(req): POST /v1/image/generations
getImageGeneration(id): GET /v1/image/generations/{id}
listImageGenerations(params): GET /v1/image/generations

// 分镜拆解
analyzeStoryboard(video, prompt): POST /v1/storyboard/analyze
getStoryboard(id): GET /v1/storyboard/{id}
updateShot(storyboardId, shotId, prompt): PUT /v1/storyboard/{id}/shots/{shotId}
generateFromStoryboard(id, overrides): POST /v1/storyboard/{id}/generate
```

### 6.2 新增分镜拆解页面

**新建文件**：`frontend/src/pages/Storyboard.tsx`

页面布局：

```
┌──────────────────────────────────────────────────┐
│  分镜拆解                                         │
├──────────────────────────────────────────────────┤
│                                                   │
│  ┌─ 参考视频上传 ─────────────────────────────┐   │
│  │  [拖拽上传视频文件] 或 [粘贴视频URL]         │   │
│  │  [补充描述：如"帮我拆成电商展示视频"]         │   │
│  │  [开始分析] 按钮                             │   │
│  └─────────────────────────────────────────────┘   │
│                                                   │
│  ┌─ 分镜预览（分析完成后展示）─────────────────┐   │
│  │  分镜1    分镜2    分镜3                     │   │
│  │  [关键帧] [关键帧] [关键帧]                  │   │
│  │  prompt   prompt   prompt                   │   │
│  │  [编辑]   [编辑]   [编辑]                    │   │
│  │                                             │   │
│  │  分镜4    分镜5    分镜6                     │   │
│  │  [关键帧] [关键帧] [关键帧]                  │   │
│  │  prompt   prompt   prompt                   │   │
│  │  [编辑]   [编辑]   [编辑]                    │   │
│  │                                             │   │
│  │  分镜7    分镜8    分镜9                     │   │
│  │  [关键帧] [关键帧] [关键帧]                  │   │
│  │  prompt   prompt   prompt                   │   │
│  │  [编辑]   [编辑]   [编辑]                    │   │
│  │                                             │   │
│  │  [批量生成视频] 按钮                         │   │
│  └─────────────────────────────────────────────┘   │
│                                                   │
│  ┌─ 生成进度（点击批量生成后展示）─────────────┐   │
│  │  分镜1: ✅ 已完成   [预览]                   │   │
│  │  分镜2: ⏳ 生成中...                         │   │
│  │  分镜3: ⏳ 等待中                            │   │
│  │  ...                                        │   │
│  │  分镜9: ⏳ 等待中                            │   │
│  │  总进度: 1/9 ██░░░░░░░░ 11%                 │   │
│  └─────────────────────────────────────────────┘   │
│                                                   │
└──────────────────────────────────────────────────┘
```

交互流程：
1. 用户上传视频或粘贴 URL，可选输入补充描述
2. 点击"开始分析"，显示 loading 动画（"正在提取关键帧..."/"AI 正在分析分镜..."）
3. 分析完成，展示 3x3 九宫格分镜卡片
4. 每个卡片：关键帧缩略图 + 运镜标签 + prompt 文本 + 编辑按钮
5. 点击"编辑"展开 Textarea 修改 prompt
6. 点击"批量生成视频"→ 提交 9 个 Seedance 任务
7. 下方显示逐条进度，完成的可以预览
8. 全部完成后可跳转 Gallery 查看所有视频

### 6.3 改造 Playground 页面

**修改文件**：`frontend/src/pages/Playground.tsx`

- 顶部 Tab 切换：**视频生成** | **图片生成**
- 视频模式：prompt + Seedance 模型选择 + 时长 + 宽高比
- 图片模式：prompt + 尺寸选择 + 质量选择 + 格式选择 + 数量（1-4张）
- 图片完成后展示 `<img>` 标签网格（多张时 2x2 布局）

### 6.4 改造 Gallery 页面

**修改文件**：`frontend/src/pages/Gallery.tsx`

- 新增媒体类型筛选：**全部** | **视频** | **图片**
- 卡片根据类型渲染 `<video>` 或 `<img>`
- 支持按 storyboard_id 筛选，查看同一组分镜的所有视频

### 6.5 更新 Settings 页面

**修改文件**：`frontend/src/pages/Settings.tsx`

- Provider 列表更新为：Seedance、OpenAI Image、千问 VL
- 千问 VL 不需要 API Key 管理（通过 config 配置），但可以显示配置状态

### 6.6 更新 Usage 页面

**修改文件**：`frontend/src/pages/Usage.tsx`

- 图片生成费用单独统计（按张计费 vs 按秒计费）
- 分镜分析费用统计（千问 API 调用费用）
- Pricing 表格新增图片定价

### 6.7 更新导航和文案

**修改文件**：`frontend/src/App.tsx`

- 导航栏新增：**分镜拆解**
- 所有 UI 文案改为中文（按钮、标签、提示文字、状态等）

---

## 七、完整文件变更清单

| 操作 | 文件 | 说明 |
|------|------|------|
| **新建** | `backend/src/providers/seedance.py` | Seedance 2.0 视频 Provider |
| **新建** | `backend/src/providers/openai_image.py` | OpenAI gpt-image-1 图片 Provider |
| **新建** | `backend/src/services/storyboard_analyzer.py` | 分镜拆解核心服务 |
| **新建** | `backend/src/models/storyboard.py` | 分镜数据表模型 |
| **新建** | `frontend/src/pages/Storyboard.tsx` | 分镜拆解前端页面 |
| **修改** | `backend/src/providers/__init__.py` | 注册新 Provider，删除旧的 |
| **修改** | `backend/src/providers/base.py` | 新增 ImageProvider 抽象基类 |
| **修改** | `backend/src/api/routes.py` | 新增图片+分镜 API 端点 |
| **修改** | `backend/src/api/schemas.py` | 新增图片+分镜 Schema |
| **修改** | `backend/src/models/generation.py` | 加 type 字段区分视频/图片 |
| **修改** | `backend/src/models/__init__.py` | 更新导出 |
| **修改** | `backend/src/services/cost_calculator.py` | 更新定价 |
| **修改** | `backend/src/services/video_storage.py` | 改为通用 MediaStorage |
| **修改** | `backend/src/config.py` | 新增 Seedance/DashScope 配置 |
| **修改** | `backend/src/main.py` | 更新路由挂载 |
| **修改** | `backend/requirements.txt` | 新增依赖 |
| **修改** | `backend/Dockerfile` | 安装 ffmpeg |
| **修改** | `frontend/src/lib/api.ts` | 新增类型和方法 |
| **修改** | `frontend/src/pages/Playground.tsx` | 视频/图片 Tab + 中文 |
| **修改** | `frontend/src/pages/Gallery.tsx` | 媒体类型筛选 + 中文 |
| **修改** | `frontend/src/pages/Settings.tsx` | Provider 列表 + 中文 |
| **修改** | `frontend/src/pages/Usage.tsx` | 图片费用 + 中文 |
| **修改** | `frontend/src/App.tsx` | 导航中文 + 新增分镜入口 |
| **删除** | `backend/src/providers/sora.py` | 删除 Sora Provider |
| **删除** | `backend/src/providers/runway.py` | 删除 Runway Provider |
| **删除** | `backend/src/providers/kling.py` | 删除 Kling Provider |

---

## 八、环境变量配置

```env
# === Seedance 2.0（火山引擎 Ark）===
SEEDANCE_API_KEY=your-volcengine-ark-api-key
SEEDANCE_ENDPOINT_ID=ep-xxxxxxxxxxxx

# === OpenAI 图片生成 ===
OPENAI_API_KEY=your-openai-api-key

# === 千问 VL（DashScope）===
DASHSCOPE_API_KEY=your-dashscope-api-key
DASHSCOPE_MODEL=qwen-vl-max

# === 基础配置 ===
DATABASE_URL=sqlite:///./storage/db.sqlite
STORAGE_PATH=./storage/videos
TEMP_PATH=./storage/temp
ENCRYPTION_KEY=change-this-key
SECRET_KEY=change-this-secret
```

---

## 九、依赖更新

### 后端 requirements.txt

```
fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlalchemy==2.0.23
pydantic==2.5.0
pydantic-settings==2.1.0
python-multipart==0.0.6
python-jose[cryptography]==3.3.0
cryptography==41.0.7
httpx==0.25.2
openai>=1.40.0          # 升级，支持 gpt-image-1 + DashScope 兼容
aiofiles==23.2.1
python-dotenv==1.0.0
celery==5.3.4
redis==5.0.1
ffmpeg-python==2.0.2    # 新增：ffmpeg 绑定
```

### 前端 package.json

不需要新增依赖，现有依赖足够。

---

## 十、验证方式

1. **后端启动**：`cd backend && python run.py`，确认无 import 错误
2. **API 文档**：访问 `http://localhost:3001/docs`，确认新端点可见
3. **Seedance 测试**：配置火山引擎 API Key + endpoint_id，提交 text-to-video 任务
4. **OpenAI Image 测试**：配置 OpenAI API Key，提交图片生成（n=2），确认返回 2 张图
5. **分镜拆解测试**：上传一个 15-30 秒参考视频，确认关键帧提取和千问分析正常
6. **前端**：`cd frontend && npm run dev`，确认所有页面中文、Tab 切换正常
7. **Docker**：`docker-compose up --build`，确认全栈运行

---

## 十一、注意事项

1. **ffmpeg 依赖**：Docker 环境自动安装；本地开发需确保 `ffmpeg` 命令可用
2. **视频大小限制**：建议限制上传 100MB 以内
3. **千问 VL 图片限制**：单次请求最多 10-20 张图片，关键帧控制在 12 帧
4. **Seedance 并发**：9 个分镜建议限制并发（如 3 个同时），避免限流
5. **DashScope 费用**：qwen-vl-max 约 ¥0.02/千 token，一次分镜分析约 ¥0.1-0.5
6. **openai SDK 升级**：原项目 `openai==1.3.7` 过旧，需升级到 `>=1.40.0`
7. **数据库迁移**：给 Generation 表加 `type` 字段，默认 `"video"`，已有数据兼容
