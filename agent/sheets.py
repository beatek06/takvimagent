"""Google Sheets okuma. Servis hesabı anahtarı GOOGLE_SERVICE_ACCOUNT_JSON ortam değişkeninden gelir."""
import json
import os
from urllib.parse import quote

from google.auth.transport.requests import AuthorizedSession
from google.oauth2.service_account import Credentials

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
BASE = "https://sheets.googleapis.com/v4/spreadsheets"


def _session():
    info = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"])
    return AuthorizedSession(Credentials.from_service_account_info(info, scopes=SCOPES))


def get_values(tab="TAKVIM", cells="A1:Z400", sheet_id=None):
    """Sekmenin değerlerini satır listesi olarak döndürür (tarihler seri sayı, sayılar sayı)."""
    sheet_id = sheet_id or os.environ["SHEET_ID"]
    rng = quote(f"'{tab}'!{cells}", safe="")
    r = _session().get(
        f"{BASE}/{sheet_id}/values/{rng}",
        params={"valueRenderOption": "UNFORMATTED_VALUE", "dateTimeRenderOption": "SERIAL_NUMBER"},
    )
    if not r.ok:
        raise RuntimeError(f"Sheets API hatası {r.status_code}: {r.text[:300]}")
    return r.json().get("values", [])
