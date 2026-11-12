
import os
import requests
from dotenv import load_dotenv

load_dotenv(override=True)

key = os.getenv("GEMINI_API_KEY", "").strip()
model = os.getenv("GEMINI_MODEL", "gemini-3.8-flash").strip()

if not key:
    print("ERROR: Gemini API key not detected in .env")
    raise SystemExit

headers = {
    "Content-Type": "application/json",
    "x-goog-api-key": key
}

tests = [
    (
        "TEST A - API KEY",
        "GET",
        "https://generativelanguage.googleapis.com/v1beta/models",
        None
    ),
    (
        "TEST B - INTERACTIONS",
        "POST",
        "https://generativelanguage.googleapis.com/v1beta/interactions",
        {
            "model": model,
            "input": "Reply with OK",
            "store": False
        }
    )
]

for name, method, url, payload in tests:
    print("\n", name)
    try:
        if method == "GET":
            response = requests.get(
                url, headers=headers, timeout=30
            )
        else:
            response = requests.post(
                url, headers=headers, json=payload, timeout=30
            )

        print("HTTP:", response.status_code)
        print("Response:", response.text[:2000])

    except requests.RequestException as error:
        print("Connection error:", str(error))
