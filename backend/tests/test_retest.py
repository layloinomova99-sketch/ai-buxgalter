"""Retest after fixes: AI chat + trailing-slash + regressions."""
import os
import time
import uuid
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    # fallback from frontend/.env
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.strip().split("=", 1)[1].strip().rstrip("/")

CREATOR_EMAIL = "layloinomova99@gmail.com"
CREATOR_PASSWORD = "Creator@2026!Secure"


@pytest.fixture(scope="session")
def creator_token():
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": CREATOR_EMAIL, "password": CREATOR_PASSWORD}, timeout=30)
    assert r.status_code == 200, f"Creator login failed: {r.status_code} {r.text}"
    return r.json()["token"]


@pytest.fixture(scope="session")
def creator_headers(creator_token):
    return {"Authorization": f"Bearer {creator_token}", "Content-Type": "application/json"}


# ---------- AI chat ----------
class TestAIChat:
    conv_id = None

    def test_ai_chat_basic(self, creator_headers):
        r = requests.post(f"{BASE_URL}/api/ai/chat",
                          headers=creator_headers,
                          json={"message": "Salom"}, timeout=90)
        assert r.status_code == 200, f"AI chat 500: {r.text}"
        data = r.json()
        assert "conversation_id" in data
        assert "content" in data
        assert isinstance(data["content"], str) and len(data["content"]) > 0
        TestAIChat.conv_id = data["conversation_id"]
        print(f"[ai basic] conv_id={TestAIChat.conv_id} content_len={len(data['content'])}")

    def test_ai_chat_tool_use_list_companies(self, creator_headers):
        r = requests.post(f"{BASE_URL}/api/ai/chat",
                          headers=creator_headers,
                          json={"message": "Mening kompaniyalarimni ro'yxatini ko'rsat",
                                "conversation_id": TestAIChat.conv_id}, timeout=120)
        assert r.status_code == 200, f"AI chat tool 500: {r.text}"
        data = r.json()
        assert "content" in data
        tool_trace = data.get("tool_trace") or data.get("tools") or []
        print(f"[ai tool] trace={tool_trace}")
        tools_used = [t.get("tool") or t.get("name") for t in tool_trace] if isinstance(tool_trace, list) else []
        assert "list_companies" in tools_used, f"list_companies not in tool_trace: {tool_trace}"

    def test_ai_chat_conversation_continuity(self, creator_headers):
        assert TestAIChat.conv_id, "no conv id from prior test"
        r = requests.get(f"{BASE_URL}/api/ai/conversations/{TestAIChat.conv_id}/messages",
                         headers=creator_headers, timeout=30)
        assert r.status_code == 200, r.text
        msgs = r.json()["messages"]
        roles = [m["role"] for m in msgs]
        user_count = roles.count("user")
        assistant_count = roles.count("assistant")
        print(f"[ai continuity] user={user_count} assistant={assistant_count} total={len(msgs)}")
        assert user_count >= 2, f"expected >=2 user, got {user_count}"
        assert assistant_count >= 2, f"expected >=2 assistant, got {assistant_count}"


# ---------- Trailing-slash fix ----------
class TestNoTrailingSlashRedirect:
    def test_patch_creator_users_no_307(self, creator_headers):
        # Need a target user. Create one via register.
        email = f"test_slash_{uuid.uuid4().hex[:8]}@example.com"
        rr = requests.post(f"{BASE_URL}/api/auth/register",
                           json={"email": email, "password": "Passw0rd!123", "full_name": "Slash Test"},
                           timeout=30)
        assert rr.status_code == 200, rr.text
        # Find user id via creator/users
        lr = requests.get(f"{BASE_URL}/api/creator/users", headers=creator_headers, timeout=30)
        assert lr.status_code == 200
        users = lr.json().get("users", lr.json() if isinstance(lr.json(), list) else [])
        if isinstance(users, dict):
            users = users.get("users", [])
        target = next((u for u in users if u.get("email") == email), None)
        assert target, f"user {email} not found"
        uid = target.get("id") or target.get("_id")

        # PATCH without trailing slash + no redirect follow
        pr = requests.patch(f"{BASE_URL}/api/creator/users/{uid}",
                            headers=creator_headers,
                            json={"access_granted": False},
                            allow_redirects=False, timeout=30)
        print(f"[patch no-slash] status={pr.status_code} body={pr.text[:200]}")
        assert pr.status_code == 200, f"expected 200, got {pr.status_code}"
        body = pr.json()
        assert body.get("access_granted") is False or body.get("updated") or body.get("id"), body

    def test_delete_mappings_no_307(self, creator_headers):
        # Need a company + mapping. Creator has permission to POST mappings? Try; else create via new admin token.
        # Try to create a company under creator.
        cr = requests.post(f"{BASE_URL}/api/companies",
                           headers=creator_headers,
                           json={"name": f"TEST_slash_{uuid.uuid4().hex[:6]}", "inn": "123456789"},
                           timeout=30)
        if cr.status_code >= 400:
            pytest.skip(f"cannot create company as creator: {cr.status_code} {cr.text}")
        company_id = cr.json().get("id") or cr.json().get("_id")

        mr = requests.post(f"{BASE_URL}/api/mappings",
                           headers=creator_headers,
                           json={"company_id": company_id, "soliq_name": "TEST_soliq", "one_c_name": "TEST_1c"},
                           timeout=30)
        if mr.status_code >= 400:
            pytest.skip(f"cannot create mapping: {mr.status_code} {mr.text}")
        mid = mr.json().get("id") or mr.json().get("_id")

        # DELETE without trailing slash, no redirect follow
        dr = requests.delete(f"{BASE_URL}/api/mappings/{mid}",
                             headers=creator_headers,
                             allow_redirects=False, timeout=30)
        print(f"[delete mapping no-slash] status={dr.status_code} body={dr.text[:200]}")
        assert dr.status_code == 200, f"expected 200, got {dr.status_code} body={dr.text}"


# ---------- Regressions ----------
class TestRegression:
    def test_register_and_login(self):
        email = f"reg_{uuid.uuid4().hex[:8]}@example.com"
        r = requests.post(f"{BASE_URL}/api/auth/register",
                          json={"email": email, "password": "Passw0rd!123", "full_name": "Reg Test"},
                          timeout=30)
        assert r.status_code == 200, r.text
        assert "token" in r.json()
        # login
        lr = requests.post(f"{BASE_URL}/api/auth/login",
                           json={"email": email, "password": "Passw0rd!123"}, timeout=30)
        assert lr.status_code == 200
        assert lr.json()["user"]["role"] == "administrator"

    def test_creator_login(self):
        r = requests.post(f"{BASE_URL}/api/auth/login",
                          json={"email": CREATOR_EMAIL, "password": CREATOR_PASSWORD}, timeout=30)
        assert r.status_code == 200
        assert r.json()["user"]["role"] == "creator"

    def test_companies_crud(self):
        # fresh user
        email = f"co_{uuid.uuid4().hex[:8]}@example.com"
        rr = requests.post(f"{BASE_URL}/api/auth/register",
                           json={"email": email, "password": "Passw0rd!123", "full_name": "CoTest"}, timeout=30)
        tok = rr.json()["token"]
        h = {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}

        gr = requests.get(f"{BASE_URL}/api/companies", headers=h, timeout=30)
        assert gr.status_code == 200
        data = gr.json()
        # accept list or {companies:[]}
        arr = data.get("companies") if isinstance(data, dict) else data
        assert isinstance(arr, list) and len(arr) == 0

        cr = requests.post(f"{BASE_URL}/api/companies", headers=h,
                           json={"name": "TEST_co", "inn": "999888777"}, timeout=30)
        assert cr.status_code == 200, cr.text
        cid = cr.json().get("id") or cr.json().get("_id")

        sr = requests.get(f"{BASE_URL}/api/companies/{cid}/stats", headers=h, timeout=30)
        assert sr.status_code == 200

    def test_creator_users_list(self, creator_headers):
        r = requests.get(f"{BASE_URL}/api/creator/users", headers=creator_headers, timeout=30)
        assert r.status_code == 200

    def test_root(self):
        r = requests.get(f"{BASE_URL}/api/", timeout=30)
        assert r.status_code == 200
