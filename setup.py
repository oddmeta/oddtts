import os
import shutil
import subprocess

from setuptools import setup
from setuptools.command.build_py import build_py as _build_py


class build_py(_build_py):
    """自定义 build_py，在构建 wheel 时自动将外部仓库 vendoring 到 oddtts/vendor/"""

    def run(self):
        super().run()
        self._vendor_moss_nano()
        self._vendor_audio8()

    def _vendor_moss_nano(self):
        """将 moss-tts-nano 仓库复制到 build/lib/oddtts/vendor/moss-tts-nano/（排除 models/ 等大目录）"""
        build_lib = self.build_lib
        dst = os.path.join(build_lib, "oddtts", "vendor", "moss-tts-nano")

        # 已存在则跳过（支持增量构建）
        if os.path.isdir(dst):
            return

        # 1. 优先使用本地已有的源码
        src_candidates = [
            os.path.join(os.path.dirname(__file__), "tests", "moss-tts-nano"),
            os.path.join(os.path.dirname(__file__), "moss-tts-nano"),
        ]
        src = None
        for candidate in src_candidates:
            if os.path.isdir(candidate):
                src = candidate
                break

        # 2. 本地没有则尝试 git clone
        if src is None:
            target = os.path.join(os.path.dirname(__file__), "moss-tts-nano")
            try:
                subprocess.check_call(
                    [
                        "git", "clone", "--depth", "1",
                        "https://github.com/OpenMOSS/MOSS-TTS-Nano.git",
                        target,
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                src = target
            except Exception:
                pass

        if not src or not os.path.isdir(src):
            return

        # 3. 复制时排除不需要的子目录
        ignore_patterns = shutil.ignore_patterns(
            "models", "__pycache__", "*.egg-info", "generated_audio",
            ".cache", ".git", "*.onnx", "*.data", "*.wav",
        )
        shutil.copytree(src, dst, ignore=ignore_patterns, dirs_exist_ok=True)

    def _vendor_audio8(self):
        """将 Audio8_TTS 仓库复制到 build/lib/oddtts/vendor/Audio8_TTS/"""
        build_lib = self.build_lib
        dst_base = os.path.join(build_lib, "oddtts", "vendor", "Audio8_TTS")

        if os.path.isdir(dst_base):
            return

        src = os.path.join(os.path.dirname(__file__), "Audio8_TTS")

        # 本地没有则尝试 git clone
        if not os.path.isdir(src):
            target = os.path.join(os.path.dirname(__file__), "Audio8_TTS")
            try:
                subprocess.check_call(
                    [
                        "git", "clone", "--depth", "1",
                        "https://github.com/Audio8-AI/Audio8_TTS.git",
                        target,
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                src = target
            except Exception:
                pass

        if not os.path.isdir(src):
            return

        os.makedirs(dst_base, exist_ok=True)

        # 只复制引擎实际需要的子目录
        required_subdirs = ["onnx_runtime", "onnx_runtime_0_1b_int8"]
        for subdir in required_subdirs:
            src_sub = os.path.join(src, subdir)
            if os.path.isdir(src_sub):
                dst_sub = os.path.join(dst_base, subdir)
                shutil.copytree(src_sub, dst_sub, dirs_exist_ok=True)


setup(cmdclass={"build_py": build_py})
