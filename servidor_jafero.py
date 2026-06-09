#!/usr/bin/env python3
"""
MIS AGENTES JAFERO · Backend Pro
- Modelo estable claude-3-5-sonnet-20241022
- NEXO devuelve JSON estructurado con scoring 0-100
- Contexto resumido entre fases (menos tokens, menos coste)
- Memoria en historial.json
- Endpoints: /run-system, /run-atlas, /historial, /api, /ping
- Filtros: nicho, precio, tipo
"""
import http.server
import json
import urllib.request
import urllib.error
import urllib.parse
import os
import time
from datetime import datetime

API_KEY   = os.environ.get("ANTHROPIC_API_KEY", "")
PORT      = int(os.environ.get("PORT", 8080))
MAX_RETRY = 3
MODEL     = "claude-3-5-sonnet-20241022"
HISTORY_FILE = "historial.json"

# ══════════════════════════════════════════════════════
#  PROMPTS
# ══════════════════════════════════════════════════════
def prompt_atlas(nicho="", precio="", tipo=""):
    filtros = ""
    if nicho:  filtros += f"\n- Nicho preferido: {nicho}"
    if precio: filtros += f"\n- Rango de precio de venta: {precio}"
    if tipo:   filtros += f"\n- Tipo de producto: {tipo}"
    return f"""Eres ATLAS, Cazador de Productos Ganadores para España.
Encuentra 1 producto viral vendiendo +10.000€/mes en TikTok o Facebook ahora mismo.
{f"Filtros aplicados:{filtros}" if filtros else "Sin filtros específicos — elige el mejor producto disponible."}

ENTREGA EXACTAMENTE:
## PRODUCTO
Nombre: [nombre]
Categoría: [categoría]
Tendencia: [descripción breve]

## NÚMEROS
Coste compra: [X]€
Precio venta: [X]€
Margen bruto: [X]€ ([X]%)

## REVALORIZADOR
Bonus regalo: [producto barato complementario]
Garantía: [X] días

## POR QUÉ AHORA
[2 líneas sobre tracción actual en España]

Español de España. Sin emojis en nombres."""

PROMPT_NEXO = """Eres NEXO, CFO Virtual ecommerce España.
Analiza el producto y devuelve ÚNICAMENTE JSON válido, sin texto adicional, sin markdown, sin explicaciones.

Calcula margen neto:
Precio venta - Coste producto - Envío (4€) - Comisión Shopify 2% - CPA estimado (10€) = MARGEN NETO

Scoring:
- margen (0-30): 0 si margen<8€, 15 si 8-14€, 25 si 15-20€, 30 si >20€
- saturacion (0-30): 30=poco saturado, 0=muy saturado
- demanda (0-40): según tracción en España

JSON de respuesta:
{
  "veredicto": "APTO",
  "motivo": "Una línea explicando",
  "margen_neto": 15.5,
  "desglose": {
    "precio_venta": 39.99,
    "coste": 8.0,
    "envio": 4.0,
    "shopify": 0.8,
    "cpa": 10.0,
    "neto": 17.19
  },
  "score": {
    "margen": 25,
    "saturacion": 22,
    "demanda": 35,
    "total": 82
  },
  "punto_equilibrio": 18,
  "roas_minimo": 2.8
}

Si margen neto < 10€ o score total < 45, usa "veredicto": "NO APTO"."""

PROMPT_NOVA = """Eres NOVA, creadora de ofertas ecommerce España.
Con el producto que te pasan, crea la oferta lista para usar.

## OFERTA
Nombre producto: [nombre]
Precio tachado: [X]€
Precio oferta: [X]€
Ahorro: [X]€ ([X]%)

## BONUSES
1. [bonus] — valor percibido [X]€
2. [bonus] — valor percibido [X]€

## GARANTÍA
[Texto exacto listo para copiar]

## URGENCIA
[Elemento de escasez legítima]

## VALOR PERCIBIDO TOTAL
[X]€ por solo [precio]€

Español de España. Sin clichés."""

PROMPT_PLUMA = """Eres PLUMA, copywriter ecommerce España.
Con el producto y oferta que te pasan, escribe el copy completo.

## TÍTULO
[máx 60 caracteres, beneficio principal]

## SUBTÍTULO
[1 línea gancho]

## BULLETS (5)
- [beneficio + dato concreto]
- [beneficio + dato concreto]
- [beneficio + dato concreto]
- [beneficio + dato concreto]
- [beneficio + dato concreto]

## DESCRIPCIÓN
[Problema — Solución — Resultado, 3 párrafos]

## EMAIL CARRITO #1 (1h)
Asunto: [asunto]
[cuerpo máx 5 líneas]

## EMAIL CARRITO #2 (24h)
Asunto: [asunto]
[cuerpo con bonus, máx 6 líneas]

Tú directo al cliente. Sin clichés. Frases cortas."""

PROMPT_VOLTIO = """Eres VOLTIO, director de anuncios TikTok/Facebook España.
Crea 3 scripts TikTok + 1 Facebook para el producto.

## TIKTOK #1 — DEMO PURA
Hook (0-3s): [frase exacta]
Guion: [breve, qué se ve y dice]
CTA: [acción]
Caption: [texto post]

## TIKTOK #2 — TESTIMONIO POV
Hook: [frase]
Guion: [breve]
CTA: [acción]
Caption: [texto]

## TIKTOK #3 — ANTES/DESPUÉS
Hook: [frase]
Guion: [breve]
CTA: [acción]
Caption: [texto]

## FACEBOOK — OFERTA DIRECTA
Hook: [frase]
Cuerpo: [máx 5 líneas]
CTA: [acción]

Conversacional. Producto en pantalla antes del segundo 7."""

def prompt_core(objetivo=""):
    obj_line = f"
Objetivo del usuario: {objetivo}" if objetivo else ""
    return f"""Eres CORE, estratega ecommerce.{obj_line}
Con todo el trabajo anterior, genera el resumen ejecutivo final.

## RESUMEN (5 líneas máx)
[Lo más importante: producto, margen, oferta, canales]

## CHECKLIST LANZAMIENTO
[ ] Shopify Basic (1€/mes primeros 3 meses)
[ ] Subir producto con copy de PLUMA
[ ] Activar Shopify Payments
[ ] Publicar 3 anuncios de VOLTIO en TikTok
[ ] Activar emails carrito de PLUMA
[ ] Monitorizar ROAS mínimo 3 días

## PRÓXIMOS 3 PASOS HOY
1. [acción concreta — tiempo estimado]
2. [acción concreta — tiempo estimado]
3. [acción concreta — tiempo estimado]

## RIESGO PRINCIPAL
[1 línea directa + cómo mitigarlo]

## DECISIÓN FINAL
LANZAR o NO LANZAR

## POR QUÉ
[1 línea clara con el motivo]

Sin teoría. Solo acción."""

# ══════════════════════════════════════════════════════
#  UTILIDADES
# ══════════════════════════════════════════════════════
def call_ai(system_prompt, user_message, max_tokens=1500, retries=3):
    """Llama a la API con retry automático en caso de fallo."""
    body = json.dumps({
        "model"     : MODEL,
        "max_tokens": max_tokens,
        "system"    : system_prompt,
        "messages"  : [{"role":"user","content":user_message}]
    }).encode("utf-8")

    last_error = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                "https://api.anthropic.com/v1/messages",
                data    = body,
                headers = {
                    "Content-Type"      : "application/json",
                    "x-api-key"         : API_KEY,
                    "anthropic-version" : "2023-06-01"
                },
                method = "POST"
            )
            with urllib.request.urlopen(req, timeout=120) as resp:
                return json.loads(resp.read())["content"][0]["text"]
        except Exception as e:
            last_error = e
            if attempt < retries - 1:
                wait = 2 * (attempt + 1)  # 2s, 4s
                print(f"  ⚠ API error (intento {attempt+1}/{retries}): {e}. Reintentando en {wait}s...")
                time.sleep(wait)
    raise Exception(f"API falló tras {retries} intentos: {last_error}")

def summarize(text, max_chars=600):
    """Reduce contexto entre fases para ahorrar tokens."""
    return text[:max_chars].rsplit("\n", 1)[0] + "…" if len(text) > max_chars else text

def save_history(entry):
    """Guarda producto exitoso con todos los datos para poder reconstruirlo."""
    history = []
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE) as f:
                history = json.load(f)
        except Exception:
            history = []
    # Añadir timestamp legible
    entry["timestamp"]      = time.time()
    entry["fecha"]          = datetime.now().strftime("%d/%m/%Y %H:%M")
    history.append(entry)
    history = history[-30:]  # máximo 30 productos
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def load_history():
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def parse_nexo(text):
    """Parsea JSON de NEXO con fallback robusto."""
    # Intenta extraer JSON del texto
    try:
        start = text.index("{")
        end   = text.rindex("}") + 1
        return json.loads(text[start:end])
    except Exception:
        pass
    # Fallback: análisis de texto
    veredicto = "NO APTO" if "NO APTO" in text.upper() else "APTO"
    return {
        "veredicto": veredicto,
        "motivo"   : "Análisis completado.",
        "margen_neto": 0,
        "desglose" : {},
        "score"    : {"margen":20,"saturacion":20,"demanda":20,"total":60},
        "punto_equilibrio": 20,
        "roas_minimo": 3.0
    }

# ══════════════════════════════════════════════════════
#  PIPELINE ORQUESTADOR
# ══════════════════════════════════════════════════════
def run_pipeline(send, nicho="", precio="", tipo="", objetivo=""):
    for attempt in range(1, MAX_RETRY + 1):

        # ── FASE 1: ATLAS ──────────────────────
        send("phase_start", {"id":"atlas","name":"ATLAS","emoji":"🔍",
            "label":"Buscando producto ganador en TikTok y Facebook..."})
        atlas_text = call_ai(
            prompt_atlas(nicho, precio, tipo),
            "Búscame el mejor producto ganador ahora mismo para España.",
            max_tokens=800
        )
        send("phase_done", {"id":"atlas", "content": atlas_text})

        # ── FASE 2: NEXO (JSON + SCORE) ────────
        send("phase_start", {"id":"nexo","name":"NEXO","emoji":"🧮",
            "label":"Calculando rentabilidad y puntuando el producto..."})
        nexo_text = call_ai(
            PROMPT_NEXO,
            f"Valida este producto:\n\n{summarize(atlas_text, 400)}",
            max_tokens=600
        )
        nexo_data = parse_nexo(nexo_text)
        send("phase_done", {
            "id"      : "nexo",
            "content" : nexo_text,
            "score"   : nexo_data.get("score"),
            "veredicto": nexo_data.get("veredicto","APTO"),
            "motivo"  : nexo_data.get("motivo",""),
            "margen_neto": nexo_data.get("margen_neto", 0),
            "desglose": nexo_data.get("desglose",{}),
            "punto_equilibrio": nexo_data.get("punto_equilibrio",0),
            "roas_minimo": nexo_data.get("roas_minimo",0)
        })

        # ── VALIDACIÓN ─────────────────────────
        if nexo_data.get("veredicto","APTO") == "NO APTO":
            if attempt < MAX_RETRY:
                send("retry", {"attempt":attempt,"max":MAX_RETRY,
                    "message":f"Score insuficiente ({nexo_data.get('score',{}).get('total','?')}/100): {nexo_data.get('motivo','')} — Buscando otro producto... ({attempt+1}/{MAX_RETRY})"})
                continue
            else:
                send("error", {"message":"No se encontró producto viable en 3 intentos. Prueba con otros filtros."})
                return

        # Resumen corto del producto para pasar entre fases
        producto_resumen = f"Producto: {summarize(atlas_text, 300)}\nMargen neto: {nexo_data.get('margen_neto',0)}€\nScore: {nexo_data.get('score',{}).get('total','?')}/100"

        # ── FASE 3: NOVA ───────────────────────
        send("phase_start", {"id":"nova","name":"NOVA","emoji":"🏗️",
            "label":"Construyendo oferta irresistible..."})
        nova_text = call_ai(PROMPT_NOVA,
            f"Crea la oferta para:\n{producto_resumen}",
            max_tokens=800)
        send("phase_done", {"id":"nova", "content": nova_text})

        # ── FASE 4: PLUMA ──────────────────────
        send("phase_start", {"id":"pluma","name":"PLUMA","emoji":"✍️",
            "label":"Escribiendo copy persuasivo..."})
        pluma_text = call_ai(PROMPT_PLUMA,
            f"Escribe copy para:\n{producto_resumen}\n\nOFERTA:\n{summarize(nova_text, 300)}",
            max_tokens=2000)
        send("phase_done", {"id":"pluma", "content": pluma_text})

        # ── FASE 5: VOLTIO ─────────────────────
        send("phase_start", {"id":"voltio","name":"VOLTIO","emoji":"⚡",
            "label":"Creando scripts de anuncios virales..."})
        voltio_text = call_ai(PROMPT_VOLTIO,
            f"Crea anuncios para:\n{producto_resumen}\n\nCOPY CLAVE:\n{summarize(pluma_text, 300)}",
            max_tokens=2000)
        send("phase_done", {"id":"voltio", "content": voltio_text})

        # ── FASE 6: CORE ───────────────────────
        send("phase_start", {"id":"core","name":"CORE","emoji":"🧠",
            "label":"Generando estrategia y checklist de lanzamiento..."})
        core_text = call_ai(prompt_core(objetivo),
            f"Resumen ejecutivo para:\n{producto_resumen}",
            max_tokens=800)
        send("phase_done", {"id":"core", "content": core_text})

        # Extraer DECISIÓN FINAL del CORE
        decision = "LANZAR"
        for line in core_text.upper().split("\n"):
            if "NO LANZAR" in line:
                decision = "NO LANZAR"; break
            if "LANZAR" in line and "DECISIÓN" not in line:
                decision = "LANZAR"; break

        # ── GUARDAR EN HISTORIAL (datos completos) ──
        save_history({
            "producto"       : atlas_text[:300],
            "producto_full"  : atlas_text,
            "nexo_data"      : nexo_data,
            "nova"           : nova_text[:500],
            "resumen_copy"   : pluma_text[:300],
            "decision"       : decision,
            "score"          : nexo_data.get("score",{}).get("total",0),
            "margen"         : nexo_data.get("margen_neto",0),
            "nicho"          : nicho or "General",
            "precio"         : precio or "Libre",
            "tipo"           : tipo or "Libre",
            "objetivo"       : objetivo or ""
        })

        send("decision", {"decision": decision})

        send("complete", {"message":"Sistema completado. Producto listo para lanzar."})
        return

def run_atlas_only(send, nicho="", precio="", tipo=""):
    """Ejecuta solo ATLAS (regenerar producto)."""
    send("phase_start", {"id":"atlas","name":"ATLAS","emoji":"🔍",
        "label":"Buscando nuevo producto ganador..."})
    atlas_text = call_ai(
        prompt_atlas(nicho, precio, tipo),
        "Búscame un producto ganador diferente al anterior.",
        max_tokens=800
    )
    send("phase_done", {"id":"atlas", "content": atlas_text})
    send("complete", {"message":"Nuevo producto encontrado."})

# ══════════════════════════════════════════════════════
#  HTTP HANDLER
# ══════════════════════════════════════════════════════
class Handler(http.server.BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        print(f"  → {args[0]} {args[1]}")

    def do_OPTIONS(self):
        self.send_response(200); self._cors(); self.end_headers()

    def _sse_run(self, runner_fn, params):
        self.send_response(200)
        self.send_header("Content-Type",  "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection",    "keep-alive")
        self._cors(); self.end_headers()

        def send(event_type, data):
            msg = f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
            try:
                self.wfile.write(msg.encode("utf-8"))
                self.wfile.flush()
            except Exception:
                pass
        try:
            runner_fn(send, **params)
        except Exception as e:
            send("error", {"message": str(e)})

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        qs     = urllib.parse.parse_qs(parsed.query)
        nicho   = qs.get("nicho",   [""])[0]
        precio  = qs.get("precio",  [""])[0]
        tipo    = qs.get("tipo",    [""])[0]
        objetivo= qs.get("objetivo",[""])[0]
        path   = parsed.path

        if path == "/ping":
            self.send_response(200); self._cors(); self.end_headers()
            self.wfile.write(b"pong"); return

        if path == "/run-system":
            self._sse_run(run_pipeline, {"nicho":nicho,"precio":precio,"tipo":tipo,"objetivo":objetivo}); return

        if path == "/run-atlas":
            self._sse_run(run_atlas_only, {"nicho":nicho,"precio":precio,"tipo":tipo}); return

        if path == "/historial":
            data = json.dumps(load_history(), ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self._cors(); self.end_headers()
            self.wfile.write(data); return

        if path in ["/", "/index.html"]:
            base = os.path.dirname(os.path.abspath(__file__))
            try:
                with open(os.path.join(base, "mis_agentes_jafero.html"), "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self._cors(); self.end_headers()
                self.wfile.write(content)
            except FileNotFoundError:
                self.send_error(404)
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path == "/api":
            length = int(self.headers.get("Content-Length", 0))
            body   = self.rfile.read(length)
            req = urllib.request.Request(
                "https://api.anthropic.com/v1/messages",
                data    = body,
                headers = {
                    "Content-Type"      : "application/json",
                    "x-api-key"         : API_KEY,
                    "anthropic-version" : "2023-06-01"
                },
                method = "POST"
            )
            try:
                with urllib.request.urlopen(req, timeout=60) as resp:
                    data = resp.read()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self._cors(); self.end_headers()
                self.wfile.write(data)
            except urllib.error.HTTPError as e:
                err = e.read()
                self.send_response(e.code)
                self.send_header("Content-Type", "application/json")
                self._cors(); self.end_headers()
                self.wfile.write(err)
        else:
            self.send_error(404)

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin",  "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")


if __name__ == "__main__":
    print(f"\n{'═'*50}")
    print(f"  MIS AGENTES JAFERO · Backend Pro")
    print(f"  Modelo: {MODEL}")
    print(f"  Puerto: {PORT}")
    print(f"{'═'*50}\n")
    server = http.server.HTTPServer(("0.0.0.0", PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Servidor apagado.")
