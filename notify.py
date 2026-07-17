import requests
from config import NTFY_TOPIC


def send_notification(title, message):
    if not NTFY_TOPIC:
        print("NTFY topic missing.")
        return False

    url = f"https://ntfy.sh/{NTFY_TOPIC}"

    headers = {
        "Title": title,
        "Priority": "default",
        "Tags": "chart_with_upwards_trend"
    }

    try:
        response = requests.post(
            url,
            headers=headers,
            data=message.encode("utf-8"),
            timeout=15
        )

        response.raise_for_status()
        return True

    except Exception as e:
        print(f"NTFY Error: {e}")
        return False
