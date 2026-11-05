"""Generate the application .ico and a preview PNG from the Qt mark."""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PIL import Image  # noqa: E402
from PySide6.QtGui import QGuiApplication  # noqa: E402

from qingdan.icons import make_app_pixmap  # noqa: E402

app = QGuiApplication([])
assets = ROOT / "assets"
assets.mkdir(exist_ok=True)

pixmap = make_app_pixmap(1024)
png_path = assets / "app.png"
pixmap.save(str(png_path))

image = Image.open(png_path).convert("RGBA")
image.save(
    assets / "app.ico",
    format="ICO",
    sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
)
print("wrote", png_path, "and", assets / "app.ico")
