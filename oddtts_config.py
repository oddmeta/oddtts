from oddtts.oddtts_params import ODDTTS_TYPE

## Flask server binding IP & port
HOST = "127.0.0.1"
PORT = 9001

## working mode - Debug mode: True/False， Release mode: False/True
Debug = False

oddtts_cfg = {
    ## load model and allocate memory on startup
    "preload_model": True,
    ## enable gpu
    "enable_gpu": False,
    ## disable stream mode TTS
    "disable_stream": False,
    ## concurrent threads, 0 auto detect CPU cores
    "concurrent_thread": 0,
    ## tts type
    "tts_type": ODDTTS_TYPE.ODDTTS_EDGETTS,
    ## HTTPS configuration
    "enable_https": False,
    "ssl_cert_path": "scripts/cert.pem",
    "ssl_key_path": "scripts/key.pem",
}

## db config
db_cfg = {
    "db_engine": "sqlite",
    "db_name": "oddtts.db",
    "db_user": "",
    "db_password": "",
    "db_host": "",
    "db_port": "",
}

## redis config
redis_cfg = {
    "redis_enabled": False,
    "redis_host": "127.0.0.1",
    "redis_port": 7379,
    "redis_password": "",
}

## log config
log_file = "oddtts.log"
log_path = "logs/"
log_level = 10 # 10-debug 20-info 30-warn 40-error 50-crit
