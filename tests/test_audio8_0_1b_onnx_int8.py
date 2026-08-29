# -*- coding: utf-8 -*-
"""Tests for Audio8 TTS 0.1B-ONNX-INT8 model.

This test script downloads the Audio8 TTS ONNX INT8 model from ModelScope
and performs basic validation.

ModelScope: https://www.modelscope.cn/models/Audio8/audio8-TTS-0.1B-ONNX-INT8

Note: Full inference requires the Audio8 TTS runtime from:
  https://github.com/Audio8-AI/Audio8_TTS/tree/main/onnx_runtime_0_1b_int8
"""

import os
import sys
import json
import unittest
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

MODEL_ID = "Audio8/audio8-TTS-0.1B-ONNX-INT8"
MODEL_DIR = os.path.join(os.path.dirname(__file__), "models", "audio8_0_1b_onnx_int8")


def download_model():
    from modelscope.hub.snapshot_download import snapshot_download

    print(f"Downloading model {MODEL_ID}...")
    model_path = snapshot_download(
        model_id=MODEL_ID,
        local_dir=MODEL_DIR,
        allow_patterns=["*.onnx", "*.json", "*.npy", "*.txt", "*.data"],
    )
    print(f"Model downloaded to: {model_path}")
    return model_path


def list_model_files(model_path):
    files = []
    for root, dirs, filenames in os.walk(model_path):
        for f in filenames:
            rel_path = os.path.relpath(os.path.join(root, f), model_path)
            files.append(rel_path)
    return files


def load_onnx_model(model_path, filename):
    import onnxruntime as ort
    path = os.path.join(model_path, filename)
    if os.path.exists(path):
        session = ort.InferenceSession(path, providers=["CPUExecutionProvider"])
        return session, path
    return None, None


def synthesize_with_reference(model_path, output_path):
    """Decode reference codes through the codec decoder to verify ONNX codec works."""
    import onnxruntime as ort
    import soundfile as sf

    with open(os.path.join(model_path, "runtime_manifest.json"), "r", encoding="utf-8") as f:
        manifest = json.load(f)

    ref_codes_path = os.path.join(model_path, manifest.get("reference_codes", "reference_codes.npy"))
    reference_codes = np.load(ref_codes_path)
    print(f"Reference codes shape: {reference_codes.shape}")

    codec_path = os.path.join(model_path, manifest.get("codec_models", {}).get("fp16", "codec_decoder_fp16.onnx"))
    codec_session = ort.InferenceSession(codec_path, providers=["CPUExecutionProvider"])

    print("Codec decoder inputs:")
    for inp in codec_session.get_inputs():
        print(f"  {inp.name}: {inp.shape} {inp.type}")

    codes = reference_codes.astype(np.int64)
    if codes.ndim == 2:
        codes = codes[np.newaxis, :, :]
    print(f"Codec input shape: {codes.shape}")

    waveform = codec_session.run(None, {"codes": codes})[0]

    if isinstance(waveform, np.ndarray):
        waveform = waveform.flatten()
    waveform = waveform.astype(np.float32)

    max_val = np.max(np.abs(waveform))
    if max_val > 0:
        waveform = waveform / max_val * 0.95

    sf.write(output_path, waveform, 44100)
    print(f"Audio saved to: {output_path}")
    print(f"Audio duration: {len(waveform) / 44100:.2f} seconds")
    return output_path


class TestAudio8_0_1b_OnnxInt8(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.model_path = download_model()

    def test_model_files_exist(self):
        files = list_model_files(self.model_path)
        print(f"Model files ({len(files)}):")

        required = [
            "slow_ar_int8.onnx",
            "fast_ar_int8.onnx",
            "codec_decoder_fp16.onnx",
            "tokenizer/tokenizer.json",
            "runtime_manifest.json",
            "reference_codes.npy",
        ]

        for r in required:
            found = any(f.replace("\\", "/") == r for f in files)
            self.assertTrue(found, f"Missing required file: {r}")

        for f in files:
            size = os.path.getsize(os.path.join(self.model_path, f))
            print(f"  {f} ({size / 1024 / 1024:.2f} MB)")

    def test_onnx_sessions_load(self):
        session, _ = load_onnx_model(self.model_path, "slow_ar_int8.onnx")
        self.assertIsNotNone(session, "Failed to load slow_ar_int8.onnx")
        print(f"Slow AR inputs: {[i.name for i in session.get_inputs()]}")
        print(f"Slow AR outputs: {[o.name for o in session.get_outputs()]}")

        session, _ = load_onnx_model(self.model_path, "fast_ar_int8.onnx")
        self.assertIsNotNone(session, "Failed to load fast_ar_int8.onnx")
        print(f"Fast AR inputs: {[i.name for i in session.get_inputs()]}")

        session, _ = load_onnx_model(self.model_path, "codec_decoder_fp16.onnx")
        self.assertIsNotNone(session, "Failed to load codec_decoder_fp16.onnx")
        print(f"Codec inputs: {[i.name for i in session.get_inputs()]}")

    def test_reference_codec_decode(self):
        output_path = os.path.join(os.path.dirname(__file__), "test_audio8_0_1b_reference.wav")
        result = synthesize_with_reference(self.model_path, output_path)

        self.assertIsNotNone(result)
        self.assertTrue(os.path.exists(output_path))

        import soundfile as sf
        audio, sr = sf.read(output_path)
        self.assertEqual(sr, 44100)
        self.assertGreater(len(audio), 0)
        print(f"Reference decode successful: {output_path}")


def main():
    print("=" * 60)
    print("Audio8 TTS 0.1B-ONNX-INT8 Test")
    print("=" * 60)

    print("\n1. Downloading model...")
    model_path = download_model()

    print("\n2. Verifying model files...")
    files = list_model_files(model_path)
    for f in files:
        size = os.path.getsize(os.path.join(model_path, f))
        print(f"  {f} ({size / 1024 / 1024:.2f} MB)")

    print("\n3. Loading ONNX sessions...")
    import onnxruntime as ort
    for name in ["slow_ar_int8.onnx", "fast_ar_int8.onnx", "codec_decoder_fp16.onnx"]:
        path = os.path.join(model_path, name)
        if os.path.exists(path):
            sess = ort.InferenceSession(path, providers=["CPUExecutionProvider"])
            inputs = [f"{i.name}: {i.shape}" for i in sess.get_inputs()]
            print(f"  {name}: {inputs}")
        else:
            print(f"  {name}: NOT FOUND")

    print("\n4. Decoding reference audio through codec...")
    output_path = os.path.join(os.path.dirname(__file__), "test_audio8_0_1b_reference.wav")
    result = synthesize_with_reference(model_path, output_path)

    if result:
        print("\nAll tests passed!")
        print(f"Output audio: {output_path}")
    else:
        print("\nTest failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
