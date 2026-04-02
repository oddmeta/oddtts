import sys
import subprocess
import importlib.util
import argparse
from huggingface_hub import HfApi, snapshot_download
from huggingface_hub.utils import RepositoryNotFoundError
import os

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
    
    Args:
        repo_id (str): Hugging Face 模型的 ID，例如 "hexgrad/Kokoro-82M"。
        local_dir (str): 模型下载的本地目录。
    """
    api = HfApi()
    
    print(f"正在检查模型: {repo_id}")
    try:
        # 尝试获取模型信息
        api.model_info(repo_id=repo_id)
        print(f"✅ 模型 '{repo_id}' 存在！")
        
        # 模型存在，开始下载
        print(f"开始下载模型到: {local_dir}")
        snapshot_download(
            repo_id=repo_id,
            local_dir=local_dir,
            resume_download=True,  # 支持断点续传
            local_dir_use_symlinks=False # 避免符号链接问题
        )
        print("✅ 模型下载完成！")
        
    except RepositoryNotFoundError:
        # 捕获模型不存在的错误
        print(f"❌ 错误：模型 '{repo_id}' 在 Hugging Face Hub 上不存在。")
        print("请检查模型 ID 是否拼写正确。")
    except Exception as e:
        # 捕获其他可能的错误，如网络问题
        print(f"❌ 发生未知错误: {e}")


def main():
    # install_required_packages()
    
    parser = argparse.ArgumentParser(description='ODD TTS Application')
    parser.add_argument('--host', type=str, default=None, help='Host address (default: from config)')
    parser.add_argument('--port', type=int, default=None, help='Port number (default: from config)')
    
    args = parser.parse_args()
    
    try:
        from oddtts.oddtts import app
        import oddtts.oddtts_config as config

        asciiart = r"""
 OOO   dddd   dddd   M   M  eeeee  ttttt   aaaaa
O   O  d   d  d   d  MM MM  e        t    a     a
O   O  d   d  d   d  M M M  eeee     t    aaaaaaa
O   O  d   d  d   d  M   M  e        t    a     a
 OOO   dddd   dddd   M   M  eeeee    t    a     a

 ⭐️ Open Source: https://github.com/oddmeta/oddtts
 📖 Documentation: https://docs.oddmeta.net/
        """
        
        print(asciiart)

        host = args.host if args.host else config.HOST
        port = args.port if args.port else config.PORT

        print(f"Running TTS engine: {config.oddtts_cfg['tts_type'].name}")
        print(f"Visit Web interface: http://{host}:{port}/")

        # 1. 设置 Hugging Face 镜像地址 (国内用户推荐)
        os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

        # # 2. 定义要检查的模型ID和本地保存路径
        # model_id = config.oddtts_cfg['local_repo_id']
        # download_path = config.oddtts_cfg['local_model_dir']
        # print(f"Local repo ID: {model_id}, Local model dir: {download_path}")

        # # 3. 执行检查和下载
        # check_and_download_model(model_id, download_path)

        app.run(host=host, port=port, debug=config.Debug)
    except Exception as e:
        print(f"Failed to start application: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()