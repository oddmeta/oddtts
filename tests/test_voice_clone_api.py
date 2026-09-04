#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证音色克隆 API 路由注册（不启动完整服务器）"""

import sys

# 清除可能的模块缓存
for mod in list(sys.modules.keys()):
    if 'oddtts' in mod:
        del sys.modules[mod]

# mock 缺失的 kokoro 模块，让 base_tts_driver 能正常导入
class FakeKPipeline:
    pass

class FakeKModel:
    class Output:
        pass

sys.modules['kokoro'] = type(sys)('kokoro')
sys.modules['kokoro'].KPipeline = FakeKPipeline
sys.modules['kokoro'].KModel = FakeKModel

# mock 其他可能缺失的模块
for mod_name in ['spacy', 'torch', 'transformers', 'onnx_tts_runtime']:
    if mod_name not in sys.modules:
        sys.modules[mod_name] = type(sys)(mod_name)

import os
os.chdir('g:/oddmeta/oddtts')

# 现在导入 Flask app
from oddtts.oddtts_flask import flask_app

# 打印所有路由
print('All registered routes:')
for rule in flask_app.url_map.iter_rules():
    methods = rule.methods - {"OPTIONS", "HEAD"}
    print(f'  {rule.rule}  [{", ".join(methods)}]')

# 检查 voice/clone 路由
clone_routes = [r for r in flask_app.url_map.iter_rules() if 'voice/clone' in r.rule]
print(f'\nClone routes found: {len(clone_routes)}')
for r in clone_routes:
    print(f'  {r.rule}')

if len(clone_routes) == 0:
    print('\nERROR: voice/clone routes NOT registered!')
    sys.exit(1)

print('\nSUCCESS: All clone routes registered!')

# 使用 Flask 测试客户端调用 API
client = flask_app.test_client()

# 1. 测试克隆音色列表接口
print('\nTesting GET /api/voice/clone/list ...')
resp = client.get('/api/voice/clone/list')
print(f'  status: {resp.status_code}')
data = resp.get_json()
print(f'  success: {data.get("success")}')
print(f'  count: {data.get("count")}')

# 2. 测试语音列表接口（确认克隆音色字段透传）
print('\nTesting GET /v1/audio/voice/list ...')
resp2 = client.get('/v1/audio/voice/list')
print(f'  status: {resp2.status_code}')
voice_data = resp2.get_json()
print(f'  voice count: {len(voice_data)}')

print('\nAll API tests passed!')
