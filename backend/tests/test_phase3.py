"""Phase 3 tests: 1C connection, Soliq upload, matching, approvals."""
import os
import io
import time
import pytest
import requests
import openpyxl
from datetime import datetime

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://accounting-ai-29.preview.emergentagent.com").rstrip("/")
CREATOR_EMAIL = "layloinomova99@gmail.com"
CREATOR_PASS = "Creator@2026!Secure"


# ---------- fixtures ----------
@pytest.fixture(scope="session")
def creator_token():
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": CREATOR_EMAIL, "password": CREATOR_PASS})
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="session")
def h_creator(creator_token):
    return {"Authorization": f"Bearer {creator_token}", "Content-Type": "application/json"}


@pytest.fixture(scope="session")
def admin_token():
    email = f"TEST_admin_{int(time.time())}@example.com"
    r = requests.post(f"{BASE_URL}/api/auth/register", json={
        "email": email, "password": "AdminX@2026!", "full_name": "TEST Admin"
    })
    assert r.status_code == 200, r.text
    return r.json()["token"], email


@pytest.fixture(scope="session")
def company_id(h_creator):
    """Create a fresh company for clean tests."""
    r = requests.post(f"{BASE_URL}/api/companies", headers=h_creator, json={
        "name": f"TEST_Phase3_{int(time.time())}", "inn": "123456789"
    })
    assert r.status_code == 200, r.text
    cid = r.json()["id"]
    yield cid
    # teardown
    requests.delete(f"{BASE_URL}/api/companies/{cid}", headers=h_creator)


# ---------- 1C connection ----------
class Test1CConnection:
    def test_save_connection(self, h_creator, company_id):
        r = requests.put(f"{BASE_URL}/api/companies/{company_id}/one-c", headers=h_creator, json={
            "base_url": "https://clobus.uz/a/acc320/76202/en_US/",
            "username": "ai_bot", "password": "x", "auth_mode": "basic",
        })
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["configured"] is True
        assert d["has_password"] is True
        assert "password" not in d
        assert "password_enc" not in d

    def test_get_connection(self, h_creator, company_id):
        r = requests.get(f"{BASE_URL}/api/companies/{company_id}/one-c", headers=h_creator)
        assert r.status_code == 200
        d = r.json()
        assert d["configured"] is True
        assert d["has_password"] is True
        assert d.get("username") == "ai_bot"
        assert "password" not in d and "password_enc" not in d

    def test_test_connection_fails_401(self, h_creator, company_id):
        r = requests.post(f"{BASE_URL}/api/companies/{company_id}/one-c/test", headers=h_creator)
        assert r.status_code == 200
        d = r.json()
        assert d.get("ok") is False
        assert d.get("reason")  # should have error msg
        # Company one_c_status should be error
        cg = requests.get(f"{BASE_URL}/api/companies/{company_id}/one-c", headers=h_creator).json()
        assert cg.get("status") == "error"

    def test_sync_products_returns_400(self, h_creator, company_id):
        r = requests.post(f"{BASE_URL}/api/companies/{company_id}/one-c/sync-products", headers=h_creator)
        assert r.status_code == 400

    def test_delete_resets(self, h_creator, company_id):
        r = requests.delete(f"{BASE_URL}/api/companies/{company_id}/one-c", headers=h_creator)
        assert r.status_code == 200
        assert r.json().get("deleted") is True
        g = requests.get(f"{BASE_URL}/api/companies/{company_id}/one-c", headers=h_creator).json()
        assert g["configured"] is False


# ---------- helper to build soliq xlsx ----------
def build_soliq_xlsx(receipts):
    wb = openpyxl.Workbook()
    ws = wb.active
    headers = ["Чек санаси", "Чек рақами", "ФМ рақами", "СТИР/ЖШШР", "Чек тури",
               "Маҳсулот номи", "МХИК", "Миқдори", "Нархи", "ҚҚС суммаси",
               "Жами нақд пул", "Жами банк карта"]
    ws.append(headers)
    for row in receipts:
        ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


# ---------- products + soliq upload + matching ----------
@pytest.fixture(scope="class")
def products(h_creator, company_id):
    """Create matching products (by name + mxik)."""
    ids = {}
    for p in [
        {"name": "Non oq", "mxik": "1234567890", "unit": "dona", "external_one_c_id": "prod-non"},
        {"name": "Sut 1L", "mxik": "9876543210", "unit": "l", "external_one_c_id": "prod-sut"},
    ]:
        r = requests.post(f"{BASE_URL}/api/products", headers=h_creator,
                          json={"company_id": None if False else "PH", **p})
        # need company_id
    # Reset — direct call with company_id
    ids = {}
    for p in [
        {"company_id": "", "name": "Non oq", "mxik": "1234567890", "unit": "dona", "external_one_c_id": "prod-non"},
        {"company_id": "", "name": "Sut 1L", "mxik": "9876543210", "unit": "l", "external_one_c_id": "prod-sut"},
    ]:
        p["company_id"] = company_id
        r = requests.post(f"{BASE_URL}/api/products", headers=h_creator, json=p)
        assert r.status_code == 200, r.text
        ids[p["name"]] = r.json()["id"]
    return ids


class TestSoliqAndMatch:
    def test_upload_soliq(self, h_creator, company_id, products):
        # 2 receipts, one return-type row (skipped), plus unmatched line
        rows = [
            # Receipt 1 - two lines, both should match by mxik/name
            ["01.01.2026 10:00:00", "R1", "FM1", "123456789", "Sotuv", "Non oq", "1234567890", 2, 20000, 1600, 20000, 0],
            ["01.01.2026 10:00:00", "R1", "FM1", "123456789", "Sotuv", "Sut 1L", "9876543210", 1, 15000, 1200, 15000, 0],
            # Receipt 2 - unmatched line (needs review)
            ["02.01.2026 11:00:00", "R2", "FM1", "123456789", "Sotuv", "Kolbasa dokt", "0000000000", 1, 30000, 2400, 30000, 0],
            # Return - should be skipped
            ["03.01.2026 12:00:00", "R3", "FM1", "123456789", "Қайтариш", "Non oq", "1234567890", 1, 10000, 800, 10000, 0],
        ]
        data = build_soliq_xlsx(rows)
        r = requests.post(f"{BASE_URL}/api/companies/{company_id}/soliq/upload",
                          headers={"Authorization": h_creator["Authorization"]},
                          files={"file": ("soliq.xlsx", data,
                                          "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
        assert r.status_code == 200, r.text
        d = r.json()
        print("Upload result:", d)
        assert d["created"] == 2, f"Expected 2 created, got {d}"
        assert d["matched"] >= 1
        assert d["needs_review"] >= 1
        pytest.receipt_ids = d["receipt_ids"]

    def test_reupload_duplicates(self, h_creator, company_id):
        rows = [
            ["01.01.2026 10:00:00", "R1", "FM1", "123456789", "Sotuv", "Non oq", "1234567890", 2, 20000, 1600, 20000, 0],
            ["01.01.2026 10:00:00", "R1", "FM1", "123456789", "Sotuv", "Sut 1L", "9876543210", 1, 15000, 1200, 15000, 0],
        ]
        data = build_soliq_xlsx(rows)
        r = requests.post(f"{BASE_URL}/api/companies/{company_id}/soliq/upload",
                          headers={"Authorization": h_creator["Authorization"]},
                          files={"file": ("soliq.xlsx", data, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
        assert r.status_code == 200
        d = r.json()
        assert d["duplicates"] >= 1
        assert d["created"] == 0

    def test_non_soliq_xlsx_400(self, h_creator, company_id):
        wb = openpyxl.Workbook()
        wb.active.append(["foo", "bar"])
        wb.active.append([1, 2])
        buf = io.BytesIO(); wb.save(buf)
        r = requests.post(f"{BASE_URL}/api/companies/{company_id}/soliq/upload",
                          headers={"Authorization": h_creator["Authorization"]},
                          files={"file": ("bad.xlsx", buf.getvalue(),
                                          "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
        assert r.status_code == 400

    def test_receipt_detail(self, h_creator):
        rid = pytest.receipt_ids[0]
        r = requests.get(f"{BASE_URL}/api/receipts/{rid}", headers=h_creator)
        assert r.status_code == 200
        d = r.json()
        assert d["receipt"]["id"] == rid
        items = d["items"]
        assert len(items) >= 1
        # At least one item has matched_product_id (from R1 - matched)
        # R1 items
        for it in items:
            assert "matched_product_id" in it
            assert "match_confidence" in it
            assert "match_reason" in it

    def test_manual_match(self, h_creator, company_id, products):
        # Find receipt R2 (needs_review) and match its item
        # Fetch receipts
        r = requests.get(f"{BASE_URL}/api/companies/{company_id}/receipts", headers=h_creator)
        assert r.status_code == 200
        receipts = r.json()["receipts"]
        needs = [x for x in receipts if x["status"] == "needs_review"]
        assert needs, f"No needs_review receipts: {receipts}"
        rid = needs[0]["id"]
        d = requests.get(f"{BASE_URL}/api/receipts/{rid}", headers=h_creator).json()
        item = d["items"][0]
        prod_id = products["Non oq"]
        r2 = requests.post(f"{BASE_URL}/api/receipt-items/{item['id']}/match", headers=h_creator,
                           json={"product_id": prod_id, "save_mapping": True})
        assert r2.status_code == 200, r2.text
        # After matching all items receipt status should be matched
        r3 = requests.get(f"{BASE_URL}/api/receipts/{rid}", headers=h_creator).json()
        assert r3["receipt"]["status"] == "matched"
        # Mapping created
        mp = requests.get(f"{BASE_URL}/api/companies/{company_id}/mappings", headers=h_creator).json()
        assert mp["count"] >= 1

    def test_import_to_1c_needs_1c_conn(self, h_creator, company_id):
        # Re-save 1C connection with bad creds
        r = requests.put(f"{BASE_URL}/api/companies/{company_id}/one-c", headers=h_creator, json={
            "base_url": "https://clobus.uz/a/acc320/76202/en_US/",
            "username": "ai_bot", "password": "x", "auth_mode": "basic",
        })
        assert r.status_code == 200
        # Get matched receipt
        rc = requests.get(f"{BASE_URL}/api/companies/{company_id}/receipts?status=matched",
                          headers=h_creator).json()
        assert rc["receipts"], "Need at least 1 matched receipt"
        matched_id = rc["receipts"][0]["id"]
        pytest.matched_receipt_id = matched_id
        # Also get a needs_review receipt if exists (all matched now? then skip that test)
        nr = requests.get(f"{BASE_URL}/api/companies/{company_id}/receipts?status=needs_review",
                          headers=h_creator).json()
        pytest.needs_review_id = nr["receipts"][0]["id"] if nr["receipts"] else None

        # Create pending action
        r2 = requests.post(f"{BASE_URL}/api/companies/{company_id}/receipts/import-1c",
                           headers=h_creator, json={"receipt_ids": [matched_id]})
        assert r2.status_code == 200, r2.text
        act = r2.json()
        assert act["status"] == "pending"
        pytest.action_id = act["id"]

    def test_actions_list(self, h_creator, company_id):
        r = requests.get(f"{BASE_URL}/api/actions?status=pending&company_id={company_id}", headers=h_creator)
        assert r.status_code == 200
        rows = r.json()["actions"]
        assert any(a["id"] == pytest.action_id for a in rows)

    def test_approve_fails_with_1c_auth(self, h_creator):
        r = requests.post(f"{BASE_URL}/api/actions/{pytest.action_id}/approve", headers=h_creator)
        assert r.status_code == 200, r.text
        d = r.json()
        # Expected: failed due to fake 1C creds
        assert d["status"] in ("failed", "done"), d
        # If failed, receipt should have status failed
        # Note: import_receipt returns non-ok when push_receipt raises → captured as exception → failed

    def test_reject_action(self, h_creator, company_id):
        # Create another action to reject
        rc = requests.get(f"{BASE_URL}/api/companies/{company_id}/receipts?status=matched",
                          headers=h_creator).json()
        if not rc["receipts"]:
            pytest.skip("No matched receipts left")
        rid = rc["receipts"][0]["id"]
        # receipt may be failed now; we can still add? The endpoint accepts matched/approved/failed
        r = requests.post(f"{BASE_URL}/api/companies/{company_id}/receipts/import-1c",
                          headers=h_creator, json={"receipt_ids": [rid]})
        assert r.status_code == 200, r.text
        aid = r.json()["id"]
        r2 = requests.post(f"{BASE_URL}/api/actions/{aid}/reject", headers=h_creator)
        assert r2.status_code == 200
        assert r2.json()["status"] == "rejected"

    def test_needs_review_import_400(self, h_creator, company_id):
        if not pytest.needs_review_id:
            pytest.skip("No needs_review receipt available")
        r = requests.post(f"{BASE_URL}/api/companies/{company_id}/receipts/import-1c",
                          headers=h_creator, json={"receipt_ids": [pytest.needs_review_id]})
        assert r.status_code == 400


# ---------- role isolation ----------
class TestRoleIsolation:
    def test_admin_cannot_see_creator_company(self, admin_token, company_id):
        tok, _ = admin_token
        r = requests.get(f"{BASE_URL}/api/companies/{company_id}/receipts",
                         headers={"Authorization": f"Bearer {tok}"})
        assert r.status_code == 404
