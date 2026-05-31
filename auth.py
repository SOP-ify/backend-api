import os
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from passlib.context import CryptContext
try:
    from jose import jwt
except ImportError:
    raise ImportError("python-jose package is required. Install it with: pip install python-jose[cryptography]")
from dotenv import load_dotenv

# Load variabel dari file .env
load_dotenv()

# Inisialisasi Router khusus Auth
router = APIRouter(
    prefix="/api/auth",
    tags=["Auth"]
)

# Ambil konfigurasi dari .env
SECRET_KEY = os.getenv("SECRET_KEY", "default-insecure-key")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
# Sesuaikan tokenUrl dengan prefix router kita
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")

# --- Mock Database Sementara Khusus Auth ---
mock_users_db = {}

# --- Skema Pydantic ---
class UserRegister(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

# --- Helper Functions ---
def get_password_hash(password):
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta if expires_delta else timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# --- Endpoints ---
@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_user(user: UserRegister):
    """Endpoint untuk mendaftarkan pengguna baru (Dummy)."""
    if user.username in mock_users_db:
        raise HTTPException(status_code=400, detail="Username sudah terdaftar")
    
    hashed_password = get_password_hash(user.password)
    mock_users_db[user.username] = {
        "username": user.username,
        "hashed_password": hashed_password
    }
    return {"message": "Registrasi berhasil"}

@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """Endpoint login yang mengembalikan token JWT."""
    user_dict = mock_users_db.get(form_data.username)
    if not user_dict or not verify_password(form_data.password, user_dict["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Username atau password salah",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user_dict["username"]}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}