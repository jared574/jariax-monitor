"""Resumen de cada manana en #pendientes de Discord: lo que hay hoy en el Google Calendar de Jared,
los prospectos del foro #prospectos que llevan 3 dias o mas sin movimiento y como va el pipeline."""
import json
import os
import urllib.request
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

try:
    ZONA = ZoneInfo("America/Monterrey")
except Exception:  # Windows sin tzdata; Monterrey es UTC-6 todo el ano desde 2022
    ZONA = timezone(timedelta(hours=-6))
GUILD = "749574102414524460"
DIAS_SEGUIMIENTO = 3
CERRADAS = {"cerrado", "perdido"}
ORDEN = ["investigada", "contactado", "demo", "propuesta", "cerrado", "perdido"]
DIAS = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre",
         "octubre", "noviembre", "diciembre"]


def pedir(url: str, headers: dict | None = None, data: bytes | None = None, metodo: str = "GET"):
    req = urllib.request.Request(url, data=data, method=metodo,
                                 headers={"User-Agent": "jariax-monitor", **(headers or {})})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def hora12(d: datetime) -> str:
    h = d.hour % 12 or 12
    return f"{h}:{d.minute:02d} {'am' if d.hour < 12 else 'pm'}"


def agenda(hoy: date) -> list[str]:
    url = os.environ.get("GOOGLE_ICAL_URL")
    if not url:
        return ["Calendario sin conectar todavia (falta la direccion secreta iCal)."]
    import icalendar
    import recurring_ical_events

    cal = icalendar.Calendar.from_ical(pedir(url))
    inicio = datetime.combine(hoy, datetime.min.time(), ZONA)
    eventos = recurring_ical_events.of(cal).between(inicio, inicio + timedelta(days=1))
    filas = []
    for e in eventos:
        cuando = e.get("DTSTART").dt
        titulo = str(e.get("SUMMARY", "Sin titulo")).strip()
        if isinstance(cuando, datetime):
            local = cuando.astimezone(ZONA)
            filas.append((local.strftime("%H:%M"), f"- {hora12(local)} · {titulo}"))
        else:
            filas.append(("00:00", f"- Todo el dia · {titulo}"))
    return [f for _, f in sorted(filas)] or ["Nada en el calendario hoy."]


def discord(ruta: str):
    token = os.environ["DISCORD_BOT_TOKEN"]
    return json.loads(pedir(f"https://discord.com/api/v10{ruta}", {"Authorization": f"Bot {token}"}))


def fecha_de_id(snowflake: str) -> datetime:
    return datetime.fromtimestamp(((int(snowflake) >> 22) + 1420070400000) / 1000, timezone.utc)


def prospectos(ahora: datetime) -> tuple[list[str], str]:
    if not os.environ.get("DISCORD_BOT_TOKEN"):
        return ["Foro sin conectar (falta DISCORD_BOT_TOKEN)."], ""
    foro = next(c for c in discord(f"/guilds/{GUILD}/channels") if c["name"] == "prospectos" and c["type"] == 15)
    etiquetas = {t["id"]: t["name"] for t in foro.get("available_tags", [])}
    hilos = [h for h in discord(f"/guilds/{GUILD}/threads/active")["threads"] if h.get("parent_id") == foro["id"]]
    hilos += discord(f"/channels/{foro['id']}/threads/archived/public?limit=100")["threads"]
    conteo = {nombre: 0 for nombre in ORDEN}
    pendientes = []
    for h in {h["id"]: h for h in hilos}.values():
        tags = [etiquetas.get(t, "") for t in h.get("applied_tags", [])]
        etapa = next((t for t in reversed(ORDEN) if t in tags), "sin etiqueta")
        conteo[etapa] = conteo.get(etapa, 0) + 1
        if etapa in CERRADAS:
            continue
        ultimo = fecha_de_id(h.get("last_message_id") or h["id"])
        dias = (ahora - ultimo).days
        if dias >= DIAS_SEGUIMIENTO:
            pendientes.append((dias, f"- {h['name']} · {etapa} · {dias} dias sin movimiento · https://discord.com/channels/{GUILD}/{h['id']}"))
    lineas = [f for _, f in sorted(pendientes, reverse=True)] or ["Nadie pendiente. Todos tienen movimiento reciente."]
    pipeline = " · ".join(f"{k} {v}" for k, v in conteo.items() if v or k in ORDEN)
    return lineas, pipeline


def main() -> None:
    ahora = datetime.now(timezone.utc)
    hoy = ahora.astimezone(ZONA).date()
    partes = [f"**Buenos dias. Hoy es {DIAS[hoy.weekday()]} {hoy.day} de {MESES[hoy.month - 1]}**", ""]
    for titulo, fn in (("Agenda de hoy", lambda: agenda(hoy)),):
        try:
            partes += [f"**{titulo}**", *fn(), ""]
        except Exception as e:
            partes += [f"**{titulo}**", f"No se pudo leer: {type(e).__name__}", ""]
    try:
        seguimiento, pipeline = prospectos(ahora)
        partes += [f"**Toca seguimiento** ({DIAS_SEGUIMIENTO}+ dias sin movimiento)", *seguimiento, ""]
        if pipeline:
            partes += [f"**Pipeline:** {pipeline}"]
    except Exception as e:
        partes += ["**Prospectos**", f"No se pudo leer el foro: {type(e).__name__}"]
    texto = "\n".join(partes).strip()
    print(texto)
    url = os.environ.get("DISCORD_WEBHOOK_PENDIENTES")
    if url:
        body = json.dumps({"content": texto[:1900], "allowed_mentions": {"parse": []}}).encode()
        pedir(url, {"content-type": "application/json"}, body, "POST")


if __name__ == "__main__":
    main()
