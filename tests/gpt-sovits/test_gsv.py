import requests

url = "http://127.0.0.1:9880/tts"
# url = "http://127.0.0.1:9872/tts"

# 参考音频路径（请确认文件存在）
ref_path = "D:/lucy.wav"
prompt_text = "这个故事发生在第二次世界大战期间，他们为了躲避空袭逃离了伦敦。"
text = "关注我的公众号：奥德元，一起学习 AI，一起追赶时代。"
text = "我是小落同学，一个可以让你克隆另一个你自己的平台，我会为你提供以下服务"

# 尝试两种常见的参数名组合
candidates = [
    # 方案 A：api_v2.py 常见参数名（你的版本大概率是这个）
    {
        "ref_audio_path": ref_path,
        "prompt_text": prompt_text,
        "prompt_lang": "zh",
        "text": text,
        "text_lang": "zh",
        "speed_factor": 1.2,  # ← 加上这个，1.0=正常语速，1.2=快一点，0.8=慢一点
    },
    # 方案 B：api.py 风格参数名
    {
        "refer_wav_path": ref_path,
        "prompt_text": prompt_text,
        "prompt_lang": "zh",
        "text": text,
        "text_language": "zh",
        "speed_factor": 1.2,  # ← 加上这个，1.0=正常语速，1.2=快一点，0.8=慢一点
    },
]

for i, payload in enumerate(candidates, 1):
    print(f"\n{'='*50}")
    print(f"尝试方案 {i}: {list(payload.keys())}")
    resp = requests.post(url, json=payload)
    print(f"状态码: {resp.status_code}")
    
    if resp.status_code == 200:
        size = len(resp.content)
        print(f"✅ 成功！响应大小: {size} bytes")
        with open(f"output_{i}.wav", "wb") as f:
            f.write(resp.content)
        print(f"✅ 音频已保存到 output_{i}.wav")
        break
    else:
        print(f"❌ 失败: {resp.text[:200]}")
else:
    print("\n所有方案都失败了。请检查：")
    print(f"1. 参考音频是否存在: {ref_path}")
    print("2. 访问 http://127.0.0.1:9880/docs 查看 Swagger 文档确认参数名")