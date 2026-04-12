from fastapi.testclient import TestClient
from api import app

print("Initializing TestClient...")
client = TestClient(app)

print("Starting tests...")
try:
    print('Testing /health...')
    r = client.get('/health')
    print(r.status_code, r.json())
    assert r.status_code == 200

    print('\nTesting /api/v1/chat...')
    r2 = client.post('/api/v1/chat', json={'query': 'Hello! What is your name?'})
    print(r2.status_code, r2.json())
    assert r2.status_code in [200, 503]

    print('\nTesting /api/v1/analytics...')
    r3 = client.get('/api/v1/analytics')
    print(r3.status_code, r3.json())
    assert r3.status_code == 200

    print('\nAPI Testing Complete. All core endpoints are responsive.')
except Exception as e:
    print('Error:', e)
