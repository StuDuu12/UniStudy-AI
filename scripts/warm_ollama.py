"""Start the local Ollama server if needed and preload the smallest UI model."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen


BASE_URL = "http://127.0.0.1:11434"
MODEL = "qwen3.5:2b"


def ollama_ready():
    try:
        with urlopen(f"{BASE_URL}/api/version", timeout=1) as response:
            return bool(json.load(response).get("version"))
    except (OSError, ValueError):
        return False


def main():
    if not ollama_ready():
        executable = shutil.which("ollama")
        if not executable:
            default = Path(os.environ["LOCALAPPDATA"]) / "Programs" / "Ollama" / "ollama.exe"
            if not default.is_file():
                print("[Ollama] Chua tim thay Ollama. Van co the tra cuu giao trinh.")
                return
            executable = str(default)

        try:
            subprocess.Popen(
                [executable, "serve"],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        except OSError as error:
            print(f"[Ollama] Khong the khoi dong: {error}")
            return

        for _ in range(20):
            if ollama_ready():
                break
            time.sleep(0.5)
        else:
            print("[Ollama] API tren cong 11434 chua san sang.")
            return

    body = json.dumps({"model": MODEL, "stream": False, "keep_alive": "10m"}).encode()
    request = Request(f"{BASE_URL}/api/generate", body, {"Content-Type": "application/json"})
    try:
        with urlopen(request, timeout=90):
            print(f"[Ollama] Model {MODEL} da san sang.")
    except HTTPError as error:
        if error.code == 404:
            print(f"[Ollama] Chua co {MODEL}. Chay: ollama pull {MODEL}")
        else:
            print(f"[Ollama] Khong nap duoc {MODEL} (HTTP {error.code}).")
    except OSError:
        print(f"[Ollama] Het thoi gian cho hoac mat ket noi khi nap {MODEL}.")


if __name__ == "__main__":
    main()
