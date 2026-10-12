#!/usr/bin/env python3
"""
Funciones reutilizables para capturar bibliotecacuir.org en formato movil
e imprimirla en la impresora termica ESC/POS (TX-30 II / printer-80) por USB.
"""

from __future__ import annotations

import os
import random
import time
import urllib.request
from playwright.sync_api import sync_playwright
from PIL import Image, ImageDraw, ImageFont
from escpos.printer import Usb
from escpos.exceptions import USBNotFoundError
import usb.core

VENDOR_ID = 0x0483
PRODUCT_ID = 0x5743

URL = "https://bibliotecacuir.org/"
SCREENSHOT_PATH = os.path.join(os.path.dirname(__file__), "webpage_capture.png")
RESIZED_PATH = os.path.join(os.path.dirname(__file__), "webpage_capture_resized.png")

# Viewport tipo telefono (ancho de iPhone estandar)
MOBILE_WIDTH = 390
MOBILE_HEIGHT = 844
DEVICE_SCALE_FACTOR = 2

# Anchos de impresion estandar segun el rollo de papel puesto en la misma
# impresora (8 dots/mm, valores tipicos de la industria para clones ESC/POS).
ROLL_PRESETS_PX = {
    "80mm": 576,
    "58mm": 384,
}
DEFAULT_ROLL = "58mm"
PRINTER_WIDTH_PX = ROLL_PRESETS_PX[DEFAULT_ROLL]
DOTS_PER_MM = 8  # dots por milimetro, igual en horizontal y vertical

# La impresora esta configurada para rollo de 80mm (576 dots) y empieza a
# imprimir en el borde izquierdo del cabezal. Con un rollo de 58mm el papel
# no cubre ese borde, asi que se agrega un margen blanco a la izquierda de
# cada imagen. El valor se obtiene con calibrar_ancho.py (0 = sin margen).
# Calibrado con rollo de 58mm: el papel cubre aprox. de 48 a 462 dots, asi
# que 64 deja la imagen de 384 px centrada.
ANCHO_CABEZAL_PX = 576
MARGEN_IZQUIERDO_PX = int(os.environ.get("MARGEN_IZQUIERDO_PX", "64"))

MONTSERRAT_PATH = os.path.expanduser("~/Library/Fonts/Montserrat[wght].ttf")
# Si Montserrat no esta instalada, se usa Helvetica Bold (indice 1 del .ttc).
FALLBACK_FONT_PATH = "/System/Library/Fonts/Helvetica.ttc"
FALLBACK_FONT_INDEX = 1
HEADER_TEXT = "bibliotecacuir.org"

# La imagen del hero del home NO cambia sola al cargar la pagina (es un
# carrusel que solo avanza si el usuario lo desliza a mano), por eso cada
# captura salia identica. Estas son las 9 imagenes que existen en el
# servidor (assets/home/home-slide-01.webp ... 09.webp); forzamos una al
# azar antes de la captura para que cada impresion sea distinta.
HOME_SLIDE_COUNT = 9

# Copia local del repo del sitio, para poder imprimir su codigo fuente.
# Se puede cambiar con la variable de entorno REPO_ROOT. Si el archivo no
# existe localmente, se descarga en vivo desde el sitio (URL + ruta).
REPO_ROOT = os.environ.get(
    "REPO_ROOT",
    os.path.join(os.path.dirname(__file__), "bibliotecacuir.github.io"),
)
CODE_LISTING_PATH = os.path.join(os.path.dirname(__file__), "code_listing.png")
CODE_FONT_PATH = "/System/Library/Fonts/Menlo.ttc"


class PrinterError(Exception):
    """Error al comunicarse con la impresora USB."""


def capture_full_page(url: str = URL, out_path: str = SCREENSHOT_PATH) -> str:
    # OJO: se probo mantener un navegador Chromium persistente entre
    # impresiones (para ahorrar 1-2s de arranque), pero la API sincronica
    # de Playwright esta atada al hilo del sistema operativo donde se creo
    # ("cannot switch to a different thread"). El servidor Flask no
    # garantiza que cada request se maneje en el mismo hilo, asi que un
    # navegador reusado entre requests fallaba de forma intermitente.
    # Por eso se lanza un Chromium nuevo en cada captura: es mas lento
    # pero confiable.
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(
            viewport={"width": MOBILE_WIDTH, "height": MOBILE_HEIGHT},
            device_scale_factor=DEVICE_SCALE_FACTOR,
            is_mobile=True,
            has_touch=True,
        )
        try:
            # Parametro anti-cache: garantiza que cada captura sea una carga
            # en vivo del sitio (nunca una respuesta cacheada), asi las
            # imagenes que el sitio muestra al azar en cada visita cambian
            # entre impresiones.
            sep = "&" if "?" in url else "?"
            live_url = f"{url}{sep}_ts={int(time.time() * 1000)}"
            page.goto(live_url, wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(500)

            # Recorrer la pagina con scroll real para disparar el lazy-loading
            # de imagenes (un screenshot full_page NO hace scroll de verdad,
            # asi que las imagenes con IntersectionObserver quedan en blanco
            # si no se fuerza el scroll antes).
            prev_height = 0
            while True:
                height = page.evaluate("document.body.scrollHeight")
                page.mouse.wheel(0, height)
                page.wait_for_timeout(250)
                new_height = page.evaluate("document.body.scrollHeight")
                if new_height == prev_height:
                    break
                prev_height = new_height

            page.evaluate("window.scrollTo(0, 0)")
            page.wait_for_timeout(300)

            # Forzar una imagen de hero al azar (ver nota en HOME_SLIDE_COUNT):
            # el carrusel no autoavanza, asi que sin esto cada captura
            # mostraba siempre la misma foto inicial. Se hace al final,
            # justo antes del screenshot, porque el sitio re-renderiza el
            # hero durante el scroll y revierte cualquier cambio anterior.
            slide_num = random.randint(1, HOME_SLIDE_COUNT)
            new_src = f"{url.split('?')[0].rstrip('/')}/assets/home/home-slide-{slide_num:02d}.webp"
            # Esperamos a que la nueva imagen termine de cargar (no un
            # tiempo fijo): si el <img> no tiene un alto fijo por CSS, una
            # foto con proporciones distintas puede correr el layout de
            # toda la pagina despues de que ya medimos su altura,
            # desincronizando las rebanadas de la captura.
            page.evaluate(
                """(src) => new Promise((resolve) => {
                    const el = document.querySelector('.presentacion-diapositiva.esta-activo');
                    if (!el) return resolve();
                    const done = () => resolve();
                    el.addEventListener('load', done, { once: true });
                    el.addEventListener('error', done, { once: true });
                    el.src = src;
                    if (el.complete) resolve();
                })""",
                new_src,
            )
            page.wait_for_timeout(200)

            # Mas abajo del hero hay un "carrusel ovalado"
            # (.ovalo-carrusel-elemento) que rota en todo momento via JS
            # (una animacion continua tipo orbita, no slides discretos).
            # Esperamos un tiempo extra aleatorio para que cada captura
            # quede en una fase distinta del giro, en vez de siempre la
            # misma. El rango se recorto (era 0-15s) para que las
            # impresiones no demoren tanto; sigue cubriendo una porcion
            # util del ciclo de ~24s.
            page.wait_for_timeout(int(random.uniform(0, 6000)))

            # NO se puede usar screenshot(full_page=True): Playwright lo
            # logra cambiando el tamano del viewport justo antes de
            # capturar, y ese resize CONGELA para siempre la animacion del
            # carrusel ovalado (confirmado: tras cualquier resize, siempre
            # queda en el mismo frame inicial sin importar cuanto se espere
            # despues). En cambio, hacer scroll normal NO la congela. Por
            # eso armamos la captura completa a mano: sacamos "rebanadas"
            # del viewport mientras scrolleamos, y las pegamos con Pillow.
            total_height = page.evaluate("document.body.scrollHeight")
            viewport_h = MOBILE_HEIGHT

            positions = list(range(0, total_height, viewport_h))
            if not positions:
                positions = [0]
            # la ultima rebanada se alinea contra el fondo real (puede
            # solaparse con la anterior) para no dejar un hueco en blanco
            # al final.
            positions[-1] = max(0, total_height - viewport_h)

            slice_paths = []
            for idx, y in enumerate(positions):
                page.evaluate(f"window.scrollTo(0, {y})")
                page.wait_for_timeout(400)
                slice_path = f"{out_path}.slice{idx}.png"
                page.screenshot(path=slice_path)
                slice_paths.append((y, slice_path))
        finally:
            browser.close()

    canvas = None
    for y, slice_path in slice_paths:
        slice_img = Image.open(slice_path)
        if canvas is None:
            canvas = Image.new(
                "RGB",
                (slice_img.width, total_height * DEVICE_SCALE_FACTOR),
                "white",
            )
        canvas.paste(slice_img, (0, y * DEVICE_SCALE_FACTOR))
        os.remove(slice_path)
    canvas.save(out_path)

    # Algunos carruseles/sliders del sitio se extienden mas alla del viewport
    # (dejan "asomar" la siguiente diapositiva), generando un desborde
    # horizontal en el screenshot full_page. Recortamos al ancho real del
    # viewport movil para eliminar ese sobrante.
    crop_width = MOBILE_WIDTH * DEVICE_SCALE_FACTOR
    img = Image.open(out_path)
    if img.width > crop_width:
        img.crop((0, 0, crop_width, img.height)).save(out_path)

    return out_path


def resize_for_printer(img_path: str, target_width: int = PRINTER_WIDTH_PX,
                        out_path: str = RESIZED_PATH) -> str:
    img = Image.open(img_path)
    w, h = img.size
    new_h = int(h * (target_width / w))
    img = img.convert("RGB").resize((target_width, new_h), Image.LANCZOS)
    img.save(out_path)
    return out_path


def crop_to_height_cm(img_path: str, cm: float) -> str:
    """Recorta la imagen (desde arriba) a una altura equivalente a `cm` centimetros
    de papel impreso. Si la imagen es mas corta que eso, la deja intacta."""
    img = Image.open(img_path)
    height_px = min(int(cm * 10 * DOTS_PER_MM), img.height)
    img.crop((0, 0, img.width, height_px)).save(img_path)
    return img_path


def make_header_image(width_px: int, text: str = HEADER_TEXT) -> Image.Image:
    """Genera una tira blanca con `text` centrado en Montserrat Bold,
    del ancho exacto de impresion, para pegar arriba de la captura."""
    font_size = max(12, width_px // 14)
    if os.path.exists(MONTSERRAT_PATH):
        font = ImageFont.truetype(MONTSERRAT_PATH, font_size)
        try:
            font.set_variation_by_name("Bold")
        except OSError:
            pass  # si la variacion no esta disponible, sigue con el peso default
    else:
        font = ImageFont.truetype(FALLBACK_FONT_PATH, font_size, index=FALLBACK_FONT_INDEX)

    padding = font_size // 2
    tmp = Image.new("RGB", (width_px, 10), "white")
    draw = ImageDraw.Draw(tmp)
    bbox = draw.textbbox((0, 0), text, font=font)
    text_h = bbox[3] - bbox[1]

    header_h = text_h + padding * 2
    header = Image.new("RGB", (width_px, header_h), "white")
    draw = ImageDraw.Draw(header)
    text_w = bbox[2] - bbox[0]
    draw.text(((width_px - text_w) / 2 - bbox[0], padding - bbox[1]),
               text, font=font, fill="black")
    return header


def make_code_listing_image(text: str, width_px: int) -> Image.Image:
    """Renderiza `text` como un listado de codigo monoespaciado (con numeros
    de linea), del ancho exacto de impresion."""
    font_size = max(10, round(width_px / 32))
    font = ImageFont.truetype(CODE_FONT_PATH, font_size, index=0)
    char_w = font.getlength("M")
    line_height = font_size + 6
    padding = 10

    raw_lines = text.replace("\t", "  ").split("\n")
    total_lines = len(raw_lines)
    gutter_digits = len(str(total_lines))
    gutter_chars = gutter_digits + 1
    content_chars = max(10, int((width_px - 2 * padding) / char_w) - gutter_chars)

    rows: list[tuple[int | None, str]] = []
    for num, line in enumerate(raw_lines, start=1):
        if line == "":
            rows.append((num, ""))
            continue
        chunks = [line[i:i + content_chars] for i in range(0, len(line), content_chars)]
        rows.append((num, chunks[0]))
        for cont in chunks[1:]:
            rows.append((None, cont))

    height = padding * 2 + len(rows) * line_height
    img = Image.new("RGB", (width_px, height), "white")
    draw = ImageDraw.Draw(img)
    gutter_px = int(gutter_chars * char_w)

    for idx, (num, content) in enumerate(rows):
        y = padding + idx * line_height
        if num is not None:
            draw.text((padding, y), str(num).rjust(gutter_digits),
                       font=font, fill=(150, 150, 150))
        draw.text((padding + gutter_px, y), content, font=font, fill="black")

    return img


def run_code_print_job(mode: str, cm: float | None = None, roll: str = DEFAULT_ROLL,
                        relative_path: str = "index.html") -> str:
    """mode: 'long' (archivo completo) o 'short' (recortado a `cm` centimetros).
    Imprime el codigo fuente de un archivo del repo local de bibliotecaCuir."""
    width_px = ROLL_PRESETS_PX.get(roll, PRINTER_WIDTH_PX)

    file_path = os.path.join(REPO_ROOT, relative_path)
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()
    else:
        with urllib.request.urlopen(URL + relative_path, timeout=30) as res:
            text = res.read().decode("utf-8")

    header = make_header_image(width_px, text=relative_path)
    body = make_code_listing_image(text, width_px)
    combined = Image.new("RGB", (width_px, header.height + body.height), "white")
    combined.paste(header, (0, 0))
    combined.paste(body, (0, header.height))
    combined.save(CODE_LISTING_PATH)

    if mode == "short":
        crop_to_height_cm(CODE_LISTING_PATH, cm or 20)

    print_image(CODE_LISTING_PATH)
    return CODE_LISTING_PATH


def agregar_margen_izquierdo(img_path: str, margen_px: int) -> str:
    """Pega la imagen a `margen_px` del borde izquierdo de un lienzo blanco
    del ancho completo del cabezal (la impresora corre hacia la derecha las
    imagenes mas angostas que el cabezal)."""
    img = Image.open(img_path).convert("RGB")
    con_margen = Image.new("RGB", (ANCHO_CABEZAL_PX, img.height), "white")
    con_margen.paste(img, (margen_px, 0))
    ruta = f"{os.path.splitext(img_path)[0]}_margen.png"
    con_margen.save(ruta)
    return ruta


def print_image(img_path: str, margen_px: int | None = None) -> None:
    if margen_px is None:
        margen_px = MARGEN_IZQUIERDO_PX
    if margen_px > 0:
        img_path = agregar_margen_izquierdo(img_path, margen_px)

    device = usb.core.find(idVendor=VENDOR_ID, idProduct=PRODUCT_ID)
    if device is None:
        raise PrinterError(
            "No se encontro la impresora USB. Revisa que este conectada y encendida."
        )
    printer = None
    try:
        printer = Usb(VENDOR_ID, PRODUCT_ID, profile="default")
        # ESC @: reinicia margenes/anchos guardados en la impresora, para que
        # solo cuente el margen que se agrega a la imagen.
        printer.hw("INIT")
        printer.image(img_path)
        printer.text("\n")
        printer.cut()
    except USBNotFoundError as e:
        raise PrinterError(f"No se pudo abrir el dispositivo USB: {e}") from e
    except usb.core.USBError as e:
        raise PrinterError(f"Error de USB (posible problema de permisos): {e}") from e
    finally:
        # Sin esto, el proceso del servidor (que vive entre impresiones) se
        # queda con el USB reclamado en exclusiva y la SIGUIENTE impresion
        # falla con "Access denied", aunque la impresora este bien.
        if printer is not None:
            printer.close()


def run_print_job(mode: str, cm: float | None = None, url: str = URL,
                   roll: str = DEFAULT_ROLL) -> str:
    """mode: 'long' (scroll completo) o 'short' (recortado a `cm` centimetros).
    roll: '80mm' o '58mm', segun el rollo de papel puesto en la impresora.
    Devuelve la ruta de la imagen que efectivamente se envio a imprimir."""
    width_px = ROLL_PRESETS_PX.get(roll, PRINTER_WIDTH_PX)

    capture_full_page(url, SCREENSHOT_PATH)
    resized = resize_for_printer(SCREENSHOT_PATH, width_px)
    if mode == "short":
        crop_to_height_cm(resized, cm or 20)

    # Pegar el encabezado (URL en Montserrat) arriba de la captura final,
    # sin contar contra el limite de cm del formato corto.
    body = Image.open(resized)
    header = make_header_image(width_px)
    combined = Image.new("RGB", (width_px, header.height + body.height), "white")
    combined.paste(header, (0, 0))
    combined.paste(body, (0, header.height))
    combined.save(resized)

    print_image(resized)
    return resized
