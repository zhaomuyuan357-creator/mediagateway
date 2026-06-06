"""动态 API 路由服务 — 基于 DB 配置的加权轮询 + 动态 AsyncOpenAI 实例化.

核心职责：
1. 从 api_providers 表读取 is_active=1 且 model_mapping 包含目标 task_type 的中转站
2. 按 weight 加权轮询选择一个
3. 从 model_mapping 取出对应模型名
4. 动态实例化 AsyncOpenAI(base_url=..., api_key=...)
"""
import logging
import random
from dataclasses import dataclass
from typing import Optional

from openai import AsyncOpenAI
from sqlalchemy.orm import Session

from ..models.api_provider import APIProvider
from ..services.encryption import get_encryption_service

logger = logging.getLogger(__name__)


@dataclass
class ResolvedProvider:
    """路由解析结果."""

    provider_id: int
    provider_name: str
    base_url: str
    model: str
    client: AsyncOpenAI


# ---------------------------------------------------------------------------
# 加权轮询状态（进程内维护，重启后重新从 DB 加载）
# ---------------------------------------------------------------------------

# 格式: {task_type: [(provider_id, weight, cumulative_weight), ...]}
_cumulative_weights: dict[str, list[tuple[int, int, int]]] = {}
# 格式: {task_type: last_used_cumulative_weight}
_last_pick: dict[str, int] = {}


def _build_weight_table(db: Session, task_type: str) -> list[tuple[int, int, int]]:
    """从 DB 加载指定 task_type 的活跃中转站，构建累积权重表。

    Returns:
        [(provider_id, weight, cumulative_weight), ...]
    """
    providers = (
        db.query(APIProvider)
        .filter(APIProvider.is_active == True)
        .all()
    )

    table: list[tuple[int, int, int]] = []
    cumulative = 0
    for p in providers:
        # model_mapping 的 key 就是支持的 task_type
        mapping = p.model_mapping or {}
        if task_type not in mapping:
            continue
        cumulative += max(p.weight, 1)
        table.append((p.id, max(p.weight, 1), cumulative))

    return table


def _weighted_round_robin(db: Session, task_type: str) -> Optional[int]:
    """加权轮询选择一个 provider_id。

    实现：累积权重区间 + 循环指针。
    每次调用向后移动指针，落在哪个区间就选哪个 provider。
    """
    table = _build_weight_table(db, task_type)
    if not table:
        return None

    total_weight = table[-1][2]  # 最后一个的累积权重 = 总权重

    # 获取上次 pick 位置，初始化为 -1
    last = _last_pick.get(task_type, -1)

    # 向后移动一个步长（最小步长 1）
    next_pick = (last + 1) % total_weight

    for provider_id, _, cumulative in table:
        if next_pick < cumulative:
            _last_pick[task_type] = next_pick
            return provider_id

    # fallback（理论上不会到这里）
    _last_pick[task_type] = 0
    return table[0][0]


# ---------------------------------------------------------------------------
# 公开接口
# ---------------------------------------------------------------------------


def resolve_provider(db: Session, task_type: str) -> ResolvedProvider:
    """根据 task_type 从 DB 路由到一个可用的中转站，返回动态实例化的客户端。

    Args:
        db: 数据库会话
        task_type: "image" / "video" / "analysis"

    Returns:
        ResolvedProvider 包含 provider 信息和已实例化的 AsyncOpenAI 客户端

    Raises:
        ValueError: 没有可用的中转站
    """
    provider_id = _weighted_round_robin(db, task_type)
    if provider_id is None:
        raise ValueError(f"没有可用的中转站支持 task_type={task_type}，请在「中转站管理」中添加配置")

    provider = db.query(APIProvider).filter(APIProvider.id == provider_id).first()
    if not provider:
        # DB 不一致，清除缓存重试
        _cumulative_weights.pop(task_type, None)
        _last_pick.pop(task_type, None)
        raise ValueError(f"中转站 ID={provider_id} 不存在或已被删除")

    # 解密 API Key
    encryption = get_encryption_service()
    api_key = encryption.decrypt(provider.encrypted_key)

    # 从 model_mapping 取模型名
    model = (provider.model_mapping or {}).get(task_type)
    if not model:
        raise ValueError(
            f"中转站「{provider.name}」的 model_mapping 中没有 {task_type} 对应的模型配置"
        )

    # 动态实例化 AsyncOpenAI
    client = AsyncOpenAI(
        base_url=provider.base_url,
        api_key=api_key,
    )

    logger.info(
        "路由 task_type=%s → 中转站「%s」(id=%d, base_url=%s, model=%s)",
        task_type, provider.name, provider.id, provider.base_url, model,
    )

    return ResolvedProvider(
        provider_id=provider.id,
        provider_name=provider.name,
        base_url=provider.base_url,
        model=model,
        client=client,
    )


def reload_weights(task_type: str = None):
    """清除缓存的权重表，下次调用时重新从 DB 加载。

    在中转站配置变更后调用。
    """
    if task_type:
        _cumulative_weights.pop(task_type, None)
        _last_pick.pop(task_type, None)
    else:
        _cumulative_weights.clear()
        _last_pick.clear()
