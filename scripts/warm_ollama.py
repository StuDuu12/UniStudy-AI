"""Start the local Ollama server if needed and preload the UI's local models."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen


BASE_URL = "http://127.0.0.1:11434"
# Load largest first so that the lightest model is requested last.
LOCAL_MODELS = ("qwen3.5:9b", "qwen3.5:4b", "qwen3.5:2b")


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

    for model in LOCAL_MODELS:
        preload(model)

    try:
        with urlopen(f"{BASE_URL}/api/ps", timeout=3) as response:
            loaded = {model["name"] for model in json.load(response)["models"]}
    except (OSError, ValueError, KeyError):
        print("[Ollama] Khong kiem tra duoc cac model dang o trong bo nho.")
        return

    resident = ", ".join(model for model in LOCAL_MODELS if model in loaded)
    missing = ", ".join(model for model in LOCAL_MODELS if model not in loaded)
    print(f"[Ollama] Dang duoc giu trong bo nho: {resident or 'khong co'}.")
    if missing:
        print(f"[Ollama] Chua co trong bo nho: {missing}.")


def preload(model):
    body = json.dumps({"model": model, "stream": False, "keep_alive": "10m"}).encode()
    request = Request(f"{BASE_URL}/api/generate", body, {"Content-Type": "application/json"})
    try:
        with urlopen(request, timeout=90):
            print(f"[Ollama] Da nap {model}.")
    except HTTPError as error:
        if error.code == 404:
            print(f"[Ollama] Chua co {model}. Chay: ollama pull {model}")
        else:
            print(f"[Ollama] Khong nap duoc {model} (HTTP {error.code}).")
    except OSError:
        print(f"[Ollama] Het thoi gian cho hoac mat ket noi khi nap {model}.")


if __name__ == "__main__":
    main()
