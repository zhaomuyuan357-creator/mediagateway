"""统一任务流水线 — execute_pipeline 主函数 + 三种流水线实现.

三种流水线：
1. 短流水线（纯文本输入）: pending → processing → [调中转站 API] → success/failed
2. 复合流水线（含参考图/视频）: pending → processing → [千问 VL 分析] → analyzing → [组装 Prompt] → [调中转站 API] → generating → success/failed
3. 分析流水线: pending → processing → [千问 VL 分析] → success/failed

每个节点更新 Task 的 status / progress / result_url / error_msg。
"""
import asyncio
import base64
import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

import httpx
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db.database import SessionLocal
from ..models.task import Task, TaskStatus, TaskType
from ..services.provider_router import resolve_provider, ResolvedProvider

logger = logging.getLogger(__name__)

# 视频生成轮询配置
VIDEO_POLL_INTERVAL = 5       # 秒
VIDEO_POLL_MAX_ATTEMPTS = 120  # 最多轮询次数 (120 × 5s = 10 分钟)


# ===========================================================================
# 公开入口
# ===========================================================================

async def execute_pipeline(task_id: str) -> None:
    """统一任务流水线入口.

    由 Task 创建路由通过 BackgroundTasks 调用。
    根据 task.task_type 分派到对应的子流水线。

    Args:
        task_id: Task.task_id（对外暴露的任务 ID）
    """
    db = SessionLocal()
    try:
        task = db.query(Task).filter(Task.task_id == task_id).first()
        if not task:
            logger.error("Task %s not found", task_id)
            return

        _update_task(db, task,
                     status=TaskStatus.PROCESSING,
                     started_at=datetime.utcnow())

        logger.info("Pipeline start: task_id=%s, task_type=%s",
                     task_id, task.task_type.value)

        if task.task_type == TaskType.IMAGE:
            await _run_image_pipeline(db, task)
        elif task.task_type == TaskType.VIDEO:
            await _run_video_pipeline(db, task)
        elif task.task_type == TaskType.ANALYSIS:
            await _run_analysis_pipeline(db, task)
        else:
            raise ValueError(f"未知的 task_type: {task.task_type}")

    except Exception as e:
        logger.exception("Pipeline failed: task_id=%s", task_id)
        _update_task(db, task,
                     status=TaskStatus.FAILED,
                     error_msg=str(e),
                     completed_at=datetime.utcnow())
    finally:
        db.close()


# ===========================================================================
# 子流水线 1：图片生成
# ===========================================================================

async def _run_image_pipeline(db: Session, task: Task) -> None:
    """图片生成流水线.

    payload 字段:
        prompt: str             — 生成提示词（必填）
        reference_image_url: str — 参考图片 URL（可选，触发复合流水线）
        size: str               — 图片尺寸，如 "1024x1024"（可选）
        quality: str            — 质量 low/medium/high/auto（可选）
        output_format: str      — png/jpeg/webp（可选）
        n: int                  — 生成数量 1-4（可选）
    """
    payload = task.payload or {}
    prompt = payload.get("prompt")
    if not prompt:
        raise ValueError("图片生成任务缺少 prompt 字段")

    # ── 复合流水线：有参考图 → 先用千问 VL 分析，再组装增强 Prompt ──
    reference_image_url = payload.get("reference_image_url")
    if reference_image_url:
        _update_task(db, task, progress="analyzing")
        logger.info("[%s] 参考图分析中: %s", task.task_id, reference_image_url)

        analysis_result = await _analyze_reference_image(reference_image_url, prompt)
        enhanced_prompt = _build_enhanced_prompt(prompt, analysis_result)
        payload["prompt"] = enhanced_prompt
        payload["_original_prompt"] = prompt
        payload["_analysis_result"] = analysis_result

        logger.info("[%s] Prompt 增强完成，原长度 %d → 增强后 %d",
                     task.task_id, len(prompt), len(enhanced_prompt))

    # ── 调中转站 API 生成图片 ──
    _update_task(db, task, progress="generating")
    rp = _resolve_and_bind(db, task, "image")

    # 从 payload 中提取参数，保留到请求中（覆盖默认值）
    image_params = {
        "model": rp.model,
        "prompt": payload["prompt"],
        "n": payload.get("n", 1),
        "size": payload.get("size", "1024x1024"),
    }
    # 仅在中转站支持时传递可选参数
    if payload.get("quality"):
        image_params["quality"] = payload["quality"]
    if payload.get("output_format"):
        image_params["output_format"] = payload["output_format"]

    logger.info("[%s] 调用中转站「%s」生成图片: model=%s, size=%s",
                task.task_id, rp.provider_name, rp.model,
                image_params.get("size"))

    try:
        response = await rp.client.images.generate(**image_params)
    except TypeError:
        # 某些中转站不支持 output_format / quality 等参数，回退到基础参数
        fallback_params = {
            "model": rp.model,
            "prompt": payload["prompt"],
            "n": payload.get("n", 1),
            "size": payload.get("size", "1024x1024"),
        }
        logger.info("[%s] 回退到基础参数重试", task.task_id)
        response = await rp.client.images.generate(**fallback_params)

    # 保存生成结果
    image_urls = await _save_image_results(task.task_id, response)

    if not image_urls:
        raise RuntimeError("图片生成未返回有效结果")

    result_data = {
        "image_urls": image_urls,
        "model": rp.model,
        "provider": rp.provider_name,
    }

    _update_task(db, task,
                 status=TaskStatus.SUCCESS,
                 result_url=json.dumps(result_data),
                 completed_at=datetime.utcnow())
    logger.info("[%s] 图片生成完成: %d 张", task.task_id, len(image_urls))


# ===========================================================================
# 子流水线 2：视频生成
# ===========================================================================

async def _run_video_pipeline(db: Session, task: Task) -> None:
    """视频生成流水线.

    payload 字段:
        prompt: str              — 生成提示词（必填）
        reference_video_url: str — 参考视频 URL（可选，触发复合流水线）
        duration: int            — 视频时长（秒），默认 5（可选）
        aspect_ratio: str        — 宽高比，如 "16:9"（可选）
        resolution: str          — 分辨率，如 "1280x720"（可选）
        seed: int                — 随机种子（可选）
        fps: int                 — 帧率（可选）
    """
    payload = task.payload or {}
    prompt = payload.get("prompt")
    if not prompt:
        raise ValueError("视频生成任务缺少 prompt 字段")

    # ── 复合流水线：有参考视频 → 先用千问 VL 分析，再组装增强 Prompt ──
    reference_video_url = payload.get("reference_video_url")
    if reference_video_url:
        _update_task(db, task, progress="analyzing")
        logger.info("[%s] 参考视频分析中: %s", task.task_id, reference_video_url)

        analysis_result = await _analyze_reference_video(reference_video_url, prompt)
        enhanced_prompt = _build_enhanced_prompt(prompt, analysis_result)
        payload["prompt"] = enhanced_prompt
        payload["_original_prompt"] = prompt
        payload["_analysis_result"] = analysis_result

        logger.info("[%s] Prompt 增强完成，原长度 %d → 增强后 %d",
                     task.task_id, len(prompt), len(enhanced_prompt))

    # ── 调中转站 API 生成视频 ──
    _update_task(db, task, progress="generating")
    rp = _resolve_and_bind(db, task, "video")

    # 构建视频请求参数
    video_params = {
        "model": rp.model,
        "prompt": payload["prompt"],
    }
    if payload.get("duration"):
        video_params["duration"] = payload["duration"]
    if payload.get("aspect_ratio"):
        video_params["aspect_ratio"] = payload["aspect_ratio"]
    if payload.get("resolution"):
        video_params["resolution"] = payload["resolution"]
    if payload.get("seed") is not None:
        video_params["seed"] = payload["seed"]
    if payload.get("fps"):
        video_params["fps"] = payload["fps"]

    logger.info("[%s] 调用中转站「%s」生成视频: model=%s",
                task.task_id, rp.provider_name, rp.model)

    # 视频生成采用「提交 + 轮询」模式
    submit_result = await _submit_video_generation(rp, video_params)

    if submit_result.get("status") == "failed":
        raise RuntimeError(submit_result.get("error", "视频提交失败"))

    job_id = submit_result.get("job_id")
    if not job_id:
        raise RuntimeError("视频提交未返回 job_id")

    logger.info("[%s] 视频任务已提交: job_id=%s", task.task_id, job_id)

    # 轮询等待完成
    video_url = await _poll_video_status(rp, job_id, task.task_id)

    if not video_url:
        raise RuntimeError("视频生成超时或未返回有效结果")

    # 下载视频到本地存储
    from ..services.video_storage import get_video_storage
    storage = get_video_storage()
    filename = f"{task.task_id}.mp4"
    local_path = await storage.download_video(video_url, filename)

    result_data = {
        "video_url": local_path,
        "source_url": video_url,
        "model": rp.model,
        "provider": rp.provider_name,
        "job_id": job_id,
    }

    _update_task(db, task,
                 status=TaskStatus.SUCCESS,
                 result_url=json.dumps(result_data),
                 completed_at=datetime.utcnow())
    logger.info("[%s] 视频生成完成: %s", task.task_id, local_path)


# ===========================================================================
# 子流水线 3：视觉分析
# ===========================================================================

async def _run_analysis_pipeline(db: Session, task: Task) -> None:
    """分析流水线.

    payload 字段:
        image_url: str    — 图片 URL（与 video_url 二选一）
        video_url: str    — 视频 URL（与 image_url 二选一）
        user_intent: str  — 用户意图描述（必填）
        analysis_type: str — 分析类型，"image" / "video"（可选，自动推断）
    """
    payload = task.payload or {}
    user_intent = payload.get("user_intent", "通用分析")
    image_url = payload.get("image_url")
    video_url = payload.get("video_url")
    analysis_type = payload.get("analysis_type")

    # 自动推断分析类型
    if not analysis_type:
        if video_url:
            analysis_type = "video"
        elif image_url:
            analysis_type = "image"
        else:
            raise ValueError("分析任务需要提供 image_url 或 video_url")

    _update_task(db, task, progress="analyzing")

    # 通过 provider_router 获取分析服务的客户端
    rp = resolve_provider(db, "analysis")
    _update_task(db, task,
                 provider_id=rp.provider_id,
                 provider_name=rp.provider_name)

    if analysis_type == "image":
        if not image_url:
            raise ValueError("图片分析需要 image_url")

        logger.info("[%s] 图片分析中: %s", task.task_id, image_url[:80])
        from ..services.image_analyzer import get_image_analyzer
        result = await get_image_analyzer().analyze(
            image_url, user_intent, client=rp.client, model=rp.model,
        )

        result_data = {
            "analysis_type": "image",
            "analysis_id": result.analysis_id,
            "image_url": result.image_url,
            "intent": result.intent,
            "prompts": [p.to_dict() for p in result.prompts],
        }

    elif analysis_type == "video":
        if not video_url:
            raise ValueError("视频分析需要 video_url")

        logger.info("[%s] 视频分析中: %s", task.task_id, video_url[:80])
        from ..services.video_analyzer import get_video_analyzer
        result = await get_video_analyzer().analyze(
            video_url, user_intent, client=rp.client, model=rp.model,
        )

        result_data = {
            "analysis_type": "video",
            "analysis_id": result.analysis_id,
            "video_url": result.video_url,
            "intent": result.intent,
            "viral_analysis": [v.to_dict() for v in result.viral_analysis],
            "storyboard": [s.to_dict() for s in result.storyboard],
        }
    else:
        raise ValueError(f"未知的 analysis_type: {analysis_type}")

    _update_task(db, task,
                 status=TaskStatus.SUCCESS,
                 result_url=json.dumps(result_data),
                 completed_at=datetime.utcnow())
    logger.info("[%s] 分析完成: type=%s", task.task_id, analysis_type)


# ===========================================================================
# 内部辅助函数
# ===========================================================================

def _update_task(db: Session, task: Task, **kwargs) -> None:
    """更新 Task 字段并提交到 DB."""
    for key, value in kwargs.items():
        if hasattr(task, key):
            setattr(task, key, value)
    task.updated_at = datetime.utcnow()
    db.commit()


def _resolve_and_bind(db: Session, task: Task, task_type: str) -> ResolvedProvider:
    """路由解析 + 绑定 provider 信息到 Task.

    Args:
        db: 数据库会话
        task: 当前任务
        task_type: "image" / "video"

    Returns:
        ResolvedProvider 包含已实例化的 AsyncOpenAI 客户端
    """
    rp = resolve_provider(db, task_type)
    _update_task(db, task,
                 provider_id=rp.provider_id,
                 provider_name=rp.provider_name)
    return rp


async def _analyze_reference_image(image_url: str, user_intent: str) -> str:
    """调用千问 VL 分析参考图片，返回结构化分析文本.

    用于复合流水线：提取参考图的视觉特征，用于增强生成 Prompt。
    """
    from ..services.image_analyzer import get_image_analyzer
    result = await get_image_analyzer().analyze(image_url, user_intent)

    # 将分析结果转为可拼接到 Prompt 的文本
    parts = []
    for p in result.prompts:
        parts.append(f"[{p.purpose}] {p.prompt}")
    return "\n".join(parts) if parts else ""


async def _analyze_reference_video(video_url: str, user_intent: str) -> str:
    """调用千问 VL 分析参考视频，返回结构化分析文本.

    用于复合流水线：提取参考视频的分镜结构和风格特征。
    """
    from ..services.video_analyzer import get_video_analyzer
    result = await get_video_analyzer().analyze(video_url, user_intent)

    # 提取分镜的 seedance_prompt 作为参考
    parts = []
    for shot in result.storyboard:
        if shot.seedance_prompt:
            parts.append(f"[Shot {shot.shot_id}] {shot.seedance_prompt}")
    return "\n".join(parts) if parts else ""


def _build_enhanced_prompt(original_prompt: str, analysis_text: str) -> str:
    """将分析结果融入原始 Prompt，生成增强版 Prompt.

    Args:
        original_prompt: 用户原始提示词
        analysis_text: 千问 VL 分析结果文本

    Returns:
        增强后的 Prompt
    """
    if not analysis_text:
        return original_prompt

    return (
        f"{original_prompt}\n\n"
        f"--- Reference Analysis ---\n"
        f"{analysis_text}\n"
        f"--- End Reference ---\n\n"
        f"Please incorporate the visual style and key elements from the "
        f"reference analysis above while following the main prompt."
    )


async def _save_image_results(task_id: str, response) -> list[str]:
    """保存图片生成结果到本地存储.

    Args:
        task_id: 任务 ID（用于日志）
        response: AsyncOpenAI images.generate() 的响应对象

    Returns:
        保存后的本地 URL 列表
    """
    import aiofiles

    settings = get_settings()
    image_dir = Path(settings.storage_path).parent / "images"
    image_dir.mkdir(parents=True, exist_ok=True)

    image_urls: list[str] = []

    for item in response.data:
        # 优先处理 b64_json（OpenAI gpt-image-1 默认返回 base64）
        b64_data = getattr(item, "b64_json", None)
        if b64_data:
            filename = f"{uuid.uuid4().hex[:12]}.png"
            file_path = image_dir / filename
            image_bytes = base64.b64decode(b64_data)
            async with aiofiles.open(file_path, "wb") as f:
                await f.write(image_bytes)
            image_urls.append(f"/images/{filename}")
            continue

        # 回退处理 url（部分中转站返回 URL 而非 base64）
        url = getattr(item, "url", None)
        if url:
            # 下载到本地
            filename = f"{uuid.uuid4().hex[:12]}.png"
            file_path = image_dir / filename
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                async with aiofiles.open(file_path, "wb") as f:
                    await f.write(resp.content)
            image_urls.append(f"/images/{filename}")

    return image_urls


async def _submit_video_generation(
    rp: ResolvedProvider, params: dict
) -> dict:
    """向中转站提交视频生成请求.

    中转站通常兼容 OpenAI API 格式：
    POST {base_url}/videos/generations

    Returns:
        {"job_id": "...", "status": "queued/processing/failed", "error": "..."}
    """
    headers = {
        "Authorization": f"Bearer {rp.client.api_key}",
        "Content-Type": "application/json",
    }

    # 构建请求体（中转站格式）
    request_body = {"model": rp.model, **params}

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{rp.base_url}/videos/generations",
            headers=headers,
            json=request_body,
        )

        if resp.status_code not in (200, 201, 202):
            return {
                "status": "failed",
                "error": f"中转站返回 {resp.status_code}: {resp.text[:500]}",
            }

        data = resp.json()

    # 兼容多种返回格式
    job_id = (
        data.get("id")
        or data.get("job_id")
        or data.get("task_id")
    )
    status = data.get("status", "queued")

    return {"job_id": job_id, "status": status}


async def _poll_video_status(
    rp: ResolvedProvider,
    job_id: str,
    task_id: str,
) -> Optional[str]:
    """轮询中转站视频生成状态.

    中转站通常兼容 OpenAI API 格式：
    GET {base_url}/videos/generations/{job_id}

    Returns:
        视频 URL（成功时），None（超时或失败）
    """
    headers = {
        "Authorization": f"Bearer {rp.client.api_key}",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        for attempt in range(VIDEO_POLL_MAX_ATTEMPTS):
            await asyncio.sleep(VIDEO_POLL_INTERVAL)

            try:
                resp = await client.get(
                    f"{rp.base_url}/videos/generations/{job_id}",
                    headers=headers,
                )

                if resp.status_code != 200:
                    logger.warning(
                        "[%s] 轮询返回 %d: %s",
                        task_id, resp.status_code, resp.text[:200],
                    )
                    continue

                data = resp.json()
                status = data.get("status", "")

                if status in ("completed", "succeeded", "done"):
                    # 从多种可能的字段中提取视频 URL
                    video_url = (
                        data.get("video_url")
                        or data.get("url")
                        or data.get("output", {}).get("video_url")
                        or data.get("output", {}).get("url")
                        or data.get("result", {}).get("video_url")
                        or data.get("result", {}).get("url")
                    )
                    if video_url:
                        logger.info("[%s] 视频生成完成: attempt=%d",
                                    task_id, attempt + 1)
                        return video_url

                    # 某些中转站在 data 数组中返回
                    videos = data.get("data", [])
                    if videos and isinstance(videos, list):
                        for v in videos:
                            if isinstance(v, dict) and v.get("url"):
                                return v["url"]

                    logger.warning("[%s] 视频状态 completed 但未找到 URL: %s",
                                   task_id, json.dumps(data, ensure_ascii=False)[:300])

                elif status in ("failed", "error"):
                    error = data.get("error", {})
                    if isinstance(error, dict):
                        error_msg = error.get("message", str(error))
                    else:
                        error_msg = str(error)
                    raise RuntimeError(f"中转站视频生成失败: {error_msg}")

                elif status in ("queued", "processing", "running", "pending"):
                    if attempt % 12 == 0:  # 每分钟打一次日志
                        logger.info("[%s] 视频生成中: status=%s, attempt=%d/%d",
                                    task_id, status, attempt + 1,
                                    VIDEO_POLL_MAX_ATTEMPTS)
                else:
                    logger.warning("[%s] 未知的视频状态: %s", task_id, status)

            except httpx.HTTPError as e:
                logger.warning("[%s] 轮询 HTTP 错误: %s", task_id, str(e))

    return None  # 超时
