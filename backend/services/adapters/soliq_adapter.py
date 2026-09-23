"""Soliq adapter — parses Soliq 'Чеклар рўйхати' Excel export into receipts (ported from V129)."""
import re
import io
import collections
from datetime import datetime
from typing import Optional
import openpyxl

COLS = {
    "date": {"чексанаси", "датачека", "чекдата", "sana", "cheksanasi"},
    "number": {"чекрақами", "номерчека", "чекномери", "chekraqami"},
    "product": {"маҳсулотноми", "махсулотноми", "наименованиетовара", "номенклатура", "mahsulotnomi"},
    "qty": {"миқдори", "количество", "miqdori"},
    "total": {"нархи", "суммапозиции", "сумма", "narxi", "summa"},
    "cash": {"жаминақдпул", "итогонал", "naqd"},
    "card": {"жамибанккарта", "итогокарта", "karta"},
    "vat": {"ққссуммаси", "суммандс", "qqssummasi"},
    "fm": {"фмрақами", "фмномер", "fmraqami"},
    "stir": {"стиржишшр", "стир", "stir", "инн"},
    "type": {"чектури", "типчека", "chekturi"},
    "mxik": {"мхик", "икпу", "mxik", "ikpu", "мхиккод", "mxikkodi"},
    "unit": {"ўлчовбирлиги", "единицаизмерения", "olchovbirligi"},
}


def _norm(s) -> str:
    return re.sub(r"[^0-9a-zа-яёўқғҳ']+", "", str(s or "").lower())


def _num(v) -> Optional[float]:
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = re.sub(r"[\s\u00a0\u202f]", "", str(v)).replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def _dt(v) -> Optional[datetime]:
    if isinstance(v, datetime):
        return v.replace(tzinfo=None)
    s = str(v or "").strip()
    for fmt in ("%d.%m.%Y %H:%M:%S", "%d.%m.%Y %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%d.%m.%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def is_soliq_excel(data: bytes) -> bool:
    try:
        return parse_soliq_excel(data)["meta"]["header_found"]
    except Exception:
        return False


def parse_soliq_excel(data: bytes) -> dict:
    """-> {docs: [...], skipped, warnings, meta}. Raises ValueError if header not found."""
    ws = openpyxl.load_workbook(io.BytesIO(data), data_only=True, read_only=True).worksheets[0]
    rows = list(ws.iter_rows(values_only=True))
    hdr_idx, cm = None, {}
    for i, r in enumerate(rows[:20]):
        cur = {}
        for j, cell in enumerate(r):
            n = _norm(cell)
            for key, names in COLS.items():
                if n in names and key not in cur:
                    cur[key] = j
        if {"date", "number", "product", "qty", "total"} <= set(cur):
            hdr_idx, cm = i, cur
            break
    if hdr_idx is None:
        raise ValueError("Excel'da chek sarlavhasi topilmadi (kerak: Чек санаси, Чек рақами, Маҳсулот номи, Миқдори, Нархи). "
                         "Soliq'dan 'Чеклар рўйхати' ni .xlsx qilib yuklab oling.")
    get = lambda r, k: (r[cm[k]] if k in cm and cm[k] < len(r) else None)  # noqa: E731
    docs, skipped, warnings = {}, [], []
    stirs = collections.Counter()
    for xi, r in enumerate(rows[hdr_idx + 1:], start=hdr_idx + 2):
        if not r or not any(c not in (None, "") for c in r):
            continue
        name, dt = str(get(r, "product") or "").strip(), _dt(get(r, "date"))
        number = str(get(r, "number") or "").strip()
        if re.fullmatch(r"\d+\.0", number):
            number = number[:-2]
        qty, total = _num(get(r, "qty")), _num(get(r, "total"))
        if not name or not number or dt is None or not qty or qty <= 0 or not total or total <= 0:
            skipped.append(f"{xi}-qator: to'liq emas")
            continue
        ctype = str(get(r, "type") or "").lower()
        if any(w in ctype for w in ("қайт", "возвр", "return", "qayt")):
            skipped.append(f"{xi}-qator: qaytarish cheki (№{number})")
            continue
        fm = str(get(r, "fm") or "").strip()
        stir = re.sub(r"\D", "", str(get(r, "stir") or ""))
        if stir:
            stirs[stir] += 1
        cash, card = _num(get(r, "cash")) or 0.0, _num(get(r, "card")) or 0.0
        vat = _num(get(r, "vat"))
        mxik = re.sub(r"\D", "", str(get(r, "mxik") or ""))
        if abs(cash + card - total) > 1.0 and (cash or card):
            warnings.append(f"chek №{number}: naqd+karta ≠ jami")
        d = docs.setdefault((fm, number), {"fm": fm, "number": number, "dt": dt, "lines": [], "cash": 0.0, "card": 0.0, "total": 0.0, "stir": stir})
        d["dt"] = min(d["dt"], dt)
        d["lines"].append({"name": name, "qty": qty, "amount": total, "price": round(total / qty, 2), "mxik": mxik or None,
                           "unit": str(get(r, "unit") or "") or None, "vat": vat if vat is not None and 0 <= vat < total else None})
        d["cash"] += cash; d["card"] += card; d["total"] += total
    out = sorted(docs.values(), key=lambda d: (d["dt"], d["number"]))
    for d in out:
        d["token"] = f"soliq:{d['fm']}:{d['number']}"
    return {"docs": out, "skipped": skipped, "warnings": warnings,
            "meta": {"header_found": True, "stirs": dict(stirs), "rows": sum(len(d["lines"]) for d in out), "columns": sorted(cm)}}


class SoliqAdapter:
    """Receipt source = Soliq Excel export (my.soliq.uz -> Чеклар рўйхати). No unofficial API is used."""

    def __init__(self, company_id: str):
        self.company_id = company_id

    def parse(self, data: bytes) -> dict:
        return parse_soliq_excel(data)
