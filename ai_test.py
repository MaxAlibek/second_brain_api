import asyncio
import httpx
import time
import sys

# Force stdout to utf-8 just in case, or just don't use emojis
API_URL = "http://localhost:8000"

async def test_ai_agent():
    print("--- STARTING AI AGENT TEST (RAG) ---")
    
    async with httpx.AsyncClient() as client:
        print("\n1. Authorization...")
        login_data = {
            "username": "testuser",
            "password": "testpassword123"
        }
        res = await client.post(f"{API_URL}/auth/login", data=login_data)
        if res.status_code != 200:
            print("User not found, registering new test user...")
            reg_data = {"username": "testuser", "email": "test@ai.com", "password": "testpassword123"}
            await client.post(f"{API_URL}/auth/register", json=reg_data)
            res = await client.post(f"{API_URL}/auth/login", data=login_data)

        if res.status_code != 200:
            print(f"Login error. Is the server running? {res.text}")
            return
            
        token = res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("SUCCESS: Authorized.")

        print("\n2. Creating test notes (Knowledge Base)...")
        notes = [
            {"title": "Квантовая физика", "content": "Кот Шрёдингера — это мысленный эксперимент, в котором кот одновременно жив и мертв, пока коробку не откроют."},
            {"title": "Рецепт Борща", "content": "Для красного борща нужна свекла. Варите свеклу отдельно с каплей уксуса, чтобы сохранить цвет. Добавьте капусту, картофель и мясо."},
            {"title": "Тренировки", "content": "Для гипертрофии мышц лучше делать от 8 до 12 повторений в подходе, отдыхая около 2 минут."}
        ]
        
        for note in notes:
            res = await client.post(f"{API_URL}/brain/", json=note, headers=headers)
            if res.status_code == 201:
                print(f"SUCCESS Created note: {note['title']}")
            else:
                print(f"ERROR: {res.text}")

        print("\nWaiting 5 seconds for Celery to generate embeddings asynchronously...")
        await asyncio.sleep(5)

        print("\n3. Asking AI Agent (Testing Semantic Search / RAG)...")
        question = "Что нужно сделать, чтобы борщ был красным?"
        print(f"User Question: '{question}'")
        
        ai_payload = {"question": question}
        res = await client.post(f"{API_URL}/ai/chat", json=ai_payload, headers=headers)
        
        if res.status_code == 200:
            answer = res.json()['answer']
            # safely print avoiding charmap errors
            print(f"\n--- AI ANSWER ---\n{answer.encode('cp1251', 'replace').decode('cp1251')}")
        else:
            print(f"ERROR: AI Request Failed: {res.text}")
            
        print("\nSUCCESS: AI Agent testing completed.")

if __name__ == "__main__":
    asyncio.run(test_ai_agent())
