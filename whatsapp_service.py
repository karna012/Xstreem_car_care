import os
import requests
from dotenv import load_dotenv

load_dotenv()


def send_whatsapp_message(to: str, message: str):
    url = (
        f"https://graph.facebook.com/v25.0/"
        f"{os.getenv('WHATSAPP_PHONE_NUMBER_ID')}/messages"
    )

    headers = {
        "Authorization": f"Bearer {os.getenv('WHATSAPP_ACCESS_TOKEN')}",
        "Content-Type": "application/json",
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {
            "body": message[:4096]
        }
    }

    response = requests.post(url, headers=headers, json=payload)

    print("WhatsApp Status Code:", response.status_code)
    print("WhatsApp Response:", response.text)

    response.raise_for_status()

    return response.json()
