from fastapi.testclient import TestClient
from src.presentation.app import create_app
from src.infrastructure.database import Base, engine, SessionLocal
import pytest

# Create a test client
app = create_app()
client = TestClient(app)

def setup_module(module):
    # Create tables in the test database (using the same SQLite for local tests is fine)
    Base.metadata.create_all(bind=engine)

def test_auth_workflow():
    import uuid
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    password = "testpassword123"
    
    # 1. Register
    response = client.post(
        "/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Test User"}
    )
    assert response.status_code == 200
    assert response.json()["message"] == "User created successfully"
    
    # 2. Login
    response = client.post(
        "/v1/auth/login",
        json={"email": email, "password": password}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == email

if __name__ == "__main__":
    test_auth_workflow()
    print("✅ Auth logic verified via TestClient!")
