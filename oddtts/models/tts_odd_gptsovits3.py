# from gradio_client import Client, file

# client = Client("http://localhost:9872/")

# def to_speech_wav(text, language):
#     """
#     文本生成语音
#     """
#     # 根据输入语言决定输出语言
#     text_language = "多语种混合"
#     if language == "zh":
#         text_language = "中英混合"
#     elif language == "ja":
#         text_language = "日英混合"

#     # 参考音频的文本
#     with open('./resource/ref.txt', 'r', encoding='utf-8') as text_file:
#         prompt_text = text_file.read()

#     # 调用 GPT-SoVITS 推理API
#     result = client.predict(
#             ref_wav_path=file('./resource/ref.wav'),
#             prompt_text=prompt_text,
#             prompt_language="日文",
#             text=text,
#             text_language=text_language,
#             how_to_cut="凑四句一切",
#             top_k=15,
#             top_p=1,
#             temperature=1,
#             ref_free=False,
#             speed=1,
#             if_freeze=False,
#             inp_refs=[],
#             api_name="/get_tts_wav"
#     )
#     return result

# def to_speech_wav_gpt_sovits(text, language):
#     """
#     文本生成语音
#     """
#     # 根据输入语言决定输出语言
#     text_language = "多语种混合"
#     if language == "zh":
#         text_language = "中英混合"
#     elif language == "ja":
#         text_language = "日英混合"

#     # 参考音频的文本
#     with open('./resource/ref.txt', 'r', encoding='utf-8') as text_file:
#         prompt_text = text_file.read()

#     # 调用 GPT-SoVITS 推理API
#     result = client.predict(
#             ref_wav_path=file('./resource/ref.wav'),
#             prompt_text=prompt_text,
#             prompt_language="日文",
#             text=text,
#             text_language=text_language,
#             how_to_cut="凑四句一切",
#             top_k=15,
#             top_p=1,
#             temperature=1,
#             ref_free=False,
#             speed=1,
#             if_freeze=False,
#             inp_refs=[],
#             api_name="/get_tts_wav"
#     )
#     return result

# if __name__ == "__main__":
#     speech_wav = to_speech_wav('我是埃癸斯', 'zh')
#     print(speech_wav)
