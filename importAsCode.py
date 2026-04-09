import argparse
import json
import subprocess
import sys
from pathlib import Path

import requests

try:
    from config import GIT_LOCAL as CONFIG_GIT_LOCAL
except Exception:
    CONFIG_GIT_LOCAL = "."

from vtom_common import (
    API_PATHS,
    get_import_settings,
    IMPORT_ORDER_PREFIXES,
    parse_message,
    print_format,
    request_vtom,
)


def get_changed_files(from_sha: str, to_sha: str, repo_root: Path) -> list[tuple[str, str]]:
    if from_sha == to_sha:
        # Interpret same SHA as "single commit mode".
        result = subprocess.run(
            ["git", "show", "--name-status", "--format=", to_sha],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            check=True,
        )
    else:
        result = subprocess.run(
            ["git", "diff", "--name-status", from_sha, to_sha],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            check=True,
        )

    changed: list[tuple[str, str]] = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue

        parts = line.split("\t")
        status = parts[0].strip()

        # Rename/copy format: R100\told\tnew or C100\told\tnew
        if (status.startswith("R") or status.startswith("C")) and len(parts) >= 3:
            old_path, new_path = parts[1], parts[2]
            changed.append(("D", old_path))
            changed.append(("A", new_path))
            continue

        if len(parts) < 2:
            continue
        path_part = parts[1]

        if status == "A":
            changed.append(("A", path_part))
        elif status == "D":
            changed.append(("D", path_part))
        elif status in ("M", "T", "U"):
            changed.append(("M", path_part))

    return changed


def build_prefix_rank() -> dict[str, int]:
    return {prefix: idx for idx, prefix in enumerate(IMPORT_ORDER_PREFIXES)}


def get_prefix_rank(rel_path: str, rank_map: dict[str, int]) -> int:
    path_without_ext = rel_path[:-5] if rel_path.endswith(".json") else rel_path
    segments = [segment for segment in path_without_ext.split("/") if segment]
    best = 10**6
    for segment in segments:
        if segment in rank_map:
            best = min(best, rank_map[segment])
    return best


def sort_changes(changes: list[tuple[str, str]], rank_map: dict[str, int]) -> list[tuple[str, str]]:
    adds_mods = [item for item in changes if item[0] in ("A", "M")]
    deletes = [item for item in changes if item[0] == "D"]
    others = [item for item in changes if item[0] not in ("A", "M", "D")]

    adds_mods.sort(key=lambda item: (get_prefix_rank(item[1], rank_map), item[1].count("/"), item[1]))
    deletes.sort(key=lambda item: (get_prefix_rank(item[1], rank_map), item[1].count("/"), item[1]), reverse=True)
    return adds_mods + deletes + others


def load_json_from_commit(repo_root: Path, commit_sha: str, rel_path: str) -> dict | list:
    result = subprocess.run(
        ["git", "show", f"{commit_sha}:{rel_path}"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)


def is_graph_path(file_no_ext: str) -> bool:
    graph_markers = ("/graph", "/properties", "/nodes", "/node")
    return (
        file_no_ext in ("graph", "properties")
        or file_no_ext.endswith(graph_markers)
        or any(marker + "/" in file_no_ext for marker in graph_markers)
    )


def is_security_path(file_no_ext: str) -> bool:
    return file_no_ext.startswith("profiles")


def normalize_graph_file_path(file_no_ext: str) -> str:
    if file_no_ext == "graph":
        return ""
    if file_no_ext.endswith("/graph"):
        return file_no_ext[: -len("/graph")]
    return file_no_ext


def parse_calendar_file_id(file_no_ext: str) -> str:
    # calendars/<name>-<year>  -> calendars/<name>/<year>
    if not file_no_ext.startswith("calendars/"):
        return file_no_ext
    calendar_id = file_no_ext.split("/", 1)[1]
    if "-" not in calendar_id:
        return file_no_ext
    name, year = calendar_id.rsplit("-", 1)
    if year.isdigit():
        return f"calendars/{name}/{year}"
    return file_no_ext


def is_graph_snapshot_file(rel_path: str) -> bool:
    return Path(rel_path).name in {"graph.json", "nodes.json", "links.json"}


def sanitize_graph_node_payload(body: dict | list) -> dict | list:
    # Graph node PUT rejects read-only identity fields from exports.
    if isinstance(body, list) and len(body) == 1 and isinstance(body[0], dict):
        body = body[0]
    if isinstance(body, dict):
        sanitized = dict(body)
        for key in ("id", "objectId", "name", "type"):
            sanitized.pop(key, None)
        return sanitized
    return body


def compute_base_urls(domain_base_url: str) -> dict[str, str]:
    public_root = domain_base_url.rsplit("/domain/", 1)[0]
    return {
        "domain": domain_base_url,
        "graph": f"{public_root}{API_PATHS['graph']}",
        "security": f"{public_root}{API_PATHS['security']}",
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Import repository JSON changes between two commit SHAs to Visual TOM.",
        epilog="Default is dry-run. Use --run to send API requests.",
    )
    parser.add_argument("--from", dest="from_sha", required=True, help="Start commit SHA (excluded)")
    parser.add_argument("--to", dest="to_sha", required=True, help="End commit SHA (included)")
    parser.add_argument(
        "--run",
        action="store_true",
        help="Execute API requests (default is dry-run preview)",
    )
    args = parser.parse_args()

    requests.packages.urllib3.disable_warnings()

    settings = None
    if not args.run:
        try:
            settings = get_import_settings()
        except ValueError:
            settings = {
                "base_url": "<VTOM base URL not configured>",
                "headers": {},
                "verify_ssl": False,
            }
        print_format("INFO", "Running in dry-run mode (no API calls).")
    else:
        try:
            settings = get_import_settings()
        except ValueError as err:
            print_format("ERROR", str(err))
            return 2

    repo_root = Path(CONFIG_GIT_LOCAL).resolve()
    changed = get_changed_files(args.from_sha, args.to_sha, repo_root)
    rank_map = build_prefix_rank()
    changed = sort_changes(changed, rank_map)
    base_urls = compute_base_urls(settings["base_url"])

    errors = []
    applied = 0

    for status, rel_path in changed:
        if not rel_path.endswith(".json"):
            continue
        if is_graph_snapshot_file(rel_path):
            print_format("INFO", f"SKIP {status} {rel_path} (graph snapshot file)")
            continue

        file_no_ext = rel_path[:-5]
        parent_path = str(Path(file_no_ext).parent).replace("\\", "/")
        if parent_path == ".":
            parent_path = ""

        method = ""
        url = ""
        try:
            if is_graph_path(file_no_ext):
                base_url = base_urls["graph"]
                normalized_file_no_ext = normalize_graph_file_path(file_no_ext)
            elif is_security_path(file_no_ext):
                base_url = base_urls["security"]
                normalized_file_no_ext = file_no_ext
            else:
                base_url = base_urls["domain"]
                normalized_file_no_ext = parse_calendar_file_id(file_no_ext)

            if status == "A":
                url = f"{base_url}/{parent_path}".rstrip("/")
                body = load_json_from_commit(repo_root, args.to_sha, rel_path)
                method = "POST"
                if not args.run:
                    print_format("INFO", f"DRY-RUN A {rel_path} -> {method} {url}")
                    applied += 1
                    continue
                response = request_vtom(method, url, settings["headers"], settings["verify_ssl"], body)
            elif status == "M":
                url = f"{base_url}/{normalized_file_no_ext}".rstrip("/")
                body = load_json_from_commit(repo_root, args.to_sha, rel_path)
                if normalized_file_no_ext.endswith("/nodes") or normalized_file_no_ext == "nodes":
                    # Graph nodes collection accepts POST (Allow: HEAD,POST,GET,OPTIONS).
                    method = "POST"
                else:
                    method = "PUT"

                if normalized_file_no_ext.endswith("/node") or normalized_file_no_ext == "node":
                    body = sanitize_graph_node_payload(body)
                if not args.run:
                    print_format("INFO", f"DRY-RUN M {rel_path} -> {method} {url}")
                    applied += 1
                    continue
                response = request_vtom(method, url, settings["headers"], settings["verify_ssl"], body)
            elif status == "D":
                url = f"{base_url}/{normalized_file_no_ext}".rstrip("/")
                method = "DELETE"
                if not args.run:
                    print_format("INFO", f"DRY-RUN D {rel_path} -> {method} {url}")
                    applied += 1
                    continue
                response = request_vtom(method, url, settings["headers"], settings["verify_ssl"])
            else:
                continue
        except subprocess.CalledProcessError as err:
            errors.append(f"{status} {rel_path}: cannot read {args.to_sha}:{rel_path} ({err.stderr.strip() or err})")
            print_format("ERROR", f"{status} {rel_path}: cannot read content from commit {args.to_sha}")
            continue
        except json.JSONDecodeError as err:
            errors.append(f"{status} {rel_path}: invalid JSON ({err})")
            print_format("ERROR", f"{status} {rel_path}: invalid JSON ({err})")
            continue
        except requests.exceptions.RequestException as err:
            errors.append(f"{status} {rel_path}: request failed ({err})")
            print_format("ERROR", f"{status} {rel_path}: request failed ({err})")
            continue

        if response.status_code in (200, 201, 204):
            applied += 1
            print_format("SUCCESS", f"{status} {rel_path} -> {response.status_code}")
        elif status == "D" and response.status_code == 404:
            # Deletion is idempotent: object already absent is acceptable.
            applied += 1
            print_format("INFO", f"{status} {rel_path}: already absent (404)")
        else:
            message = parse_message(response)
            errors.append(f"{status} {rel_path}: {response.status_code} {message}")
            print_format("ERROR", f"{status} {rel_path}: {response.status_code} {message}")

    print_format("INFO", f"Applied changes: {applied}")
    if errors:
        print_format("ERROR", "Some operations failed")
        for err in errors:
            print(err)
        return 1

    print_format("SUCCESS", "All operations completed successfully")
    return 0


if __name__ == "__main__":
    sys.exit(main())
