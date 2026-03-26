import requests
from openai import OpenAI

base_url = "http://localhost:9001/v1"
model = "oddtts-1"
api_key = "dummy"

voice = "zh-HK-WanLungNeural"
voice = "zh-CN-YunxiaNeural"
voice = "zh-CN-XiaoxiaoNeural"
voice = "zh-CN-XiaoyiNeural"

text = "欢迎关注我的公众号: 奥德元。一起学习AI，一起追赶时代！Good good study, day day up!"


def test_openai_tts_api(voice_id):
    print("测试生成TTS音频(文件) API")
    client = OpenAI(
        api_key=api_key,
        base_url=base_url
    )

    response = client.audio.speech.create(
        model=model,
        input=text,
        voice=voice_id,
        response_format="mp3"
    )
    response.write_to_file("output.mp3")

def get_voice_details(voice_id):
    print("测试获取指定语音的详细信息")
    try:
        # 明确指定完整URL
        response = requests.get(f"{base_url}/audio/voice/list/{voice_id}")
        print(f"请求URL: {base_url}/audio/voice/list/{voice_id}")
        print(f"响应状态码: {response.status_code}")
        
        response.raise_for_status()
        
        voice_details = response.json()
        print(f"成功获取 {voice_details}")
        
        return voice_details
    
    except requests.exceptions.HTTPError as e:
        if response.status_code == 404:
            print("测试失败: 接口不存在，请检查服务端是否正确实现了该API")
            # 尝试获取服务器上所有可用的接口信息
            try:
                response = requests.get(f"{API_BASE_URL}/docs")
                if response.status_code == 200:
                    print("提示: 你可以访问以下地址查看可用API文档:")
                    print(f"{API_BASE_URL}/docs")
            except:
                pass
        else:
            print(f"测试失败: {str(e)}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"测试失败: {str(e)}")
        return None


def get_voices():
    print("测试获取所有语音选项")
    try:
        # 明确指定完整URL
        response = requests.get(f"{base_url}/audio/voice/list")
        print(f"请求URL: {base_url}/audio/voice/list")
        print(f"响应状态码: {response.status_code}")
        
        response.raise_for_status()
        
        voices = response.json()
        print(f"成功获取 {len(voices)} 个语音选项")
        
        # 打印前5个语音的信息
        print("\n前5个可用语音:")
        for i, voice in enumerate(voices[:5]):
            print(f"{i+1}. 名称: {voice.get('name')}")
            print(f"   语言: {voice.get('locale')}")
            print(f"   性别: {voice.get('gender')}")
            print(f"   语音ID: {voice.get('short_name')}\n")
        
        return voices
    
    except requests.exceptions.HTTPError as e:
        if response.status_code == 404:
            print("测试失败: 接口不存在，请检查服务端是否正确实现了该API")
            # 尝试获取服务器上所有可用的接口信息
            try:
                response = requests.get(f"{API_BASE_URL}/docs")
                if response.status_code == 200:
                    print("提示: 你可以访问以下地址查看可用API文档:")
                    print(f"{API_BASE_URL}/docs")
            except:
                pass
        else:
            print(f"测试失败: {str(e)}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"测试失败: {str(e)}")
        return None

if __name__ == "__main__":
    get_voices()
    get_voice_details(voice)
    test_openai_tts_api(voice)
