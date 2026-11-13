#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VoiceCloneManager 独立测试脚本"""

import importlib.util
import sys
import os

# 直接加载 manager.py，绕过 oddtts 包的级联导入
spec = importlib.util.spec_from_file_location('vc_manager', 'oddtts/voice_clone/manager.py')
mod = importlib.util.module_from_spec(spec)

# 模拟 oddtts_log 模块
class FakeLogger:
    def info(self, *a, **k): pass
    def warning(self, *a, **k): pass
    def error(self, *a, **k): pass

fake_log_mod = type(sys)('oddtts.oddtts_log')
fake_log_mod.setup_logger = lambda name: FakeLogger()
sys.modules['oddtts'] = type(sys)('oddtts')
sys.modules['oddtts.oddtts_log'] = fake_log_mod

spec.loader.exec_module(mod)
print('manager module loaded OK')

manager = mod.VoiceCloneManager('g:/oddmeta/oddtts/voices')
print(f'voices_root: {manager.voices_root}')

voices = manager.list_voices()
print(f'current cloned voices count: {len(voices)}')

# 找一个测试音频
test_audio = 'tests/test_tts_file_zh_HK_HiuG.mp3'
if os.path.exists(test_audio):
    meta = manager.save_voice('moss_nano', 'test_voice', 'TestVoice', test_audio, 'zh-CN', 'Male')
    print(f'save_voice OK: voice_id={meta["voice_id"]}, display_name={meta["display_name"]}')

    voices = manager.list_voices('moss_nano')
    print(f'after save moss_nano count: {len(voices)}')
    print(f'voice info: {voices[0]}')

    ap = manager.get_audio_path('moss_nano', 'test_voice')
    print(f'audio_path: {ap}')
    print(f'audio exists: {os.path.exists(ap)}')

    manager.delete_voice('moss_nano', 'test_voice')
    print('delete_voice OK')

    voices = manager.list_voices('moss_nano')
    print(f'after delete moss_nano count: {len(voices)}')
else:
    print(f'test audio not found: {test_audio}')
