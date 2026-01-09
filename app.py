# g:\oddmeta\oddtts\oddtts\app.py
# run.py
import sys
import subprocess
import importlib.util
import argparse

def install_required_packages():
    required_packages = [
        'gradio',
        'fastapi',
        'uvicorn',
        'asyncio',
        'edge_tts'
    ]
    
    for package in required_packages:
        if importlib.util.find_spec(package) is None:
            print(f"Installing {package}...")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", package])
                print(f"{package} installed successfully.")
            except Exception as e:
                print(f"Failed to install {package}: {e}")
                sys.exit(1)


def main():
    install_required_packages()
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='ODD TTS Application')
    parser.add_argument('--host', type=str, default=None, help='Host address (default: from config)')
    parser.add_argument('--port', type=int, default=None, help='Port number (default: from config)')
    
    args = parser.parse_args()
    
    # 导入应用和配置 - 使用更明确的导入路径
    try:
        # 修改这里：直接从oddtts模块导入app对象
        from oddtts.oddtts import app
        import uvicorn
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

        # 使用命令行参数或默认配置
        host = args.host if args.host else config.HOST
        port = args.port if args.port else config.PORT
        
        # 使用直接导入的app对象
        uvicorn.run(
            app,
            host=host,
            port=port,
            reload=config.Debug
        )
    except Exception as e:
        print(f"Failed to start application: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()