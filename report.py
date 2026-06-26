import os
import requests
from datetime import datetime, timedelta

WINDSOR_API_KEY = os.environ["WINDSOR_API_KEY"]
SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
SLACK_CHANNEL = "p-natyfranz-ecommerce"

today = datetime.today()
last_monday = today - timedelta(days=today.weekday() + 7)
last_sunday = last_monday + timedelta(days=6)
month_start = today.replace(day=1)

# Campos ampliados para traer conversiones
FIELDS = ["date", "source", "campaign", "spend", "impressions", "clicks",
          "conversions", "conversion_value", "purchases", "purchase_value",
          "roas", "cpa", "revenue", "cost_per_conversion"]

def fetch_windsor(connector, date_from, date_to):
    url = f"https://connectors.windsor.ai/{connector}"
    params = {
        "api_key": WINDSOR_API_KEY,
        "date_from": date_from,
        "date_to": date_to,
        "fields": ",".join(FIELDS),
    }
    r = requests.get(url, params=params, timeout=30)
    print(f"\n=== DEBUG {connector.upper()} ===")
    print("URL:", r.url)
    print("STATUS:", r.status_code)
    print("RESPONSE:", r.text[:2000])
    r.raise_for_status()
    data = r.json().get("data", [])
    if data:
        print(f"=== PRIMERAS 2 FILAS DE {connector.upper()} ===")
        import json
        print(json.dumps(data[:2], indent=2))
    else:
        print(f"=== SIN DATA para {connector.upper()} ===")
    return data

def to_float(value):
    try:
        return float(value or 0)
    except:
        return 0

def agg(rows):
    spend = sum(to_float(row.get("spend")) for row in rows)
    # Intentamos distintos nombres de campo para conversiones
    conversions = sum(to_float(row.get("conversions") or row.get("purchases")) for row in rows)
    conv_value = sum(to_float(row.get("conversion_value") or row.get("purchase_value") or row.get("revenue")) for row in rows)
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
    # Probamos facebook_ads primero, si falla probamos facebook
    try:
        meta_data = fetch_windsor("facebook_ads", date_from, date_to)
    except Exception as e:
        print(f"facebook_ads falló ({e}), intentando con 'facebook'...")
        meta_data = fetch_windsor("facebook", date_from, date_to)

    google_data = fetch_windsor("google_ads", date_from, date_to)

    meta = agg(meta_data)
    google = agg(google_data)
    total = {
        "spend": meta["spend"] + google["spend"],
        "conversions": meta["conversions"] + google["conversions"],
        "conv_value": meta["conv_value"] + google["conv_value"],
        "cpa": 0,
        "roas": 0,
    }
    if total["conversions"]:
        total["cpa"] = total["spend"] / total["conversions"]
    if total["spend"]:
        total["roas"] = total["conv_value"] / total["spend"]

    return (
        f"*{title}*\n"
        f"_Período: {datetime.strptime(date_from, '%Y-%m-%d').strftime('%d/%m')} → "
        f"{datetime.strptime(date_to, '%Y-%m-%d').strftime('%d/%m/%Y')}_\n\n"
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
data = resp.json()
if not data.get("ok"):
    raise Exception(f"Error de Slack: {data}")

print("✅ Informe enviado a Slack")
