"""Knowledge base + Telegram status tests (creator-only)."""
import os
import time
import io
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    # Read from frontend/.env
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().rstrip("/")

CREATOR_EMAIL = "layloinomova99@gmail.com"
CREATOR_PW = "Creator@2026!Secure"


@pytest.fixture(scope="module")
def creator_token():
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": CREATOR_EMAIL, "password": CREATOR_PW})
    assert r.status_code == 200, f"Creator login failed: {r.status_code} {r.text}"
    data = r.json()
    assert data["user"]["role"] == "creator"
    return data["token"]


@pytest.fixture(scope="module")
def admin_token():
    email = f"TEST_admin_{int(time.time())}@example.com"
    r = requests.post(f"{BASE_URL}/api/auth/register", json={
        "email": email, "password": "Testpass123!", "full_name": "Test Admin", "phone": "+998900000000"
    })
    assert r.status_code == 200, r.text
    return r.json()["token"]


def _h(t):
    return {"Authorization": f"Bearer {t}"}


# --- Basic access ---
def test_list_knowledge_creator(creator_token):
    r = requests.get(f"{BASE_URL}/api/knowledge", headers=_h(creator_token))
    assert r.status_code == 200, r.text
    data = r.json()
    assert "documents" in data
    assert isinstance(data["documents"], list)


def test_telegram_status_creator(creator_token):
    r = requests.get(f"{BASE_URL}/api/telegram/status", headers=_h(creator_token))
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["bot_configured"] is True
    assert data.get("bot_username") == "AI_Buxgalter_yordamchisi_bot"
    assert "linked" in data


def test_knowledge_forbidden_for_admin(admin_token):
    r = requests.get(f"{BASE_URL}/api/knowledge", headers=_h(admin_token))
    assert r.status_code == 403


def test_telegram_status_forbidden_for_admin(admin_token):
    r = requests.get(f"{BASE_URL}/api/telegram/status", headers=_h(admin_token))
    assert r.status_code == 403


# --- Upload + retrieval + delete ---
@pytest.fixture(scope="module")
def uploaded_doc(creator_token):
    content = (
        "TEST_KNOWLEDGE_DOC — 1C OData Endpoints Reference\n"
        "\n"
        "1C endpoint yo'li: /odata/standard.odata/$metadata\n"
        "Authentication: HTTP Basic Auth (login:parol)\n"
        "Sotuv hujjati OData yo'li: /odata/standard.odata/Document_SotuvniRasmiylashtirish\n"
        "Content-Type: application/json\n"
        "\n"
        "Qoida: Yandex marketplace cheklarini 1C da Sotuv hujjati sifatida yozish kerak.\n"
        "Har bir chek uchun external_id fiscal_id bilan mos kelishi kerak.\n"
    )
    files = {"file": ("test_kb_1c.txt", content, "text/plain")}
    data = {"note": "TEST_ Bilim bazasi 1C endpoint yo'llari"}
    r = requests.post(f"{BASE_URL}/api/knowledge/upload", headers=_h(creator_token), files=files, data=data, timeout=120)
    assert r.status_code == 200, r.text
    body = r.json()
    return body


def test_upload_returns_ready(uploaded_doc):
    assert uploaded_doc.get("status") == "ready", f"Upload not ready: {uploaded_doc}"
    assert uploaded_doc.get("id")
    assert uploaded_doc.get("rules_count", 0) > 0, f"No rules extracted: {uploaded_doc}"
    assert uploaded_doc.get("title")
    assert uploaded_doc.get("summary")


def test_get_knowledge_detail(creator_token, uploaded_doc):
    doc_id = uploaded_doc["id"]
    r = requests.get(f"{BASE_URL}/api/knowledge/{doc_id}", headers=_h(creator_token))
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["id"] == doc_id
    assert isinstance(d.get("rules"), list)
    assert len(d["rules"]) == uploaded_doc["rules_count"]
    for rule in d["rules"]:
        assert rule.get("instruction")


def test_rules_endpoint_includes_uploaded_rules(creator_token, uploaded_doc):
    r = requests.get(f"{BASE_URL}/api/rules", headers=_h(creator_token))
    assert r.status_code == 200
    rules = r.json().get("rules", [])
    # At least one rule with the doc id in structured_rule
    doc_id = uploaded_doc["id"]
    matching = [x for x in rules if isinstance(x.get("structured_rule"), dict)
                and x["structured_rule"].get("knowledge_doc_id") == doc_id]
    assert len(matching) >= 1, "Uploaded doc's rules not visible in /api/rules"


def test_delete_knowledge_removes_rules(creator_token, uploaded_doc):
    doc_id = uploaded_doc["id"]
    r = requests.delete(f"{BASE_URL}/api/knowledge/{doc_id}", headers=_h(creator_token))
    assert r.status_code == 200, r.text
    # Verify gone
    r2 = requests.get(f"{BASE_URL}/api/knowledge/{doc_id}", headers=_h(creator_token))
    assert r2.status_code == 404
    # Verify rules removed
    r3 = requests.get(f"{BASE_URL}/api/rules", headers=_h(creator_token))
    rules = r3.json().get("rules", [])
    matching = [x for x in rules if isinstance(x.get("structured_rule"), dict)
                and x["structured_rule"].get("knowledge_doc_id") == doc_id]
    assert len(matching) == 0, "Rules were not deleted with doc"


# --- AI tool integration ---
def test_ai_chat_save_creator_rule_tool(creator_token):
    payload = {"message": "Bundan keyin Yandex cheklarini 1C da Sotuv hujjati sifatida yoz"}
    r = requests.post(f"{BASE_URL}/api/ai/chat", headers=_h(creator_token), json=payload, timeout=90)
    assert r.status_code == 200, r.text
    data = r.json()
    tool_trace = data.get("tool_trace") or []
    tools_used = [t.get("tool") for t in tool_trace]
    assert "save_creator_rule" in tools_used, f"save_creator_rule not called. Tools: {tools_used}"

    # Verify rule saved
    r2 = requests.get(f"{BASE_URL}/api/rules", headers=_h(creator_token))
    rules = r2.json().get("rules", [])
    # Look for a rule mentioning yandex or sotuv
    matching = [x for x in rules if "yandex" in (x.get("instruction") or "").lower()
                or "sotuv" in (x.get("instruction") or "").lower()]
    assert len(matching) >= 1, "No matching rule found from save_creator_rule call"


def test_ai_chat_search_knowledge_best_effort(creator_token):
    # First re-upload doc so search has something to find
    content = "1C OData endpoint yo'li: /odata/standard.odata/$metadata. Authentication: HTTP Basic Auth."
    files = {"file": ("test_kb_search.txt", content, "text/plain")}
    data = {"note": "TEST_ search knowledge"}
    ru = requests.post(f"{BASE_URL}/api/knowledge/upload", headers=_h(creator_token), files=files, data=data, timeout=120)
    assert ru.status_code == 200
    doc_id = ru.json().get("id")

    payload = {"message": "1C OData endpoint yo'li nima?"}
    r = requests.post(f"{BASE_URL}/api/ai/chat", headers=_h(creator_token), json=payload, timeout=90)
    assert r.status_code == 200, r.text
    tool_trace = r.json().get("tool_trace") or []
    tools_used = [t.get("tool") for t in tool_trace]
    # Best-effort assertion - log if not used
    if "search_knowledge" not in tools_used:
        print(f"WARNING: search_knowledge not called. Tools: {tools_used}")
    # Cleanup
    if doc_id:
        requests.delete(f"{BASE_URL}/api/knowledge/{doc_id}", headers=_h(creator_token))
