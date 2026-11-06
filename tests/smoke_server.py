"""Smoke test: boot the uvicorn server and hit it over real HTTP.

Run with:
    python3 tests/smoke_server.py
"""

import socket
import subprocess
import sys
import time
import urllib.request
import json


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def main() -> int:
    port = free_port()
    proc = subprocess.Popen(
        [
            sys.executable, "-m", "uvicorn", "app.main:app",
            "--host", "127.0.0.1", "--port", str(port),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    base = f"http://127.0.0.1:{port}"
    try:
        # Wait for the server to come up.
        for _ in range(100):
            try:
                urllib.request.urlopen(f"{base}/health", timeout=1)
                break
            except Exception:
                time.sleep(0.1)
        else:
            print("FAIL: server did not start")
            return 1

        health = json.load(urllib.request.urlopen(f"{base}/health", timeout=2))
        assert health == {"status": "ok"}, health

        req = urllib.request.Request(
            f"{base}/items",
            data=json.dumps({"name": "Smoke ball", "price": 1.5}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        created = json.load(urllib.request.urlopen(req, timeout=2))
        assert created["id"] == 1, created

        item = json.load(urllib.request.urlopen(f"{base}/items/1", timeout=2))
        assert item["name"] == "Smoke ball", item

        print("Smoke test passed: server boots and serves requests.")
        return 0
    finally:
        proc.terminate()
        proc.wait(timeout=5)


if __name__ == "__main__":
    sys.exit(main())
