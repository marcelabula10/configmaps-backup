#!/usr/bin/env python3
import os, subprocess, argparse, json
from datetime import datetime
from excel_report import generate_excel
from pdf_report import export_pdf
import yaml

BASE = os.path.expanduser("~/Desktop/backups")

def run(cmd):
    """Run a shell command and return stdout text"""
    return subprocess.check_output(cmd, shell=True, text=True)

def load_profiles():
    with open("profiles.yaml") as f:
        return yaml.safe_load(f)

def set_ibmcloud_context(account, region, rg, project):
    """Automatically select IBM Cloud target for CE"""
    run(f"ibmcloud target -c {account}")
    run(f"ibmcloud target -r {region}")
    run(f"ibmcloud target -g {rg}")
    run(f"ibmcloud ce project select -n {project}")

############################################
# NEW CORRECT BACKUP FUNCTION
############################################
def backup(profile, apcode, mode):
    """
    Creates a backup of all ConfigMaps in the selected project.
    mode = 'before' or 'after'
    """
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = f"{BASE}/{profile}/{apcode}/{mode}/{timestamp}"
    os.makedirs(path, exist_ok=True)

    # Fetch configmaps in proper JSON format
    cms_json = json.loads(run("ibmcloud ce configmap list --output json"))

    # Extract only the names
    cms = [cm["name"] for cm in cms_json]

    for cm in cms:
        data = run(f"ibmcloud ce configmap get --name {cm} --output json")
        with open(f"{path}/{cm}.json", "w") as f:
            f.write(data)

############################################
# REPORT MODE
############################################
def generate_report(profile, apcode):
    """
    Generates Excel and PDF report from newest BEFORE + AFTER
    """
    base_path = f"{BASE}/{profile}/{apcode}"

    # Find LAST before and after folders
    before_path = sorted(os.listdir(f"{base_path}/before"))[-1]
    after_path  = sorted(os.listdir(f"{base_path}/after"))[-1]

    before = f"{base_path}/before/{before_path}"
    after  = f"{base_path}/after/{after_path}"

    # Compare JSON files
    results = []
    before_files = os.listdir(before)
    after_files = os.listdir(after)

    for f in set(before_files + after_files):
        before_exist = f in before_files
        after_exist  = f in after_files

        if before_exist and after_exist:
            with open(f"{before}/{f}") as fb, open(f"{after}/{f}") as fa:
                fbj = json.loads(fb.read())
                faj = json.loads(fa.read())

                if fbj != faj:
                    results.append([f, "MODIFIED"])
        elif before_exist:
            results.append([f, "DELETED"])
        else:
            results.append([f, "ADDED"])

    # Output paths
    excel_path = f"{base_path}/report.xlsx"
    pdf_path = f"{base_path}/report.pdf"

    generate_excel(results, excel_path)
    export_pdf(results, pdf_path)

    print(f"\nReports generated:")
    print(f"✔ Excel: {excel_path}")
    print(f"✔ PDF:   {pdf_path}")

############################################
# CLI ENTRY POINT
############################################
if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True)
    parser.add_argument("--ap", required=True)
    parser.add_argument("--mode", required=True, choices=["before", "after", "report"])
    args = parser.parse_args()

    profiles = load_profiles()
    p = profiles[args.profile]["projects"][args.ap]

    # auto select cloud context
    set_ibmcloud_context(
        profiles[args.profile]["account"],
        profiles[args.profile]["region"],
        p["resource_group"],
        p["project"]
    )

    if args.mode == "report":
        generate_report(args.profile, args.ap)
    else:
        backup(args.profile, args.ap, args.mode)
