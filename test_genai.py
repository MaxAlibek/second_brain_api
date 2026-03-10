import os
from google import genai

key = os.environ.get("GEMINI_API_KEY", "AIzaSyAsrp8dm0qUuZZagTgUHMrjYxtBM26M1d8")
client = genai.Client(api_key=key)

print("Listing models...")
for m in client.models.list():
    if 'embed' in m.name.lower():
        print("Found:", m.name)

try:
    print("\nTesting text-embedding-004...")
    resp = client.models.embed_content(model="text-embedding-004", contents="hello")
    print("Success text-embedding-004! length:", len(resp.embeddings[0].values))
except Exception as e:
    print(f"Failed: {e}")

try:
    print("\nTesting embedding-001...")
    resp = client.models.embed_content(model="models/embedding-001", contents="hello")
    print("Success embedding-001! length:", len(resp.embeddings[0].values))
except Exception as e:
    print(f"Failed: {e}")
