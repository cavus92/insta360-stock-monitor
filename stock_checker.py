import json
import os
import smtplib
import ssl
import sys
from dataclasses import dataclass
from email.message import EmailMessage
from pathlib import Path
from typing import Any

import requests

STATE_FILE = Path("state.json")
TIMEOUT = 20

PRODUCTS = [
    {
        "name": "Insta360 Luna Ultra",
        "url": "https://shop.insta360turkiye.com/products/insta360-luna-ultra?variant=44055396417610",
        "handle": "insta360-luna-ultra",
        "variant_id": 44055396417610,
    },
    {
        "name": "Insta360 Mic Pro Transmitter",
        "url": "https://shop.insta360turkiye.com/products/insta360-mic-pro-transmitter?variant=44086311452746",
        "handle": "insta360-mic-pro-transmitter",
        "variant_id": 44086311452746,
    },
]

SESSION = requests.Session()
SESSION.headers.update(
    {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 Chrome/151.0 Safari/537.36"
        ),
        "Accept": "application/json,text/plain,*/*",
    }
)


@dataclass
class StockResult:
    name: str
    url: str
    available: bool
    variant_title: str
    price: str


def load_state() -> dict[str, bool]:
    if not STATE_FILE.exists():
        return {p["name"]: False for p in PRODUCTS}

    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        return {p["name"]: bool(data.get(p["name"], False)) for p in PRODUCTS}
    except (OSError, json.JSONDecodeError):
        return {p["name"]: False for p in PRODUCTS}


def save_state(state: dict[str, bool]) -> None:
    STATE_FILE.write_text(
        json.dumps(state, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def check_product(product: dict[str, Any]) -> StockResult:
    endpoint = (
        f"https://shop.insta360turkiye.com/products/"
        f"{product['handle']}.js"
        f"?variant={product['variant_id']}"
    )

    response = SESSION.get(endpoint, timeout=TIMEOUT)
    response.raise_for_status()
    data = response.json()

    variants = data.get("variants") or []
    variant = next(
        (v for v in variants if int(v.get("id", 0)) == product["variant_id"]),
        None,
    )

    if variant is None:
        raise RuntimeError(
            f"Variant {product['variant_id']} bulunamadı: {product['name']}"
        )

    return StockResult(
        name=product["name"],
        url=product["url"],
        available=bool(variant.get("available")),
        variant_title=str(variant.get("title") or "Default"),
        price=str(variant.get("price") or ""),
    )


def send_email(items: list[StockResult]) -> None:
    host = os.environ["SMTP_HOST"]
    port = int(os.environ.get("SMTP_PORT", "465"))
    username = os.environ["SMTP_USERNAME"]
    password = os.environ["SMTP_PASSWORD"]
    recipient = os.environ["ALERT_EMAIL"]

    subject = (
        "🚨 Insta360 stok bildirimi: "
        + ", ".join(item.name for item in items)
    )

    lines = [
        "Insta360 Türkiye mağazasında stok durumu değişti.",
        "",
    ]

    for item in items:
        lines.extend(
            [
                f"Ürün: {item.name}",
                f"Variant: {item.variant_title}",
                f"Fiyat: {item.price}",
                f"Link: {item.url}",
                "",
            ]
        )

    lines.append("Bu bildirim ürünün stok dışından stoğa geçtiği anda gönderildi.")

    message = EmailMessage()
    message["From"] = username
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content("\n".join(lines))

    context = ssl.create_default_context()

    if port == 465:
        with smtplib.SMTP_SSL(host, port, context=context) as server:
            server.login(username, password)
            server.send_message(message)
    else:
        with smtplib.SMTP(host, port, timeout=TIMEOUT) as server:
            server.ehlo()
            server.starttls(context=context)
            server.ehlo()
            server.login(username, password)
            server.send_message(message)


def main() -> int:
    # Manual email test. This is enabled only when the workflow's
    # manual "test_email" input is set to true.
    if os.environ.get("TEST_EMAIL", "").lower() == "true":
        test_item = StockResult(
            name="TEST - Insta360 Stock Monitor",
            url="https://shop.insta360turkiye.com/products/insta360-luna-ultra",
            available=True,
            variant_title="Email delivery test",
            price="",
        )
        send_email([test_item])
        print("TEST: E-posta başarıyla gönderildi.")
        return 0

    old_state = load_state()
    new_state = old_state.copy()
    newly_available: list[StockResult] = []

    for product in PRODUCTS:
        try:
            result = check_product(product)
            print(
                f"{result.name}: "
                f"{'STOKTA' if result.available else 'STOK YOK'}"
            )

            was_available = old_state.get(result.name, False)
            new_state[result.name] = result.available

            if result.available and not was_available:
                newly_available.append(result)

        except Exception as exc:
            print(f"HATA - {product['name']}: {exc}", file=sys.stderr)
            # Hata durumunda mevcut state'i koruyoruz.
            new_state[product["name"]] = old_state.get(product["name"], False)

    if newly_available:
        send_email(newly_available)
        print(
            "Bildirim gönderildi: "
            + ", ".join(item.name for item in newly_available)
        )
    else:
        print("Yeni stok geçişi yok; e-posta gönderilmedi.")

    save_state(new_state)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
