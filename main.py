from fastapi import FastAPI, UploadFile, File, Depends 
from pydantic import BaseModel
import asyncio
import auth


# 1. Initialize the App
app = FastAPI(
    title="SOP-ify Backend",
    description="API for the SOP-ify Mobile App (Dummy Pipeline)",
    version="0.1.0"
)

# Masukkan semua rute dari auth.py ke dalam aplikasi utama
app.include_router(auth.router)

# 2. Define Data Models (Contracts for the mobile app)
class SOPResponse(BaseModel):
    id: str
    title: str
    content: str
    status: str
    

# 3. Mock Database
mock_db = {
    "123": {
        "id": "123",
        "title": "SOP Pelayanan Pelanggan",
        "content": "1. Sapa pelanggan dengan ramah.\n2. Tanyakan kebutuhan mereka.",
        "status": "completed"
    }
}

# 4. Core Endpoints
@app.get("/", tags=["Health Check"])
async def root():
    return {"message": "SOP-ify Backend is running smoothly!"}

@app.get("/sops", response_model=list[SOPResponse], tags=["SOP Management"])
# Tambahkan Depends(auth.get_current_user) di parameter fungsi
async def get_all_sops(current_user: dict = Depends(auth.get_current_user)):
    """
    Endpoint ini sekarang TERKUNCI. 
    Hanya mengembalikan SOP jika request memiliki Token JWT yang valid.
    """
    # Opsional: Kamu bisa print current_user untuk melihat siapa yang sedang akses
    print(f"User yang sedang akses: {current_user['username']}")
    
    return list(mock_db.values())

@app.post("/sops/generate", response_model=SOPResponse, tags=["AI Integration"])
async def generate_dummy_sop(title: str, current_user: dict = Depends(auth.get_current_user)):
    """Simulate the Vertex AI generation delay."""
    # Simulate a 3-second delay for AI processing
    await asyncio.sleep(3)
    
    new_id = str(len(mock_db) + 100)
    new_sop = {
        "id": new_id,
        "title": title,
        "content": f"Dummy generated content for {title}. (Vertex AI will replace this later).",
        "status": "completed"
    }
    mock_db[new_id] = new_sop
    return new_sop

@app.post("/upload-audio", tags=["Media"])
async def upload_audio(file: UploadFile = File(...), current_user: dict = Depends(auth.get_current_user)):
    """Save audio locally (Will migrate to GCP Cloud Storage later)."""
    file_location = f"temp_audio/{file.filename}"
    with open(file_location, "wb+") as file_object:
        file_object.write(file.file.read())
    return {"info": f"file '{file.filename}' saved at '{file_location}'"}