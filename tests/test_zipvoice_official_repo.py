"""
ZipVoice 官方版本测试

使用 ZipVoice 官方代码进行推理，不依赖 sherpa-onnx
"""

import sys
from pathlib import Path
import subprocess
import time

# 设置 UTF-8 编码
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')


def test_zipvoice_official():
    """使用 ZipVoice 官方代码进行测试"""
    
    print("=" * 70)
    print("ZipVoice 官方版本测试")
    print("=" * 70)
    
    # 检查 ZipVoice 仓库
    zipvoice_repo = Path("ZipVoice")
    if not zipvoice_repo.exists():
        print("[ERROR] ZipVoice 仓库不存在")
        print("\n请运行:")
        print("  git clone https://github.com/k2-fsa/ZipVoice.git")
        return False
    
    print(f"[OK] ZipVoice 仓库: {zipvoice_repo}")
    
    # 检查依赖
    print("\n检查依赖...")
    missing = []
    
    try:
        import torch
        print(f"  [OK] torch {torch.__version__}")
    except ImportError:
        missing.append("torch")
    
    try:
        import torchaudio
        print(f"  [OK] torchaudio")
    except ImportError:
        missing.append("torchaudio")
    
    try:
        import vocos
        print(f"  [OK] vocos")
    except ImportError:
        missing.append("vocos")
    
    try:
        import pypinyin
        print(f"  [OK] pypinyin")
    except ImportError:
        missing.append("pypinyin")
    
    try:
        import jieba
        print(f"  [OK] jieba")
    except ImportError:
        missing.append("jieba")
    
    if missing:
        print(f"\n[ERROR] 缺少依赖: {', '.join(missing)}")
        print("\n请安装:")
        print("  cd ZipVoice")
        print("  pip install -r requirements.txt")
        return False
    
    # 准备测试
    print(f"\n{'='*60}")
    print("准备测试数据")
    print(f"{'='*60}")
    
    # 使用模型自带的测试音频
    ref_audio = Path("models/sherpa-onnx-zipvoice-distill-int8-zh-en-emilia/test_wavs/news-female.wav")
    
    if not ref_audio.exists():
        print(f"[ERROR] 参考音频不存在: {ref_audio}")
        return False
    
    ref_text = "This is a reference audio sample for voice cloning."
    
    print(f"参考音频: {ref_audio}")
    print(f"参考文本: {ref_text}")
    
    # 测试文本
    test_texts = [
        "Hello World, this is a test of ZipVoice text-to-speech system.",
        "The quick brown fox jumps over the lazy dog.",
        "欢迎关注我的公众号: 奥德元。一起学习AI，一起追赶时代！",
    ]
    
    output_dir = Path("output_zipvoice_official")
    output_dir.mkdir(exist_ok=True)
    
    # 运行官方推理脚本
    print(f"\n{'='*60}")
    print("运行 ZipVoice 官方推理")
    print(f"{'='*60}")
    
    for i, text in enumerate(test_texts, 1):
        output_file = output_dir / f"test{i:02d}.wav"
        
        print(f"\n{'─'*60}")
        print(f"测试 {i}/{len(test_texts)}")
        print(f"文本: {text[:60]}...")
        print(f"{'─'*60}")
        
        # 构建命令
        cmd = [
            sys.executable, "-m", "zipvoice.bin.infer_zipvoice",
            "--model-name", "zipvoice_distill",  # 使用蒸馏版本更快
            "--prompt-wav", str(ref_audio),
            "--prompt-text", ref_text,
            "--text", text,
            "--res-wav-path", str(output_file),
            "--num-step", "8",  # 默认步数
        ]
        
        print(f"命令: {' '.join(cmd[2:])}")  # 不显示 python 路径
        print(f"运行中...")
        
        start = time.time()
        
        try:
            # 设置环境变量使用镜像
            import os
            env = os.environ.copy()
            env['HF_ENDPOINT'] = 'https://hf-mirror.com'
            
            # 将 ZipVoice 目录添加到 PYTHONPATH
            zipvoice_dir_abs = Path("ZipVoice").resolve()
            if 'PYTHONPATH' not in env:
                env['PYTHONPATH'] = str(zipvoice_dir_abs)
            else:
                env['PYTHONPATH'] = str(zipvoice_dir_abs) + os.pathsep + env['PYTHONPATH']
            
            print(f"PYTHONPATH: {env['PYTHONPATH']}")
            
            result = subprocess.run(
                cmd,
                cwd=str(Path.cwd()),
                env=env,
                capture_output=True,
                text=True,
                timeout=300  # 5 分钟超时
            )
            
            elapsed = time.time() - start
            
            if result.returncode == 0:
                if output_file.exists():
                    size_kb = output_file.stat().st_size / 1024
                    print(f"[OK] 合成成功!")
                    print(f"     耗时: {elapsed:.2f}s")
                    print(f"     输出: {output_file} ({size_kb:.1f} KB)")
                else:
                    print(f"[WARNING] 命令成功但输出文件不存在")
            else:
                print(f"[ERROR] 命令失败 (返回码: {result.returncode})")
                if result.stderr:
                    print(f"错误: {result.stderr[:500]}")
            
        except subprocess.TimeoutExpired:
            print(f"[ERROR] 超时 (>{300}s)")
        except Exception as e:
            print(f"[ERROR] 异常: {e}")
    
    # 总结
    print(f"\n{'='*60}")
    print("测试完成!")
    print(f"{'='*60}")
    
    output_files = list(output_dir.glob("*.wav"))
    if output_files:
        print(f"\n生成的音频文件:")
        for f in sorted(output_files):
            size_kb = f.stat().st_size / 1024
            print(f"  - {f} ({size_kb:.1f} KB)")
        
        print(f"\n播放命令:")
        for f in sorted(output_files):
            print(f"  start {f}")
        
        return True
    else:
        print("\n没有生成任何音频文件")
        return False


if __name__ == "__main__":
    success = test_zipvoice_official()
    
    if not success:
        print("\n测试失败，请检查上述错误信息")
        sys.exit(1)
