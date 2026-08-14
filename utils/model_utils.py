"""
通用模型下载工具模块
支持从 HuggingFace Hub 和 ModelScope 下载模型
"""

import os
import sys
import subprocess
import importlib.util
from typing import Optional

from oddtts_log import setup_logger

logger = setup_logger(__name__)

# 默认下载源优先级（auto 模式下依次尝试）
DEFAULT_SOURCE_PRIORITY = ["modelscope", "huggingface"]

# 环境变量键：控制默认下载源
ENV_MODEL_SOURCE = "ODDTTS_MODEL_SOURCE"


def _ensure_package(package_name: str, import_name: str = None) -> None:
    """确保指定包已安装，未安装则尝试自动安装"""
    check_name = (import_name or package_name).replace("-", "_")
    if importlib.util.find_spec(check_name) is None:
        logger.info(f"正在安装依赖包: {package_name} ...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])
            logger.info(f"{package_name} 安装成功")
        except Exception as e:
            logger.error(f"{package_name} 安装失败: {e}")
            raise RuntimeError(f"缺少必要依赖包: {package_name}，请手动安装") from e


def get_default_source() -> str:
    """获取默认下载源，优先从环境变量读取"""
    env_source = os.environ.get(ENV_MODEL_SOURCE, "").lower()
    if env_source in ("huggingface", "modelscope"):
        return env_source
    return "auto"


def download_model(
    repo_id: str,
    local_dir: Optional[str] = None,
    source: str = None,
    cache_dir: Optional[str] = None,
    **kwargs
) -> str:
    """
    通用模型下载接口，支持 HuggingFace 和 ModelScope

    Args:
        repo_id: 模型仓库 ID，如 "hexgrad/Kokoro-82M-v1.1-zh"
        local_dir: 下载到指定本地目录（可选）。若提供，模型文件会被复制/链接到此目录
        source: 下载源，可选值:
            - None / "auto": 自动尝试，默认先 HuggingFace 后 ModelScope
            - "huggingface": 仅从 HuggingFace 下载
            - "modelscope": 仅从 ModelScope 下载
            也可通过环境变量 ODDTTS_MODEL_SOURCE 全局设置
        cache_dir: 缓存目录（可选）
        **kwargs: 额外参数，透传给底层下载函数

    Returns:
        模型本地绝对路径

    Raises:
        RuntimeError: 所有下载源均失败时抛出
    """
    if source is None:
        source = get_default_source()

    if source not in ("auto", "huggingface", "modelscope"):
        raise ValueError(
            f"不支持的下载源: {source}，可选: auto, huggingface, modelscope"
        )

    sources = []
    if source == "auto":
        sources = DEFAULT_SOURCE_PRIORITY.copy()
    else:
        sources = [source]

    last_error = None

    for src in sources:
        try:
            if src == "huggingface":
                return _download_from_huggingface(repo_id, local_dir, cache_dir, **kwargs)
            elif src == "modelscope":
                return _download_from_modelscope(repo_id, local_dir, cache_dir, **kwargs)
        except Exception as e:
            last_error = e
            logger.warning(f"[{src}] 下载失败: {e}")
            continue

    raise RuntimeError(
        f"模型 {repo_id} 下载失败，已尝试源: {sources}。最后错误: {last_error}"
    )


def _download_from_huggingface(
    repo_id: str,
    local_dir: Optional[str] = None,
    cache_dir: Optional[str] = None,
    **kwargs
) -> str:
    """从 HuggingFace Hub 下载模型"""
    _ensure_package("huggingface-hub", "huggingface_hub")

    from huggingface_hub import snapshot_download

    download_kwargs = {"repo_id": repo_id}
    if local_dir:
        download_kwargs["local_dir"] = local_dir
    if cache_dir:
        download_kwargs["cache_dir"] = cache_dir

    # 透传额外参数（如 resume_download 等）
    for key in ("resume_download", "local_dir_use_symlinks"):
        if key in kwargs:
            download_kwargs[key] = kwargs[key]

    logger.info(f"[HuggingFace] 开始下载模型: {repo_id}")
    model_path = snapshot_download(**download_kwargs)
    logger.info(f"[HuggingFace] 模型下载完成: {model_path}")
    return model_path


def _download_from_modelscope(
    repo_id: str,
    local_dir: Optional[str] = None,
    cache_dir: Optional[str] = None,
    **kwargs
) -> str:
    """从 ModelScope 下载模型"""
    _ensure_package("modelscope")

    from modelscope import snapshot_download

    download_kwargs = {"model_id": repo_id}
    if local_dir:
        download_kwargs["local_dir"] = local_dir
    if cache_dir:
        download_kwargs["cache_dir"] = cache_dir

    for key in ("revision",):
        if key in kwargs:
            download_kwargs[key] = kwargs[key]

    logger.info(f"[ModelScope] 开始下载模型: {repo_id}")
    model_path = snapshot_download(**download_kwargs)
    logger.info(f"[ModelScope] 模型下载完成: {model_path}")
    return model_path


def check_model_exists(repo_id: str, source: str = "huggingface") -> bool:
    """
    检查模型在指定源上是否存在

    Args:
        repo_id: 模型仓库 ID
        source: 检查源，"huggingface" 或 "modelscope"

    Returns:
        是否存在
    """
    try:
        if source == "huggingface":
            _ensure_package("huggingface-hub", "huggingface_hub")
            from huggingface_hub import HfApi

            api = HfApi()
            api.model_info(repo_id=repo_id)
            return True
        elif source == "modelscope":
            _ensure_package("modelscope")
            from modelscope.hub.api import HubApi

            hub_api = HubApi()
            hub_api.get_model_info(repo_id)
            return True
        else:
            raise ValueError(f"不支持的源: {source}")
    except Exception as e:
        logger.debug(f"[{source}] 模型 {repo_id} 不存在或检查失败: {e}")
        return False
