"""
Audio8 TTS 0.1B 测试程序
========================================
功能：
1. 自动下载 Audio8 TTS 0.1B 模型（ONNX INT8 / PyTorch）
2. 自动安装必要依赖
3. 使用 ONNX Runtime 进行语音合成（首选路径）
4. 提供 PyTorch 备选推理路径（当 ONNX 环境未就绪时）

模型信息：
- 参数规模：约 1.7 亿（主模型）+ 约 1.2 亿（解码器）
- 架构：DualAR（Slow AR + Fast AR）
- 采样率：44.1 kHz
- 支持语言：中文、粤语、英语、日语、韩语、法语、德语、
             西班牙语、意大利语、荷兰语、波兰语（共 11 种）
- 许可：Apache 2.0

使用说明：
- 首次运行会自动下载模型并安装依赖，请保持网络畅通
- 合成音频保存为 44.1kHz WAV 格式

作者：OddTTS Test Suite
日期：2026-08-28
"""

import os
import sys
import json
import time
import subprocess
import importlib.util

# ============================================================
# 配置常量
# ============================================================
ONNX_REPO_ID = os.environ.get("AUDIO8_ONNX_REPO_ID", "Audio8/audio8-TTS-0.1B-ONNX-INT8")
PYTORCH_REPO_ID = os.environ.get("AUDIO8_PYTORCH_REPO_ID", "Audio8/Audio8-TTS-Preview-0.1b")
MODEL_DIR = os.environ.get("AUDIO8_MODEL_DIR", "models/audio8-0.1b-onnx-int8")
OFFICIAL_REPO_URL = "https://github.com/Audio8-AI/Audio8_TTS.git"
OFFICIAL_REPO_DIR = "Audio8_TTS"
SAMPLE_RATE = 44100

TEST_TEXT_ZH = "欢迎使用 Audio8 TTS 语音合成系统。这是一段中文测试。"
TEST_TEXT_EN = "Welcome to Audio8 TTS. This is an English voice synthesis test."
TEST_TEXT_ZH_EN_MIXED = "Hello! 欢迎关注 OddTTS。一起学习 AI，一起追赶时代。Good good study, day day up!"


# ============================================================
# 1. 依赖检查与自动安装
# ============================================================
def ensure_dependencies():
    """确保必要的 Python 包已安装"""
    required = {
        "onnxruntime": "onnxruntime",
        "numpy": "numpy",
        "soundfile": "soundfile",
        "transformers": "transformers",
    }

    print("[依赖检查] 检查必要依赖...")
    for pkg_name, import_name in required.items():
        spec = importlib.util.find_spec(import_name.replace("-", "_"))
        if spec is None:
            print(f"[依赖检查] 未安装 {pkg_name}，正在安装...")
            try:
                subprocess.check_call(
                    [sys.executable, "-m", "pip", "install", pkg_name],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                print(f"[依赖检查] {pkg_name} 安装成功")
            except Exception as e:
                print(f"[依赖检查] {pkg_name} 安装失败: {e}")
                raise RuntimeError(f"无法安装依赖 {pkg_name}，请手动安装后重试") from e
        else:
            print(f"[依赖检查] {pkg_name} 已安装")

    if importlib.util.find_spec("torch") is None:
        print("[依赖检查] 未安装 torch，正在安装 CPU 版本...")
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "torch", "--index-url", "https://download.pytorch.org/whl/cpu"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            print("[依赖检查] torch 安装成功")
        except Exception as e:
            print(f"[依赖检查] torch 安装失败: {e}")
            raise

    print("[依赖检查] 所有依赖已就绪\n")


# ============================================================
# 2. 模型自动下载
# ============================================================
def download_onnx_model():
    """下载 Audio8 TTS 0.1B ONNX INT8 模型"""
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from oddtts.utils.model_utils import download_model

    print(f"[模型下载] 开始下载 ONNX INT8 模型: {ONNX_REPO_ID}")
    print(f"[模型下载] 目标目录: {os.path.abspath(MODEL_DIR)}")
    start_time = time.time()

    sources_to_try = ["huggingface", "modelscope"]
    last_error = None

    for src in sources_to_try:
        try:
            print(f"[模型下载] 尝试从 [{src}] 下载...")
            model_path = download_model(
                repo_id=ONNX_REPO_ID,
                local_dir=MODEL_DIR,
                source=src,
            )
            elapsed = time.time() - start_time
            print(f"[模型下载] 完成，耗时: {elapsed:.1f} 秒")
            print(f"[模型下载] 模型路径: {model_path}")
            return model_path
        except Exception as e:
            last_error = e
            print(f"[模型下载] [{src}] 下载失败: {e}")
            continue

    print(f"\n[模型下载] 所有下载源均失败。最后错误: {last_error}")
    return None


def verify_model_files(model_path):
    """验证 ONNX 模型关键文件是否存在"""
    print("\n[文件验证] 检查模型文件完整性...")

    expected_files = [
        "slow_ar_int8.onnx",
        "fast_ar_int8.onnx",
        "codec_decoder_fp16.onnx",
        "runtime_manifest.json",
        "tokenizer/tokenizer.json",
    ]

    all_ok = True
    for fname in expected_files:
        fpath = os.path.join(model_path, fname)
        if os.path.exists(fpath):
            size_mb = os.path.getsize(fpath) / (1024 * 1024)
            print(f"  [OK] {fname:<40} ({size_mb:>7.1f} MB)")
        else:
            print(f"  [MISSING] {fname}")
            all_ok = False

    if all_ok:
        print("[文件验证] 所有关键文件已就位\n")
    else:
        print("[文件验证] 部分文件缺失，可能影响推理\n")
    return all_ok


# ============================================================
# 3. 官方推理代码获取
# ============================================================
def setup_official_repo():
    """获取 Audio8 官方 GitHub 仓库（包含 0.1B ONNX Runtime 推理代码）"""
    print("[官方代码] 检查 Audio8 官方推理代码...")

    if os.path.exists(OFFICIAL_REPO_DIR):
        print(f"[官方代码] 本地仓库已存在: {OFFICIAL_REPO_DIR}")
        return OFFICIAL_REPO_DIR

    if importlib.util.find_spec("git") is None:
        try:
            subprocess.run(["git", "--version"], capture_output=True, check=True)
        except (FileNotFoundError, subprocess.CalledProcessError):
            print("[官方代码] 未找到 git 命令，跳过自动克隆")
            return None

    print(f"[官方代码] 正在克隆 {OFFICIAL_REPO_URL} ...")
    try:
        subprocess.check_call(
            ["git", "clone", "--depth", "1", OFFICIAL_REPO_URL, OFFICIAL_REPO_DIR],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        print(f"[官方代码] 克隆成功: {OFFICIAL_REPO_DIR}")
        return OFFICIAL_REPO_DIR
    except Exception as e:
        print(f"[官方代码] 克隆失败: {e}")
        return None


# ============================================================
# 4. ONNX 推理（首选路径）
# ============================================================
def test_onnx_inference(model_path, text, output_path):
    """
    使用 Audio8 官方 ONNX Runtime 代码进行语音合成

    使用 onnx_runtime_0_1b_int8 目录下的 ArkTtsRuntime，
    该 runtime 已适配 0.1B Falcon-H1/Mamba SSM 的聚合缓存格式。
    """
    print(f"\n[ONNX 推理] 尝试 ONNX Runtime 语音合成...")
    print(f"[ONNX 推理] 输入文本: {text[:60]}...")

    repo_dir = setup_official_repo()
    if repo_dir is None:
        print("[ONNX 推理] 未找到官方推理代码，跳过")
        return False

    # 0.1B 模型使用专门的 onnx_runtime_0_1b_int8 目录
    onnx_dir = os.path.join(repo_dir, "onnx_runtime_0_1b_int8")
    if not os.path.isdir(onnx_dir):
        print(f"[ONNX 推理] 未找到 0.1B Runtime 目录: {onnx_dir}")
        return False

    print(f"[ONNX 推理] 0.1B Runtime 目录: {onnx_dir}")

    if onnx_dir not in sys.path:
        sys.path.insert(0, onnx_dir)

    # 修复 Windows 下 Path.read_text() 默认使用 GBK 编码的问题
    import pathlib
    _original_read_text = pathlib.Path.read_text

    def _patched_read_text(self, encoding=None, errors=None):
        if encoding is None:
            encoding = "utf-8"
        return _original_read_text(self, encoding=encoding, errors=errors)

    pathlib.Path.read_text = _patched_read_text

    try:
        from arktts_runtime.runtime import ArkTtsRuntime
        import numpy as np
        import soundfile as sf

        # 使用模型自带的 reference_codes.npy 创建默认音色
        voices_dir = os.path.join(onnx_dir, "voices")
        default_voice_dir = os.path.join(voices_dir, "default_voice")
        os.makedirs(default_voice_dir, exist_ok=True)

        ref_codes_src = os.path.join(model_path, "reference_codes.npy")
        ref_codes_dst = os.path.join(default_voice_dir, "codes.npy")
        meta_path = os.path.join(default_voice_dir, "meta.json")

        if os.path.exists(ref_codes_src):
            if not os.path.exists(ref_codes_dst):
                import shutil
                shutil.copy2(ref_codes_src, ref_codes_dst)
                print("[ONNX 推理] 已复制内置参考音色 codes.npy")

            if not os.path.exists(meta_path):
                manifest_path = os.path.join(model_path, "runtime_manifest.json")
                ref_text = "Reference audio for voice cloning."
                try:
                    with open(manifest_path, "r", encoding="utf-8") as f:
                        manifest = json.load(f)
                    ref_text = manifest.get("reference_text", ref_text)
                except Exception:
                    pass
                with open(meta_path, "w", encoding="utf-8") as f:
                    json.dump(
                        {"name": "default_voice", "reference_text": ref_text},
                        f,
                        ensure_ascii=False,
                    )
                print("[ONNX 推理] 已创建默认音色 meta.json")
        else:
            print("[ONNX 推理] 警告: 未找到 reference_codes.npy，无法创建默认音色")
            return False

        print("[ONNX 推理] 初始化 ArkTtsRuntime (0.1B INT8)...")
        runtime = ArkTtsRuntime(
            model_dir=model_path,
            voices_dir=voices_dir,
        )
        print(f"[ONNX 推理] 采样率: {runtime.manifest['sample_rate']} Hz")

        print("[ONNX 推理] 开始合成...")
        audio, codes = runtime.synthesize(
            text=text,
            voice="default_voice",
            max_new_tokens=1024,
            temperature=0.7,
            top_p=0.9,
            top_k=50,
            seed=42,
        )
        sf.write(output_path, audio, int(runtime.manifest["sample_rate"]))
        print(f"[ONNX 推理] 合成成功: {output_path}")
        print(
            f"[ONNX 推理] 音频时长: {len(audio) / int(runtime.manifest['sample_rate']):.2f} 秒"
        )
        return True

    except Exception as e:
        print(f"[ONNX 推理] 失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        pathlib.Path.read_text = _original_read_text


# ============================================================
# 5. PyTorch 推理（备选路径）
# ============================================================
def test_pytorch_inference(text, output_path):
    """使用 transformers 加载 Audio8 TTS 0.1B PyTorch 版本进行语音合成"""
    print(f"\n[PyTorch 推理] 使用 PyTorch 版本进行语音合成...")
    print(f"[PyTorch 推理] 输入文本: {text[:60]}...")

    import transformers
    import torch
    import numpy as np
    import soundfile as sf

    tf_version = transformers.__version__
    tf_major = int(tf_version.split('.')[0])
    if tf_major >= 5:
        print(f"[PyTorch 推理] ⚠️ 当前 transformers 版本为 {tf_version}")
        print("[PyTorch 推理] Audio8 0.1B 需要 transformers >=4.57.0,<5")
        print(f"[PyTorch 推理] 解决方案: {sys.executable} -m pip install \"transformers>=4.57.0,<5\"")
        print("[PyTorch 推理] 跳过 PyTorch 推理")
        return False

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[PyTorch 推理] 使用设备: {device}")

    print(f"[PyTorch 推理] 正在加载模型: {PYTORCH_REPO_ID} ...")
    start_time = time.time()

    try:
        from transformers import AutoModel, AutoProcessor

        model = AutoModel.from_pretrained(
            PYTORCH_REPO_ID,
            trust_remote_code=True,
            torch_dtype=torch.float16 if device == "cuda" else torch.float32,
        ).to(device).eval()

        processor = AutoProcessor.from_pretrained(
            PYTORCH_REPO_ID,
            trust_remote_code=True,
        )

        load_time = time.time() - start_time
        print(f"[PyTorch 推理] 模型加载完成，耗时: {load_time:.1f} 秒")

        ref_codes_path = os.path.join(MODEL_DIR, "reference_codes.npy")
        if not os.path.exists(ref_codes_path):
            print(f"[PyTorch 推理] 未找到参考音色: {ref_codes_path}")
            return False

        print(f"[PyTorch 推理] 使用参考音色: {ref_codes_path}")

        ref_text = "Reference audio for voice cloning."
        manifest_path = os.path.join(MODEL_DIR, "runtime_manifest.json")
        if os.path.exists(manifest_path):
            try:
                with open(manifest_path, "r", encoding="utf-8") as f:
                    manifest = json.load(f)
                ref_text = manifest.get("reference_text", ref_text)
                print(f"[PyTorch 推理] 参考文本: {ref_text[:40]}...")
            except Exception:
                pass

        inputs = processor(
            text=text,
            reference_codes=ref_codes_path,
            reference_text=ref_text,
        )
        inputs = {k: v.to(device) for k, v in inputs.items()}

        audio_array = None

        if hasattr(model, "generate_audio"):
            print("[PyTorch 推理] 调用 model.generate_audio() ...")
            with torch.no_grad():
                waveforms, lengths, codes = model.generate_audio(**inputs)
                audio_array = waveforms[0].cpu().numpy()
                if audio_array.ndim > 1:
                    audio_array = audio_array.squeeze()
        elif hasattr(model, "generate"):
            print("[PyTorch 推理] 调用 model.generate() ...")
            with torch.no_grad():
                result = model.generate(**inputs)
                if hasattr(model, "decode_audio"):
                    waveforms, lengths = model.decode_audio(result)
                    audio_array = waveforms[0].cpu().numpy()
                    if audio_array.ndim > 1:
                        audio_array = audio_array.squeeze()
                else:
                    audio_array = _extract_audio(result)
        else:
            print("[PyTorch 推理] 未找到标准推理方法")
            return False

        if audio_array is not None:
            if isinstance(audio_array, torch.Tensor):
                audio_array = audio_array.detach().cpu().numpy()
            if audio_array.ndim > 1:
                audio_array = audio_array.squeeze()

            sf.write(output_path, audio_array, SAMPLE_RATE)
            print(f"[PyTorch 推理] 音频已保存: {output_path}")
            print(f"[PyTorch 推理] 音频时长: {len(audio_array) / SAMPLE_RATE:.2f} 秒")
            return True

    except Exception as e:
        print(f"[PyTorch 推理] 失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    return False


def _extract_audio(result):
    """从模型输出中提取音频数组"""
    if isinstance(result, tuple) and len(result) > 0:
        return result[0]
    if isinstance(result, dict):
        for key in ["audio", "wav", "waveform", "speech", "output"]:
            if key in result:
                return result[key]
    return result


# ============================================================
# 6. 主测试流程
# ============================================================
def main():
    print("=" * 60)
    print("Audio8 TTS 0.1B 测试程序")
    print("=" * 60)
    print()

    ensure_dependencies()

    model_path = download_onnx_model()
    if model_path:
        verify_model_files(model_path)

    print("=" * 60)
    print("开始语音合成测试")
    print("=" * 60)

    results = []

    # 测试 1: 中文
    output_zh = "output_audio8_zh.wav"
    print(f"\n--- 测试 1: 中文语音合成 ---")
    success = False
    if model_path:
        try:
            success = test_onnx_inference(model_path, TEST_TEXT_ZH, output_zh)
        except Exception as e:
            print(f"[测试 1] ONNX 推理异常: {e}")
    if not success:
        print("[测试 1] ONNX 路径未就绪，尝试 PyTorch 备选...")
        success = test_pytorch_inference(TEST_TEXT_ZH, output_zh)
    results.append(("中文", success, output_zh))

    # 测试 2: 英文
    output_en = "output_audio8_en.wav"
    print(f"\n--- 测试 2: 英文语音合成 ---")
    success = False
    if model_path:
        try:
            success = test_onnx_inference(model_path, TEST_TEXT_EN, output_en)
        except Exception as e:
            print(f"[测试 2] ONNX 推理异常: {e}")
    if not success:
        print("[测试 2] ONNX 路径未就绪，尝试 PyTorch 备选...")
        success = test_pytorch_inference(TEST_TEXT_EN, output_en)
    results.append(("英文", success, output_en))

    # 测试 3: 中英混合
    output_mixed = "output_audio8_mixed.wav"
    print(f"\n--- 测试 3: 中英混合语音合成 ---")
    success = False
    if model_path:
        try:
            success = test_onnx_inference(model_path, TEST_TEXT_ZH_EN_MIXED, output_mixed)
        except Exception as e:
            print(f"[测试 3] ONNX 推理异常: {e}")
    if not success:
        print("[测试 3] ONNX 路径未就绪，尝试 PyTorch 备选...")
        success = test_pytorch_inference(TEST_TEXT_ZH_EN_MIXED, output_mixed)
    results.append(("中英混合", success, output_mixed))

    # 测试报告
    print("\n" + "=" * 60)
    print("测试报告")
    print("=" * 60)
    for lang, success, path in results:
        status = "通过" if success else "未通过"
        print(f"  {lang:<10} {status:<10} {path}")

    print("\n" + "=" * 60)
    print("提示信息")
    print("=" * 60)
    if model_path:
        onnx_status = f"已下载到: {os.path.abspath(MODEL_DIR)}"
    else:
        onnx_status = "下载失败"

    print(f"""
1. ONNX INT8 模型状态: {onnx_status}
2. ONNX 推理使用 onnx_runtime_0_1b_int8 目录（适配 Falcon-H1/Mamba）
3. PyTorch 版本作为备选路径
4. 生成的音频采样率为 44.1 kHz（WAV 格式）
5. 环境变量配置：
   - AUDIO8_ONNX_REPO_ID: 自定义 ONNX 仓库 ID
   - AUDIO8_PYTORCH_REPO_ID: 自定义 PyTorch 仓库 ID
   - HF_ENDPOINT=https://hf-mirror.com: 使用 HuggingFace 镜像站
    """)

    print("=" * 60)
    print("Audio8 TTS 测试程序执行完毕")
    print("=" * 60)


if __name__ == "__main__":
    main()
