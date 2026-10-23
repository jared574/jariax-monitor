"""Revisa que los sitios de Jariax esten arriba y avisa a #alertas de Discord solo cuando algo cambia
(se cae o vuelve). El estado queda en estado.json; el workflow lo guarda con un commit si cambio."""
import json
import os
import pathlib
import time
import urllib.request
from datetime import datetime, timezone

SITIOS = {
    "jariax.com": "https://jariax.com",
    "Vangil clinicas": "https://clinicas.jariax.com/login",
    "Vangil barberias": "https://barberias.jariax.com/login",
    "Vangil admin": "https://admin.jariax.com/login",
    "n8n": "https://n8n.jariax.com/healthz",
}
ESTADO = pathlib.Path(__file__).with_name("estado.json")


def revisar(url: str) -> str | None:
    """None si responde bien; si no, el motivo. Dos intentos para no avisar por un tropiezo de red."""
    motivo = None
    for intento in range(2):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "jariax-monitor"})
            with urllib.request.urlopen(req, timeout=20) as r:
                if r.status == 200:
                    return None
                motivo = f"respondio {r.status}"
        except urllib.error.HTTPError as e:
            motivo = f"respondio {e.code}"
        except Exception as e:  # timeout, DNS, certificado
            motivo = type(e).__name__ + (f": {e.reason}" if hasattr(e, "reason") else "")
        if intento == 0:
            time.sleep(20)
    return motivo


def avisar(texto: str) -> None:
    url = os.environ.get("DISCORD_WEBHOOK_ALERTAS")
    if not url:
        print("sin webhook:", texto)
        return
    body = json.dumps({"content": texto[:1900], "allowed_mentions": {"parse": []}}).encode()
    req = urllib.request.Request(url, data=body, method="POST",
                                 headers={"content-type": "application/json", "User-Agent": "jariax-monitor"})
    urllib.request.urlopen(req, timeout=15).read()


def minutos(desde: str, ahora: datetime) -> int:
    return max(1, round((ahora - datetime.fromisoformat(desde)).total_seconds() / 60))


def main() -> None:
    estado = json.loads(ESTADO.read_text()) if ESTADO.exists() else {}
    ahora = datetime.now(timezone.utc)
    cambio = False
    for nombre, url in SITIOS.items():
        motivo = revisar(url)
        antes = estado.get(nombre, {"arriba": True, "desde": ahora.isoformat()})
        arriba = motivo is None
        print(f"{nombre}: {'ok' if arriba else motivo}")
        if arriba == antes["arriba"]:
            continue
        if arriba:
            avisar(f"**Volvio** · {nombre}\nEstuvo caido unos {minutos(antes['desde'], ahora)} min. {url}")
        else:
            avisar(f"**Caido** · {nombre}\n{url} {motivo}")
        estado[nombre] = {"arriba": arriba, "desde": ahora.isoformat()}
        cambio = True
    if cambio or not ESTADO.exists():
        ESTADO.write_text(json.dumps(estado, indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
