# run.py
import sys
import subprocess
import importlib.util

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

if __name__ == "__main__":
    install_required_packages()
    
    # Now run the main application
    try:
        from oddtts import app
        import uvicorn
        import oddtts_config as config

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

        # 移除了自定义信号处理器，让uvicorn处理信号
        uvicorn.run(
            "oddtts:app",
            host=config.HOST,
            port=config.PORT,
            reload=config.Debug
        )
    except Exception as e:
        print(f"Failed to start application: {e}")
        sys.exit(1)