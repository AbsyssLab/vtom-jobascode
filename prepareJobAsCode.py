import argparse
import getpass
import json
import subprocess
import sys
import time
from pathlib import Path

import requests

try:
    from config import API_KEY as CONFIG_API_KEY
    from config import FQDN_HOSTNAME as CONFIG_FQDN_HOSTNAME
    from config import GIT_ORIGIN as CONFIG_GIT_ORIGIN
    from config import GIT_LOCAL as CONFIG_GIT_LOCAL
    from config import VERIFY_SSL as CONFIG_VERIFY_SSL
except Exception:
    CONFIG_FQDN_HOSTNAME = ""
    CONFIG_API_KEY = ""
    CONFIG_GIT_ORIGIN = ""
    CONFIG_GIT_LOCAL = ""
    CONFIG_VERIFY_SSL = False


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


def run_git(args: list[str], cwd: str) -> subprocess.CompletedProcess:
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, check=True)


def get_origin_url(repo_path: str) -> tuple[bool, str]:
    try:
        result = run_git(["git", "remote", "get-url", "origin"], repo_path)
    except subprocess.CalledProcessError as err:
        return False, f"cannot read origin remote ({err.stderr.strip() or err})"
    return True, result.stdout.strip()


def ensure_local_repo(local_repo: str, central_origin: str, dry_run: bool = False) -> tuple[bool, str]:
    path = Path(local_repo).resolve()
    if not path.exists():
        if dry_run and central_origin:
            return True, f"DRY-RUN: would clone {central_origin} into {path}"
        if dry_run and not central_origin:
            return True, f"DRY-RUN: would create local git repository in {path} (no origin configured)"
        path.parent.mkdir(parents=True, exist_ok=True)
        if not central_origin:
            path.mkdir(parents=True, exist_ok=True)
            run_git(["git", "init"], str(path))
            return True, f"local repo initialized ({path}) without origin"
        try:
            subprocess.run(
                ["git", "clone", central_origin, str(path)],
                capture_output=True,
                text=True,
                check=True,
            )
            return True, f"local repo created by clone ({path})"
        except subprocess.CalledProcessError as err:
            # If central repository does not exist yet, bootstrap local repository anyway.
            if not path.exists():
                path.mkdir(parents=True, exist_ok=True)
            try:
                run_git(["git", "init"], str(path))
                run_git(["git", "remote", "add", "origin", central_origin], str(path))
                clone_err = err.stderr.strip() or str(err)
                return True, (
                    f"clone failed, local repo initialized instead ({path}) with origin={central_origin}. "
                    f"Clone error: {clone_err}"
                )
            except subprocess.CalledProcessError as init_err:
                return False, f"clone failed and bootstrap init failed ({init_err.stderr.strip() or init_err})"

    if not path.is_dir():
        return False, f"path is not a directory ({path})"

    git_dir = path / ".git"
    if not git_dir.exists():
        if dry_run:
            return True, f"DRY-RUN: would initialize git repository in {path}"
        try:
            run_git(["git", "init"], str(path))
        except subprocess.CalledProcessError as err:
            return False, f"git init failed ({err.stderr.strip() or err})"

    ok_origin, current_origin = get_origin_url(str(path))
    if central_origin:
        if ok_origin:
            if current_origin != central_origin:
                if dry_run:
                    return True, f"DRY-RUN: would set origin to {central_origin} (currently {current_origin})"
                try:
                    run_git(["git", "remote", "set-url", "origin", central_origin], str(path))
                except subprocess.CalledProcessError as err:
                    return False, f"cannot set origin ({err.stderr.strip() or err})"
        else:
            if dry_run:
                return True, f"DRY-RUN: would add origin={central_origin} in {path}"
            try:
                run_git(["git", "remote", "add", "origin", central_origin], str(path))
            except subprocess.CalledProcessError as err:
                return False, f"cannot add origin ({err.stderr.strip() or err})"
        return True, f"local repo ready ({path}) with origin={central_origin}"
    return True, f"local repo ready ({path}) without origin (can be configured later)"


def update_config_file(
    config_file: str,
    endpoint: str,
    api_key: str,
    verify_ssl: bool,
    dry_run: bool = False,
) -> tuple[bool, str]:
    path = Path(config_file).resolve()
    if not path.exists():
        template_path = path.parent / "config.py.template"
        if not template_path.exists():
            return False, f"config file not found ({path}) and template missing ({template_path})"
        if dry_run:
            return True, f"DRY-RUN: would create {path} from template {template_path} and update values"
        path.write_text(template_path.read_text(encoding="utf-8"), encoding="utf-8")

    content = path.read_text(encoding="utf-8")
    updates = {
        "FQDN_HOSTNAME": f"\"{endpoint}\"",
        "API_KEY": f"\"{api_key}\"",
        "VERIFY_SSL": "True" if verify_ssl else "False",
    }
    for key, value in updates.items():
        marker = f"{key} = "
        if marker not in content:
            return False, f"key not found in config: {key}"
        lines = content.splitlines()
        for i, line in enumerate(lines):
            if line.startswith(marker):
                lines[i] = f"{key} = {value}"
        content = "\n".join(lines) + "\n"

    if dry_run:
        return True, f"DRY-RUN: would update config ({path})"

    path.write_text(content, encoding="utf-8")
    return True, f"config updated ({path})"


def to_bool(value: str) -> bool:
    return value.strip().lower() in ("1", "true", "yes", "on")


def prompt_with_default(prompt: str, default_value: str) -> str:
    suffix = f" [{default_value}]" if default_value else ""
    value = input(f"{prompt}{suffix}: ").strip()
    return value if value else default_value


def prompt_secret(prompt: str, default_present: bool) -> str:
    suffix = " [from config]" if default_present else ""
    value = getpass.getpass(f"{prompt}{suffix}: ").strip()
    return value


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Prepare one JobAsCode side (source or target): VTOM, local repo, and config."
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
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate actions without modifying local repo or config file",
    )
    args = parser.parse_args()

    requests.packages.urllib3.disable_warnings()
    role = prompt_with_default("Role (source/target)", "source").lower()
    vtom = prompt_with_default("VTOM host:port", (CONFIG_FQDN_HOSTNAME or "").strip())
    entered_token = prompt_secret("VTOM API token", bool((CONFIG_API_KEY or "").strip()))
    token = entered_token if entered_token else (CONFIG_API_KEY or "").strip()
    central_origin = prompt_with_default("Git origin URL", (CONFIG_GIT_ORIGIN or "").strip())
    local_repo = prompt_with_default("Local repository path", (CONFIG_GIT_LOCAL or "").strip())

    verify_default = "true" if bool(CONFIG_VERIFY_SSL) else "false"
    verify_ssl = to_bool(prompt_with_default("Verify SSL (true/false)", verify_default))

    missing = []
    if role not in ("source", "target"):
        missing.append("role(source|target)")
    if not vtom:
        missing.append("vtom/FQDN_HOSTNAME")
    if not token:
        missing.append("token/API_KEY")
    if not local_repo:
        missing.append("local-repo/GIT_LOCAL")
    if missing:
        print_format("ERROR", "Missing required values: " + ", ".join(missing))
        return 2

    if args.json_only:
        args.output_json = True

    def log(level: str, content: str) -> None:
        if not args.json_only:
            print_format(level, content)

    failed = 0
    results = []
    log("INFO", f"Starting preparation for {role} side")
    if args.dry_run:
        log("INFO", "Running in dry-run mode (no local write operations).")

    checks = [
        (
            "VTOM server",
            lambda: check_vtom_server(f"{role} VTOM", vtom, token, verify_ssl),
        ),
        (
            "Local git repository",
            lambda: ensure_local_repo(local_repo, central_origin, args.dry_run),
        ),
    ]

    for label, check in checks:
        ok, message = check()
        results.append({"name": label, "ok": ok, "message": message})
        if ok:
            log("SUCCESS", f"{label}: {message}")
        else:
            failed += 1
            log("ERROR", f"{label}: {message}")

    version_ok, version = detect_domain_api_version(vtom, token, verify_ssl)
    results.append({"name": "VTOM domain API version", "ok": version_ok, "message": version})
    if version_ok:
        log("SUCCESS", f"VTOM domain API version: {version}")
    else:
        failed += 1
        log("ERROR", "VTOM domain API version: unable to detect")

    swagger_ok, swagger_msg = check_swagger(vtom, verify_ssl)
    results.append({"name": "VTOM Swagger", "ok": swagger_ok, "message": swagger_msg})
    if swagger_ok:
        log("SUCCESS", f"VTOM Swagger: {swagger_msg}")
    else:
        failed += 1
        log("ERROR", f"VTOM Swagger: {swagger_msg}")

    config_ok, config_msg = update_config_file(
        "./config.py",
        vtom,
        token,
        verify_ssl,
        args.dry_run,
    )
    results.append({"name": "Config update", "ok": config_ok, "message": config_msg})
    if config_ok:
        log("SUCCESS", f"Config update: {config_msg}")
    else:
        failed += 1
        log("ERROR", f"Config update: {config_msg}")

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
