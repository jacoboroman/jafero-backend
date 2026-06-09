from http.server import BaseHTTPRequestHandler, HTTPServer
import json

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
        if self.path == "/chat":
            length = int(self.headers.get('Content-Length'))
            body = self.rfile.read(length)
            data = json.loads(body)

            response = "Respuesta de prueba: " + data.get("msg","")

            self.send_response(200)
            self.send_header("Content-type","text/plain")
            self.end_headers()
            self.wfile.write(response.encode())

server = HTTPServer(("0.0.0.0", 10000), Handler)
print("Servidor corriendo...")
server.serve_forever()