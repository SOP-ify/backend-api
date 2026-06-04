# app/main.py

# -> entry point
#      -> konfigurasi CORS untuk Android client
#      -> manage lifecycle MongoDB (connect/disconnect via lifespan)
#      -> route
#      -> global exception handler and 505

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.core.config import settings
from app.core.database import connect_to_mongo, close_mongo_connection
from app.modules.auth import repository as auth_repository
from app.modules.auth.router import router as auth_router


# lifespan ------------------------------------------------------------------------

# manage startup dan shutdown MongoDB
@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    await connect_to_mongo()
    await auth_repository.ensure_indexes()

    yield  

    # shutdown
    await close_mongo_connection()

# end of lifespan -----------------------------------------------------------------


# application factory -------------------------------------------------------------

# instance FastAPI
def create_application() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        description=(
            "Backend API SOP-ify. "
            "mewoooowwwwwwww, i love hoshino ai"
        ),
        version=settings.APP_VERSION,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # cors middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # global exception handler
    # - output : { success: False, message, data: [{ field, message }] }
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
        errors = []
        for error in exc.errors():
            field = " -> ".join(str(loc) for loc in error["loc"] if loc != "body")
            errors.append({"field": field, "message": error["msg"]})

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "success": False,
                "message": "Validasi input gagal",
                "data": errors,
            },
        )

    # exception handler error yang tidak ter-handle
    # - output : { success: False, message: "Terjadi kesalahan internal pada server", data: None }
    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "message": "Terjadi kesalahan internal pada server",
                "data": None,
            },
        )

    app.include_router(auth_router)
    # tambah router modul baru di bawah sini
    # app.include_router(history_router)
    # app.include_router(ml_router)

    # health check endpoint
    # - output : { success: True, message: "<APP_NAME> v<VERSION> is running", data: None }
    @app.get("/", tags=["Health Check"], summary="Health Check")
    async def health_check():
        return {
            "success": True,
            "message": f"{settings.APP_NAME} v{settings.APP_VERSION} is running",
            "data": None,
        }

    return app


app = create_application()

# end of application factory ------------------------------------------------------
