#!/usr/bin/env python3
import http.server
import json
import urllib.request
import os

API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
PORT = int(os.environ.get("PORT", 8080))
MODEL = "claude-3-5-sonnet-20241022"

def call_ai(prompt):
    body = json.dumps({
        "model": MODEL,
        "max_tokens": 1000,
        "messages": [{"role": "user", "content": prompt}]
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=body,
        headers={
            "Content-Type": "application/json",
            "x-api-key": API_KEY,
            "anthropic-version": "2023-06-01"
        },
        method="POST"
    )

    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())["content"][0]["text"]

class Handler(http.server.BaseHTTPRequestHandler):

    def do_GET(self):
        if self.path == "/":
            try:
                with open("mis_agentes_jafero.html", "r", encoding="utf-8") as f:
                    html = f.read()
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write(html.encode())
            except:
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"Servidor activo")
            return

        if self.path == "/ping":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"ok")
            return

        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        if self.path == "/api":
            length = int(self.headers.get('Content-Length'))
            body = json.loads(self.rfile.read(length))
            prompt = body.get("prompt", "")

            try:
                respuesta = call_ai(prompt)
                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"response": respuesta}).encode())
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(str(e).encode())

if __name__ == "__main__":
    print(f"Servidor corriendo en puerto {PORT}")
    http.server.HTTPServer(("", PORT), Handler).serve_forever()
