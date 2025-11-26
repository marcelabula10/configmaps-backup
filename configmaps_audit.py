#!/usr/bin/env python3
import os
import json
import subprocess
import datetime
import argparse
import pandas as pd
from pathlib import Path
from deepdiff import DeepDiff
from prettytable import PrettyTable

# ----------------------------
# Execute safe shell commands
# ----------------------------
def run_cmd(cmd: list):
    """Executes IBM Cloud CLI and returns output as JSON."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        output = result.stdout.strip()
        return json.loads(output) if output else {}
    except Exception as e:
        print(f"[ERROR] while running: {' '.join(cmd)}")
        print(e)
        return {}

# ----------------------------
# Create clean folders
# ----------------------------
def ensure_backup_dir(country_code):
    backup_dir = Path.home() / "Desktop" / "backups" / country_code
    backup_dir.mkdir(parents=True, exist_ok=True)
    return backup_dir

def timestamp():
    return datetime.datetime.now().strftime("%Y%m%d_%H%M")

def sanitize(name: str):
    return name.replace("-", "_")

# ----------------------------
# Backup ConfigMaps
# ----------------------------
def backup_configmaps(project, country_code, tag):
    print(f"\n📦 BACKUP STARTED for {project} → [{tag}]")

    backup_dir = ensure_backup_dir(country_code)
    fname = f"{country_code}_{sanitize(project)}_{tag}_{timestamp()}.json"
    file_path = backup_dir / fname

    # Select project
    subprocess.run(["ibmcloud", "ce", "project", "select", "-n", project], check=True)

    # List configmaps
    configmaps = run_cmd(["ibmcloud", "ce", "configmap", "list", "-o", "json"])
    snapshots = {}

    for cm in configmaps:
        name = cm["name"]
        print(f"  ⬇️ Downloading {name}")
        data = run_cmd(["ibmcloud", "ce", "configmap", "get", "--name", name, "-o", "json"])
        snapshots[name] = data

    with open(file_path, "w") as f:
        json.dump(snapshots, f, indent=2)

    print(f"✅ Backup saved: {file_path}")
    return file_path, backup_dir

# ----------------------------
# Compare before vs after
# ----------------------------
def compare_backups(country, project, before_file, after_file, backup_dir):
    print("\n🔍 COMPARING CONFIGMAPS...")

    with open(before_file) as f1, open(after_file) as f2:
        before = json.load(f1)
        after = json.load(f2)

    report = {}
    table = PrettyTable(["ConfigMap", "Status", "Changes"])

    for name in before.keys() | after.keys():
        old = before.get(name, {}).get("data", {})
        new = after.get(name, {}).get("data", {})
        diff = DeepDiff(old, new, ignore_order=True)

        if diff:
            report[name] = diff.to_dict()
            table.add_row([name, "⚠️ Modified", len(diff)])
        else:
            table.add_row([name, "OK", "-"])

    safe_name = sanitize(project)
    diff_file = backup_dir / f"{country}_{safe_name}_diff_{timestamp()}.json"
    summary_file = backup_dir / f"{country}_{safe_name}_summary_{timestamp()}.csv"

    with open(diff_file, "w") as f:
        json.dump(report, f, indent=2)

    pd.DataFrame(table._rows, columns=table.field_names).to_csv(summary_file, index=False)

    print("\n📊 RESULTS")
    print(table)
    print("\n📌 Saved:")
    print(diff_file)
    print(summary_file)

    if report:
        print(f"\n⚠️ {len(report)} ConfigMaps changed!")
    else:
        print("\n✨ No differences found!")

# ----------------------------
# Main CLI Entry
# ----------------------------
def main():
    parser = argparse.ArgumentParser(description="Audit Code Engine ConfigMaps")
    parser.add_argument("--country", required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument("--mode", required=True, choices=["before", "after"])
    args = parser.parse_args()

    backup_file, backup_dir = backup_configmaps(args.project, args.country, args.mode)

    if args.mode == "after":
        before_files = sorted(backup_dir.glob(f"{args.country}*before*.json"))
        if not before_files:
            print("⚠️ No previous backup found!")
            return
        compare_backups(args.country, args.project, before_files[-1], backup_file, backup_dir)

if __name__ == "__main__":
    main()
