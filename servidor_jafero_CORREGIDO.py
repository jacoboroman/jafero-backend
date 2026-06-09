from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import urllib.request
import os

API_KEY = os.getenv("ANTHROPIC_API_KEY")

class Handler(BaseHTTPRequestHandler):

    def do_GET(self):
        if self.path == "/":
            with open("mis_agentes_jafero.html","r",encoding="utf-8") as f:
                html = f.read()
            self.send_response(200)
            self.send_header("Content-type","text/html")
            self.end_headers()
            self.wfile.write(html.encode())

    def do_POST(self):
        if self.path == "/api":

            length = int(self.headers.get('Content-Length'))
            body = self.rfile.read(length)
            data = json.loads(body)

            user_msg = data.get("msg","")

            try:
                req = urllib.request.Request(
                    "https://api.anthropic.com/v1/messages",
                    data=json.dumps({
                        "model": "claude-3-haiku-20240307",
                        "max_tokens": 200,
                        "messages": [
                            {"role": "user", "content": user_msg}
                        ]
                    }).encode(),
                    headers={
                        "x-api-key": API_KEY,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json"
                    }
                )

                with urllib.request.urlopen(req) as res:
                    result = json.loads(res.read().decode())
                    respuesta = result["content"][0]["text"]

            except Exception as e:
                respuesta = "Error IA: " + str(e)

            self.send_response(200)
            self.send_header("Content-type","text/plain")
            self.end_headers()
            self.wfile.write(respuesta.encode())


server = HTTPServer(("0.0.0.0", 10000), Handler)
print("Servidor corriendo...")
server.serve_forever()
