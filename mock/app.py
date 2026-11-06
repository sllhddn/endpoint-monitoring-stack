"""Tiny stand-in for an application server's monitoring page (e.g. a JavaMelody /monitoring URL).

MODE controls behaviour so the dashboard has something interesting to show:
  ok     - 200 quickly
  slow   - 200 after SLOW_SECONDS
  error  - 500 every time
  flaky  - 500 roughly FLAKY_RATE of the time
"""
import base64
import os
import random
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MODE = os.getenv("MODE", "ok")
USER = os.getenv("MONITOR_USER", "monitor")
PASSWORD = os.getenv("MONITOR_PASSWORD", "demo-only")
SLOW_SECONDS = float(os.getenv("SLOW_SECONDS", "1.5"))
FLAKY_RATE = float(os.getenv("FLAKY_RATE", "0.3"))
EXPECTED = "Basic " + base64.b64encode(f"{USER}:{PASSWORD}".encode()).decode()


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, body: str):
        data = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(data)))
        if code == 401:
            self.send_header("WWW-Authenticate", 'Basic realm="monitoring"')
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if not self.path.startswith("/monitoring"):
            return self._send(404, "not found")
        if self.headers.get("Authorization") != EXPECTED:
            return self._send(401, "auth required")
        if MODE == "slow":
            time.sleep(SLOW_SECONDS)
        if MODE == "error" or (MODE == "flaky" and random.random() < FLAKY_RATE):
            return self._send(500, "internal error")
        self._send(200, f"<h1>Monitoring - {os.getenv('APP_NAME', 'app')}</h1><p>status: UP</p>")

    def log_message(self, *args):  # keep container logs quiet
        pass


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
