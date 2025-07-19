# 🔒 TestPilot Secure Configuration Guide

## Overview

TestPilot now supports secure credential management through environment variables, preventing sensitive information from being stored in version control. This guide explains how to configure TestPilot securely.

## ⚡ Quick Start

1. **Run the migration script** (if upgrading from an older version):
   ```bash
   python migrate_config.py
   ```

2. **Copy the template files**:
   ```bash
   cp config/hosts.json.template config/hosts.json
   cp .env.template .env
   ```

3. **Edit the `.env` file** with your credentials:
   ```bash
   # Use your favorite editor
   nano .env
   # or
   vim .env
   ```

4. **Set proper permissions**:
   ```bash
   chmod 600 .env
   chmod 600 ~/.ssh/your_private_key
   ```

5. **Test your configuration**:
   ```bash
   python test_pilot.py --dry-run -i your_test.xlsx -m otp
   ```

## 📋 Configuration File Structure

### hosts.json

The main configuration file now supports environment variable substitution:

```json
{
    "hosts": [
        {
            "name": "production-server",
            "hostname": "${PROD_HOSTNAME}",
            "username": "${PROD_USERNAME}",
            "password": "${PROD_PASSWORD}",
            "key_file": "${PROD_SSH_KEY_PATH}",
            "namespace": "${PROD_NAMESPACE}"
        }
    ]
}
```

### Environment Variables

TestPilot supports two syntaxes for environment variables:

1. **Required variables**: `${VAR_NAME}`
   - Throws an error if not found
   - Use for critical configuration

2. **Optional variables with defaults**: `${VAR_NAME:-default_value}`
   - Uses the default if variable not set
   - Good for optional settings

## 🔐 Security Best Practices

### 1. Never Commit Secrets

- ✅ Commit: `config/hosts.json.template`
- ❌ Never commit: `config/hosts.json`, `.env`, private keys

### 2. Use SSH Keys Instead of Passwords

```bash
# Generate a new SSH key
ssh-keygen -t ed25519 -f ~/.ssh/testpilot_key

# Add to your .env
PROD_SSH_KEY_PATH=~/.ssh/testpilot_key
PROD_PASSWORD=  # Leave empty when using key
```

### 3. Proper File Permissions

```bash
# Protect your credentials
chmod 600 .env
chmod 600 ~/.ssh/testpilot_key
chmod 644 ~/.ssh/testpilot_key.pub
```

### 4. Use a Password Manager

Store your credentials in a password manager and copy them to `.env` when needed:

```bash
# Example using 1Password CLI
op read "op://vault/TestPilot/password" > temp && echo "PROD_PASSWORD=$(cat temp)" >> .env && rm temp
```

## 🛠️ Advanced Configuration

### Multiple Environments

Create environment-specific files:

```bash
.env.development
.env.staging
.env.production
```

Load the appropriate file:

```bash
# Linux/Mac
export $(cat .env.production | xargs)

# Or use direnv
echo "dotenv .env.production" > .envrc
direnv allow
```

### Using AWS Secrets Manager

```python
# In your wrapper script
import boto3
import os

def load_aws_secrets():
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId='testpilot/prod')
    secrets = json.loads(response['SecretString'])

    for key, value in secrets.items():
        os.environ[key] = value

# Load secrets before running TestPilot
load_aws_secrets()
```

### Using HashiCorp Vault

```bash
# Export secrets from Vault
export PROD_PASSWORD=$(vault kv get -field=password secret/testpilot/prod)
export PROD_SSH_KEY_PATH=$(vault kv get -field=ssh_key secret/testpilot/prod)
```

## 🔍 Troubleshooting

### Missing Environment Variable Error

```
ValueError: Required environment variable 'PROD_HOSTNAME' not found
```

**Solution**: Ensure the variable is set in your `.env` file or shell environment.

### SSH Key Not Found

```
Warning: SSH key file not found for host 'production': /path/to/key
```

**Solution**:
1. Check the path in your `.env` file
2. Ensure the key file exists and has correct permissions
3. Use absolute paths or `~` for home directory

### Permission Denied

```
Permission denied (publickey,password)
```

**Solution**:
1. Verify SSH key permissions: `chmod 600 ~/.ssh/your_key`
2. Ensure the public key is added to the target server
3. Check username and hostname are correct

## 📝 Configuration Validation

TestPilot now validates configurations on startup:

- ✅ Required fields are present
- ✅ Either password or key_file is provided
- ✅ File paths exist (for key files)
- ✅ Environment variables are resolved

## 🔄 Migration from Old Format

If you have existing configuration files with hardcoded credentials:

1. **Run the migration script**:
   ```bash
   python migrate_config.py
   ```

2. **Review the generated `.env` file**:
   - Update any placeholder values
   - Remove unnecessary entries
   - Add any missing credentials

3. **Verify backups were created**:
   ```bash
   ls config/*.backup_*
   ```

4. **Test the new configuration**:
   ```bash
   python test_pilot.py --dry-run -i test.xlsx -m otp
   ```

5. **Securely delete backups** (after confirming everything works):
   ```bash
   shred -vfz config/*.backup_*
   ```

## 🚀 CI/CD Integration

### GitHub Actions

```yaml
- name: Run TestPilot
  env:
    PROD_HOSTNAME: ${{ secrets.PROD_HOSTNAME }}
    PROD_USERNAME: ${{ secrets.PROD_USERNAME }}
    PROD_PASSWORD: ${{ secrets.PROD_PASSWORD }}
  run: |
    python test_pilot.py -i tests.xlsx -m otp
```

### Jenkins

```groovy
withCredentials([
    string(credentialsId: 'prod-hostname', variable: 'PROD_HOSTNAME'),
    string(credentialsId: 'prod-username', variable: 'PROD_USERNAME'),
    string(credentialsId: 'prod-password', variable: 'PROD_PASSWORD')
]) {
    sh 'python test_pilot.py -i tests.xlsx -m otp'
}
```

## 📚 Additional Resources

- [Environment Variables Best Practices](https://12factor.net/config)
- [SSH Key Management](https://www.ssh.com/academy/ssh/keygen)
- [HashiCorp Vault Integration](https://www.vaultproject.io/)
- [AWS Secrets Manager](https://aws.amazon.com/secrets-manager/)

---

Remember: **Security is everyone's responsibility**. Always follow your organization's security policies and never share credentials through insecure channels.
