import http.server, json, os
from urllib.parse import urlparse
from urllib.request import Request, urlopen

API_KEY = os.environ.get("ANTHROPIC_API_KEY","")
PORT = int(os.environ.get("PORT",8080))

def call_ai(system, message):
    import urllib.request
    body = json.dumps({
        "model":"claude-3-5-sonnet-20241022",
        "max_tokens":500,
        "system":system,
        "messages":[{"role":"user","content":message}]
    }).encode()

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=body,
        headers={
            "Content-Type":"application/json",
            "x-api-key":API_KEY,
            "anthropic-version":"2023-06-01"
        }
    )

    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())["content"][0]["text"]

class Handler(http.server.BaseHTTPRequestHandler):

    def do_GET(self):
        if self.path == "/":
            with open("mis_agentes_jafero.html","rb") as f:
                self.send_response(200)
                self.send_header("Content-type","text/html")
                self.end_headers()
                self.wfile.write(f.read())

    def do_POST(self):
        if self.path == "/api":
            length = int(self.headers.get('Content-Length'))
            body = json.loads(self.rfile.read(length))

            response = call_ai(body.get("system",""), body.get("message",""))

            self.send_response(200)
            self.send_header("Content-Type","application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"response":response}).encode())

http.server.HTTPServer(("",PORT), Handler).serve_forever()
