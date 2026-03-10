import os
from google import genai

key = os.environ.get("GEMINI_API_KEY", "AIzaSyAsrp8dm0qUuZZagTgUHMrjYxtBM26M1d8")
client = genai.Client(api_key=key)

for m in client.models.list():
    if 'embed' in m.name.lower() or 'text-embedding' in m.name.lower():
        print("TRYING:", m.name)
        try:
            resp = client.models.embed_content(model=m.name, contents="hello")
            print("SUCCESS:", m.name)
            break
        except Exception as e:
            print("FAILED:", str(e))
