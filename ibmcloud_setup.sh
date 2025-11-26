#!/bin/bash

echo "🔐 Logging into IBM Cloud..."
ibmcloud login --sso

echo "📌 Select account:"
ibmcloud account list
read -p "Enter account ID: " ACCOUNT
ibmcloud target -c $ACCOUNT

echo "📍 Select region:"
ibmcloud regions
read -p "Enter region (e.g. br-sao, us-south): " REGION
ibmcloud target -r $REGION

echo "📦 Select resource group:"
ibmcloud resource groups
read -p "Enter resource group name: " RG
ibmcloud target -g "$RG"

echo "🚀 Select Code Engine project:"
ibmcloud ce project list
read -p "Enter project name: " PROJECT
ibmcloud ce project select -n "$PROJECT"

echo "✔️ IBM Cloud environment configured successfully"
