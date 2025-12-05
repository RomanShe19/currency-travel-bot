import requests
from dotenv import load_dotenv
import os

load_dotenv()

def get_current_rate(default: str = "USD", currencies: list[str] = ["USD", "EUR", "GBP", "JPY", "KRW", "CNY", "INR", "BRL", "MXN", "ARS", "CLP", "COP", "PEN", "UYU", "VEF", "VND", "ZAR", "TRY", "RUB", "UAH", "KZT", "KGS", "TJS", "TMT", "AZN", "AMD", "BYN"]):
    url = f"https://api.exchangerate.host/live"
    params = {
        "access_key": os.getenv("CURRENCY_ACCESS_KEY"),
        "source": default,
        "currencies": ",".join(currencies)
    }
    response = requests.get(url, params=params)
    data = response.json()
    return data

def convert_currency(amount: float, from_currency: str, to_currency: str):
    url = "https://api.exchangerate.host/convert"
    params = {
        "access_key": os.getenv("CURRENCY_ACCESS_KEY"),
        "from": from_currency,
        "to": to_currency,
        "amount": amount
    }
    response = requests.get(url, params=params)
    data = response.json()
    return data

def get_all_supported_currencies():
    url = "https://api.exchangerate.host/list"
    params = {
        "access_key": os.getenv("CURRENCY_ACCESS_KEY"),
    }
    response = requests.get(url, params=params)
    data = response.json()
    return data


if __name__ == "__main__":
    print(convert_currency(100, "USD", "CNY"))