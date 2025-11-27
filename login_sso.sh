#!/bin/bash
set -e

# Login to IBM Cloud using SSO MFA
ibmcloud logout >/dev/null 2>&1 || true
ibmcloud login --sso

echo "✔ Logged in"
