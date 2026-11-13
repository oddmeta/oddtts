# g:\oddmeta\oddtts\oddtts\oddtts_log.py
import logging
import os
from logging.handlers import RotatingFileHandler

from oddtts.oddtts_config import log_file, log_path, log_level

def setup_logger(name=None):
    """
    设置并返回一个配置好的日志记录器
    
    Args:
        name: 日志记录器名称，如果为None则返回根日志记录器
    
    Returns:
        配置好的日志记录器
    """
    logger = logging.getLogger(name)
    
    # 避免重复添加处理器
    if logger.handlers:
        return logger
    
    # 设置日志级别
    logger.setLevel(log_level)
    
    # 防止日志传播到父日志记录器，避免重复输出
    logger.propagate = False
    
    # 创建日志格式
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 文件处理器
    if log_path and log_file:
        # 确保日志目录存在
        os.makedirs(log_path, exist_ok=True)
        
        log_file_path = os.path.join(log_path, log_file)
        file_handler = RotatingFileHandler(
            log_file_path,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger

# 创建默认日志记录器
logger = setup_logger('oddtts')

# 导出常用的日志函数
def debug(msg, *args, **kwargs):
    logger.debug(msg, *args, **kwargs)

def info(msg, *args, **kwargs):
    logger.info(msg, *args, **kwargs)

def warning(msg, *args, **kwargs):
    logger.warning(msg, *args, **kwargs)

def error(msg, *args, **kwargs):
    logger.error(msg, *args, **kwargs)

def critical(msg, *args, **kwargs):
    logger.critical(msg, *args, **kwargs)