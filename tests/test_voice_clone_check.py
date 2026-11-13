#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证音色克隆相关代码的完整性"""

import ast

# 验证 tts_moss_nano.py
with open('oddtts/models/tts_moss_nano.py', 'r', encoding='utf-8') as f:
    code = f.read()
ast.parse(code)
print('tts_moss_nano.py syntax OK')

assert 'def _resolve_voice_and_prompt' in code
assert 'prompt_audio_path' in code
assert 'get_voice_clone_manager' in code
assert 'ENGINE_NAME = "moss_nano"' in code
print('tts_moss_nano.py key logic OK')

# 验证 api.py
with open('oddtts/router/api.py', 'r', encoding='utf-8') as f:
    code2 = f.read()
ast.parse(code2)
print('api.py syntax OK')

assert '/api/voice/clone' in code2
assert 'api_clone_voice' in code2
assert 'api_list_cloned_voices' in code2
assert 'api_delete_cloned_voice' in code2
assert 'api_play_cloned_voice_audio' in code2
print('api.py key routes OK')

# 验证 oddtts_params.py
with open('oddtts/oddtts_params.py', 'r', encoding='utf-8') as f:
    code3 = f.read()
ast.parse(code3)
print('oddtts_params.py syntax OK')
assert 'prompt_audio_path' in code3
print('oddtts_params.py prompt_audio_path OK')

# 验证 index.html
with open('oddtts/templates/index.html', 'r', encoding='utf-8') as f:
    html = f.read()
assert 'voice-clone' in html
assert 'btn-clone-upload' in html
assert 'loadClonedVoices' in html
assert 'playClonedAudio' in html
assert 'deleteClonedVoice' in html
print('index.html key elements OK')

print('\nAll checks passed!')
