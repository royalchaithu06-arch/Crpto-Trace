import os, tempfile
os.environ["DATABASE_URL"]="sqlite:///./test_cryptotrace.db"
from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app)

def test_public_root():
    r=client.get("/")
    assert r.status_code==200 and r.json()["mode"]=="DEMO DATA"

def test_auth_required():
    r=client.get("/api/dashboard")
    assert r.status_code==401

def test_register_login_and_dashboard():
    email="testuser+api@example.com"
    client.post("/api/auth/register",json={"name":"Test User","email":email,"password":"LongPassphrase123!","terms_accepted":True})
    r=client.post("/api/auth/login",json={"email":email,"password":"LongPassphrase123!"})
    assert r.status_code==200
    token=r.json()["token"]
    dash=client.get("/api/dashboard",headers={"Authorization":f"Bearer {token}"})
    assert dash.status_code==200
    assert "transaction_count" in dash.json()
