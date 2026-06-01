from fastapi.testclient import TestClient
from main import app

# Inisialisasi TestClient yang akan bertindak sebagai "Aplikasi Mobile Tiruan"
client = TestClient(app)

def test_health_check():
    """Test apakah server berjalan dengan baik"""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "SOP-ify Backend is running smoothly!"}

def test_auth_and_sops_flow():
    """Test alur dari registrasi, login, hingga akses endpoint terproteksi"""
    
    # 1. Coba Registrasi User Baru
    register_data = {"username": "testuser_123", "password": "supersecretpassword"}
    response = client.post("/api/auth/register", json=register_data)
    # Kita menggunakan in karena jika test dijalankan ulang, user mungkin sudah ada (400)
    assert response.status_code in [201, 400] 

    # 2. Coba Login untuk mendapatkan Token
    # Catatan: OAuth2 meminta form data, bukan JSON
    login_data = {"username": "testuser_123", "password": "supersecretpassword"}
    response = client.post("/api/auth/token", data=login_data)
    assert response.status_code == 200
    
    # Ekstrak token dari response
    token = response.json()["access_token"]
    assert token is not None

    # 3. Coba akses /sops TANPA token (Harus Ditolak!)
    response_no_token = client.get("/sops")
    assert response_no_token.status_code == 401

    # 4. Coba akses /sops DENGAN token (Harus Berhasil!)
    headers = {"Authorization": f"Bearer {token}"}
    response_with_token = client.get("/sops", headers=headers)
    
    assert response_with_token.status_code == 200
    # Pastikan data yang dikembalikan adalah sebuah list (daftar SOP)
    assert isinstance(response_with_token.json(), list)