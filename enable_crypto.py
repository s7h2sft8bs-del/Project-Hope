import os
from dotenv import load_dotenv
import requests
import json

load_dotenv()

ALPACA_API_KEY = os.getenv('ALPACA_API_KEY')
ALPACA_SECRET_KEY = os.getenv('ALPACA_SECRET_KEY')

url = "https://paper-api.alpaca.markets/v1/account"
headers = {
    "APCA-API-KEY-ID": ALPACA_API_KEY,
    "APCA-API-SECRET-KEY": ALPACA_SECRET_KEY
}

response = requests.get(url, headers=headers)
print("Status:", response.status_code)
print(json.dumps(response.json(), indent=2))
