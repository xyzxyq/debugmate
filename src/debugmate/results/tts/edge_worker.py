"""Isolated edge-tts worker with a bytes-only stdin/stdout contract.

This process deliberately has no filesystem output argument.  Its parent owns
the deadline and can terminate the whole process even if an upstream coroutine
swallows cancellation.
"""

from __future__ import annotations

import argparse
import asyncio
import sys

import edge_tts

_MAX_RECAP_BYTES = 16 * 1024
_MAX_AUDIO_BYTES = 8_000_000
_VOICES = {"zh-CN-XiaoxiaoNeural"}
_RATES = {"-10%", "+10%"}


async def _stream_audio(text: str, *, voice: str, rate: str) -> bytes:
    output = bytearray()
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    async for chunk in communicate.stream():
        if chunk.get("type") != "audio":
            continue
        data = chunk.get("data")
        if not isinstance(data, bytes) or len(output) + len(data) > _MAX_AUDIO_BYTES:
            raise ValueError
        output.extend(data)
    if not output:
        raise ValueError
    return bytes(output)


def main() -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--voice", required=True)
    parser.add_argument("--rate", required=True)
    try:
        arguments = parser.parse_args()
        if arguments.voice not in _VOICES or arguments.rate not in _RATES:
            return 2
        raw = sys.stdin.buffer.read(_MAX_RECAP_BYTES + 1)
        if len(raw) > _MAX_RECAP_BYTES:
            return 2
        text = raw.decode("utf-8", errors="strict")
        if not text:
            return 2
        sys.stdout.buffer.write(
            asyncio.run(_stream_audio(text, voice=arguments.voice, rate=arguments.rate))
        )
        sys.stdout.buffer.flush()
        return 0
    except (UnicodeError, ValueError, OSError):
        return 2


if __name__ == "__main__":  # pragma: no cover - spawned process entry point
    raise SystemExit(main())
