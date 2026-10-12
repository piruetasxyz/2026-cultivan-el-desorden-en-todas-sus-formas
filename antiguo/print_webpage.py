#!/usr/bin/env python3
"""
Captura una web en formato movil (scroll completo del home) y la imprime
en la impresora termica ESC/POS (TX-30 II / printer-80) por USB.
"""

import sys
from playwright.sync_api import sync_playwright
from PIL import Image
from escpos.printer import Usb
from escpos.exceptions import USBNotFoundError
import usb.core

VENDOR_ID = 0x0483
PRODUCT_ID = 0x5743

URL = "https://bibliotecacuir.org/"
SCREENSHOT_PATH = "webpage_capture.png"

# Viewport tipo telefono (ancho de iPhone estandar)
MOBILE_WIDTH = 390
MOBILE_HEIGHT = 844

# Ancho de impresion en pixeles. Una impresora de 80mm suele imprimir
# a 576 px de ancho (203 dpi). Si el resultado sale recortado o con
# margenes raros, ajusta este valor (comunes: 384 para 58mm, 576 para 80mm).
PRINTER_WIDTH_PX = 576


def capture_full_page(url: str, out_path: str) -> None:
    print(f"Abriendo {url} en viewport movil ({MOBILE_WIDTH}x{MOBILE_HEIGHT})...")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(
            viewport={"width": MOBILE_WIDTH, "height": MOBILE_HEIGHT},
            device_scale_factor=2,
            is_mobile=True,
            has_touch=True,
        )
        page.goto(url, wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(1000)

        # Recorrer la pagina con scroll real para disparar el lazy-loading
        # de imagenes (un screenshot full_page NO hace scroll de verdad,
        # asi que las imagenes con IntersectionObserver quedan en blanco
        # si no se fuerza el scroll antes).
        prev_height = 0
        while True:
            height = page.evaluate("document.body.scrollHeight")
            page.mouse.wheel(0, height)
            page.wait_for_timeout(400)
            new_height = page.evaluate("document.body.scrollHeight")
            if new_height == prev_height:
                break
            prev_height = new_height

        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(500)
        page.screenshot(path=out_path, full_page=True)
        device_scale_factor = 2
        browser.close()
    print(f"Captura guardada en {out_path}")

    # Algunos carruseles/sliders del sitio se extienden mas alla del viewport
    # (dejan "asomar" la siguiente diapositiva), lo que genera un desborde
    # horizontal capturado por el screenshot full_page. Recortamos al ancho
    # real del viewport movil para eliminar ese sobrante.
    crop_width = MOBILE_WIDTH * device_scale_factor
    img = Image.open(out_path)
    if img.width > crop_width:
        print(f"Recortando desborde horizontal: {img.width}px -> {crop_width}px")
        img.crop((0, 0, crop_width, img.height)).save(out_path)


def resize_for_printer(img_path: str, target_width: int) -> str:
    img = Image.open(img_path)
    w, h = img.size
    new_h = int(h * (target_width / w))
    img = img.convert("RGB").resize((target_width, new_h), Image.LANCZOS)
    resized_path = "webpage_capture_resized.png"
    img.save(resized_path)
    print(f"Imagen redimensionada a {target_width}x{new_h} -> {resized_path}")
    return resized_path


def print_image(img_path: str) -> None:
    device = usb.core.find(idVendor=VENDOR_ID, idProduct=PRODUCT_ID)
    if device is None:
        print("ERROR: no se encontro la impresora USB.")
        sys.exit(1)

    try:
        printer = Usb(VENDOR_ID, PRODUCT_ID, profile="default")
        printer.image(img_path)
        printer.text("\n")
        printer.cut()
        print("Impresion enviada y papel cortado.")
    except USBNotFoundError as e:
        print(f"ERROR: no se pudo abrir el dispositivo USB: {e}")
        sys.exit(1)
    except usb.core.USBError as e:
        print(f"ERROR de USB (posible problema de permisos): {e}")
        sys.exit(1)


def main():
    capture_full_page(URL, SCREENSHOT_PATH)
    resized = resize_for_printer(SCREENSHOT_PATH, PRINTER_WIDTH_PX)
    print_image(resized)


if __name__ == "__main__":
    main()
