# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
# -*- coding: utf-8 -*-
"""调用系统 Chrome/Edge 渲染本地 HTML，输出桌面与移动视口 PNG。

优先使用 Chrome DevTools Protocol（CDP）精确设置视口，避免 Windows headless
把窗口宽度钳制到 ~500px 的问题；CDP 不可用时回退到 --screenshot CLI 模式。

用法：
    uv run capture_html.py templates/echarts/line.html --outdir shots --json
    uv run capture_html.py templates/dashboard/sales_dashboard.html \
        --viewport desktop=1280x800 --viewport mobile=390x844 --json
"""
import argparse
import base64
import json
import os
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

sys.stdout.reconfigure(encoding="utf-8")

DEFAULT_VIEWPORTS = [("desktop", 1280, 800), ("mobile", 390, 844)]

BROWSER_CANDIDATES = [
    os.environ.get("CHROME_PATH"),
    os.environ.get("EDGE_PATH"),
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/usr/bin/google-chrome",
    "/usr/bin/google-chrome-stable",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
    "/usr/bin/microsoft-edge",
]


def find_browser(explicit: str | None) -> str | None:
    if explicit:
        return explicit if Path(explicit).is_file() else None
    for candidate in BROWSER_CANDIDATES:
        if candidate and Path(candidate).is_file():
            return candidate
    for name in ("chrome", "google-chrome", "chromium", "msedge", "microsoft-edge"):
        found = shutil.which(name)
        if found:
            return found
    return None


def parse_viewports(values: list[str] | None) -> list[tuple[str, int, int]]:
    if not values:
        return list(DEFAULT_VIEWPORTS)
    viewports = []
    for raw in values:
        name, _, size = raw.partition("=")
        width, _, height = size.lower().partition("x")
        try:
            viewports.append((name or f"vp{len(viewports) + 1}", int(width), int(height)))
        except ValueError:
            raise SystemExit(f"非法视口：{raw}，应为 name=1280x800")
    return viewports


def png_size(path: Path) -> tuple[int, int] | None:
    try:
        with path.open("rb") as fh:
            header = fh.read(24)
        if header[:8] != b"\x89PNG\r\n\x1a\n":
            return None
        width, height = struct.unpack(">II", header[16:24])
        return int(width), int(height)
    except OSError:
        return None


def target_url(raw: str) -> str:
    if raw.startswith(("http://", "https://", "file://")):
        return raw
    return Path(raw).resolve().as_uri()


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


# --------------------------------------------------------------------------- #
# 最小 WebSocket 客户端（CDP over ws，纯标准库）
# --------------------------------------------------------------------------- #
class CDPWebSocket:
    def __init__(self, url: str, timeout: float = 60.0):
        parsed = urlparse(url)
        host, port = parsed.hostname, parsed.port or 80
        path = parsed.path + (("?" + parsed.query) if parsed.query else "")
        self.sock = socket.create_connection((host, port), timeout=timeout)
        self.sock.settimeout(timeout)
        key = base64.b64encode(os.urandom(16)).decode()
        request = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {host}:{port}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n\r\n"
        )
        self.sock.sendall(request.encode("ascii"))
        buffer = b""
        while b"\r\n\r\n" not in buffer:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise RuntimeError("WebSocket 握手失败：连接被关闭")
            buffer += chunk
        head, _, rest = buffer.partition(b"\r\n\r\n")
        status = head.split(b"\r\n", 1)[0]
        if b"101" not in status:
            raise RuntimeError(f"WebSocket 握手失败：{status.decode('latin-1')}")
        self._prebuffer = rest
        self._next_id = 0

    def _read_exact(self, n: int) -> bytes:
        if self._prebuffer:
            data, self._prebuffer = self._prebuffer[:n], self._prebuffer[n:]
            if len(data) == n:
                return data
            return data + self._read_exact(n - len(data))
        chunks = []
        remaining = n
        while remaining > 0:
            chunk = self.sock.recv(remaining)
            if not chunk:
                raise ConnectionError("WebSocket 连接被关闭")
            chunks.append(chunk)
            remaining -= len(chunk)
        return b"".join(chunks)

    def _send_frame(self, payload: bytes, opcode: int = 0x1):
        mask = os.urandom(4)
        header = bytearray([0x80 | opcode])
        length = len(payload)
        if length < 126:
            header.append(0x80 | length)
        elif length < 65536:
            header.append(0x80 | 126)
            header += struct.pack(">H", length)
        else:
            header.append(0x80 | 127)
            header += struct.pack(">Q", length)
        header += mask
        masked = bytes(byte ^ mask[i % 4] for i, byte in enumerate(payload))
        self.sock.sendall(bytes(header) + masked)

    def recv_message(self) -> str:
        fragments = b""
        while True:
            first, second = self._read_exact(2)
            fin = bool(first & 0x80)
            opcode = first & 0x0F
            masked = bool(second & 0x80)
            length = second & 0x7F
            if length == 126:
                length = struct.unpack(">H", self._read_exact(2))[0]
            elif length == 127:
                length = struct.unpack(">Q", self._read_exact(8))[0]
            mask = self._read_exact(4) if masked else b""
            payload = self._read_exact(length)
            if mask:
                payload = bytes(byte ^ mask[i % 4] for i, byte in enumerate(payload))
            if opcode == 0x9:  # ping
                self._send_frame(payload, opcode=0xA)
                continue
            if opcode == 0x8:
                raise ConnectionError("WebSocket 关闭")
            if opcode in (0x1, 0x2):
                fragments = payload
            elif opcode == 0x0:
                fragments += payload
            else:
                continue
            if fin:
                return fragments.decode("utf-8")

    def command(self, method: str, params: dict | None = None) -> dict:
        self._next_id += 1
        msg_id = self._next_id
        payload = {"id": msg_id, "method": method}
        if params:
            payload["params"] = params
        self._send_frame(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
        while True:
            message = json.loads(self.recv_message())
            if message.get("id") == msg_id:
                if "error" in message:
                    raise RuntimeError(f"{method}: {message['error']}")
                return message.get("result", {})

    def close(self):
        try:
            self._send_frame(b"", opcode=0x8)
        except Exception:  # noqa: BLE001
            pass
        try:
            self.sock.close()
        except Exception:  # noqa: BLE001
            pass


# --------------------------------------------------------------------------- #
# 浏览器启动与截图
# --------------------------------------------------------------------------- #
def start_browser(browser: str, profile: Path, port: int) -> subprocess.Popen:
    cmd = [
        browser,
        "--headless=new",
        "--disable-gpu",
        "--hide-scrollbars",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-extensions",
        "--disable-background-networking",
        "--disable-sync",
        "--mute-audio",
        f"--remote-debugging-port={port}",
        "--remote-allow-origins=*",
        f"--user-data-dir={profile}",
        "about:blank",
    ]
    return subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def wait_for_cdp(port: int, timeout: float = 25.0) -> dict:
    deadline = time.time() + timeout
    last_error = None
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=2) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, ConnectionError, TimeoutError) as exc:
            last_error = exc
            time.sleep(0.25)
    raise RuntimeError(f"等待 Chrome DevTools 端口超时：{last_error}")


def create_target(port: int) -> dict:
    request = urllib.request.Request(f"http://127.0.0.1:{port}/json/new?about:blank", method="PUT")
    with urllib.request.urlopen(request, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def capture_cdp(ws: CDPWebSocket, url: str, out: Path, width: int, height: int,
                wait_ms: int, full_page: bool = False) -> tuple[bool, str]:
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        ws.command("Emulation.setDeviceMetricsOverride", {
            "width": width, "height": height, "deviceScaleFactor": 1,
            "mobile": width < 600, "screenWidth": width, "screenHeight": height,
        })
        try:
            ws.command("Emulation.setScrollbarsHidden", {"hidden": True})
        except RuntimeError:
            pass
        ws.command("Page.navigate", {"url": url})
        # 先等 readyState=complete，再留时间给 ECharts/D3 动画与 ResizeObserver
        deadline = time.time() + 15
        while time.time() < deadline:
            time.sleep(0.2)
            try:
                result = ws.command("Runtime.evaluate", {
                    "expression": "document.readyState",
                    "returnByValue": True,
                })
                if result.get("result", {}).get("value") == "complete":
                    break
            except RuntimeError:
                pass
        time.sleep(max(wait_ms, 500) / 1000.0)
        params = {"format": "png", "fromSurface": True, "captureBeyondViewport": False}
        if full_page:
            try:
                metrics = ws.command("Page.getLayoutMetrics")
                content = metrics.get("cssContentSize") or metrics.get("contentSize") or {}
                content_height = int(round(float(content.get("height", height))))
            except (RuntimeError, TypeError, ValueError):
                content_height = height
            content_height = max(height, content_height)
            params.update({
                "captureBeyondViewport": True,
                "clip": {"x": 0, "y": 0, "width": width, "height": content_height, "scale": 1},
            })
        shot = ws.command("Page.captureScreenshot", params)
        data = shot.get("data")
        if not data:
            return False, "CDP 未返回截图数据"
        out.write_bytes(base64.b64decode(data))
        if not out.is_file() or out.stat().st_size == 0:
            return False, "截图文件为空"
        return True, ""
    except Exception as exc:  # noqa: BLE001
        return False, f"{type(exc).__name__}: {exc}"


def capture_cli(browser: str, url: str, out: Path, width: int, height: int,
                wait_ms: int, timeout: int, profile: Path) -> tuple[bool, str]:
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        browser,
        "--headless=new",
        "--disable-gpu",
        "--hide-scrollbars",
        "--force-device-scale-factor=1",
        f"--window-size={width},{height}",
        f"--virtual-time-budget={wait_ms}",
        "--run-all-compositor-stages-before-draw",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-extensions",
        "--disable-background-networking",
        "--disable-sync",
        "--mute-audio",
        f"--user-data-dir={profile}",
        f"--screenshot={out}",
        url,
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return False, f"截图超时（>{timeout}s）"
    if proc.returncode != 0:
        tail = (proc.stderr or b"").decode("utf-8", errors="replace").strip().splitlines()[-3:]
        return False, f"浏览器退出码 {proc.returncode}: {' | '.join(tail)}"
    if not out.is_file() or out.stat().st_size == 0:
        return False, "未生成截图或文件为空"
    return True, ""


def main() -> int:
    ap = argparse.ArgumentParser(description="Headless 多视口 HTML 截图（CDP 优先）")
    ap.add_argument("files", nargs="+", help="本地 HTML 文件或 URL")
    ap.add_argument("--outdir", default="screenshots")
    ap.add_argument("--stem", default=None, help="输出文件名前缀（多文件时自动追加序号）")
    ap.add_argument("--viewport", action="append", default=None,
                    help="name=WxH，可重复；默认 desktop=1280x800 与 mobile=390x844")
    ap.add_argument("--browser", default=None, help="Chrome/Edge 可执行文件路径")
    ap.add_argument("--mode", choices=["auto", "cdp", "cli"], default="auto",
                    help="auto=CDP 失败时回退 CLI；cli 会有 Windows 最小窗口宽度钳制")
    ap.add_argument("--wait-ms", type=int, default=2500, help="页面加载后的等待毫秒数")
    ap.add_argument("--full-page", action="store_true",
                    help="按内容高度截取整页（CDP 模式；画布可高于视口）")
    ap.add_argument("--timeout", type=int, default=60, help="CLI 模式单次截图超时秒数")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--out", default=None, help="另存 JSON 报告")
    args = ap.parse_args()

    viewports = parse_viewports(args.viewport)
    browser = find_browser(args.browser)
    result = {"status": "error", "outputs": [], "rows_used": 0, "rows_dropped": 0,
              "verified": False, "warnings": [], "browser": browser, "mode": None,
              "viewports": [{"name": n, "width": w, "height": h} for n, w, h in viewports],
              "captures": []}
    if browser is None:
        result["warnings"].append("未找到 Chrome/Edge；请安装或通过 --browser / CHROME_PATH 指定")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2

    outdir = Path(args.outdir)
    profile = Path(tempfile.mkdtemp(prefix="vizshot-"))
    process = None
    ws = None
    cdp_ok = False
    if args.mode in ("auto", "cdp"):
        port = free_port()
        try:
            process = start_browser(browser, profile, port)
            info = wait_for_cdp(port)
            target = create_target(port)
            ws = CDPWebSocket(target["webSocketDebuggerUrl"])
            ws.command("Page.enable")
            ws.command("Runtime.enable")
            cdp_ok = True
            result["mode"] = "cdp"
            result["browser_version"] = info.get("Browser")
        except Exception as exc:  # noqa: BLE001
            result["warnings"].append(f"CDP 启动失败，将回退 CLI：{type(exc).__name__}: {exc}")
            if process:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
            process = None
            ws = None
    if not cdp_ok:
        result["mode"] = "cli"
        if args.mode == "cdp":
            result["warnings"].append("指定了 --mode cdp 但 CDP 不可用")
    if result["mode"] == "cli":
        result["warnings"].append(
            "CLI 模式下 Windows headless 可能把布局视口钳制到约 500px；移动端布局验收请使用 CDP 模式"
        )
        if args.full_page:
            result["warnings"].append("--full-page 仅支持 CDP 模式，CLI 回退将按视口截图")

    failures = 0
    try:
        prepared = []
        for index, raw in enumerate(args.files, start=1):
            path = Path(raw) if not raw.startswith(("http://", "https://", "file://")) else None
            base_stem = args.stem or (path.stem if path else f"page{index}")
            if args.stem and len(args.files) > 1:
                base_stem = f"{args.stem}_{index:02d}"
            prepared.append((raw, path, target_url(raw), base_stem))
        stem_counts: dict[str, int] = {}
        for _, _, _, stem in prepared:
            stem_counts[stem] = stem_counts.get(stem, 0) + 1
        for raw, path, url, stem in prepared:
            if stem_counts[stem] > 1 and path is not None:
                stem = f"{path.parent.name}_{stem}"
            if raw.startswith(("http://", "https://")):
                result["warnings"].append(f"输入为外部 URL，会触发网络请求：{raw}")
            if path is not None and not path.is_file():
                result["warnings"].append(f"文件不存在：{raw}")
                failures += 1
                continue
            for name, width, height in viewports:
                out = outdir / f"{stem}_{name}.png"
                ok, message = (False, "未执行")
                if cdp_ok and ws is not None:
                    ok, message = capture_cdp(ws, url, out, width, height, args.wait_ms,
                                              args.full_page)
                    if not ok and args.mode == "auto":
                        result["warnings"].append(f"{raw} [{name}] CDP 失败，回退 CLI：{message}")
                        ok, message = capture_cli(browser, url, out, width, height,
                                                  args.wait_ms, args.timeout, profile)
                else:
                    ok, message = capture_cli(browser, url, out, width, height,
                                              args.wait_ms, args.timeout, profile)
                size = png_size(out) if ok else None
                record = {"file": raw, "viewport": name, "width": width, "height": height,
                          "output": str(out), "ok": ok, "png_size": size,
                          "full_page": bool(args.full_page and cdp_ok),
                          "mode": "cdp" if cdp_ok else "cli"}
                if not ok:
                    failures += 1
                    record["error"] = message
                    result["warnings"].append(f"{raw} [{name}]：{message}")
                else:
                    result["outputs"].append(str(out))
                    if size and size != (width, height) and not (args.full_page and cdp_ok):
                        result["warnings"].append(
                            f"{raw} [{name}] 截图尺寸 {size} 与请求视口 {(width, height)} 不一致"
                        )
                result["captures"].append(record)
    finally:
        if ws:
            ws.close()
        if process:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
        shutil.rmtree(profile, ignore_errors=True)

    result["status"] = "success" if failures == 0 else "partial"
    result["verified"] = failures == 0 and bool(result["outputs"])
    payload = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(payload + "\n", encoding="utf-8")
        result["outputs"].append(str(args.out))
        payload = json.dumps(result, ensure_ascii=False, indent=2)

    if args.json or not sys.stdout.isatty():
        print(payload)
    else:
        print(f"浏览器：{browser}｜模式：{result['mode']}")
        for record in result["captures"]:
            mark = "✓" if record["ok"] else "✗"
            print(f"  {mark} {record['file']} [{record['viewport']}] -> {record['output']} {record.get('png_size')}")
        for warning in result["warnings"]:
            print("警告:", warning)
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
