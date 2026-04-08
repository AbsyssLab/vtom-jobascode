import argparse
import json
import subprocess
import sys
from pathlib import Path

import requests

from vtom_common import (
    get_import_settings,
    IMPORT_ORDER_PREFIXES,
    parse_message,
    print_format,
    request_vtom,
)


def get_changed_files(before_sha: str, after_sha: str) -> list[tuple[str, str]]:
    cmd = ["git", "diff", "--name-status", before_sha, after_sha]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)

    changed = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue

        parts = line.split("\t")
        status = parts[0].strip()

        # Handles A/M/D and rename/copy forms (R100/C100 old new).
        if status.startswith("R") or status.startswith("C"):
            if len(parts) >= 3:
                changed.append(("D", parts[1]))
                changed.append(("A", parts[2]))
            continue

        if len(parts) >= 2:
            changed.append((status, parts[1]))

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


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply Git changes to Visual TOM via API.")
    parser.add_argument("--before", required=True, help="Previous commit SHA")
    parser.add_argument("--after", required=True, help="Current commit SHA")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate operations without calling the API",
    )
    parser.add_argument(
        "--repo-root",
        default=".",
        help="Repository root where changed files are read from (default: current directory)",
    )
    args = parser.parse_args()

    requests.packages.urllib3.disable_warnings()

    settings = None
    if args.dry_run:
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

    repo_root = Path(args.repo_root).resolve()
    changed = get_changed_files(args.before, args.after)
    rank_map = build_prefix_rank()
    changed = sort_changes(changed, rank_map)

    errors = []
    applied = 0

    for status, rel_path in changed:
        if not rel_path.endswith(".json"):
            continue

        file_path = (repo_root / rel_path).resolve()
        file_no_ext = rel_path[:-5]
        parent_path = str(Path(file_no_ext).parent).replace("\\", "/")
        if parent_path == ".":
            parent_path = ""

        method = ""
        url = ""
        try:
            if status == "A":
                url = f"{settings['base_url']}/{parent_path}".rstrip("/")
                with open(file_path, "r", encoding="utf-8") as f:
                    body = json.load(f)
                method = "POST"
                if args.dry_run:
                    print_format("INFO", f"DRY-RUN A {rel_path} -> {method} {url}")
                    applied += 1
                    continue
                response = request_vtom(method, url, settings["headers"], settings["verify_ssl"], body)
            elif status == "M":
                url = f"{settings['base_url']}/{file_no_ext}"
                with open(file_path, "r", encoding="utf-8") as f:
                    body = json.load(f)
                method = "PUT"
                if args.dry_run:
                    print_format("INFO", f"DRY-RUN M {rel_path} -> {method} {url}")
                    applied += 1
                    continue
                response = request_vtom(method, url, settings["headers"], settings["verify_ssl"], body)
            elif status == "D":
                url = f"{settings['base_url']}/{file_no_ext}"
                method = "DELETE"
                if args.dry_run:
                    print_format("INFO", f"DRY-RUN D {rel_path} -> {method} {url}")
                    applied += 1
                    continue
                response = request_vtom(method, url, settings["headers"], settings["verify_ssl"])
            else:
                continue
        except FileNotFoundError:
            errors.append(f"{status} {rel_path}: file not found")
            print_format("ERROR", f"{status} {rel_path}: file not found")
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
