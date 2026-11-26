#!/usr/bin/env python3
"""
test_websocket_streaming_tts.py

测试 OddTTS WebSocket 实时流式 TTS 接口 (/v1/audio/speech/ws)。

依赖:
    pip install websocket-client

用法示例:
    # 基本测试（使用服务器默认模型）
    python tests/test_websocket_streaming_tts.py

    # 指定模型和音色
    python tests/test_websocket_streaming_tts.py --model oddtts-kokoro-v1-1 --voice zf_001 --text "你好世界"

    # 测试请求级引擎路由（切换模型）
    python tests/test_websocket_streaming_tts.py --model oddtts-zipvoice --voice news-female

    # 测试 volume / pitch 透传
    python tests/test_websocket_streaming_tts.py --volume 20 --pitch -10 --output test_vp.wav

    # 批量测试多个模型
    python tests/test_websocket_streaming_tts.py --multi
"""

from __future__ import annotations

import argparse
import json
import sys
import time


def _check_dependency():
    """检查 websocket-client 是否已安装。"""
    try:
        import websocket
        return websocket
    except ImportError:
        print("[错误] 缺少依赖: websocket-client")
        print("[提示] 请执行: pip install websocket-client")
        sys.exit(1)


def test_websocket_tts(
    host: str = "127.0.0.1",
    port: int = 9001,
    text: str = "关注我的公众号：奥德元，一起学习 AI，一起追赶时代。",
    voice: str | None = None,
    model: str | None = None,
    speed: float = 1.0,
    volume: int = 0,
    pitch: int = 0,
    response_format: str = "wav",
    output_file: str | None = None,
    timeout: int = 120,
) -> bool:
    """通过 WebSocket 请求 TTS 合成并保存音频文件。

    Args:
        host: 服务器地址
        port: 服务器端口
        text: 要合成的文本
        voice: 音色名称（留空则使用服务器默认第一个音色）
        model: 模型名称（如 oddtts-kokoro-v1-1），留空使用服务器默认配置
        speed: 语速倍率 (0.25 ~ 4.0)
        volume: 音量调节 (-50 ~ 50)
        pitch: 音调调节 (-50 ~ 50)
        response_format: 输出格式 (wav / mp3)
        output_file: 输出文件路径（留空则自动生成）
        timeout: WebSocket 连接超时秒数

    Returns:
        合成成功返回 True，否则返回 False
    """
    websocket = _check_dependency()

    ws_url = f"ws://{host}:{port}/v1/audio/speech/ws"
    print(f"[*] 连接到 {ws_url}")

    try:
        ws = websocket.create_connection(ws_url, timeout=timeout)
    except Exception as e:
        print(f"[!] 连接失败: {e}")
        return False

    # 构造请求参数（与 /v1/audio/speech REST 接口兼容）
    payload: dict = {
        "input": text,
        "speed": speed,
        "locale": "zh-CN",
        "response_format": response_format,
        "volume": volume,
        "pitch": pitch,
    }
    if voice:
        payload["voice"] = voice
    if model:
        payload["model"] = model

    print(f"[*] 发送参数: {json.dumps(payload, ensure_ascii=False, indent=2)}")

    start_time = time.time()
    ws.send(json.dumps(payload))

    chunks: list[bytes] = []
    header_received = False
    result_info: dict = {}

    while True:
        try:
            msg = ws.recv()
        except websocket.WebSocketTimeoutException:
            print("[!] 接收超时")
            break
        except Exception as e:
            print(f"[!] 接收异常: {e}")
            break

        if isinstance(msg, str):
            try:
                data = json.loads(msg)
            except json.JSONDecodeError:
                print(f"[!] 收到非 JSON 文本: {msg[:200]}")
                continue

            msg_type = data.get("type")

            if msg_type == "header":
                header_received = True
                print(f"[+] 收到 header: format={data.get('format')}")

            elif msg_type == "end":
                result_info = data
                gen_time = data.get("generation_time")
                total_bytes = data.get("total_bytes")
                print(f"[+] 合成完成: generation_time={gen_time}s, total_bytes={total_bytes}")
                break

            elif msg_type == "error":
                print(f"[!] 服务端错误: {data.get('message')}")
                ws.close()
                return False

            else:
                print(f"[*] 收到消息: {data}")
        else:
            # 二进制音频数据
            chunks.append(msg)
            print(f"[+] 收到音频 chunk: {len(msg)} bytes")

    ws.close()
    elapsed = time.time() - start_time

    if not chunks:
        print("[!] 未收到任何音频数据")
        return False

    # 保存音频文件
    audio_data = b"".join(chunks)
    if output_file is None:
        ts = int(time.time())
        model_suffix = f"_{model.replace('-', '_')}" if model else ""
        output_file = f"output_websocket{model_suffix}_{ts}.{response_format}"

    with open(output_file, "wb") as f:
        f.write(audio_data)

    print(f"[+] 音频已保存: {output_file}")
    print(f"    文件大小: {len(audio_data):,} bytes ({len(audio_data) / 1024:.1f} KB)")
    print(f"    总耗时:   {elapsed:.3f}s")
    if result_info.get("generation_time"):
        print(f"    生成耗时: {result_info['generation_time']}s (服务端)")

    return True


def test_multiple_models(host: str, port: int, text: str) -> None:
    """批量测试多个模型，验证请求级引擎路由是否正常。"""
    test_cases = [
        {
            "model": "oddtts-kokoro-v1-1",
            "voice": "zf_001",
            "format": "wav",
            "desc": "Kokoro v1.1 (纯CPU 中英混合)",
        },
        {
            "model": "oddtts-kokoro",
            "voice": "af",
            "format": "wav",
            "desc": "Kokoro (纯CPU 中文)",
        },
        {
            "model": "oddtts-edgetts",
            "voice": "zh-CN-XiaoxiaoNeural",
            "format": "mp3",
            "desc": "EdgeTTS (在线服务)",
        },
    ]

    results: list[tuple[str, bool]] = []

    for case in test_cases:
        print(f"\n{'=' * 60}")
        print(f"[*] 测试: {case['desc']}")
        print(f"    model={case['model']}, voice={case['voice']}, format={case['format']}")

        output = f"output_ws_{case['model'].replace('-', '_')}.{case['format']}"
        success = test_websocket_tts(
            host=host,
            port=port,
            text=text,
            voice=case["voice"],
            model=case["model"],
            response_format=case["format"],
            output_file=output,
        )
        results.append((case["model"], success))

    print(f"\n{'=' * 60}")
    print("[*] 批量测试结果汇总:")
    for model, ok in results:
        status = "✅ 通过" if ok else "❌ 失败"
        print(f"    {status}  {model}")


# =============================================================================
# CLI 入口
# =============================================================================

def main() -> int:
    parser = argparse.ArgumentParser(
        description="测试 OddTTS WebSocket 实时流式 TTS 接口",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 使用默认配置测试
  python tests/test_websocket_streaming_tts.py

  # 指定模型和音色
  python tests/test_websocket_streaming_tts.py --model oddtts-kokoro-v1-1 --voice zf_001

  # 调节音量和音调
  python tests/test_websocket_streaming_tts.py --volume 20 --pitch -10 --output test.wav

  # 批量测试多个模型（验证请求级路由）
  python tests/test_websocket_streaming_tts.py --multi
        """.strip(),
    )
    parser.add_argument("--host", default="127.0.0.1", help="服务器地址 (默认: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=9001, help="服务器端口 (默认: 9001)")
    parser.add_argument(
        "--text",
        default="关注我的公众号：奥德元，一起学习 AI，一起追赶时代。",
        help="要合成的文本",
    )
    parser.add_argument("--voice", default=None, help="音色名称（留空使用服务器默认）")
    parser.add_argument(
        "--model",
        default=None,
        help='模型名称，如 oddtts-kokoro-v1-1、oddtts-zipvoice 等（留空使用服务器默认）',
    )
    parser.add_argument("--speed", type=float, default=1.0, help="语速倍率 (默认: 1.0)")
    parser.add_argument("--volume", type=int, default=0, help="音量调节 (-50~50, 默认: 0)")
    parser.add_argument("--pitch", type=int, default=0, help="音调调节 (-50~50, 默认: 0)")
    parser.add_argument(
        "--format",
        dest="response_format",
        default="wav",
        choices=["wav", "mp3"],
        help="输出格式 (默认: wav)",
    )
    parser.add_argument("--output", default=None, help="输出文件路径（留空自动生成）")
    parser.add_argument(
        "--timeout",
        type=int,
        default=120,
        help="WebSocket 接收超时秒数 (默认: 120)",
    )
    parser.add_argument(
        "--multi",
        action="store_true",
        help="批量测试多个模型（验证请求级引擎路由）",
    )

    args = parser.parse_args()

    if args.multi:
        test_multiple_models(args.host, args.port, args.text)
        return 0

    success = test_websocket_tts(
        host=args.host,
        port=args.port,
        text=args.text,
        voice=args.voice,
        model=args.model,
        speed=args.speed,
        volume=args.volume,
        pitch=args.pitch,
        response_format=args.response_format,
        output_file=args.output,
        timeout=args.timeout,
    )
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
