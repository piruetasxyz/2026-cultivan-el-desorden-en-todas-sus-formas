#!/usr/bin/env python3
"""
Interfaz web local (solo accesible desde tu Mac) con botones para
capturar bibliotecacuir.org e imprimirla en la termica USB.

Uso:
    python3 print_server.py
    (luego abre http://127.0.0.1:5005 en tu navegador)
"""

import os
import threading
import time

from flask import Flask, Response, jsonify, request, send_file

import printer_lib

app = Flask(__name__)
print_lock = threading.Lock()
last_output_path = printer_lib.RESIZED_PATH

PAGE = """<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>Imprimir bibliotecacuir.org</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  :root { color-scheme: light dark; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, sans-serif;
    max-width: 480px;
    margin: 2rem auto;
    padding: 0 1rem;
  }
  h1 { font-size: 1.3rem; }
  .card {
    border: 1px solid #8884;
    border-radius: 12px;
    padding: 1rem 1.25rem;
    margin-bottom: 1rem;
  }
  button {
    font-size: 1rem;
    padding: 0.75rem 1rem;
    width: 100%;
    border-radius: 8px;
    border: none;
    background: #d6336c;
    color: white;
    cursor: pointer;
  }
  button:disabled { background: #8888; cursor: not-allowed; }
  input[type=number] {
    font-size: 1rem;
    padding: 0.4rem;
    width: 5rem;
    margin: 0 0.5rem;
  }
  #status {
    min-height: 1.5rem;
    margin-top: 0.75rem;
    font-size: 0.95rem;
  }
  #preview {
    max-width: 100%;
    border: 1px solid #8884;
    border-radius: 8px;
    margin-top: 1rem;
    display: none;
  }
  label { display: flex; align-items: center; }
  .qty-options {
    display: flex;
    gap: 1.25rem;
    flex-wrap: wrap;
  }
  .qty-options label { width: auto; }
</style>
</head>
<body>
  <h1>Imprimir bibliotecacuir.org</h1>

  <div class="card">
    <label>Ancho de rollo puesto en la impresora:</label>
    <br><br>
    <label><input type="radio" name="roll" value="80mm"> 80mm (rollo ancho, ~8cm)</label>
    <br>
    <label><input type="radio" name="roll" value="58mm" checked> 58mm (rollo angosto, ~56mm)</label>
  </div>

  <div class="card">
    <label>Que imprimir:</label>
    <br><br>
    <label><input type="radio" name="source" value="web" checked> Sitio web (bibliotecacuir.org)</label>
    <br>
    <label><input type="radio" name="source" value="code"> Codigo fuente (index.html)</label>
  </div>

  <div class="card">
    <label>Cantidad de copias (cada una es una captura distinta):</label>
    <br><br>
    <div class="qty-options">
      <label><input type="radio" name="qty" value="1" checked> x1</label>
      <label><input type="radio" name="qty" value="2"> x2</label>
      <label><input type="radio" name="qty" value="5"> x5</label>
      <label><input type="radio" name="qty" value="10"> x10</label>
    </div>
  </div>

  <div class="card">
    <button id="btn-long" onclick="doPrint('long')">Imprimir formato LARGO (scroll completo)</button>
  </div>

  <div class="card">
    <label for="cm">Imprimir formato CORTO, largo:
      <input type="number" id="cm" value="20" min="2" max="200" step="1"> cm
    </label>
    <br><br>
    <button id="btn-short" onclick="doPrint('short')">Imprimir formato CORTO</button>
  </div>

  <div id="status"></div>
  <img id="preview" alt="Ultima captura impresa">

<script>
async function doPrint(mode) {
  const btnLong = document.getElementById('btn-long');
  const btnShort = document.getElementById('btn-short');
  const status = document.getElementById('status');
  const preview = document.getElementById('preview');

  const qty = parseInt(document.querySelector('input[name="qty"]:checked').value, 10);
  const roll = document.querySelector('input[name="roll"]:checked').value;
  const source = document.querySelector('input[name="source"]:checked').value;
  const body = mode === 'short'
    ? { cm: parseFloat(document.getElementById('cm').value), roll: roll, source: source }
    : { roll: roll, source: source };

  btnLong.disabled = true;
  btnShort.disabled = true;

  for (let i = 1; i <= qty; i++) {
    status.textContent = qty > 1
      ? `Imprimiendo copia ${i} de ${qty}... (puede tardar unos segundos por copia)`
      : 'Generando e imprimiendo... (puede tardar unos segundos)';

    try {
      const res = await fetch('/print/' + mode, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });
      const data = await res.json();
      if (data.ok) {
        preview.src = '/last_capture.png?t=' + Date.now();
        preview.style.display = 'block';
      } else {
        status.textContent = `Error en la copia ${i} de ${qty}: ` + data.error;
        break;
      }
    } catch (err) {
      status.textContent = `Error de conexion en la copia ${i} de ${qty}: ` + err;
      break;
    }

    if (i === qty) {
      status.textContent = qty > 1
        ? `Listo, se imprimieron las ${qty} copias.`
        : 'Listo, se imprimio y corto el papel.';
    }
  }

  btnLong.disabled = false;
  btnShort.disabled = false;
}
</script>
</body>
</html>
"""


@app.route("/")
def index():
    return Response(PAGE, mimetype="text/html")


@app.route("/last_capture.png")
def last_capture():
    if os.path.exists(last_output_path):
        return send_file(last_output_path, mimetype="image/png")
    return ("", 404)


@app.route("/print/<mode>", methods=["POST"])
def do_print(mode):
    if mode not in ("long", "short"):
        return jsonify(ok=False, error="Modo invalido"), 400

    if not print_lock.acquire(blocking=False):
        return jsonify(ok=False, error="Ya hay una impresion en curso, espera a que termine."), 429

    try:
        data = request.get_json(silent=True) or {}
        roll = data.get("roll", printer_lib.DEFAULT_ROLL)
        if roll not in printer_lib.ROLL_PRESETS_PX:
            return jsonify(ok=False, error="Ancho de rollo invalido"), 400

        source = data.get("source", "web")
        if source not in ("web", "code"):
            return jsonify(ok=False, error="Fuente invalida"), 400

        cm = None
        if mode == "short":
            try:
                cm = float(data.get("cm", 20))
            except (TypeError, ValueError):
                return jsonify(ok=False, error="Valor de cm invalido"), 400
            if cm <= 0:
                return jsonify(ok=False, error="El largo en cm debe ser mayor a 0"), 400

        global last_output_path
        if source == "code":
            last_output_path = printer_lib.run_code_print_job(mode, cm=cm, roll=roll)
        else:
            last_output_path = printer_lib.run_print_job(mode, cm=cm, roll=roll)
        return jsonify(ok=True)
    except printer_lib.PrinterError as e:
        return jsonify(ok=False, error=str(e)), 500
    except Exception as e:
        return jsonify(ok=False, error=f"Error inesperado: {e}"), 500
    finally:
        print_lock.release()


if __name__ == "__main__":
    print("Abriendo interfaz en http://127.0.0.1:5005")
    app.run(host="127.0.0.1", port=5005, debug=False)
