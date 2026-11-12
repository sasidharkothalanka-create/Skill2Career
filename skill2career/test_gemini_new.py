import os
import requests
from dotenv import load_dotenv

load_dotenv(override=True)

key = os.getenv("GEMINI_API_KEY", "").strip()

url = "https://generativelanguage.googleapis.com/v1beta/interactions"

payload = {
    "model": "gemini-3.8-flash",
    "input": "Reply with OK"
}

try:
    response = requests.post(
        url,
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": key
        },
        json=payload,
        timeout=90
    )

    print("HTTP:", response.status_code)
    print("Response:", response.text[:3000])

except requests.exceptions.Timeout:
    print("Gemini request timed out after 90 seconds.")

except requests.exceptions.RequestException as error:
    print("Connection error:", str(error))