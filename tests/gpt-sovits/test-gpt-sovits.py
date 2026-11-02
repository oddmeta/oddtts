import requests

base = "http://127.0.0.1:9880"
ref_path = "D:/lucy.wav"
prompt_text = "这个故事发生在第二次世界大战期间，他们为了躲避空袭逃离了伦敦。"
text = "我是小落同学，一个可以让你克隆另一个你自己的平台，我会为你提供以下服务"


# ========== 步骤 1：切换 SoVITS 权重 ==========
resp1 = requests.get(f"{base}/set_sovits_weights", params={
    "weights_path": "SoVITS_weights_v2Pro/lucy_e8_s112.pth"
    # 或某些版本用 "sovits_weights_path": "..."
})
print(f"set_sovits_weights: {resp1.status_code}, {resp1.text}")

# ========== 步骤 2：切换 GPT 权重 ==========
resp2 = requests.get(f"{base}/set_gpt_weights", params={
    "weights_path": "GPT_weights_v2Pro/lucy-e15.ckpt"
    # 或某些版本用 "gpt_weights_path": "..."
})
print(f"set_gpt_weights: {resp2.status_code}, {resp2.text}")

# ========== 步骤 3：合成语音 ==========
resp3 = requests.post(f"{base}/tts", json={
    "ref_audio_path": ref_path,
    "prompt_text": prompt_text,
    "prompt_lang": "zh",
    "text": text,
    "text_lang": "zh",
})

if resp3.status_code == 200:
    with open("output_finetuned.wav", "wb") as f:
        f.write(resp3.content)
    print(f"✅ 合成成功，{len(resp3.content)} bytes → output_finetuned.wav")
else:
    print(f"❌ 合成失败: {resp3.text[:500]}")