"""Google Sheets erişimi. Servis hesabı anahtarı GOOGLE_SERVICE_ACCOUNT_JSON ortam değişkeninden gelir."""
import json
import os
from urllib.parse import quote

from google.auth.transport.requests import AuthorizedSession
from google.oauth2.service_account import Credentials

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
BASE = "https://sheets.googleapis.com/v4/spreadsheets"
_session = None


def _sheet_id():
    return os.environ["SHEET_ID"]


def _request(method, path, **kwargs):
    global _session
    if _session is None:
        info = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"])
        _session = AuthorizedSession(Credentials.from_service_account_info(info, scopes=SCOPES))
    r = _session.request(method, f"{BASE}/{_sheet_id()}{path}", timeout=60, **kwargs)
    if not r.ok:
        raise RuntimeError(f"Sheets API hatası {r.status_code}: {r.text[:300]}")
    return r.json()


def _rng(tab, cells):
    return quote(f"'{tab}'!{cells}", safe="")


def list_tabs():
    """Dosyadaki sekmelerin adı ve boyutu."""
    data = _request("GET", "?fields=sheets.properties(title,gridProperties)")
    return [
        {
            "title": s["properties"]["title"],
            "rows": s["properties"]["gridProperties"]["rowCount"],
            "columns": s["properties"]["gridProperties"]["columnCount"],
        }
        for s in data["sheets"]
    ]


def get_values(tab="TAKVIM", cells="A1:Z400", render="UNFORMATTED_VALUE"):
    """Sekmenin değerlerini satır listesi olarak döndürür. render: UNFORMATTED_VALUE, FORMATTED_VALUE, FORMULA."""
    data = _request(
        "GET",
        f"/values/{_rng(tab, cells)}",
        params={"valueRenderOption": render, "dateTimeRenderOption": "SERIAL_NUMBER"},
    )
    return data.get("values", [])


def batch_get(tab, cells, render="FORMULA"):
    """Tek hücrelik adresler listesi için değerleri aynı sırada döndürür (boşsa '')."""
    if not cells:
        return []
    params = [("ranges", f"'{tab}'!{c}") for c in cells] + [("valueRenderOption", render)]
    data = _request("GET", "/values:batchGet", params=params)
    out = []
    for vr in data["valueRanges"]:
        vals = vr.get("values")
        out.append(vals[0][0] if vals and vals[0] else "")
    return out


def update_cells(tab, updates, input_option="RAW"):
    """updates: [(a1_hücre, değer), ...]. RAW metni olduğu gibi, USER_ENTERED sayı/formül olarak yorumlar."""
    body = {
        "valueInputOption": input_option,
        "data": [{"range": f"'{tab}'!{cell}", "values": [[value]]} for cell, value in updates],
    }
    _request("POST", "/values:batchUpdate", json=body)


def ensure_tab(tab):
    if any(t["title"] == tab for t in list_tabs()):
        return
    _request("POST", ":batchUpdate", json={"requests": [{"addSheet": {"properties": {"title": tab}}}]})


def append_rows(tab, rows):
    _request(
        "POST",
        f"/values/{_rng(tab, 'A:C')}:append",
        params={"valueInputOption": "RAW", "insertDataOption": "INSERT_ROWS"},
        json={"values": rows},
    )
