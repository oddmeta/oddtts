#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MOSS-TTS-Nano 0.1B ONNX 测试程序
================================
功能：
1. 自动克隆 MOSS-TTS-Nano 官方仓库（如未安装）
2. 自动安装项目依赖
3. 自动下载 ONNX 模型（首次运行时从 HuggingFace 拉取）
4. 使用 ONNX 后端进行语音合成测试：
   - 基础语音合成（无参考音频）
   - 语音克隆（使用参考音频）
   - 多语言语音合成
   - CLI 工具调用测试

模型信息：
- 参数规模：0.1B（约 1 亿参数）
- 架构：Audio Tokenizer + LLM 纯自回归
- 采样率：48 kHz 立体声
- 支持语言：中文、英语、日语、韩语等近 20 种
- ONNX 模型：
  * ModelScope: openmoss/MOSS-TTS-Nano-100M-ONNX
  * ModelScope: openmoss/MOSS-Audio-Tokenizer-Nano-ONNX
  * HuggingFace: OpenMOSS-Team/MOSS-TTS-Nano-100M-ONNX
  * HuggingFace: OpenMOSS-Team/MOSS-Audio-Tokenizer-Nano-ONNX
- 许可：Apache 2.0

使用说明：
- 首次运行会自动克隆仓库并下载模型，请保持网络畅通
- 生成的音频保存为 48kHz WAV 格式
- 测试输出目录：tests/output_moss_tts/

作者：OddTTS Test Suite
日期：2026-09-03
"""

import os
import sys
import time
import shutil
import subprocess
import glob

# 允许从 tests 目录导入 oddtts 包
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from oddtts.utils.model_utils import download_model
except Exception:
    download_model = None

# ============================================================
# 配置常量
# ============================================================
REPO_URL = "https://github.com/OpenMOSS/MOSS-TTS-Nano.git"
REPO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "moss-tts-nano")
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output_moss_tts")

# 测试文本
TEST_TEXT_ZH = "欢迎关注我的公众号：奥德元。一起学习AI，一起追赶时代。Good good study, day day up."
TEST_TEXT_EN = "Welcome to follow my official account: OddMeta. Let's learn AI together and keep up with the times. Good good study, day day up"
TEST_TEXT_JA = "私の公式アカウント「奥德元」をフォローしてください。一緒にAIを学び、時代に追いつきましょう。Good good study, day day up"
TEST_TEXT_KO = "제 공식 계정 '오드원'을 팔로우해 주세요. 함께 AI를 배우고 시대를 따라잡아요. Good good study, day day up."

SAMPLE_RATE = 48000


# ============================================================
# 工具函数
# ============================================================
def run_cmd(cmd, cwd=None, timeout=300, check=True):
    """运行命令并返回结果"""
    print(f"[CMD] {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    if isinstance(cmd, str):
        cmd = cmd.split()
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
        )
        if result.returncode != 0 and check:
            print(f"[ERROR] 命令失败 (code={result.returncode}):")
            print(result.stderr)
            return None
        return result
    except subprocess.TimeoutExpired:
        print(f"[ERROR] 命令超时 ({timeout}s)")
        return None
    except Exception as e:
        print(f"[ERROR] 命令异常: {e}")
        return None


def ensure_repo():
    """确保 MOSS-TTS-Nano 仓库已克隆"""
    if os.path.isdir(os.path.join(REPO_DIR, ".git")):
        print(f"[仓库] 已存在: {REPO_DIR}")
        return True

    print(f"[仓库] 开始克隆: {REPO_URL}")
    print(f"[仓库] 目标目录: {REPO_DIR}")
    start_time = time.time()

    result = run_cmd(
        ["git", "clone", "--depth", "1", REPO_URL, REPO_DIR],
        check=False,
        timeout=120,
    )
    if result is None or result.returncode != 0:
        print("[仓库] Git 克隆失败，尝试使用 ghproxy 镜像...")
        mirror_url = f"https://ghproxy.com/{REPO_URL}"
        result = run_cmd(
            ["git", "clone", "--depth", "1", mirror_url, REPO_DIR],
            check=False,
            timeout=120,
        )
        if result is None or result.returncode != 0:
            print("[仓库] 克隆失败，请手动克隆仓库到:")
            print(f"  git clone {REPO_URL} {REPO_DIR}")
            return False

    elapsed = time.time() - start_time
    print(f"[仓库] 克隆完成，耗时: {elapsed:.1f} 秒")
    return True


def _is_windows() -> bool:
    return sys.platform.startswith("win")


def _ensure_pynini_on_windows():
    """Windows 上通过 conda-forge 安装预编译 pynini，避免 MSVC 编译失败"""
    if not _is_windows():
        return True

    try:
        import pynini
        print("[依赖] pynini 已安装")
        return True
    except ImportError:
        pass

    print("[依赖] Windows 检测到，尝试通过 conda 安装预编译 pynini...")
    result = run_cmd(
        ["conda", "install", "-c", "conda-forge", "pynini=2.1.6.post1", "-y"],
        timeout=180,
        check=False,
    )
    if result is not None and result.returncode == 0:
        print("[依赖] conda 安装 pynini 成功")
        return True

    print("[警告] conda 安装 pynini 失败，WeTextProcessing 可能无法编译")
    return False


def _install_onnx_only_deps():
    """安装 ONNX 推理所需的最小依赖（含 WeTextProcessing）"""
    onnx_deps = [
        "numpy>=1.24",
        "soundfile",
        "onnxruntime>=1.20.0",
        "fastapi>=0.110.0",
        "uvicorn>=0.29.0",
        "python-multipart>=0.0.9",
        "sentencepiece>=0.1.99",
        "WeTextProcessing>=1.0.4.1",
    ]
    print("[依赖] 安装 ONNX 依赖包...")
    for dep in onnx_deps:
        run_cmd([sys.executable, "-m", "pip", "install", dep], timeout=120, check=False)


def ensure_dependencies():
    """安装 MOSS-TTS-Nano ONNX 最小依赖（跳过 PyTorch/transformers）"""
    print("[依赖] 检查并安装 ONNX 最小依赖...")

    # 检查 moss-tts-nano 是否已安装
    result = run_cmd([sys.executable, "-m", "moss_tts_nano", "--help"], check=False, timeout=10)
    if result is not None and result.returncode == 0:
        print("[依赖] moss-tts-nano 已安装")
        return True

    if not os.path.isdir(REPO_DIR):
        print("[依赖] 仓库不存在，无法安装依赖")
        return False

    # Windows 预安装 pynini（WeTextProcessing 的编译依赖）
    _ensure_pynini_on_windows()

    # 安装 ONNX 依赖（含 WeTextProcessing）
    _install_onnx_only_deps()

    # 安装项目本身（entrypoints）
    print("[依赖] 安装 moss-tts-nano 包...")
    result = run_cmd(
        [sys.executable, "-m", "pip", "install", "-e", REPO_DIR],
        timeout=180,
        check=False,
    )
    if result is None or result.returncode != 0:
        print("[依赖] pip install -e . 失败")
        return False

    print("[依赖] 安装完成")
    return True


def download_onnx_models():
    """优先从 ModelScope 下载 ONNX 模型，失败则回退 HuggingFace"""
    if download_model is None:
        print("[模型下载] 无法导入 oddtts.utils.model_utils.download_model，跳过预下载")
        print("[模型下载] 将依赖 infer_onnx.py 运行时自动从 HuggingFace 下载")
        return False

    models_dir = os.path.join(REPO_DIR, "models")
    os.makedirs(models_dir, exist_ok=True)

    # ModelScope 与 HuggingFace 的命名空间不同，分别指定
    model_repos = [
        {
            "local_name": "MOSS-TTS-Nano-100M-ONNX",
            "modelscope_id": "openmoss/MOSS-TTS-Nano-100M-ONNX",
            "huggingface_id": "OpenMOSS-Team/MOSS-TTS-Nano-100M-ONNX",
        },
        {
            "local_name": "MOSS-Audio-Tokenizer-Nano-ONNX",
            "modelscope_id": "openmoss/MOSS-Audio-Tokenizer-Nano-ONNX",
            "huggingface_id": "OpenMOSS-Team/MOSS-Audio-Tokenizer-Nano-ONNX",
        },
    ]

    all_success = True
    for repo_info in model_repos:
        local_name = repo_info["local_name"]
        local_path = os.path.join(models_dir, local_name)
        if os.path.isdir(local_path) and any(os.scandir(local_path)):
            print(f"[模型下载] {local_name} 已存在，跳过")
            continue

        print(f"\n[模型下载] 目标: {local_name}")
        start_time = time.time()
        downloaded = False

        # 1. 优先尝试 ModelScope
        try:
            print(f"[模型下载] 尝试 ModelScope: {repo_info['modelscope_id']}")
            download_model(
                repo_id=repo_info["modelscope_id"],
                local_dir=local_path,
                source="modelscope",
            )
            downloaded = True
            print(f"[模型下载] ModelScope 下载成功")
        except Exception as e:
            print(f"[模型下载] ModelScope 失败: {e}")

        # 2. 回退 HuggingFace
        if not downloaded:
            try:
                print(f"[模型下载] 尝试 HuggingFace: {repo_info['huggingface_id']}")
                download_model(
                    repo_id=repo_info["huggingface_id"],
                    local_dir=local_path,
                    source="huggingface",
                )
                downloaded = True
                print(f"[模型下载] HuggingFace 下载成功")
            except Exception as e:
                print(f"[模型下载] HuggingFace 失败: {e}")

        if downloaded:
            elapsed = time.time() - start_time
            print(f"[模型下载] {local_name} 下载完成，耗时: {elapsed:.1f} 秒")
            print(f"[模型下载] 保存路径: {local_path}")
        else:
            print(f"[模型下载] {local_name} 所有下载源均失败")
            all_success = False

    return all_success


def get_reference_audio():
    """获取仓库自带的参考音频路径"""
    ref_path = os.path.join(REPO_DIR, "assets", "audio", "zh_1.wav")
    if os.path.exists(ref_path):
        return ref_path
    # 尝试查找其他参考音频
    patterns = [
        os.path.join(REPO_DIR, "assets", "audio", "*.wav"),
        os.path.join(REPO_DIR, "examples", "*.wav"),
    ]
    for pattern in patterns:
        files = glob.glob(pattern)
        if files:
            return files[0]
    return None


def find_output_wav(search_dir, prefix=""):
    """在目录中查找最新生成的 wav 文件"""
    wav_files = glob.glob(os.path.join(search_dir, "**", "*.wav"), recursive=True)
    if prefix:
        wav_files = [f for f in wav_files if prefix in os.path.basename(f)]
    if not wav_files:
        return None
    # 返回最新修改的文件
    return max(wav_files, key=os.path.getmtime)


def _print_debug_files(search_dir):
    """打印目录下的文件列表，用于调试输出文件定位问题"""
    print(f"[DEBUG] {search_dir} 下的文件列表:")
    for root, dirs, files in os.walk(search_dir):
        level = root.replace(search_dir, "").count(os.sep)
        indent = " " * 2 * level
        print(f"{indent}{os.path.basename(root)}/")
        sub_indent = " " * 2 * (level + 1)
        for f in files[:10]:  # 最多显示 10 个文件
            fp = os.path.join(root, f)
            size = os.path.getsize(fp)
            print(f"{sub_indent}{f} ({size / 1024:.1f} KB)")
        if len(files) > 10:
            print(f"{sub_indent}... 还有 {len(files) - 10} 个文件")


def detect_infer_onnx_args():
    """探测 infer_onnx.py 支持的命令行参数"""
    infer_script = os.path.join(REPO_DIR, "infer_onnx.py")
    if not os.path.exists(infer_script):
        return set()

    result = run_cmd(
        [sys.executable, infer_script, "--help"],
        cwd=REPO_DIR,
        check=False,
        timeout=15,
    )
    if result is None:
        return set()

    help_text = result.stdout + result.stderr
    args = set()
    if "--output" in help_text:
        args.add("output")
    if "--prompt-audio-path" in help_text:
        args.add("prompt-audio-path")
    if "--model-dir" in help_text:
        args.add("model-dir")
    return args


def detect_cli_args():
    """探测 CLI 支持的命令行参数"""
    result = run_cmd(
        [sys.executable, "-m", "moss_tts_nano", "generate", "--help"],
        check=False,
        timeout=15,
    )
    if result is None:
        return set()

    help_text = result.stdout + result.stderr
    args = set()
    if "--output" in help_text:
        args.add("output")
    if "--prompt-speech" in help_text:
        args.add("prompt-speech")
    if "--backend" in help_text:
        args.add("backend")
    return args


def copy_output_to(src_path, dst_name):
    """复制输出文件到测试输出目录"""
    if not src_path or not os.path.exists(src_path):
        return None
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    dst_path = os.path.join(OUTPUT_DIR, dst_name)
    shutil.copy2(src_path, dst_path)
    print(f"[输出] 已复制到: {dst_path}")
    return dst_path


def _get_audio_duration(path):
    """获取音频文件时长（秒），失败返回 0.0"""
    if not path or not os.path.exists(path):
        return 0.0
    try:
        import soundfile as sf
        info = sf.info(path)
        return info.duration
    except Exception:
        return 0.0


# ============================================================
# 测试项
# ============================================================
def test_onnx_basic():
    """测试 1: ONNX 基础语音合成（无参考音频）"""
    print("\n" + "=" * 60)
    print("测试 1: ONNX 基础语音合成")
    print("=" * 60)

    infer_script = os.path.join(REPO_DIR, "infer_onnx.py")
    if not os.path.exists(infer_script):
        print("[跳过] 未找到 infer_onnx.py")
        return False, 0.0, 0.0

    supported_args = detect_infer_onnx_args()
    print(f"[探测] infer_onnx.py 支持参数: {supported_args}")

    # 清理之前的生成结果，避免混淆
    gen_dir = os.path.join(REPO_DIR, "generated_audio")
    if os.path.isdir(gen_dir):
        for f in glob.glob(os.path.join(gen_dir, "*.wav")):
            os.remove(f)

    cmd = [sys.executable, infer_script]
    if "model-dir" in supported_args:
        cmd.extend(["--model-dir", os.path.join(REPO_DIR, "models")])
    if "output" in supported_args:
        output_path = os.path.join(OUTPUT_DIR, "test_onnx_basic.wav")
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        cmd.extend(["--output", output_path])
    cmd.extend(["--text", TEST_TEXT_ZH])

    start_time = time.time()
    result = run_cmd(cmd, cwd=REPO_DIR, check=False, timeout=300)
    elapsed = time.time() - start_time

    if result is None or result.returncode != 0:
        print(f"[测试 1] ONNX 基础合成失败")
        if result and result.stderr:
            print(f"[DEBUG] stderr:\n{result.stderr[:800]}")
        if result and result.stdout:
            print(f"[DEBUG] stdout:\n{result.stdout[:800]}")
        return False, elapsed, 0.0

    print(f"[测试 1] 合成完成，耗时: {elapsed:.1f} 秒")

    # 查找输出文件
    if "output" in supported_args:
        output_path = os.path.join(OUTPUT_DIR, "test_onnx_basic.wav")
    else:
        output_path = find_output_wav(REPO_DIR)
        output_path = copy_output_to(output_path, "test_onnx_basic.wav")

    if output_path and os.path.exists(output_path):
        size_mb = os.path.getsize(output_path) / 1024 / 1024
        duration = _get_audio_duration(output_path)
        print(f"[测试 1] 输出文件: {output_path} ({size_mb:.2f} MB, {duration:.2f}s)")
        return True, elapsed, duration
    else:
        print("[测试 1] 未找到输出音频文件")
        # 打印调试信息帮助定位
        _print_debug_files(REPO_DIR)
        return False, elapsed, 0.0


def test_onnx_speed_mode():
    """测试 1b: ONNX 极速模式（greedy + 多线程 + 关闭预处理）"""
    print("\n" + "=" * 60)
    print("测试 1b: ONNX 极速模式")
    print("=" * 60)
    print("[极速] 参数: sample-mode=greedy, do-sample=0, 关闭 WeTextProcessing")

    infer_script = os.path.join(REPO_DIR, "infer_onnx.py")
    if not os.path.exists(infer_script):
        print("[跳过] 未找到 infer_onnx.py")
        return False, 0.0, 0.0

    supported_args = detect_infer_onnx_args()
    cpu_threads = min(os.cpu_count() or 4, 8)
    print(f"[极速] CPU 线程数: {cpu_threads}")

    # 清理之前的生成结果，避免混淆
    gen_dir = os.path.join(REPO_DIR, "generated_audio")
    if os.path.isdir(gen_dir):
        for f in glob.glob(os.path.join(gen_dir, "*.wav")):
            os.remove(f)

    cmd = [sys.executable, infer_script]
    if "model-dir" in supported_args:
        cmd.extend(["--model-dir", os.path.join(REPO_DIR, "models")])
    if "output" in supported_args:
        output_path = os.path.join(OUTPUT_DIR, "test_onnx_speed.wav")
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        cmd.extend(["--output", output_path])
    cmd.extend([
        "--text", TEST_TEXT_ZH,
        "--sample-mode", "greedy",
        "--do-sample", "0",
        "--cpu-threads", str(cpu_threads),
        "--enable-wetext-processing", "0",
    ])

    start_time = time.time()
    result = run_cmd(cmd, cwd=REPO_DIR, check=False, timeout=300)
    elapsed = time.time() - start_time

    if result is None or result.returncode != 0:
        print(f"[极速] ONNX 极速模式失败")
        if result and result.stderr:
            print(f"[DEBUG] stderr:\n{result.stderr[:800]}")
        if result and result.stdout:
            print(f"[DEBUG] stdout:\n{result.stdout[:800]}")
        return False, elapsed, 0.0

    print(f"[极速] 合成完成，耗时: {elapsed:.1f} 秒")

    # 查找输出文件
    if "output" in supported_args:
        output_path = os.path.join(OUTPUT_DIR, "test_onnx_speed.wav")
    else:
        output_path = find_output_wav(REPO_DIR)
        output_path = copy_output_to(output_path, "test_onnx_speed.wav")

    if output_path and os.path.exists(output_path):
        size_mb = os.path.getsize(output_path) / 1024 / 1024
        duration = _get_audio_duration(output_path)
        print(f"[极速] 输出文件: {output_path} ({size_mb:.2f} MB, {duration:.2f}s)")
        return True, elapsed, duration
    else:
        print("[极速] 未找到输出音频文件")
        _print_debug_files(REPO_DIR)
        return False, elapsed, 0.0


def test_onnx_voice_clone():
    """测试 2: ONNX 语音克隆（使用参考音频）"""
    print("\n" + "=" * 60)
    print("测试 2: ONNX 语音克隆")
    print("=" * 60)

    infer_script = os.path.join(REPO_DIR, "infer_onnx.py")
    ref_audio = get_reference_audio()

    if not os.path.exists(infer_script):
        print("[跳过] 未找到 infer_onnx.py")
        return False, 0.0, 0.0
    if not ref_audio:
        print("[跳过] 未找到参考音频")
        return False, 0.0, 0.0

    print(f"[参考音频] {ref_audio}")

    supported_args = detect_infer_onnx_args()
    cmd = [sys.executable, infer_script]
    if "model-dir" in supported_args:
        cmd.extend(["--model-dir", os.path.join(REPO_DIR, "models")])
    if "output" in supported_args:
        output_path = os.path.join(OUTPUT_DIR, "test_onnx_clone.wav")
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        cmd.extend(["--output", output_path])
    cmd.extend([
        "--prompt-audio-path", ref_audio,
        "--text", TEST_TEXT_EN,
    ])

    start_time = time.time()
    result = run_cmd(cmd, cwd=REPO_DIR, check=False, timeout=300)
    elapsed = time.time() - start_time

    if result is None or result.returncode != 0:
        print(f"[测试 2] ONNX 语音克隆失败")
        if result and result.stderr:
            print(f"[DEBUG] stderr:\n{result.stderr[:800]}")
        if result and result.stdout:
            print(f"[DEBUG] stdout:\n{result.stdout[:800]}")
        return False, elapsed, 0.0

    print(f"[测试 2] 克隆完成，耗时: {elapsed:.1f} 秒")

    if "output" in supported_args:
        output_path = os.path.join(OUTPUT_DIR, "test_onnx_clone.wav")
    else:
        output_path = find_output_wav(REPO_DIR)
        output_path = copy_output_to(output_path, "test_onnx_clone.wav")

    if output_path and os.path.exists(output_path):
        size_mb = os.path.getsize(output_path) / 1024 / 1024
        duration = _get_audio_duration(output_path)
        print(f"[测试 2] 输出文件: {output_path} ({size_mb:.2f} MB, {duration:.2f}s)")
        return True, elapsed, duration
    else:
        print("[测试 2] 未找到输出音频文件")
        _print_debug_files(REPO_DIR)
        return False, elapsed, 0.0


def test_cli_generate():
    """测试 3: CLI 工具 ONNX 生成"""
    print("\n" + "=" * 60)
    print("测试 3: CLI ONNX 生成")
    print("=" * 60)

    ref_audio = get_reference_audio()
    supported_args = detect_cli_args()
    print(f"[探测] CLI 支持参数: {supported_args}")

    if "backend" not in supported_args:
        print("[跳过] CLI 不支持 --backend 参数")
        return False, 0.0, 0.0

    cmd = [sys.executable, "-m", "moss_tts_nano", "generate", "--backend", "onnx"]
    if "output" in supported_args:
        output_path = os.path.join(OUTPUT_DIR, "test_cli_output.wav")
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        cmd.extend(["--output", output_path])
    if ref_audio and "prompt-speech" in supported_args:
        cmd.extend(["--prompt-speech", ref_audio])
    cmd.extend(["--text", TEST_TEXT_ZH])

    start_time = time.time()
    result = run_cmd(cmd, cwd=REPO_DIR, check=False, timeout=300)
    elapsed = time.time() - start_time

    if result is None or result.returncode != 0:
        print(f"[测试 3] CLI 生成失败")
        return False, elapsed, 0.0

    print(f"[测试 3] CLI 生成完成，耗时: {elapsed:.1f} 秒")

    if "output" in supported_args:
        output_path = os.path.join(OUTPUT_DIR, "test_cli_output.wav")
    else:
        # CLI 默认输出 generated_audio/moss_tts_nano_output.wav
        default_path = os.path.join(REPO_DIR, "generated_audio", "moss_tts_nano_output.wav")
        if os.path.exists(default_path):
            output_path = copy_output_to(default_path, "test_cli_output.wav")
        else:
            output_path = find_output_wav(REPO_DIR, "moss_tts_nano")
            output_path = copy_output_to(output_path, "test_cli_output.wav")

    if output_path and os.path.exists(output_path):
        size_mb = os.path.getsize(output_path) / 1024 / 1024
        duration = _get_audio_duration(output_path)
        print(f"[测试 3] 输出文件: {output_path} ({size_mb:.2f} MB, {duration:.2f}s)")
        return True, elapsed, duration
    else:
        print("[测试 3] 未找到输出音频文件")
        return False, elapsed, 0.0


def test_multilingual():
    """测试 4: ONNX 多语言语音合成"""
    print("\n" + "=" * 60)
    print("测试 4: ONNX 多语言语音合成")
    print("=" * 60)

    infer_script = os.path.join(REPO_DIR, "infer_onnx.py")
    if not os.path.exists(infer_script):
        print("[跳过] 未找到 infer_onnx.py")
        return False, []

    supported_args = detect_infer_onnx_args()
    test_cases = [
        ("中文", TEST_TEXT_ZH, "test_multilingual_zh.wav"),
        ("英文", TEST_TEXT_EN, "test_multilingual_en.wav"),
        ("日文", TEST_TEXT_JA, "test_multilingual_ja.wav"),
        ("韩文", TEST_TEXT_KO, "test_multilingual_ko.wav"),
    ]

    results = []
    for lang, text, filename in test_cases:
        print(f"\n[多语言] 测试 {lang}...")

        cmd = [sys.executable, infer_script]
        if "model-dir" in supported_args:
            cmd.extend(["--model-dir", os.path.join(REPO_DIR, "models")])
        if "output" in supported_args:
            output_path = os.path.join(OUTPUT_DIR, filename)
            os.makedirs(OUTPUT_DIR, exist_ok=True)
            cmd.extend(["--output", output_path])
        cmd.extend(["--text", text])

        start_time = time.time()
        result = run_cmd(cmd, cwd=REPO_DIR, check=False, timeout=300)
        elapsed = time.time() - start_time

        if result is None or result.returncode != 0:
            print(f"[多语言] {lang} 合成失败")
            if result and result.stderr:
                print(f"[DEBUG] stderr:\n{result.stderr[:800]}")
            if result and result.stdout:
                print(f"[DEBUG] stdout:\n{result.stdout[:800]}")
            results.append((lang, False, elapsed, 0.0))
            continue

        if "output" in supported_args:
            output_path = os.path.join(OUTPUT_DIR, filename)
        else:
            output_path = find_output_wav(REPO_DIR)
            output_path = copy_output_to(output_path, filename)

        if output_path and os.path.exists(output_path):
            size_mb = os.path.getsize(output_path) / 1024 / 1024
            duration = _get_audio_duration(output_path)
            print(f"[多语言] {lang} 合成成功 ({elapsed:.1f}s, {size_mb:.2f} MB, {duration:.2f}s)")
            results.append((lang, True, elapsed, duration))
        else:
            print(f"[多语言] {lang} 未找到输出文件")
            _print_debug_files(REPO_DIR)
            results.append((lang, False, elapsed, 0.0))

    success_count = sum(1 for _, ok, _, _ in results if ok)
    print(f"\n[多语言] 通过: {success_count}/{len(test_cases)}")
    return success_count == len(test_cases), results


def test_model_files():
    """测试 5: 验证 ONNX 模型文件是否已下载"""
    print("\n" + "=" * 60)
    print("测试 5: ONNX 模型文件验证")
    print("=" * 60)

    models_dir = os.path.join(REPO_DIR, "models")
    if not os.path.isdir(models_dir):
        print("[模型文件] models 目录不存在，模型可能尚未自动下载")
        return False

    expected_dirs = [
        "MOSS-TTS-Nano-100M-ONNX",
        "MOSS-Audio-Tokenizer-Nano-ONNX",
    ]

    all_found = True
    for dirname in expected_dirs:
        dir_path = os.path.join(models_dir, dirname)
        if os.path.isdir(dir_path):
            # 统计文件大小
            total_size = 0
            file_count = 0
            for root, _, files in os.walk(dir_path):
                for f in files:
                    fp = os.path.join(root, f)
                    total_size += os.path.getsize(fp)
                    file_count += 1
            print(f"[模型文件] {dirname}: {file_count} 个文件, {total_size / 1024 / 1024:.1f} MB")
        else:
            print(f"[模型文件] {dirname}: 未找到")
            all_found = False

    return all_found


# ============================================================
# 主程序
# ============================================================
def main():
    print("=" * 60)
    print("MOSS-TTS-Nano 0.1B ONNX 测试程序")
    print("=" * 60)
    print()
    print("说明：")
    print("  - 首次运行会自动克隆仓库并下载 ONNX 模型")
    print("  - 模型下载源: 优先 ModelScope，回退 HuggingFace (OpenMOSS-Team)")
    print("  - 参考音频: 仓库自带 assets/audio/zh_1.wav")
    print("  - 输出目录:", OUTPUT_DIR)
    print()

    # 1. 环境准备
    if not ensure_repo():
        print("\n[致命错误] 仓库准备失败，测试终止")
        sys.exit(1)

    if not ensure_dependencies():
        print("\n[警告] 依赖安装可能不完整，继续尝试...")

    # 2. 优先从 ModelScope 下载 ONNX 模型
    download_onnx_models()

    # 3. 模型文件验证
    model_ready = test_model_files()

    # 4. 功能测试
    results = []
    timing_records = []

    # 测试 1: ONNX 基础合成
    success, elapsed, duration = test_onnx_basic()
    results.append(("ONNX 基础合成", success))
    timing_records.append(("ONNX 基础合成", elapsed, duration))

    # 测试 1b: ONNX 极速模式
    success, elapsed, duration = test_onnx_speed_mode()
    results.append(("ONNX 极速模式", success))
    timing_records.append(("ONNX 极速模式", elapsed, duration))

    # 测试 2: ONNX 语音克隆
    success, elapsed, duration = test_onnx_voice_clone()
    results.append(("ONNX 语音克隆", success))
    timing_records.append(("ONNX 语音克隆", elapsed, duration))

    # 测试 3: CLI 生成
    success, elapsed, duration = test_cli_generate()
    results.append(("CLI ONNX 生成", success))
    timing_records.append(("CLI ONNX 生成", elapsed, duration))

    # 测试 4: 多语言
    success, lang_results = test_multilingual()
    results.append(("ONNX 多语言", success))
    for lang, ok, elapsed, duration in lang_results:
        timing_records.append((f"  ONNX {lang}", elapsed, duration))

    # 测试报告
    print("\n" + "=" * 60)
    print("测试报告")
    print("=" * 60)
    for name, success in results:
        status = "通过" if success else "未通过"
        print(f"  {name:<20} {status}")

    total = len(results)
    passed = sum(1 for _, s in results if s)
    print(f"\n  总计: {passed}/{total} 项通过")

    # 耗时统计
    print("\n" + "=" * 60)
    print("耗时统计")
    print("=" * 60)
    total_elapsed = sum(t for _, t, _ in timing_records)
    total_duration = sum(d for _, _, d in timing_records)
    for name, elapsed, duration in timing_records:
        bar_len = int(elapsed / max(total_elapsed, 1) * 30) if total_elapsed > 0 else 0
        bar = "█" * bar_len + "░" * (30 - bar_len)
        dur_str = f"{duration:.2f}s" if duration > 0 else "-"
        if duration > 0:
            rtf = elapsed / duration
            rtf_str = f"{rtf:.2f}x"
        else:
            rtf_str = "-"
        print(f"  {name:<20} {elapsed:>6.2f}s  {dur_str:>6}  {rtf_str:>6}  {bar}")
    print(f"  {'-'*20} {'-'*6}  {'-'*6}  {'-'*6}")
    total_rtf = total_elapsed / total_duration if total_duration > 0 else 0
    print(f"  {'合计':<20} {total_elapsed:>6.2f}s  {total_duration:>6.2f}s  {total_rtf:>6.2f}x")

    print("\n" + "=" * 60)
    print("提示信息")
    print("=" * 60)
    print(f"""
1. ONNX 模型目录: {os.path.join(REPO_DIR, 'models')}
2. 测试输出目录: {OUTPUT_DIR}
3. 生成音频采样率: 48 kHz（WAV 格式）
4. 如需手动测试：
   - ONNX 推理: cd {REPO_DIR} && python infer_onnx.py --text "你好"
   - CLI 生成: python -m moss_tts_nano generate --backend onnx --text "你好"
   - Web 演示: cd {REPO_DIR} && python app_onnx.py
5. 环境变量配置：
   - ODDTTS_MODEL_SOURCE=modelscope: 强制使用 ModelScope 下载
   - HF_ENDPOINT=https://hf-mirror.com: 使用 HuggingFace 镜像站
6. 若依赖安装失败，可手动执行：
   - conda install -c conda-forge pynini=2.1.6.post1 -y
   - pip install git+https://github.com/WhizZest/WeTextProcessing.git
7. 模型下载失败时，infer_onnx.py 会自动从 HuggingFace 下载
    """)

    print("=" * 60)
    print("MOSS-TTS-Nano 测试程序执行完毕")
    print("=" * 60)

    if passed < total:
        sys.exit(1)


if __name__ == "__main__":
    main()
