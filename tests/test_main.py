import pytest
import sys
import os
from httpx import AsyncClient
from httpx import ASGITransport
from fastapi import FastAPI

# Add the parent directory to the path so we can import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app, lifespan

@pytest.mark.asyncio
async def test_root_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Welcome to the Shakers AI Support System"
    assert "documentation" in data

def test_app_has_router():
    # Verifica que se haya montado al menos un router
    assert app.routes

def test_app_has_cors():
    # Verifica que el middleware de CORS esté presente
    middleware_names = [mw.cls.__name__ for mw in app.user_middleware]
    assert "CORSMiddleware" in middleware_names

@pytest.mark.asyncio
async def test_lifespan_starts_services():
    async with lifespan(None):
        # Verificamos que los servicios se hayan inicializado
        from app.api.endpoints import rag_service, recommendation_service
        assert rag_service.initialized is True
        assert recommendation_service.initialized is True