import os
import requests
from datetime import datetime, timedelta

WINDSOR_API_KEY = os.environ["WINDSOR_API_KEY"]
SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
SLACK_CHANNEL = "p-natyfranz-ecommerce"

# Rango: lunes pasado → domingo pasado
today = datetime.today()
last_monday = today - timedelta(days=today.weekday() + 7)
last_sunday = last_monday + timedelta(days=6)
date_from = last_monday.strftime("%Y-%m-%d")
date_to = last_sunday.strftime("%Y-%m-%d")

METRICS = ["spend", "conversions", "conversion_value", "cpa", "roas"]
DIMENSIONS = ["source", "channel"]

def fetch_windsor(connector):
    url = "https://connectors.windsor.ai/all"
    params = {
        "api_key": WINDSOR_API_KEY,
        "connector": connector,
        "date_from": date_from,
        "date_to": date_to,
        "fields": ",".join(DIMENSIONS + METRICS),
        "account_name": "Naty Franz",
    }
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    return r.json().get("data", [])

def agg(rows):
    spend = conversions = conv_value = 0
    for row in rows:
        spend += float(row.get("spend") or 0)
        conversions += float(row.get("conversions") or 0)
        conv_value += float(row.get("conversion_value") or 0)
    cpa = spend / conversions if conversions else 0
    roas = conv_value / spend if spend else 0
    return dict(
        spend=spend,
        conversions=conversions,
        conv_value=conv_value,
        cpa=cpa,
        roas=roas,
    )

def fmt(label, d):
    return (
        f"*{label}*\n"
        f"  💰 Inversión: ${d['spend']:,.2f}\n"
        f"  🛒 Conversiones: {d['conversions']:.0f}\n"
        f"  💵 Valor conv.: ${d['conv_value']:,.2f}\n"
        f"  📉 CPA: ${d['cpa']:,.2f}\n"
        f"  📈 ROAS: {d['roas']:.2f}x\n"
    )

meta_data = fetch_windsor("facebook_ads")
google_data = fetch_windsor("google_ads")

meta = agg(meta_data)
google = agg(google_data)
total = agg(meta_data + google_data)

periodo = f"{last_monday.strftime('%d/%m')} → {last_sunday.strftime('%d/%m/%Y')}"

mensaje = (
    f":bar_chart: *Informe Semanal — Naty Franz*\n"
    f"_Período: {periodo}_\n\n"
    f"{fmt('Meta Ads', meta)}\n"
    f"{fmt('Google Ads', google)}\n"
    f"{'─'*30}\n"
    f"{fmt('TOTAL', total)}"
)

resp = requests.post(
    "https://slack.com/api/chat.postMessage",
    headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}"},
    json={"channel": SLACK_CHANNEL, "text": mensaje},
)
resp.raise_for_status()
print("✅ Informe enviado a Slack")
