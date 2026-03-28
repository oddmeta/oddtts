import sys
import subprocess
import importlib.util
import argparse

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

        print(f"Running TTS engine: {config.oddtts_cfg['tts_type'].value}")
        print(f"Visit Web interface: http://{host}:{port}/")

        app.run(host=host, port=port, debug=config.Debug)
    except Exception as e:
        print(f"Failed to start application: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()