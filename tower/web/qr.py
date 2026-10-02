"""QR codes for joining the AP and opening the app (design C14), via ``segno``."""

from __future__ import annotations

import io

import segno
import segno.helpers


def _svg(qr: segno.QRCode) -> bytes:
    buf = io.BytesIO()
    qr.save(buf, kind="svg", scale=8, border=2, dark="#000", light="#fff", xmldecl=False)
    return buf.getvalue()


def wifi_svg(ssid: str, psk: str) -> bytes:
    """A ``WIFI:`` URI: phones offer to join the network when they scan it."""
    return _svg(segno.helpers.make_wifi(ssid=ssid, password=psk, security="WPA"))


def url_svg(url: str) -> bytes:
    return _svg(segno.make(url, error="m"))
