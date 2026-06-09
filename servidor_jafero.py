from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import urllib.request
import os

API_KEY = os.getenv("ANTHROPIC_API_KEY")
PORT    = int(os.getenv("PORT", 10000))

class Handler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        print(f"  → {args[0]} {args[1]}")

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_GET(self):
        if self.path in ["/", "/index.html"]:
            # Busca el HTML en la misma carpeta
            for name in ["centro_mando_jafero.html", "mis_agentes_jafero.html", "index.html"]:
                if os.path.exists(name):
                    with open(name, "r", encoding="utf-8") as f:
                        html = f.read()
                    self.send_response(200)
                    self.send_header("Content-type", "text/html; charset=utf-8")
                    self._cors()
                    self.end_headers()
                    self.wfile.write(html.encode("utf-8"))
                    return
            self.send_error(404, "HTML no encontrado")

    def do_POST(self):
        if self.path == "/api":
            length = int(self.headers.get("Content-Length", 0))
            body   = self.rfile.read(length)

            try:
                data = json.loads(body)

                # Construye request para Anthropic con el formato completo
                anthropic_payload = {
                    "model"     : data.get("model", "claude-3-5-sonnet-20241022"),
                    "max_tokens": data.get("max_tokens", 1500),
                    "messages"  : data.get("messages", [])
                }

                # System prompt si viene
                if data.get("system"):
                    anthropic_payload["system"] = data["system"]

                req = urllib.request.Request(
                    "https://api.anthropic.com/v1/messages",
                    data    = json.dumps(anthropic_payload).encode("utf-8"),
                    headers = {
                        "x-api-key"         : API_KEY,
                        "anthropic-version" : "2023-06-01",
                        "content-type"      : "application/json"
                    }
                )

                with urllib.request.urlopen(req, timeout=120) as res:
                    result   = json.loads(res.read().decode("utf-8"))
                    respuesta = result["content"][0]["text"]

            except Exception as e:
                respuesta = f"Error: {str(e)}"

            # Devuelve JSON con campo "response" ← lo que espera el frontend
            output = json.dumps({"response": respuesta}, ensure_ascii=False)

            self.send_response(200)
            self.send_header("Content-type", "application/json; charset=utf-8")
            self._cors()
            self.end_headers()
            self.wfile.write(output.encode("utf-8"))

        else:
            self.send_error(404)

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin",  "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")


if __name__ == "__main__":
    print(f"\n{'═'*45}")
    print(f"  Jafero Backend · Puerto {PORT}")
    print(f"{'═'*45}\n")
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
