import requests
import base64

from src.envCore.env import PAYMONGO_SECRET_KEY

# ============ PAYMONGO ============
def create_payment_link(amount, description, user_id, plan):
    secret = base64.b64encode(f"{PAYMONGO_SECRET_KEY}:".encode()).decode()
    url = "https://api.paymongo.com/v1/links"
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": f"Basic {secret}"
    }
    payload = {
        "data": {
            "attributes": {
                "amount": amount * 100,
                "description": description,
                "remarks": f"{user_id}|{plan}"
            }
        }
    }
    response = requests.post(url, json=payload, headers=headers)
    data = response.json()
    return data["data"]["attributes"]["checkout_url"], data["data"]["id"]
