from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import urllib.request
import urllib.error
import os

API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
PORT    = int(os.getenv("PORT", 10000))

# Modelo por defecto — más universal y económico
DEFAULT_MODEL = "claude-3-haiku-20240307"

class Handler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        print(f"  {args[0]} {args[1]}")

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_GET(self):
        if self.path in ["/", "/index.html"]:
            # Busca el HTML en orden de preferencia
            for name in ["centro_mando_jafero.html",
                         "mis_agentes_jafero.html",
                         "index.html"]:
                if os.path.exists(name):
                    with open(name, "r", encoding="utf-8") as f:
                        html = f.read()
                    self.send_response(200)
                    self.send_header("Content-type", "text/html; charset=utf-8")
                    self._cors()
                    self.end_headers()
                    self.wfile.write(html.encode("utf-8"))
                    print(f"  ✓ HTML servido: {name}")
                    return
            self.send_error(404, "HTML no encontrado en el directorio")
            return
        self.send_error(404)

    def do_POST(self):
        if self.path != "/api":
            self.send_error(404)
            return

        # Leer body
        length   = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(length)

        try:
            data = json.loads(raw_body)
        except Exception:
            self._json_response({"response": "Error: body JSON inválido"})
            return

        # Verificar API Key
        if not API_KEY:
            self._json_response({"response": "Error: ANTHROPIC_API_KEY no configurada en Render"})
            return

        # Construir payload para Anthropic
        payload = {
            "model"     : DEFAULT_MODEL,   # ← modelo fijo y estable
            "max_tokens": min(int(data.get("max_tokens", 1500)), 4096),
            "messages"  : data.get("messages", [])
        }
        if data.get("system"):
            payload["system"] = data["system"]

        print(f"  → Llamando Anthropic | model={payload['model']} | tokens={payload['max_tokens']}")

        try:
            req = urllib.request.Request(
                "https://api.anthropic.com/v1/messages",
                data    = json.dumps(payload).encode("utf-8"),
                headers = {
                    "x-api-key"         : API_KEY,
                    "anthropic-version" : "2023-06-01",
                    "content-type"      : "application/json"
                }
            )
            with urllib.request.urlopen(req, timeout=120) as res:
                result    = json.loads(res.read().decode("utf-8"))
                respuesta = result["content"][0]["text"]
                print(f"  ✓ Respuesta Anthropic OK ({len(respuesta)} chars)")

        except urllib.error.HTTPError as e:
            body_err = e.read().decode("utf-8", errors="ignore")
            print(f"  ✗ HTTPError {e.code}: {body_err[:200]}")
            respuesta = f"Error Anthropic {e.code}: {body_err[:300]}"

        except Exception as e:
            print(f"  ✗ Error: {e}")
            respuesta = f"Error: {str(e)}"

        self._json_response({"response": respuesta})

    def _json_response(self, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-type",   "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin",  "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")


if __name__ == "__main__":
    print(f"\n{'═'*46}")
    print(f"  Jafero Backend · Puerto {PORT}")
    print(f"  Modelo: {DEFAULT_MODEL}")
    print(f"  API Key: {'✓ OK' if API_KEY else '✗ NO CONFIGURADA'}")
    print(f"{'═'*46}\n")
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
