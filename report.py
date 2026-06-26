import os
import requests
from datetime import datetime, timedelta
import time

WINDSOR_API_KEY = os.environ["WINDSOR_API_KEY"]
SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
SLACK_CHANNEL = "p-natyfranz-ecommerce"

CLIENT_KEYWORDS = ["n3rdi"]

today = datetime.today()

last_monday = today - timedelta(days=today.weekday() + 7)
last_sunday = last_monday + timedelta(days=6)
month_start = today.replace(day=1)

FIELDS = [
    "date",
    "source",
    "campaign",
    "spend",
    "impressions",
    "clicks",
    "conversions",
    "conversion_value",
]


def to_float(value):
    try:
        return float(value or 0)
    except:
        return 0


def campaign_matches(row):
    campaign = str(row.get("campaign", "")).lower()
    return any(keyword in campaign for keyword in CLIENT_KEYWORDS)


def fetch_windsor(connector, date_from, date_to, intentos=3):
    url = f"https://connectors.windsor.ai/{connector}"
    params = {
        "api_key": WINDSOR_API_KEY,
        "date_from": date_from,
        "date_to": date_to,
        "fields": ",".join(FIELDS),
    }

    for intento in range(1, intentos + 1):
        try:
            print(f"Intento {intento} - {connector} - {date_from} a {date_to}")
            r = requests.get(url, params=params, timeout=90)
            print("STATUS:", r.status_code)
            r.raise_for_status()

            rows = r.json().get("data", [])
            filtered_rows = [row for row in rows if campaign_matches(row)]

            print(f"{connector} filas totales: {len(rows)}")
            print(f"{connector} filas filtradas N3rdi: {len(filtered_rows)}")
            print(filtered_rows[:3])

            return filtered_rows

        except requests.exceptions.Timeout:
            print(f"Timeout en intento {intento} para {connector}")
            if intento < intentos:
                time.sleep(10)
            else:
                return []

        except Exception as e:
            print(f"Error en {connector}: {e}")
            return []


def agg(rows):
    spend = sum(to_float(row.get("spend")) for row in rows)
    conversions = sum(to_float(row.get("conversions")) for row in rows)
    conv_value = sum(to_float(row.get("conversion_value")) for row in rows)

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
    meta_data = fetch_windsor("facebook", date_from, date_to)
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
