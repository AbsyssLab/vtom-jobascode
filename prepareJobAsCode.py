import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import requests


def print_format(level: str, content: str) -> None:
    timestamp = time.strftime("%H:%M:%S", time.localtime())
    print(f"{timestamp} | {level.ljust(7)} | {content}")


def check_vtom_server(name: str, endpoint: str, api_key: str, verify_ssl: bool) -> tuple[bool, str]:
    url = f"https://{endpoint}/vtom/public/domain/5.0/calendars"
    headers = {
        "accept": "application/json",
        "Content-Type": "application/json",
        "X-API-KEY": api_key,
    }
    try:
        response = requests.get(url, headers=headers, verify=verify_ssl, timeout=10)
    except requests.exceptions.RequestException as err:
        return False, f"{name}: unreachable ({err})"

    if response.status_code in (200, 201):
        return True, f"{name}: reachable and API key accepted"
    if response.status_code in (401, 403):
        return False, f"{name}: reachable but API key unauthorized ({response.status_code})"
    return False, f"{name}: reachable but unexpected API status {response.status_code}"


def detect_domain_api_version(endpoint: str, api_key: str, verify_ssl: bool) -> tuple[bool, str]:
    headers = {
        "accept": "application/json",
        "Content-Type": "application/json",
        "X-API-KEY": api_key,
    }
    for version in ("5.0", "4.0", "3.0", "2.0", "1.0"):
        url = f"https://{endpoint}/vtom/public/domain/{version}/calendars"
        try:
            response = requests.get(url, headers=headers, verify=verify_ssl, timeout=10)
        except requests.exceptions.RequestException:
            continue
        if response.status_code in (200, 201):
            return True, version
    return False, "unknown"


def check_swagger(endpoint: str, verify_ssl: bool) -> tuple[bool, str]:
    candidates = [
        f"https://{endpoint}/v3/api-docs",
        f"https://{endpoint}/swagger-ui/index.html",
        f"https://{endpoint}/swagger-ui",
    ]
    for url in candidates:
        try:
            response = requests.get(url, verify=verify_ssl, timeout=10)
        except requests.exceptions.RequestException:
            continue
        if response.status_code == 200:
            return True, f"swagger reachable ({url})"
    return False, "swagger not reachable on /v3/api-docs or /swagger-ui"


def check_local_git_repo(name: str, repo_path: str) -> tuple[bool, str]:
    path = Path(repo_path).resolve()
    if not path.exists():
        return False, f"{name}: path does not exist ({path})"
    if not path.is_dir():
        return False, f"{name}: path is not a directory ({path})"
    git_dir = path / ".git"
    if not git_dir.exists():
        return False, f"{name}: not a git repository ({path})"
    return True, f"{name}: git repository found ({path})"


def get_origin_url(repo_path: str) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as err:
        return False, f"cannot read origin remote ({err.stderr.strip() or err})"
    return True, result.stdout.strip()


def check_central_origin(source_repo: str, target_repo: str) -> tuple[bool, str]:
    ok_src, src_info = get_origin_url(source_repo)
    ok_tgt, tgt_info = get_origin_url(target_repo)

    if not ok_src:
        return False, f"source repo origin: {src_info}"
    if not ok_tgt:
        return False, f"target repo origin: {tgt_info}"

    if src_info != tgt_info:
        return False, (
            "origin mismatch between repositories "
            f"(source={src_info}, target={tgt_info})"
        )
    return True, f"shared central origin detected ({src_info})"


def to_bool(value: str) -> bool:
    return value.strip().lower() in ("1", "true", "yes", "on")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate JobAsCode software prerequisites before import/export."
    )
    parser.add_argument("--source-vtom", required=True, help="Source VTOM host:port")
    parser.add_argument("--source-token", required=True, help="API token for source VTOM")
    parser.add_argument("--target-vtom", required=True, help="Target VTOM host:port")
    parser.add_argument("--target-token", required=True, help="API token for target VTOM")
    parser.add_argument("--source-repo", required=True, help="Local source git repository path")
    parser.add_argument("--target-repo", required=True, help="Local target git repository path")
    parser.add_argument(
        "--verify-ssl",
        default="false",
        help="Enable HTTPS certificate verification (true/false), default false",
    )
    parser.add_argument(
        "--output-json",
        action="store_true",
        help="Print a JSON summary at the end (CI-friendly)",
    )
    parser.add_argument(
        "--json-only",
        action="store_true",
        help="Print only JSON output (implies --output-json)",
    )
    args = parser.parse_args()

    requests.packages.urllib3.disable_warnings()
    verify_ssl = to_bool(args.verify_ssl)
    if args.json_only:
        args.output_json = True

    def log(level: str, content: str) -> None:
        if not args.json_only:
            print_format(level, content)

    checks = [
        ("VTOM source server", lambda: check_vtom_server("source VTOM", args.source_vtom, args.source_token, verify_ssl)),
        ("VTOM target server", lambda: check_vtom_server("target VTOM", args.target_vtom, args.target_token, verify_ssl)),
        ("Local source git repository", lambda: check_local_git_repo("source repo", args.source_repo)),
        ("Local target git repository", lambda: check_local_git_repo("target repo", args.target_repo)),
        ("Central origin remote", lambda: check_central_origin(args.source_repo, args.target_repo)),
    ]

    failed = 0
    results = []
    log("INFO", "Starting prerequisite validation")
    for label, check in checks:
        ok, message = check()
        results.append({"name": label, "ok": ok, "message": message})
        if ok:
            log("SUCCESS", f"{label}: {message}")
        else:
            failed += 1
            log("ERROR", f"{label}: {message}")

    src_v_ok, src_version = detect_domain_api_version(args.source_vtom, args.source_token, verify_ssl)
    tgt_v_ok, tgt_version = detect_domain_api_version(args.target_vtom, args.target_token, verify_ssl)
    if src_v_ok:
        results.append({"name": "Source VTOM domain API version", "ok": True, "message": src_version})
        log("SUCCESS", f"Source VTOM domain API version: {src_version}")
    else:
        results.append({"name": "Source VTOM domain API version", "ok": False, "message": src_version})
        failed += 1
        log("ERROR", "Source VTOM domain API version: unable to detect")

    if tgt_v_ok:
        results.append({"name": "Target VTOM domain API version", "ok": True, "message": tgt_version})
        log("SUCCESS", f"Target VTOM domain API version: {tgt_version}")
    else:
        results.append({"name": "Target VTOM domain API version", "ok": False, "message": tgt_version})
        failed += 1
        log("ERROR", "Target VTOM domain API version: unable to detect")

    if src_v_ok and tgt_v_ok and src_version == tgt_version:
        results.append({"name": "VTOM version compatibility", "ok": True, "message": f"both use domain/{src_version}"})
        log("SUCCESS", f"VTOM version compatibility: both use domain/{src_version}")
    else:
        results.append(
            {
                "name": "VTOM version compatibility",
                "ok": False,
                "message": f"source={src_version}, target={tgt_version}",
            }
        )
        failed += 1
        log("ERROR", f"VTOM version compatibility failed: source={src_version}, target={tgt_version}")

    src_sw_ok, src_sw_msg = check_swagger(args.source_vtom, verify_ssl)
    tgt_sw_ok, tgt_sw_msg = check_swagger(args.target_vtom, verify_ssl)
    results.append({"name": "Source VTOM Swagger", "ok": src_sw_ok, "message": src_sw_msg})
    results.append({"name": "Target VTOM Swagger", "ok": tgt_sw_ok, "message": tgt_sw_msg})
    if src_sw_ok:
        log("SUCCESS", f"Source VTOM Swagger: {src_sw_msg}")
    else:
        failed += 1
        log("ERROR", f"Source VTOM Swagger: {src_sw_msg}")
    if tgt_sw_ok:
        log("SUCCESS", f"Target VTOM Swagger: {tgt_sw_msg}")
    else:
        failed += 1
        log("ERROR", f"Target VTOM Swagger: {tgt_sw_msg}")

    summary = {
        "ok": failed == 0,
        "failed_checks": failed,
        "checks": results,
    }

    if args.output_json:
        print(json.dumps(summary, ensure_ascii=True))

    if failed:
        log("ERROR", f"Validation failed ({failed} check(s) in error)")
        return 1
    log("SUCCESS", "All prerequisite checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
