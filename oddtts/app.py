import sys
import subprocess
import importlib.util
import argparse
import asyncio
import os
import platform
import webbrowser
def _get_version() -> str:
    try:
        from importlib.metadata import version
        return version("oddtts")
    except Exception:
        try:
            import tomllib
            pyproject = os.path.join(os.path.dirname(__file__), "..", "pyproject.toml")
            with open(pyproject, "rb") as f:
                return tomllib.load(f)["project"]["version"]
        except Exception:
            return "unknown"

from oddtts.utils.model_utils import download_model, check_model_exists
from .oddtts_flask import flask_app
from . import oddtts_config as config

def install_required_packages():
    required_packages = [
        'flask',
        'flask_cors',
        'edge_tts'
    ]
    
    for package in required_packages:
        if importlib.util.find_spec(package.replace('_', '-')) is None:
            print(f"Installing {package}...")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", package])
                print(f"{package} installed successfully.")
            except Exception as e:
                print(f"Failed to install {package}: {e}")
                sys.exit(1)

def check_and_download_model(repo_id, local_dir):
    """
    检查模型是否存在，如果存在则下载到指定目录。
    支持 HuggingFace 和 ModelScope 双源自动切换。

    Args:
        repo_id (str): 模型仓库 ID，例如 "hexgrad/Kokoro-82M"。
        local_dir (str): 模型下载的本地目录。
    """
    print(f"正在检查模型: {repo_id}")
    try:
        # 检查模型是否存在（优先检查 ModelScope）
        if check_model_exists(repo_id, source="modelscope"):
            print(f"✅ 模型 '{repo_id}' 存在！")
        else:
            print(f"⚠️ 模型 '{repo_id}' 在 ModelScope 上未找到，尝试 HuggingFace...")

        # 使用通用接口下载，自动处理源切换
        print(f"开始下载模型到: {local_dir}")
        download_model(
            repo_id=repo_id,
            local_dir=local_dir,
            # resume_download=True,  # 支持断点续传
            # local_dir_use_symlinks=False # 避免符号链接问题
        )
        print("✅ 模型下载完成！")

    except Exception as e:
        # 捕获所有可能的错误：模型不存在、网络问题、依赖缺失等
        print(f"❌ 模型下载失败: {e}")


def main():
    # install_required_packages()
    
    parser = argparse.ArgumentParser(description='ODD TTS Application')
    parser.add_argument('--host', type=str, default=None, help='Host address (default: from config)')
    parser.add_argument('--port', type=int, default=None, help='Port number (default: from config)')
    
    args = parser.parse_args()
    
    try:

        asciiart = r"""
 OOO   dddd   dddd   M   M  eeeee  ttttt   aaaaa
O   O  d   d  d   d  MM MM  e        t    a     a
O   O  d   d  d   d  M M M  eeee     t    aaaaaaa
O   O  d   d  d   d  M   M  e        t    a     a
 OOO   dddd   dddd   M   M  eeeee    t    a     a

 ⭐️ Open Source: https://github.com/oddmeta/oddtts
 📖 Documentation: https://oddmeta.net/docs/oddtts"""
        
        print(asciiart)
        print(f" 📖 Version: {_get_version()}")

        host = args.host if args.host else config.HOST
        port = args.port if args.port else config.PORT

        print(f"Running TTS engine: {config.oddtts_cfg['tts_type'].name}")
        print(f"Visit Web interface: http://{host}:{port}/\n")

        # 1. 设置 Hugging Face 镜像地址 (国内用户推荐)
        os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

        # 2. 根据配置决定是否预加载模型
        if config.oddtts_cfg.get('preload_model', False):
            print("预加载模型已启用，开始预热...")
            try:
                from oddtts.router.api import single_tts_driver
                asyncio.run(single_tts_driver.preload())
                print("模型预加载完成")
            except Exception as e:
                print(f"模型预加载失败: {e}")
                print("程序将继续启动，模型将在首次请求时尝试加载。")

        if platform.system() == 'Windows':
            url = f"http://{host}:{port}/"
            import threading
            threading.Timer(1.5, lambda u=url: webbrowser.open(u)).start()

        flask_app.run(host=host, port=port, debug=config.Debug)
    except Exception as e:
        print(f"Failed to start application: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()