import json
import os
import time

import requests

try:
    from config import API_KEY, FQDN_HOSTNAME, VERIFY_SSL
except Exception:
    API_KEY = ""
    FQDN_HOSTNAME = ""
    VERIFY_SSL = False

try:
    from config import CRUD_URI, GRAPH_URI, SECURITY_URI
except Exception:
    CRUD_URI = "/domain/5.0"
    GRAPH_URI = "/graph/1.0"
    SECURITY_URI = "/security/1.0"

DEFAULT_IMPORT_ORDER_PREFIXES = [
    "calendars",
    "dates",
    "tokens",
    "agents",
    "submitUnits",
    "queues",
    "users",
    "resources",
    "contexts",
    "environments",
    "profiles",
    "links",
    "alarms",
    "properties",
    "applicationServers",
]

try:
    from config import IMPORT_ORDER_PREFIXES
except Exception:
    IMPORT_ORDER_PREFIXES = DEFAULT_IMPORT_ORDER_PREFIXES

API_PATHS = {
    "crud": CRUD_URI,
    "graph": GRAPH_URI,
    "security": SECURITY_URI,
}

EXPORT_ROOT_OBJECTS = [
    "calendars",
    "users",
    "resources",
    "dates",
    "queues",
    "tokens",
    "agents",
    "submitUnits",
    "holidaysGroups",
    "holidays",
    "applicationServers/filesTransfers",
    "applicationServers/email",
    "applicationServers/amazonWebServices",
    "applicationServers/azure",
    "applicationServers/databases",
    "applicationServers/docker",
    "applicationServers/kubernetes",
    "applicationServers/m3",
    "applicationServers/dynamicsAx",
    "applicationServers/peopleSoft",
    "applicationServers/sapBo",
    "applicationServers/sapBw",
    "applicationServers/sapDs",
    "applicationServers/sapR3",
    "contexts",
    "environments",
    "alarms",
]

def print_format(level: str, content: str) -> None:
    timestamp = time.strftime("%H:%M:%S", time.localtime())
    print(f"{timestamp} | {level.ljust(7)} | {content}")


def to_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


def build_headers(api_key: str, accept: str = "application/json") -> dict:
    return {
        "accept": accept,
        "Content-Type": "application/json",
        "X-API-KEY": api_key,
    }


def get_import_settings() -> dict:
    server_name = os.getenv("VTOM_SERVER_NAME", FQDN_HOSTNAME).strip()
    api_key = os.getenv("VTOM_TOKEN", API_KEY).strip()
    api_version = os.getenv("VTOM_DOMAIN_API_VERSION", "5.0").strip()
    verify_ssl = to_bool(os.getenv("VTOM_VERIFY_SSL"), VERIFY_SSL)

    if not server_name:
        raise ValueError("Missing VTOM server name. Set VTOM_SERVER_NAME or config.FQDN_HOSTNAME.")
    if not api_key:
        raise ValueError("Missing API key. Set VTOM_TOKEN or config.API_KEY.")

    return {
        "base_url": f"https://{server_name}/vtom/public/domain/{api_version}",
        "headers": build_headers(api_key, accept="*/*"),
        "verify_ssl": verify_ssl,
    }


def parse_message(response: requests.Response) -> str:
    try:
        payload = response.json()
        if isinstance(payload, dict) and "message" in payload:
            return str(payload["message"])
        return json.dumps(payload)
    except Exception:
        return response.text.strip() or "No response payload"


def request_vtom(
    method: str,
    url: str,
    headers: dict,
    verify_ssl: bool,
    body: dict | list | None = None,
    timeout: int = 30,
) -> requests.Response:
    return requests.request(
        method=method,
        url=url,
        headers=headers,
        json=body,
        verify=verify_ssl,
        timeout=timeout,
    )
