import os
from google import genai
from app.core.config import settings

client = genai.Client(api_key=settings.GEMINI_API_KEY)
models_to_test = [
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-2.5-flash",
    "gemini-1.5-flash",
    "gemini-1.5-flash-8b",
]

for m in models_to_test:
    print(f"TRYING: {m}")
    try:
        resp = client.models.generate_content(model=m, contents="hello")
        print(f"SUCCESS: {m}")
        break
    except Exception as e:
        pass
