import json
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import quote, unquote
import html
import re
import wikipedia
import tools

class NoCacheHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def send_html_error(self, code, description):
        html = description.strip().encode("utf-8")

        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(html)))
        self.end_headers()
        self.wfile.write(html)

    def do_GET(self):
        if self.path == "/tools":
            tool_list = list(tools.TOOLS.keys())
            payload = json.dumps(tool_list).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        super().do_GET()

    def do_POST(self):
        if not self.path.startswith("/tool/"):
            return super().do_POST()
        name = self.path[len("/tool/"):]
        func = tools.TOOLS.get(name)
        if func is None:
            self.send_html_error(404, f"<b>@{name}</b> not found - such as tool does not exist")
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8")
            data = json.loads(body)
        except Exception as e:
            self.send_html_error(400, f"Invalid JSON: {e}")
            return
        if not isinstance(data, dict):
            self.send_html_error(400, "JSON must be an object containing 'messages' and 'arg'")
            return
        if "messages" not in data or "arg" not in data:
            self.send_html_error(400, "JSON must contain both 'messages' and 'arg'")
            return
        messages = data["messages"]
        arg = data["arg"]
        try:
            result = func(messages, arg)
        except Exception as e:
            self.send_html_error(500, f"<b>@{name}</b> error - {e}")
            return
        if not isinstance(result, str):
            result = str(result)
        result_bytes = result.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(result_bytes)))
        self.end_headers()
        self.wfile.write(result_bytes)

if __name__ == "__main__":
    print("http://localhost:8088/")
    HTTPServer(("0.0.0.0", 8088), NoCacheHandler).serve_forever()
