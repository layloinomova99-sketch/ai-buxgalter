"""1C OData adapter — ported from legacy OneCBridge (V129) into a per-company adapter."""
import re
import json
import base64
import asyncio
import logging
import difflib
import unicodedata
import xml.etree.ElementTree as ET
from typing import Optional
import aiohttp

log = logging.getLogger("one_c")
TRANSIENT = {408, 425, 429, 500, 502, 503, 504}


def norm(value) -> str:
    s = unicodedata.normalize("NFKC", str(value or "")).lower().replace("ё", "е")
    s = re.sub(r"[^a-zа-я0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def normc(value) -> str:
    return norm(value).replace(" ", "")


def clobus_odata_url(value: str) -> str:
    raw = (value or "").strip().split("?", 1)[0].rstrip("/")
    if not raw:
        return ""
    if "/odata/standard.odata" in raw:
        return raw
    raw = re.sub(r"/(?:ru|uz|en|en_us|ru_ru)$", "", raw, flags=re.I).rstrip("/")
    return raw + "/odata/standard.odata"


def row_name(row: dict) -> str:
    for k in ("Description", "Наименование", "Name"):
        if row.get(k):
            return str(row[k])
    return ""


class OneCAdapter:
    def __init__(self, connection: Optional[dict] = None):
        c = connection or {}
        self.base_url = clobus_odata_url(c.get("base_url") or "")
        self.username = (c.get("username") or "").strip()
        self.password = (c.get("password") or "").strip()
        self.token = (c.get("token") or "").strip()
        self.auth_mode = (c.get("auth_mode") or "basic").lower()
        self.verify_ssl = c.get("verify_ssl", True)
        self.timeout = aiohttp.ClientTimeout(total=int(c.get("timeout") or 60))
        self.metadata = ""
        self.entity_sets: dict = {}
        self.entity_properties: dict = {}
        self.entity_property_types: dict = {}
        self.entity_navigation: dict = {}
        self.enum_members: dict = {}

    @property
    def enabled(self) -> bool:
        return bool(self.base_url and (self.token or (self.username and self.password)))

    def _headers(self, json_body=False) -> dict:
        h = {"Accept": "application/json", "User-Agent": "AI-BUXGALTER-1C/2.0"}
        if json_body:
            h["Content-Type"] = "application/json"
        if self.auth_mode == "bearer" and self.token:
            h["Authorization"] = f"Bearer {self.token}"
        elif self.username and self.password:
            h["Authorization"] = "Basic " + base64.b64encode(f"{self.username}:{self.password}".encode()).decode("ascii")
        return h

    async def _request(self, method: str, url: str, **kwargs):
        json_body = kwargs.get("json") is not None
        headers = self._headers(json_body)
        headers.update(kwargs.pop("headers", {}) or {})
        kwargs["headers"] = headers
        kwargs.setdefault("ssl", self.verify_ssl)
        mu = method.upper()
        max_attempts = 1 if mu in {"POST", "PUT", "DELETE", "PATCH"} else 3
        for attempt in range(1, max_attempts + 1):
            try:
                async with aiohttp.ClientSession(timeout=self.timeout) as s:
                    async with s.request(method, url, **kwargs) as r:
                        text = await r.text(errors="ignore")
                        if r.status >= 400:
                            detail = text[:800].replace("\n", " ")
                            if r.status in (401, 402):
                                raise RuntimeError(f"1C HTTP {r.status}: autentifikatsiya rad etildi. Login/parolni tekshiring. {detail}")
                            if r.status in TRANSIENT and attempt < max_attempts:
                                await asyncio.sleep(min(8.0, 1.5 * attempt)); continue
                            raise RuntimeError(f"1C HTTP {r.status}: {detail}")
                        return r.status, text
            except (aiohttp.ClientConnectionError, asyncio.TimeoutError, OSError) as e:
                if attempt >= max_attempts:
                    raise RuntimeError(f"1C ulanish xatosi: {type(e).__name__}: {e}")
                await asyncio.sleep(min(8.0, 1.5 * attempt))
        raise RuntimeError("1C OData so'rov bajarilmadi.")

    # ---------- metadata ----------
    async def load_metadata(self, refresh=False) -> str:
        if self.metadata and not refresh:
            return self.metadata
        if not self.base_url:
            raise RuntimeError("1C URL sozlanmagan.")
        _, text = await self._request("GET", f"{self.base_url}/$metadata", headers={"Accept": "application/xml"})
        self.metadata = text
        self._parse_metadata(text)
        if not self.entity_sets:
            raise RuntimeError("1C metadata o'qildi, lekin entity topilmadi. URL to'g'rimi?")
        return text

    def _parse_metadata(self, text: str):
        self.entity_sets, self.entity_properties, self.entity_property_types, self.entity_navigation, self.enum_members = {}, {}, {}, {}, {}
        local = lambda t: t.split("}")[-1] if "}" in t else t  # noqa: E731
        try:
            root = ET.fromstring(text)
        except Exception as e:
            raise RuntimeError(f"1C metadata XML o'qilmadi: {e}")
        associations = {}
        for el in root.iter():
            if local(el.tag) == "Association" and el.get("Name"):
                associations[el.get("Name")] = [(e.get("Role") or "", (e.get("Type") or "").split(".")[-1], e.get("Multiplicity") or "1")
                                                for e in el if local(e.tag) == "End"]
        for el in root.iter():
            tag = local(el.tag)
            if tag in ("EntityType", "ComplexType") and el.get("Name"):
                et = el.get("Name"); props, types, navs = [], {}, {}
                for ch in el:
                    ct = local(ch.tag)
                    if ct == "Property" and ch.get("Name"):
                        props.append(ch.get("Name")); types[ch.get("Name")] = ch.get("Type") or ""
                    elif ct == "NavigationProperty" and ch.get("Name"):
                        navs[ch.get("Name")] = {"relationship": (ch.get("Relationship") or "").split(".")[-1], "to_role": ch.get("ToRole") or ""}
                self.entity_properties[et] = props; self.entity_property_types[et] = types; self.entity_navigation[et] = navs
            elif tag == "EntitySet" and el.get("Name") and el.get("EntityType"):
                self.entity_sets[el.get("Name")] = el.get("EntityType").split(".")[-1]
            elif tag == "EnumType" and el.get("Name"):
                members = [m.get("Name") for m in el if local(m.tag) == "Member" and m.get("Name")]
                if members:
                    self.enum_members[el.get("Name")] = members
        for et, navs in self.entity_navigation.items():
            for info in navs.values():
                target, is_coll = None, False
                for role, ttype, mult in associations.get(info["relationship"]) or []:
                    if role == info["to_role"]:
                        target, is_coll = ttype, mult.strip() in {"*", "0..*", "1..*"}
                info["target_type"], info["is_collection"] = target, is_coll

    # ---------- reads ----------
    async def health(self) -> dict:
        if not self.enabled:
            return {"ok": False, "reason": "URL yoki login/parol to'liq emas."}
        try:
            await self.load_metadata(refresh=True)
            return {"ok": True, "entities": len(self.entity_sets)}
        except Exception as e:
            return {"ok": False, "reason": str(e)}

    async def get_entities(self, entity_set: str, top=100, params: Optional[dict] = None) -> list:
        p = {"$format": "json", "$top": str(top)}
        p.update(params or {})
        _, text = await self._request("GET", f"{self.base_url}/{entity_set}", params=p)
        try:
            data = json.loads(text)
        except Exception:
            raise RuntimeError(f"1C {entity_set} JSON qaytarmadi: {text[:300]}")
        v = data.get("value", []) if isinstance(data, dict) else data
        return v if isinstance(v, list) else []

    async def get_entities_all(self, entity_set: str, limit=10000, page_size=1000) -> list:
        await self.load_metadata()
        rows, skip = [], 0
        while len(rows) < limit:
            take = min(page_size, limit - len(rows))
            vals = await self.get_entities(entity_set, top=take, params={"$skip": str(skip)})
            if not vals:
                break
            rows.extend(x for x in vals if isinstance(x, dict))
            if len(vals) < take:
                break
            skip += take
        return rows[:limit]

    def pick_entity_set(self, aliases: list, explicit: Optional[str] = None) -> Optional[str]:
        if explicit and explicit in self.entity_sets:
            return explicit
        cands = [(n, normc(n)) for n in self.entity_sets if n.count("_") == 1]
        for a in aliases:
            an = normc(a)
            for n, nn in cands:
                if an and an in nn:
                    return n
        return None

    async def load_catalog(self, aliases: list, limit=5000) -> tuple:
        await self.load_metadata()
        ent = self.pick_entity_set(["Catalog_" + a for a in aliases] + aliases)
        if not ent:
            return None, []
        rows = await self.get_entities_all(ent, limit=limit)
        return ent, [r for r in rows if r.get("IsFolder") is not True and r.get("ЭтоГруппа") is not True and r.get("DeletionMark") is not True]

    async def load_nomenclature(self, limit=20000) -> list:
        ent, rows = await self.load_catalog(["Номенклатура", "Nomenclature"], limit)
        out = []
        for r in rows:
            mxik = ""
            for k, v in r.items():
                if v and any(w in normc(k) for w in ("икпу", "mxik", "ikpu", "мхик")):
                    mxik = str(v); break
            out.append({"ref_key": r.get("Ref_Key"), "name": row_name(r), "code": str(r.get("Code") or r.get("Код") or ""),
                        "mxik": mxik, "unit": str(r.get("ЕдиницаИзмерения") or ""), "entity": ent})
        return [x for x in out if x["ref_key"] and x["name"]]

    # ---------- check document structure ----------
    @staticmethod
    def _pick(props: list, names: list) -> Optional[str]:
        nrm = [(p, normc(p)) for p in props]
        for a in names:
            an = normc(a)
            for p, n in nrm:
                if n == an:
                    return p
        for a in names:
            an = normc(a)
            for p, n in nrm:
                if an in n:
                    return p
        return None

    def check_doc_candidates(self) -> list:
        out = []
        for e in self.entity_sets:
            if not e.startswith("Document_") or e.count("_") > 1:
                continue
            n = normc(e[len("Document_"):])
            if any(w in n for w in ("возврат", "коррект", "смен", "оплат", "подароч", "переоценк", "егаис", "маркиров")):
                continue
            if "чекккм" in n: out.append((100, e, "check"))
            elif n.startswith("чек") or n.endswith("чек"): out.append((60, e, "check"))
            elif n.startswith("отчет") and "розничныхпродаж" in n: out.append((40, e, "report"))
            elif "розничныепродажи" in n or "розничнаяпродажа" in n: out.append((30, e, "report"))
            elif "реализациятоваровуслуг" in n: out.append((20, e, "sale"))
        out.sort(key=lambda x: (-x[0], x[1]))
        return out

    def table_sections(self, ent: str) -> dict:
        et = self.entity_sets[ent]; out = {}
        for nav, info in self.entity_navigation.get(et, {}).items():
            if info.get("is_collection") and info.get("target_type"):
                out[nav] = (info["target_type"], list(self.entity_properties.get(info["target_type"], [])))
        for p, t in self.entity_property_types.get(et, {}).items():
            mm = re.match(r"\s*Collection\((.+)\)\s*$", str(t or ""))
            if mm and p not in out:
                tgt = mm.group(1).split(".")[-1]
                out[p] = (tgt, list(self.entity_properties.get(tgt, [])))
        for es, et2 in self.entity_sets.items():
            if es.startswith(ent + "_") and es.count("_") == 2:
                name = es[len(ent) + 1:]
                if name not in out or not out[name][1]:
                    out[name] = (et2, list(self.entity_properties.get(et2, [])))
        return {k: v for k, v in out.items() if v[1]}

    def build_structure(self, ent: str, mode: str) -> dict:
        et = self.entity_sets[ent]; props = self.entity_properties.get(et, [])
        sections = self.table_sections(ent); table, best = None, 0
        for nav, (target, tp) in sections.items():
            np_ = [norm(p) for p in tp]
            score = sum(1 for h in ("Номенклатура", "Количество", "Цена", "Сумма") if any(norm(h) in p for p in np_))
            if score > best:
                best, table = score, (nav, target, tp)
        st = {"entity": ent, "mode": mode, "etype": et, "props": props, "table": table,
              "date": self._pick(props, ["Date", "Дата"]), "comment": self._pick(props, ["Комментарий", "Comment"]),
              "warehouse": self._pick(props, ["Склад_Key", "Warehouse_Key"]), "organization": self._pick(props, ["Организация_Key", "Organization_Key"]),
              "operation": self._pick(props, ["ВидОперации", "OperationType"]), "amount": self._pick(props, ["СуммаДокумента", "DocumentAmount"]),
              "t": {}, "pay": None}
        if table:
            tp = table[2]
            st["t"] = {"nom": self._pick(tp, ["Номенклатура_Key", "Nomenclature_Key"]), "qty": self._pick(tp, ["Количество", "Quantity"]),
                       "price": self._pick(tp, ["Цена", "Price"]), "sum": self._pick(tp, ["Сумма", "Amount"]),
                       "vat_sum": self._pick(tp, ["СуммаНДС", "VATAmount"]), "vat_rate": self._pick(tp, ["СтавкаНДС", "VATRate"])}
        for nav, (target, pp) in sections.items():
            if table and nav == table[0]:
                continue
            n = normc(nav)
            if any(w in n for w in ("оплат", "безнал", "платеж")) and not any(w in n for w in ("подароч", "агент")):
                st["pay"] = {"nav": nav, "sum": self._pick(pp, ["Сумма", "Amount"])}
                break
        t = st["t"]
        st["ok"] = bool(st["date"] and table and all(t.get(k) for k in ("nom", "qty", "price", "sum")))
        return st

    def check_structure(self) -> Optional[dict]:
        first = None
        for _, ent, mode in self.check_doc_candidates():
            st = self.build_structure(ent, mode)
            if st["ok"]:
                return st
            first = first or st
        return first

    def enum_members_for(self, etype: str, prop: str) -> list:
        ptype = self.entity_property_types.get(etype, {}).get(prop, "")
        short = ptype.split(".")[-1].split("/")[-1]
        for key in (ptype, short):
            if key in self.enum_members:
                return self.enum_members[key]
        for name, members in self.enum_members.items():
            if short and name.split(".")[-1] == short:
                return members
        return []

    @staticmethod
    def vat_member(members: list, vat: Optional[float], total: float) -> Optional[str]:
        if not members:
            return None
        if not vat:
            return next((x for x in members if "без" in norm(x)), None)
        base = total - vat
        if base <= 0:
            return None
        rate = str(int(round(vat / base * 100)))
        return next((x for x in members if re.search(rf"(?<!\d){rate}(?!\d)", x)), None)

    # ---------- writes ----------
    async def create_document(self, entity: str, payload: dict) -> dict:
        _, text = await self._request("POST", f"{self.base_url}/{entity}", json=payload)
        try:
            return json.loads(text)
        except Exception:
            return {"raw": text}

    async def find_by_comment_token(self, entity: str, comment_prop: str, token: str) -> Optional[str]:
        try:
            rows = await self.get_entities(entity, top=1, params={"$filter": f"substringof('{token}', {comment_prop})"})
            return rows[0].get("Ref_Key") if rows else None
        except Exception:
            return None

    async def summary(self) -> dict:
        await self.load_metadata()
        st = self.check_structure()
        docs = [e for e in self.entity_sets if e.startswith("Document_") and e.count("_") == 1]
        cats = [e for e in self.entity_sets if e.startswith("Catalog_") and e.count("_") == 1]
        return {"entities": len(self.entity_sets), "documents": len(docs), "catalogs": len(cats),
                "check_document": st["entity"] if st else None, "check_mode": st["mode"] if st else None,
                "check_ok": bool(st and st["ok"]),
                "fields": {k: st.get(k) for k in ("date", "comment", "warehouse", "organization", "operation", "amount")} if st else {},
                "table": {"nav": st["table"][0], **st["t"]} if st and st["table"] else {},
                "pay": st["pay"] if st else None}
