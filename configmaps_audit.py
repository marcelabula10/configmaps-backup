import argparse, yaml, subprocess, os, json
from datetime import datetime
from deepdiff import DeepDiff

from excel_report import generate_excel
from pdf_report import export_pdf

# Base folder where backups are stored
BASE = os.path.expanduser("~/Desktop/backups")


def run(cmd):
    """Executes a shell command and returns stdout as text."""
    return subprocess.check_output(cmd, shell=True, text=True)


def load_profiles():
    """Loads profiles.yaml into a python dictionary."""
    with open("profiles.yaml") as f:
        return yaml.safe_load(f)


def set_ibmcloud_context(account, region, rg, project):
    """
    Automatically selects:
    - IBM Cloud account
    - Region
    - Resource Group
    - Code Engine project
    """
    run(f"ibmcloud target -c {account}")
    run(f"ibmcloud target -r {region}")
    run(f"ibmcloud target -g {rg}")
    run(f"ibmcloud ce project select -n {project}")


def backup(profile, apcode, mode):
    """
    Creates a backup of all ConfigMaps in the selected project.
    mode can be 'before' or 'after'.
    """

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = f"{BASE}/{profile}/{apcode}/{mode}/{timestamp}"
    os.makedirs(path, exist_ok=True)

    cms_raw = run("ibmcloud ce configmap list")
    cms = [line.split()[0] for line in cms_raw.splitlines()
           if "active" in line.lower()]

    for cm in cms:
        data = run(f"ibmcloud ce configmap get --name {cm} --output json")
        with open(f"{path}/{cm}.json", "w") as f:
            f.write(data)


def generate_report(profile, apcode):
    """
    Generates an Excel and PDF diff report comparing the most recent
    BEFORE and AFTER backups.
    """

    base_path = f"{BASE}/{profile}/{apcode}"

    # Find the latest before + after snapshots
    before = sorted(os.listdir(f"{base_path}/before"))[-1]
    after = sorted(os.listdir(f"{base_path}/after"))[-1]

    before_path = f"{base_path}/before/{before}"
    after_path = f"{base_path}/after/{after}"

    results = []

    for filename in os.listdir(before_path):
        if filename.endswith(".json"):

            before_file = os.path.join(before_path, filename)
            after_file = os.path.join(after_path, filename)

            with open(before_file) as f:
                before_data = json.load(f)

            # ConfigMap removed entirely
            if not os.path.exists(after_file):
                results.append([filename, "-", "-", "-", "Removed", before, after])
                continue

            with open(after_file) as f:
                after_data = json.load(f)

            diff = DeepDiff(before_data, after_data, ignore_order=True)

            # If no differences, skip
            if not diff:
                continue

            if "values_changed" in diff:
                for key, change in diff["values_changed"].items():
                    results.append([
                        filename,
                        key,
                        change["old_value"],
                        change["new_value"],
                        "Modified",
                        before,
                        after
                    ])

            if "dictionary_item_added" in diff:
                for key in diff["dictionary_item_added"]:
                    results.append([filename, key, "-", "-", "Added", before, after])

            if "dictionary_item_removed" in diff:
                for key in diff["dictionary_item_removed"]:
                    results.append([filename, key, "-", "-", "Removed", before, after])

    # Output paths
    excel_path = f"{base_path}/report.xlsx"
    pdf_path = f"{base_path}/report.pdf"

    # Generate both reports
    generate_excel(results, excel_path)
    export_pdf(results, pdf_path)


if __name__ == "__main__":

    # CLI argument parsing
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True)
    parser.add_argument("--ap", required=True)
    parser.add_argument("--mode",
        required=True, choices=["before","after","report"])

    args = parser.parse_args()
    profiles = load_profiles()

    p = profiles[args.profile]["projects"][args.ap]

    # Auto-select IBM Cloud context
    set_ibmcloud_context(
        profiles[args.profile]["account"],
        profiles[args.profile]["region"],
        p["resource_group"],
        p["project"]
    )

    # Backup or report
    if args.mode == "report":
        generate_report(args.profile, args.ap)
    else:
        backup(args.profile, args.ap, args.mode)
