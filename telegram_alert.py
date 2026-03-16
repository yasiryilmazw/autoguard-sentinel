import requests

BOT_TOKEN = "8731661445:AAEL7AOapJ2AnBvbJs26NDEkmi__VO0fhd0"
CHAT_ID = "1076375506"

def send_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    
    data = {
        "chat_id": CHAT_ID,
        "text": text
    }

    requests.post(url, data=data)


def send_photo(photo_path):

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"

    with open(photo_path, "rb") as photo:
        files = {"photo": photo}

        data = {
            "chat_id": CHAT_ID,
            "caption": "🚨 Motion detected!"
        }

        requests.post(url, data=data, files=files)