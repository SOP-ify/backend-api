import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_jwt_flow():
    # 1. Register
    response = client.post("/api/auth/register", 
        json={"username": "jwttest", "password": "test123"})
    assert response.status_code == 201
    
    # 2. Login and get token
    response = client.post("/api/auth/token",
        data={"username": "jwttest", "password": "test123"})
    assert response.status_code == 200
    token = response.json()["access_token"]
    
    # 3. Use token
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/sops", headers=headers)
    assert response.status_code == 200
    
    # 4. Test invalid token
    headers = {"Authorization": "Bearer invalidetoken"}
    response = client.get("/sops", headers=headers)
    assert response.status_code == 403

def test_jwt_wrong_password():
    response = client.post("/api/auth/token",
        data={"username": "jwttest", "password": "wrongpass"})
    assert response.status_code == 401