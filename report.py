import os
import requests
from datetime import datetime, timedelta

WINDSOR_API_KEY = os.environ["WINDSOR_API_KEY"]
SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
SLACK_CHANNEL = "p-natyfranz-ecommerce"

today = datetime.today()

# Semana pasada: lunes a domingo
last_monday = today - timedelta(days=today.weekday() + 7)
last_sunday = last_monday + timedelta(days=6)

# Mes en curso: día 1 a hoy
month_start = today.replace(day=1)

FIELDS = [
    "account_name",
    "campaign",
    "spend",
    "conversions",
    "conversion_value",
]


def fetch_windsor(connector, date_from, date_to):
    url = f"https://connectors.windsor.ai/{connector}"

    params = {
        "api_key": WINDSOR_API_KEY,
        "date_from": date_from,
        "date_to": date_to,
        "fields": ",".join(FIELDS),
        "account_name": "Naty Franz",
    }

    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()

    data = r.json().get("data", [])
    print(f"{connector} | {date_from} → {date_to} | filas: {len(data)}")
    print(data[:3])

    return data


def to_float(value):
    if value in [None, "", "-"]:
        return 0

    try:
        return float(value)
    except ValueError:
        return 0


def agg(rows):
    spend = 0
    conversions = 0
    conv_value = 0

    for row in rows:
        spend += to_float(row.get("spend"))
        conversions += to_float(row.get("conversions"))
        conv_value += to_float(row.get("conversion_value"))

    cpa = spend / conversions if conversions else 0
    roas = conv_value / spend if spend else 0

    return {
        "spend": spend,
        "conversions": conversions,
        "conv_value": conv_value,
        "cpa": cpa,
        "roas": roas,
    }


def fmt(label, data):
    return (
        f"*{label}*\n"
        f"  💰 Inversión: ${data['spend']:,.2f}\n"
        f"  🛒 Conversiones: {data['conversions']:.0f}\n"
        f"  💵 Valor conv.: ${data['conv_value']:,.2f}\n"
        f"  📉 CPA: ${data['cpa']:,.2f}\n"
        f"  📈 ROAS: {data['roas']:.2f}x\n"
    )


def build_section(title, date_from, date_to):
    meta_data = fetch_windsor("facebook_ads", date_from, date_to)
    google_data = fetch_windsor("google_ads", date_from, date_to)

    meta = agg(meta_data)
    google = agg(google_data)
    total = agg(meta_data + google_data)

    date_from_fmt = datetime.strptime(date_from, "%Y-%m-%d").strftime("%d/%m")
    date_to_fmt = datetime.strptime(date_to, "%Y-%m-%d").strftime("%d/%m/%Y")

    return (
        f"*{title}*\n"
        f"_Período: {date_from_fmt} → {date_to_fmt}_\n\n"
        f"{fmt('Meta Ads', meta)}\n"
        f"{fmt('Google Ads', google)}\n"
        f"{'─' * 30}\n"
        f"{fmt('TOTAL', total)}"
    )


week_from = last_monday.strftime("%Y-%m-%d")
week_to = last_sunday.strftime("%Y-%m-%d")

month_from = month_start.strftime("%Y-%m-%d")
month_to = today.strftime("%Y-%m-%d")

mensaje = (
    f":bar_chart: *Informe Semanal — Naty Franz*\n\n"
    f"{build_section('📅 Lo que va del mes', month_from, month_to)}\n\n"
    f"{'=' * 30}\n\n"
    f"{build_section('🗓️ Última semana cerrada', week_from, week_to)}"
)

resp = requests.post(
    "https://slack.com/api/chat.postMessage",
    headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}"},
    json={"channel": SLACK_CHANNEL, "text": mensaje},
    timeout=30,
)

resp.raise_for_status()
slack_response = resp.json()

if not slack_response.get("ok"):
    raise Exception(f"Error de Slack: {slack_response}")

print("✅ Informe enviado a Slack")
