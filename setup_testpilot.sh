#!/bin/bash

# TestPilot Setup Script
# This script helps customers set up TestPilot configuration

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}===================================${NC}"
echo -e "${BLUE}    TestPilot Setup Assistant      ${NC}"
echo -e "${BLUE}===================================${NC}"
echo

# Function to prompt user with default value
prompt_with_default() {
    local prompt_text="$1"
    local default_value="$2"
    local var_name="$3"

    if [ -n "$default_value" ]; then
        echo -n "$prompt_text [$default_value]: "
    else
        echo -n "$prompt_text: "
    fi

    read user_input
    if [ -z "$user_input" ] && [ -n "$default_value" ]; then
        eval "$var_name='$default_value'"
    else
        eval "$var_name='$user_input'"
    fi
}

# Check if config directory exists
if [ ! -d "config" ]; then
    echo -e "${YELLOW}Creating config directory...${NC}"
    mkdir -p config
fi

# Backup existing hosts.json if it exists
if [ -f "config/hosts.json" ]; then
    backup_file="config/hosts.json.backup.$(date +%Y%m%d_%H%M%S)"
    echo -e "${YELLOW}Backing up existing hosts.json to $backup_file${NC}"
    cp config/hosts.json "$backup_file"
fi

echo -e "${GREEN}Let's configure your TestPilot environment${NC}"
echo

# Environment type selection
echo "What type of environment are you setting up?"
echo "1) SLF (Subscriber Location Function)"
echo "2) NRF (Network Repository Function)"
echo "3) Other/Custom"

prompt_with_default "Select environment type (1-3)" "1" "env_choice"

# Set NF type based on selection
case $env_choice in
    1) NF_TYPE="SLF" ;;
    2) NF_TYPE="NRF" ;;
    3)
        prompt_with_default "Enter NF type" "CUSTOM" "NF_TYPE"
        ;;
    *) NF_TYPE="SLF" ;;
esac

echo
prompt_with_default "Enter NF name (e.g., slf, nrf)" "slf" "NF_NAME"
prompt_with_default "Enter software version" "v23.4.x" "VERSION"
prompt_with_default "Enter environment description" "Test Lab Environment" "ENV_DESC"

echo
echo -e "${GREEN}Namespace Configuration${NC}"

# Always use local kubectl
USE_SSH=false
POD_MODE=false
USE_PASSWORD=false

# Configure single host with null values
host_name="localhost"
CONNECT_TO="localhost"
hostname="null"
username="null"
port=22
password="null"
key_file="null"

# Ask for namespace directly
echo
prompt_with_default "Enter Kubernetes namespace" "" "namespace"

# Build host JSON
if [ "$hostname" = "null" ]; then
    hostname_json="null"
else
    hostname_json="\"$hostname\""
fi

if [ "$username" = "null" ]; then
    username_json="null"
else
    username_json="\"$username\""
fi

hosts_json="[
        {
            \"name\": \"$host_name\",
            \"hostname\": $hostname_json,
            \"username\": $username_json,
            \"key_file\": $key_file,
            \"password\": \"$password\",
            \"namespace\": \"$namespace\",
            \"port\": $port
        }
    ]"

# Generate the complete hosts.json
cat > config/hosts.json << EOF
{
    "use_ssh": $USE_SSH,
    "pod_mode": false,
    "nf_name": "$NF_NAME",
    "connect_to": "$CONNECT_TO",
    "html_generator": {
        "use_nf_style": true,
        "_comment": "Set to true for NF-style HTML reports, false for standard reports"
    },
    "system_under_test": {
        "nf_type": "$NF_TYPE",
        "version": "$VERSION",
        "environment": "$ENV_DESC",
        "deployment": "Kubernetes Cluster",
        "description": "5G Core Network Function - $NF_TYPE"
    },
    "ssh_settings": {
        "auto_add_hosts": true,
        "known_hosts_file": "~/.ssh/known_hosts",
        "max_retries": 3,
        "retry_delay": 2
    },
    "kubectl_logs_settings": {
        "capture_duration": 30,
        "since_duration": "1s"
    },
    "validation_settings": {
        "json_match_threshold": 50
    },
    "hosts": $hosts_json
}
EOF

echo
echo -e "${GREEN}✅ Configuration saved to config/hosts.json${NC}"

# Copy config to _internal directory
if [ -d "_internal" ]; then
    echo -e "${YELLOW}Copying config to _internal directory...${NC}"
    cp -r config/ _internal/
    echo -e "${GREEN}✅ Configuration copied to _internal/config/${NC}"
fi
echo

echo -e "${GREEN}Setup complete! Next steps:${NC}"
echo "1. Extract the TestPilot distribution if not already done"
echo "2. Review and adjust config/hosts.json if needed"
echo "3. Run TestPilot with: ./testPilot -i <excel-file> -m <module>"
echo
echo -e "${BLUE}For more information, see the deployment guide.${NC}"
