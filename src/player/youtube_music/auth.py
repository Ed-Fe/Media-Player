import json
import os
import time
from http.cookies import SimpleCookie

from player.session import APP_STORAGE_DIR


YTMUSIC_BROWSER_AUTH_FILE_NAME = "ytmusic_browser.json"


def get_browser_auth_file_path():
    return os.path.join(_get_storage_dir(), YTMUSIC_BROWSER_AUTH_FILE_NAME)


def _get_storage_dir():
    if os.name == "nt":
        base_dir = os.environ.get("APPDATA") or os.path.expanduser("~")
    else:
        base_dir = os.environ.get("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"), ".config")

    storage_dir = os.path.join(base_dir, APP_STORAGE_DIR)
    os.makedirs(storage_dir, exist_ok=True)
    return storage_dir


def read_auth_file_text(file_path):
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            with open(file_path, "r", encoding=encoding) as auth_file:
                return auth_file.read()
        except UnicodeDecodeError:
            continue

    raise RuntimeError("Não foi possível ler o arquivo de autenticação selecionado.")


def prepare_browser_auth_input(raw_input, *, source_name="entrada"):
    normalized_input = str(raw_input or "").strip()
    if not normalized_input:
        return ""

    json_payload = _try_parse_json(normalized_input)
    if json_payload is not None:
        browser_headers = _extract_browser_auth_headers(json_payload)
        if browser_headers:
            return _headers_dict_to_raw(browser_headers)

        cookie_header = _cookie_header_from_json_payload(json_payload)
        if cookie_header:
            return _build_headers_raw_from_cookie(cookie_header)

        raise RuntimeError(
            f"O {source_name} não contém um browser.json válido nem um export JSON de cookies compatível."
        )

    cookie_header = _cookie_header_from_netscape_text(normalized_input)
    if cookie_header:
        return _build_headers_raw_from_cookie(cookie_header)

    return normalized_input


def _try_parse_json(raw_text):
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        return None


def _extract_browser_auth_headers(payload):
    candidate = payload
    if isinstance(payload, dict) and isinstance(payload.get("headers"), dict):
        candidate = payload.get("headers")

    if not isinstance(candidate, dict):
        return None

    normalized_headers = {}
    for key, value in candidate.items():
        if not isinstance(key, str) or isinstance(value, (dict, list)):
            continue

        normalized_value = str(value).strip()
        if not normalized_value:
            continue
        normalized_headers[key] = normalized_value

    lowered_keys = {str(key).lower() for key in normalized_headers.keys()}
    if "cookie" not in lowered_keys:
        return None

    if "x-goog-authuser" not in lowered_keys:
        normalized_headers["X-Goog-AuthUser"] = "0"
    if "x-origin" not in lowered_keys:
        normalized_headers["x-origin"] = "https://music.youtube.com"

    return normalized_headers


def _cookie_header_from_json_payload(payload):
    cookie_entries = []
    _collect_cookie_entries(payload, cookie_entries)
    if not cookie_entries:
        return ""

    cookie_pairs = []
    seen_names = set()
    for cookie in cookie_entries:
        name = str(cookie.get("name") or "").strip()
        value = str(cookie.get("value") or "").strip()
        if not name or name in seen_names:
            continue
        if not _cookie_entry_matches_music_youtube(cookie):
            continue
        if _cookie_entry_is_expired(cookie):
            continue
        seen_names.add(name)
        cookie_pairs.append(f"{name}={value}")

    return "; ".join(cookie_pairs)


def _collect_cookie_entries(node, cookie_entries):
    if isinstance(node, dict):
        if _looks_like_cookie_entry(node):
            cookie_entries.append(node)
            return
        for value in node.values():
            _collect_cookie_entries(value, cookie_entries)
        return

    if isinstance(node, list):
        for item in node:
            _collect_cookie_entries(item, cookie_entries)


def _looks_like_cookie_entry(value):
    return isinstance(value, dict) and "name" in value and "value" in value


def _cookie_entry_matches_music_youtube(cookie):
    domain = str(cookie.get("domain") or cookie.get("host") or "").strip().lstrip(".").lower()
    if not domain:
        return True
    return domain.endswith("youtube.com") or domain.endswith("music.youtube.com")


def _cookie_entry_is_expired(cookie):
    expiration_value = cookie.get("expirationDate")
    if expiration_value in (None, "", 0, "0"):
        return False

    try:
        return float(expiration_value) <= time.time()
    except (TypeError, ValueError):
        return False


def _cookie_header_from_netscape_text(raw_text):
    cookie_pairs = []
    seen_names = set()

    for raw_line in str(raw_text or "").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        parts = raw_line.split("\t")
        if len(parts) < 7:
            continue

        domain, _include_subdomains, _path, _secure, expiry, name, value = parts[:7]
        normalized_domain = str(domain or "").strip().lstrip(".").lower()
        normalized_name = str(name or "").strip()
        normalized_value = str(value or "").strip()
        if not normalized_name or not normalized_value:
            continue
        if normalized_name in seen_names:
            continue
        if normalized_domain and not (
            normalized_domain.endswith("youtube.com") or normalized_domain.endswith("music.youtube.com")
        ):
            continue

        try:
            if expiry and expiry != "0" and float(expiry) <= time.time():
                continue
        except ValueError:
            pass

        seen_names.add(normalized_name)
        cookie_pairs.append(f"{normalized_name}={normalized_value}")

    return "; ".join(cookie_pairs)


def _build_headers_raw_from_cookie(cookie_header):
    normalized_cookie_header = str(cookie_header or "").strip()
    if not normalized_cookie_header:
        return ""

    origin = "https://music.youtube.com"
    authorization = _authorization_from_cookie(normalized_cookie_header, origin)
    if not authorization:
        raise RuntimeError(
            "O export de cookies não contém um cookie de autenticação compatível do YouTube Music. "
            "Faça login em music.youtube.com e exporte novamente os cookies da sessão ativa."
        )

    return "\n".join(
        [
            "Accept: */*",
            f"Authorization: {authorization}",
            "Content-Type: application/json",
            f"Cookie: {normalized_cookie_header}",
            "X-Goog-AuthUser: 0",
            f"x-origin: {origin}",
        ]
    )


def _headers_dict_to_raw(headers):
    header_lines = []
    for key, value in headers.items():
        normalized_key = str(key or "").strip()
        normalized_value = str(value or "").strip()
        if not normalized_key or not normalized_value:
            continue
        header_lines.append(f"{normalized_key}: {normalized_value}")

    return "\n".join(header_lines)


def _authorization_from_cookie(cookie_header, origin):
    cookie = SimpleCookie()
    try:
        cookie.load(str(cookie_header or "").replace('"', ""))
    except Exception:
        return ""

    sapisid = ""
    for cookie_name in ("__Secure-3PAPISID", "SAPISID", "__Secure-1PAPISID"):
        morsel = cookie.get(cookie_name)
        if morsel is not None:
            sapisid = str(morsel.value or "").strip()
            if sapisid:
                break

    if not sapisid:
        return ""

    try:
        from ytmusicapi.helpers import get_authorization
    except ImportError:
        return ""

    return get_authorization(f"{sapisid} {origin}")
