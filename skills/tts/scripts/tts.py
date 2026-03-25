#!/usr/bin/env python3
"""TTS entrypoint for MIMO TTS (xiaomimimo.com)
Works with Coze OpenClaw + Feishu robot.
"""
import argparse
import os
import sys
import tempfile
import subprocess
import shutil
from pathlib import Path
from typing import Optional

# ===================== 【API 配置】=====================
MIMO_API_URL = "https://api.xiaomimimo.com/v1/speech"

SCRIPT_DIR = Path(__file__).parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

# ===================== 读取 API KEY =====================
def load_api_key() -> Optional[str]:
    key = os.environ.get("MIMO_API_KEY", "").strip()
    return key if key else None

# ===================== 工具函数 =====================
def mktemp_suffixed(suffix: str) -> Path:
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    return Path(path)

def unlink_silent(path: Optional[Path]) -> None:
    if path:
        try:
            path.unlink()
        except OSError:
            pass

def play_audio(path: str) -> None:
    for player in ("afplay", "aplay", "paplay"):
        if shutil.which(player):
            subprocess.call([player, path])
            return

# ===================== 核心：TTS 合成 =====================
def text_to_speech(text: str, output: str, ref_audio: Optional[str] = None):
    try:
        import requests
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
        import requests

    api_key = load_api_key()
    if not api_key:
        print("Error: MIMO_API_KEY not set", file=sys.stderr)
        return False

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "text": text,
        "voice": "female_zh",
        "format": "mp3",
        "speed": 1.0
    }

    if ref_audio and Path(ref_audio).exists():
        files = {
            "audio": open(ref_audio, "rb"),
            "json": (None, json.dumps(payload), "application/json")
        }
        resp = requests.post(MIMO_API_URL, headers=headers, files=files, timeout=120)
    else:
        resp = requests.post(MIMO_API_URL, headers=headers, json=payload, timeout=120)

    if resp.status_code == 200:
        with open(output, "wb") as f:
            f.write(resp.content)
        return True
    else:
        print(f"API Error: {resp.status_code} {resp.text}", file=sys.stderr)
        return False

# ===================== 命令：speak（保持原接口）=====================
def cmd_speak(args):
    if not args.text and not args.text_file:
        return 1

    text = args.text
    if not text and args.text_file:
        text = Path(args.text_file).read_text(encoding="utf-8").strip()

    play_mode = args.output is None
    tmp_output = None
    if play_mode:
        tmp_output = mktemp_suffixed(".mp3")
        output = str(tmp_output)
    else:
        output = args.output

    ok = text_to_speech(text, output, args.ref_audio)
    if not ok:
        return 1

    if play_mode:
        play_audio(output)
        unlink_silent(tmp_output)
    return 0

# ===================== 其他命令（保持兼容）=====================
def cmd_config(args):
    print("MIMO_API_KEY is configured" if load_api_key() else "Please set MIMO_API_KEY")
    return 0

def dummy_cmd(args, extra=None):
    print("Not supported in MIMO mode", file=sys.stderr)
    return 0

# ===================== 入口（完全兼容原命令）=====================
_SUBCOMMANDS = {"speak", "render", "to-srt", "config"}

def main():
    argv = sys.argv[1:]
    if not argv or argv[0] not in _SUBCOMMANDS:
        argv = ["speak"] + argv

    parser = argparse.ArgumentParser(prog="tts.py")
    sub = parser.add_subparsers(dest="command")

    sp = sub.add_parser("speak")
    sp.add_argument("-t", "--text")
    sp.add_argument("-f", "--text-file")
    sp.add_argument("-o", "--output")
    sp.add_argument("--ref-audio")
    sp.add_argument("--speed", type=float)

    sub.add_parser("render")
    sub.add_parser("to-srt")
    sub.add_parser("config")

    args, extra = parser.parse_known_args(argv)

    if args.command == "speak":
        return cmd_speak(args)
    elif args.command == "config":
        return cmd_config(args)
    else:
        return dummy_cmd(args)

if __name__ == "__main__":
    sys.exit(main())