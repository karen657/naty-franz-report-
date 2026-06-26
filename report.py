import os
import requests
import json
from datetime import datetime, timedelta
import time

WINDSOR_API_KEY = os.environ["WINDSOR_API_KEY"]
SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
SLACK_CHANNEL = "p-natyfranz-ecommerce"

today = datetime.today()
last_monday = today - timedelta(days=today.weekday() + 7)
last_sunday = last_monday + timedelta(days=6)
month_start = today.replace(day=1)

FIELDS_META = ["date", "source", "campaign", "spend", "impressions", "clicks", "conversions"]
FIELDS_GOOGLE = ["date", "source", "campaign", "spend", "impressions", "clicks", "conversions", "conversion_value"]

def fetch_windsor(connector, date_from, date_to, fields, intentos=3):
    url = f"https://connectors.windsor.ai/{connector}"
    params = {
        "api_key": WINDSOR_API_KEY,
        "date_from": date_from,
        "date_to": date_to,
        "fields": ",".join(fields),
    }
    for intento in range(1, intentos + 1):
        try:
            print(f"\n=== Intento {intento} — {connector.upper()} ===")
            r = requests.get(url, params=params, timeout=90)  # subimos a 90 segundos
            print("STATUS:", r.status_code)
            print("RESPONSE:", r.text[:2000])
            r.raise_for_status()
            data = r.json().get("data", [])
            if data:
                print(f"=== PRIMERAS 2 FILAS {connector.upper()} ===")
                print(json.dumps(data[:2], indent=2))
            else:
                print(f"⚠️ Sin data para {connector.upper()}")
            return data
        except requests.exceptions.Timeout:
            print(f"⏱️ Timeout en intento {intento} para {connector}")
            if intento < intentos:
                print("Esperando 10 segundos antes de reintentar...")
                time.sleep(10)
            else:
                print("❌ Se agotaron los intentos")
                return []
        except Exception as e:
            print(f"❌ Error en {connector}: {e}")
            return []

month_from = month_start.strftime("%Y-%m-%d")
month_to = today.strftime("%Y-%m-%d")

print("=== PROBANDO META ===")
fetch_windsor("facebook", month_from, month_to, FIELDS_META)

print("\n=== PROBANDO GOOGLE ===")
fetch_windsor("google_ads", month_from, month_to, FIELDS_GOOGLE)

print("✅ Debug completo")
