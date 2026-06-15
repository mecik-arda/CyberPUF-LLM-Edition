import pytest
import asyncio
import websockets
import json
import os
import requests
from dotenv import load_dotenv

load_dotenv()

@pytest.mark.asyncio
async def test_api_and_websocket():
    print("--- Web API & WebSocket Testi ---")
    
    token = os.environ.get("WEBSOCKET_TOKEN")
    if not token:
        print("HATA: WEBSOCKET_TOKEN ortam degiskeni bulunamadi!")
        return
        
    print("1. HTTP GET /api/test_images (Unauthenticated) Testi...")
    resp = requests.get("http://127.0.0.1:8000/api/test_images")
    if resp.status_code == 401:
        print("   -> BASARILI: Yetkisiz erisim 401 Unauthorized ile engellendi.")
    else:
        print(f"   -> HATA: Beklenen 401, alinan {resp.status_code}")
        
    print("2. HTTP GET /api/test_images (Authenticated) Testi...")
    headers = {"Authorization": f"Bearer {token}", "X-Requested-With": "XMLHttpRequest"}
    resp = requests.get("http://127.0.0.1:8000/api/test_images", headers=headers)
    if resp.status_code == 200:
        print("   -> BASARILI: Yetkili erisim saglandi. Yanit:")
        print(f"      {resp.json()}")
    else:
        print(f"   -> HATA: Beklenen 200, alinan {resp.status_code}")
        
    print("3. WebSocket Authentication Testi...")
    try:
        async with websockets.connect("ws://127.0.0.1:8000/ws") as ws:
            auth_msg = {"type": "auth", "token": token}
            await ws.send(json.dumps(auth_msg))
            resp = await asyncio.wait_for(ws.recv(), timeout=2.0)
            data = json.loads(resp)
            if data.get("type") == "auth_response" and data.get("status") == "success":
                print("   -> BASARILI: WebSocket baglantisi kuruldu ve yetkilendirildi.")
            else:
                print(f"   -> HATA: Beklenmeyen auth yaniti: {data}")
    except Exception as e:
        print(f"   -> HATA: WebSocket test basarisiz: {e}")

if __name__ == "__main__":
    asyncio.run(test_api_and_websocket())
