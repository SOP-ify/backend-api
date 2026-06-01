from fastapi import FastAPI, UploadFile, File, Depends , HTTPException, status
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

class SOPCreate(BaseModel):
    title: str
    content: str

class SOPUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    status: str | None = None

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

# 1. CREATE (Membuat SOP Baru)
@app.post("/sops", response_model=SOPResponse, status_code=201, tags=["SOP Management"])
async def create_sop(sop: SOPCreate, current_user: dict = Depends(auth.get_current_user)):
    """Membuat SOP baru ke dalam database."""
    # Generate ID unik sederhana
    new_id = str(len(mock_db) + 100) 
    new_sop = {
        "id": new_id,
        "title": sop.title,
        "content": sop.content,
        "status": "draft" # Default status
    }
    mock_db[new_id] = new_sop
    return new_sop

# 2. READ ALL (Membaca Semua SOP - Ini sudah ada, pastikan bentuknya seperti ini)
@app.get("/sops", response_model=list[SOPResponse], tags=["SOP Management"])
async def get_all_sops(current_user: dict = Depends(auth.get_current_user)):
    return list(mock_db.values())

# 3. READ ONE (Membaca Satu SOP berdasarkan ID)
@app.get("/sops/{sop_id}", response_model=SOPResponse, tags=["SOP Management"])
async def get_sop(sop_id: str, current_user: dict = Depends(auth.get_current_user)):
    """Mengambil detail satu SOP berdasarkan ID-nya."""
    sop = mock_db.get(sop_id)
    if not sop:
        # Ini adalah implementasi Error Handling 404
        raise HTTPException(status_code=404, detail="SOP tidak ditemukan")
    return sop

# 4. UPDATE (Mengubah isi SOP)
@app.put("/sops/{sop_id}", response_model=SOPResponse, tags=["SOP Management"])
async def update_sop(sop_id: str, sop_update: SOPUpdate, current_user: dict = Depends(auth.get_current_user)):
    """Mengubah data SOP yang sudah ada."""
    sop = mock_db.get(sop_id)
    if not sop:
        raise HTTPException(status_code=404, detail="SOP tidak ditemukan")
    
    # Hanya update field yang dikirimkan
    if sop_update.title is not None:
        sop["title"] = sop_update.title
    if sop_update.content is not None:
        sop["content"] = sop_update.content
    if sop_update.status is not None:
        sop["status"] = sop_update.status
        
    mock_db[sop_id] = sop
    return sop

# 5. DELETE (Menghapus SOP)
@app.delete("/sops/{sop_id}", tags=["SOP Management"])
async def delete_sop(sop_id: str, current_user: dict = Depends(auth.get_current_user)):
    """Menghapus SOP dari database."""
    if sop_id not in mock_db:
        raise HTTPException(status_code=404, detail="SOP tidak ditemukan")
    
    del mock_db[sop_id]
    return {"message": f"SOP dengan ID {sop_id} berhasil dihapus"}