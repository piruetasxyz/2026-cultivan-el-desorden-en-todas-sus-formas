#!/usr/bin/env python3
"""
Servidor web para la red local: las personas escanean un QR con su
telefono, escriben un texto y se imprime en la impresora termica.

Uso:
    .venv/bin/python nuevo/servidor.py            # imprime el QR al iniciar
    .venv/bin/python nuevo/servidor.py --sin-qr   # no imprime el QR
"""

from __future__ import annotations

import math
import os
import re
import socket
import sys
import threading

import qrcode
from flask import Flask, Response, jsonify, request, send_from_directory
from PIL import Image, ImageDraw, ImageFont

import impresora

PUERTO = 5050
LARGO_MAXIMO = 250  # caracteres por mensaje

# Space Mono, incluida en el repo (licencia OFL, ver fuentes/SpaceMono/OFL.txt).
FUENTES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "fuentes", "SpaceMono")
FUENTE_REGULAR_PATH = os.path.join(FUENTES_DIR, "SpaceMono-Regular.ttf")
FUENTE_BOLD_PATH = os.path.join(FUENTES_DIR, "SpaceMono-Bold.ttf")
TAMANO_TEXTO = 26
TAMANO_TEXTO_MINIMO = 14
TAMANO_PIE = 18
INTERLINEADO = 1.3
PADDING = 12

# Todos los recibos tienen el mismo largo: el alto del texto alcanza para un
# mensaje de LARGO_MAXIMO caracteres (mas 2 lineas de holgura por el corte
# de palabras). Space Mono es monoespaciada, asi que todos los caracteres
# miden lo mismo.
_ancho_caracter = ImageFont.truetype(FUENTE_REGULAR_PATH, TAMANO_TEXTO).getlength("M")
COLUMNAS = int((impresora.ANCHO_PAPEL_PX - 2 * PADDING) // _ancho_caracter)
LINEAS_FIJAS = math.ceil(LARGO_MAXIMO / COLUMNAS) + 2
ALTO_TEXTO_PX = LINEAS_FIJAS * int(TAMANO_TEXTO * INTERLINEADO)

app = Flask(__name__)
candado_impresion = threading.Lock()

PAGINA = """<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Escribe algo</title>
<style>
  @font-face {
    font-family: "Space Mono";
    src: url("/fuentes/SpaceMono-Regular.ttf") format("truetype");
  }
  @font-face {
    font-family: "Space Mono";
    font-weight: bold;
    src: url("/fuentes/SpaceMono-Bold.ttf") format("truetype");
  }
  :root { color-scheme: light dark; --acento: #d6336c; }
  body {
    font-family: "Space Mono", monospace;
    max-width: 480px;
    margin: 0 auto;
    padding: 1.5rem 1rem;
  }
  h1 { font-size: 1.4rem; margin: 0 0 1rem; }
  textarea {
    box-sizing: border-box;
    width: 100%;
    min-height: 12rem;
    font-size: 1.1rem;
    font-family: inherit;
    padding: 0.75rem;
    border: 1px solid #8886;
    border-radius: 12px;
    resize: vertical;
  }
  #contador { text-align: right; font-size: 0.85rem; opacity: 0.6; margin: 0.25rem 0 1rem; }
  button {
    font-size: 1.1rem;
    padding: 0.9rem 1rem;
    width: 100%;
    border-radius: 12px;
    border: none;
    background: var(--acento);
    color: white;
  }
  button:disabled { background: #8888; }
  #estado { min-height: 1.5rem; margin-top: 1rem; }
</style>
</head>
<body>
  <h1>Escribe algo y se imprime</h1>
  <textarea id="texto" maxlength="__LARGO_MAXIMO__" placeholder="Tu mensaje..."></textarea>
  <div id="contador">0 / __LARGO_MAXIMO__</div>
  <button id="boton" onclick="enviar()">Imprimir</button>
  <div id="estado"></div>

<script>
const texto = document.getElementById('texto');
const contador = document.getElementById('contador');
const boton = document.getElementById('boton');
const estado = document.getElementById('estado');

texto.addEventListener('input', () => {
  contador.textContent = texto.value.length + ' / __LARGO_MAXIMO__';
});

async function enviar() {
  if (!texto.value.trim()) {
    estado.textContent = 'Escribe algo primero.';
    return;
  }
  boton.disabled = true;
  estado.textContent = 'Imprimiendo...';
  try {
    const res = await fetch('/imprimir', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ texto: texto.value })
    });
    const datos = await res.json();
    if (datos.ok) {
      estado.textContent = 'Listo, ya se imprimio.';
      texto.value = '';
      contador.textContent = '0 / __LARGO_MAXIMO__';
    } else {
      estado.textContent = 'Error: ' + datos.error;
    }
  } catch (err) {
    estado.textContent = 'Error de conexion: ' + err;
  }
  boton.disabled = false;
}
</script>
</body>
</html>
""".replace("__LARGO_MAXIMO__", str(LARGO_MAXIMO))


def obtener_ip_local() -> str:
    """IP de este computador en la red local. Se puede fijar con la variable
    de entorno IP_SERVIDOR (util en redes sin internet, donde la deteccion
    automatica falla). Conectar un socket UDP no envia paquetes, solo elige
    la interfaz de salida."""
    if os.environ.get("IP_SERVIDOR"):
        return os.environ["IP_SERVIDOR"]
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def partir_en_lineas(texto: str, fuente: ImageFont.FreeTypeFont, ancho_max: int) -> list[str]:
    """Separa `texto` en lineas que caben en `ancho_max` px, respetando los
    saltos de linea y partiendo palabras demasiado largas."""
    lineas = []
    for parrafo in texto.split("\n"):
        actual = ""
        for palabra in parrafo.split(" "):
            while fuente.getlength(palabra) > ancho_max:
                corte = len(palabra)
                while corte > 1 and fuente.getlength(palabra[:corte]) > ancho_max:
                    corte -= 1
                if actual:
                    lineas.append(actual)
                    actual = ""
                lineas.append(palabra[:corte])
                palabra = palabra[corte:]
            candidata = f"{actual} {palabra}" if actual else palabra
            if fuente.getlength(candidata) <= ancho_max:
                actual = candidata
            else:
                lineas.append(actual)
                actual = palabra
        lineas.append(actual)
    return lineas


def renderizar_texto(texto: str) -> Image.Image:
    """Recibo de alto fijo. Si el texto no cabe (por ejemplo, con muchos
    saltos de linea) se achica la letra; si aun asi no cabe con el tamano
    minimo, se cortan las lineas que sobran."""
    ancho = impresora.ANCHO_PAPEL_PX
    texto = re.sub(r"\n{3,}", "\n\n", texto)

    tamano = TAMANO_TEXTO
    while True:
        fuente = ImageFont.truetype(FUENTE_REGULAR_PATH, tamano)
        alto_linea = int(tamano * INTERLINEADO)
        lineas = partir_en_lineas(texto, fuente, ancho - 2 * PADDING)
        if len(lineas) * alto_linea <= ALTO_TEXTO_PX or tamano <= TAMANO_TEXTO_MINIMO:
            break
        tamano -= 1
    lineas = lineas[:ALTO_TEXTO_PX // alto_linea]

    alto = PADDING + ALTO_TEXTO_PX + PADDING
    imagen = Image.new("RGB", (ancho, alto), "white")
    dibujo = ImageDraw.Draw(imagen)
    for i, linea in enumerate(lineas):
        dibujo.text((PADDING, PADDING + i * alto_linea), linea, font=fuente, fill="black")
    return imagen


def renderizar_qr(url: str) -> Image.Image:
    ancho = impresora.ANCHO_PAPEL_PX
    fuente_titulo = ImageFont.truetype(FUENTE_BOLD_PATH, TAMANO_TEXTO)
    fuente_url = ImageFont.truetype(FUENTE_REGULAR_PATH, TAMANO_PIE)

    qr = qrcode.QRCode(border=2)
    qr.add_data(url)
    qr.make(fit=True)
    lado_qr = ancho - 4 * PADDING
    imagen_qr = qr.make_image().convert("RGB").resize((lado_qr, lado_qr), Image.NEAREST)

    titulo = "Escanea y escribe"
    alto = PADDING + TAMANO_TEXTO + PADDING + lado_qr + PADDING + TAMANO_PIE + PADDING * 2
    imagen = Image.new("RGB", (ancho, alto), "white")
    dibujo = ImageDraw.Draw(imagen)
    dibujo.text(((ancho - fuente_titulo.getlength(titulo)) / 2, PADDING), titulo,
                font=fuente_titulo, fill="black")
    y_qr = PADDING * 2 + TAMANO_TEXTO
    imagen.paste(imagen_qr, ((ancho - lado_qr) // 2, y_qr))
    dibujo.text(((ancho - fuente_url.getlength(url)) / 2, y_qr + lado_qr + PADDING), url,
                font=fuente_url, fill="black")
    return imagen


@app.route("/")
def inicio():
    return Response(PAGINA, mimetype="text/html")


@app.route("/fuentes/<nombre>")
def fuentes(nombre):
    return send_from_directory(FUENTES_DIR, nombre)


@app.route("/imprimir", methods=["POST"])
def imprimir():
    datos = request.get_json(silent=True) or {}
    texto = str(datos.get("texto", "")).strip()
    if not texto:
        return jsonify(ok=False, error="El mensaje esta vacio."), 400
    if len(texto) > LARGO_MAXIMO:
        return jsonify(ok=False, error=f"Maximo {LARGO_MAXIMO} caracteres."), 400

    # Si hay varias personas enviando a la vez, se imprimen de a una.
    with candado_impresion:
        try:
            impresora.imprimir_imagen(renderizar_texto(texto))
        except impresora.ErrorImpresora as e:
            return jsonify(ok=False, error=str(e)), 500
    print(f"Impreso: {texto!r}")
    return jsonify(ok=True)


if __name__ == "__main__":
    url = f"http://{obtener_ip_local()}:{PUERTO}"
    print(f"Abre {url} desde un telefono conectado a la misma red Wi-Fi.")
    if "--sin-qr" not in sys.argv:
        try:
            impresora.imprimir_imagen(renderizar_qr(url))
            print("QR impreso.")
        except impresora.ErrorImpresora as e:
            print(f"No se pudo imprimir el QR: {e}")
    app.run(host="0.0.0.0", port=PUERTO, debug=False, threaded=True)
