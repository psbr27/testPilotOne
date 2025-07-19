#!/usr/bin/env python3
"""
Migration script to help users transition from hardcoded credentials to secure configuration.
This script will:
1. Backup existing config files
2. Extract credentials and create .env file
3. Replace config files with template versions
"""

import json
import os
import shutil
import sys
from datetime import datetime


def backup_file(filepath):
    """Create a backup of the file with timestamp."""
    if os.path.exists(filepath):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{filepath}.backup_{timestamp}"
        shutil.copy2(filepath, backup_path)
        print(f"✓ Backed up {filepath} to {backup_path}")
        return backup_path
    return None


def extract_credentials_to_env(config_path, env_path=".env"):
    """Extract credentials from config and create .env file."""
    if not os.path.exists(config_path):
        return
    
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    env_lines = []
    env_lines.append("# Auto-generated from migration script")
    env_lines.append(f"# Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    env_lines.append("# Please review and update these values")
    env_lines.append("")
    
    # Extract host configurations
    hosts = config.get('hosts', [])
    for i, host in enumerate(hosts, 1):
        env_lines.append(f"# Host: {host.get('name', f'host{i}')}")
        
        if host.get('hostname'):
            env_lines.append(f"HOST{i}_HOSTNAME={host['hostname']}")
        
        if host.get('username'):
            env_lines.append(f"HOST{i}_USERNAME={host['username']}")
        
        if host.get('password'):
            env_lines.append(f"HOST{i}_PASSWORD={host['password']}")
        
        if host.get('key_file'):
            env_lines.append(f"HOST{i}_SSH_KEY_PATH={host['key_file']}")
        
        if host.get('namespace'):
            env_lines.append(f"HOST{i}_NAMESPACE={host['namespace']}")
        
        env_lines.append("")
    
    # Write .env file
    with open(env_path, 'w') as f:
        f.write('\n'.join(env_lines))
    
    print(f"✓ Created {env_path} with extracted credentials")
    print(f"  ⚠️  Remember to update the values and keep this file secure!")


def replace_with_template(config_path, template_path):
    """Replace config file with template version."""
    if os.path.exists(template_path):
        shutil.copy2(template_path, config_path)
        print(f"✓ Replaced {config_path} with template version")
    else:
        print(f"✗ Template not found: {template_path}")


def main():
    print("🔒 TestPilot Configuration Migration Tool")
    print("=" * 50)
    
    # Check if running from correct directory
    if not os.path.exists("config/hosts.json"):
        print("❌ Error: Please run this script from the TestPilot root directory")
        sys.exit(1)
    
    # Check if .env already exists
    if os.path.exists(".env"):
        print("⚠️  Warning: .env file already exists")
        response = input("Do you want to overwrite it? (y/N): ")
        if response.lower() != 'y':
            print("Exiting without changes")
            sys.exit(0)
    
    print("\nThis script will:")
    print("1. Backup your existing configuration files")
    print("2. Extract credentials to a .env file")
    print("3. Replace config files with secure templates")
    print("\n⚠️  WARNING: This will modify your configuration files!")
    
    response = input("\nDo you want to continue? (y/N): ")
    if response.lower() != 'y':
        print("Exiting without changes")
        sys.exit(0)
    
    print("\n📁 Processing configuration files...")
    
    # Process each config file
    config_files = [
        "config/hosts.json",
        "config/hosts.json.nrf",
        "config/hosts.json.slf"
    ]
    
    for config_file in config_files:
        if os.path.exists(config_file):
            print(f"\n📄 Processing {config_file}...")
            
            # Backup
            backup_file(config_file)
            
            # Extract credentials (only from main hosts.json)
            if config_file == "config/hosts.json":
                extract_credentials_to_env(config_file)
            
            # Replace with template
            template_file = f"{config_file}.template"
            if os.path.exists(template_file):
                replace_with_template(config_file, template_file)
            else:
                # Remove the file since it contains secrets
                os.remove(config_file)
                print(f"✓ Removed {config_file} (no template found)")
    
    print("\n✅ Migration complete!")
    print("\n📋 Next steps:")
    print("1. Review and update the .env file with your actual credentials")
    print("2. Set proper permissions: chmod 600 .env")
    print("3. Add .env to your shell environment or use a tool like direnv")
    print("4. Test your configuration with: python test_pilot.py --dry-run")
    print("\n🔒 Security reminders:")
    print("- Never commit .env or config files with real credentials")
    print("- Store SSH keys outside the project directory")
    print("- Use key-based authentication instead of passwords when possible")
    print("- Review the .gitignore file to ensure sensitive files are excluded")


if __name__ == "__main__":
    main()