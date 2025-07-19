<<<<<<< HEAD
import hashlib
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Tuple

import paramiko

from logger import get_logger

logger = get_logger("SSHConnector")


class SSHHostConfig:
    def __init__(
        self,
        name: str,
        hostname: str,
        username: str,
        key_file: Optional[str] = None,
        password: Optional[str] = None,
        port: int = 22,
        namespace: Optional[str] = None,
    ):
        self.name = name
        self.hostname = hostname
        self.username = username
        self.key_file = key_file
        self.password = password
        self.port = port
        self.namespace = namespace


class SSHConnector:
    def __init__(self, config_file: str):
        self.config_file = config_file
        self.use_ssh = False
        self.host_configs: List[SSHHostConfig] = []
        self.connections: Dict[str, paramiko.SSHClient] = {}
        self.known_hosts_file = os.path.expanduser("~/.ssh/known_hosts")
        self.auto_add_hosts = False  # Secure by default
        self.max_retries = 3  # Default retry count
        self.retry_delay = 2  # Seconds between retries
        self._load_config()

    def _load_config(self):
        with open(self.config_file, "r") as f:
            data = json.load(f)

        self.use_ssh = data.get("use_ssh", False)
        if not self.use_ssh:
            logger.warning("SSH connections are globally disabled via 'use_ssh': false")
            return

        # Load SSH security settings
        ssh_settings = data.get("ssh_settings", {})
        self.auto_add_hosts = ssh_settings.get("auto_add_hosts", False)
        self.known_hosts_file = ssh_settings.get(
            "known_hosts_file", self.known_hosts_file
        )
        self.max_retries = ssh_settings.get("max_retries", self.max_retries)
        self.retry_delay = ssh_settings.get("retry_delay", self.retry_delay)

        if self.auto_add_hosts:
            logger.warning(
                "WARNING: auto_add_hosts is enabled. This is insecure and should only be used in development!"
            )

        for host in data.get("hosts", []):
            host_cfg = SSHHostConfig(
                name=host["name"],
                hostname=host["hostname"],
                username=host["username"],
                key_file=host.get("key_file"),
                password=host.get("password"),
                port=host.get("port", 22),
                namespace=host.get("namespace"),
            )
            self.host_configs.append(host_cfg)

    def _get_host_key_policy(self):
        """Returns appropriate host key policy based on configuration"""
        if self.auto_add_hosts:
            return paramiko.AutoAddPolicy()
        else:
            # Use a custom policy that prompts for unknown hosts
            class PromptPolicy(paramiko.MissingHostKeyPolicy):
                def missing_host_key(self, client, hostname, key):
                    key_type = key.get_name()
                    fingerprint = hashlib.sha256(key.asbytes()).hexdigest()
                    logger.warning(f"Unknown host: {hostname}")
                    logger.warning(f"Key type: {key_type}")
                    logger.warning(f"Key fingerprint: {fingerprint}")

                    # In production, this should either:
                    # 1. Reject the connection (raise paramiko.SSHException)
                    # 2. Check against a pre-configured list of known host keys
                    # For now, we'll reject unknown hosts for security
                    raise paramiko.SSHException(
                        f"Host key verification failed for {hostname}. "
                        f"Add the host key to known_hosts or enable auto_add_hosts in config "
                        f"(not recommended for production)."
                    )

            return PromptPolicy()

    def _connect_host(
        self, host_config: SSHHostConfig
    ) -> Tuple[str, Optional[paramiko.SSHClient]]:
        """Connect to a host with retry mechanism."""
        last_exception = None

        for attempt in range(self.max_retries):
            ssh = paramiko.SSHClient()

            try:
                # Load known hosts file if it exists
                if os.path.exists(self.known_hosts_file):
                    try:
                        ssh.load_host_keys(self.known_hosts_file)
                        logger.debug(f"Loaded known hosts from {self.known_hosts_file}")
                    except Exception as e:
                        logger.warning(f"Failed to load known hosts file: {e}")

                # Set the host key policy
                ssh.set_missing_host_key_policy(self._get_host_key_policy())

                # Attempt connection
                ssh.connect(
                    hostname=host_config.hostname,
                    port=host_config.port,
                    username=host_config.username,
                    key_filename=host_config.key_file if host_config.key_file else None,
                    password=host_config.password if not host_config.key_file else None,
                    timeout=10,
                )
                logger.debug(
                    f"Connected to {host_config.name} ({host_config.hostname}) on attempt {attempt + 1}"
                )
                return host_config.name, ssh

            except paramiko.SSHException as e:
                last_exception = e
                logger.warning(
                    f"SSH error connecting to {host_config.name} (attempt {attempt + 1}/{self.max_retries}): {e}"
                )
                ssh.close()
            except Exception as e:
                last_exception = e
                logger.warning(
                    f"Failed to connect to {host_config.name} (attempt {attempt + 1}/{self.max_retries}): {e}"
                )
                ssh.close()

            # Wait before retry (except on last attempt)
            if attempt < self.max_retries - 1:
                logger.debug(f"Waiting {self.retry_delay} seconds before retry...")
                time.sleep(self.retry_delay)

        # All attempts failed
        logger.error(
            f"Failed to connect to {host_config.name} after {self.max_retries} attempts. Last error: {last_exception}"
        )
        return host_config.name, None

    def connect_all(self, target_hosts: Optional[List[str]] = None) -> None:
        """Connect to all configured hosts or specific target hosts."""
        if not self.use_ssh:
            logger.warning("Skipping SSH connections due to use_ssh=false")
            return

        host_configs_to_connect = self.host_configs
        if target_hosts is not None:
            host_configs_to_connect = [
                hc for hc in self.host_configs if hc.name in target_hosts
            ]

        if not host_configs_to_connect:
            logger.warning("No host configurations found to connect to")
            return

        with ThreadPoolExecutor(max_workers=len(host_configs_to_connect)) as executor:
            futures = {
                executor.submit(self._connect_host, hc): hc.name
                for hc in host_configs_to_connect
            }
            for future in as_completed(futures):
                name, conn = future.result()
                if conn:
                    self.connections[name] = conn

    def run_command(self, command, target_hosts, timeout=30):
        """Execute command on target hosts with timeout protection"""
        results = {}

        def run_on_host(name, conn):
            try:
                # Set timeout for the command execution
                stdin, stdout, stderr = conn.exec_command(command, timeout=timeout)
                # Read with timeout
                stdout_data = stdout.read().decode().strip()
                stderr_data = stderr.read().decode().strip()
                return name, stdout_data, stderr_data
            except Exception as e:
                logger.error(f"Command execution failed on {name}: {e}")
                return name, "", str(e)

        # Validate connections exist
        valid_targets = [name for name in target_hosts if name in self.connections]
        if not valid_targets:
            logger.error("No valid SSH connections available for target hosts")
            return results

        with ThreadPoolExecutor(max_workers=len(valid_targets)) as executor:
            futures = {
                executor.submit(run_on_host, name, self.connections[name]): name
                for name in valid_targets
            }

            for future in as_completed(futures):
                try:
                    name, out, err = future.result(
                        timeout=timeout + 5
                    )  # Give extra time for cleanup
                    results[name] = {"output": out, "error": err}
                except Exception as e:
                    name = futures[future]
                    logger.error(f"Failed to get result from {name}: {e}")
                    results[name] = {"output": "", "error": str(e)}

        return results

    def get_connection(self, host_name):
        return self.connections.get(host_name)

    def get_all_connections(self):
        return self.connections

    def get_host_config(self, host_name):
        for hc in self.host_configs:
            if hc.name == host_name:
                return hc
        return None

    def close_all(self):
        for name, conn in self.connections.items():
            conn.close()
            logger.debug(f"Closed connection to {name}")
=======
import hashlib
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Tuple

import paramiko

from logger import get_logger
from utils.config_resolver import load_config_with_env, validate_host_config, mask_sensitive_data

logger = get_logger("SSHConnector")


class SSHHostConfig:
    def __init__(
        self,
        name: str,
        hostname: str,
        username: str,
        key_file: Optional[str] = None,
        password: Optional[str] = None,
        port: int = 22,
        namespace: Optional[str] = None,
    ):
        self.name = name
        self.hostname = hostname
        self.username = username
        self.key_file = key_file
        self.password = password
        self.port = port
        self.namespace = namespace


class SSHConnector:
    def __init__(self, config_file: str):
        self.config_file = config_file
        self.use_ssh = False
        self.host_configs: List[SSHHostConfig] = []
        self.connections: Dict[str, paramiko.SSHClient] = {}
        self.known_hosts_file = os.path.expanduser("~/.ssh/known_hosts")
        self.auto_add_hosts = False  # Secure by default
        self.max_retries = 3  # Default retry count
        self.retry_delay = 2  # Seconds between retries
        self._load_config()

    def _load_config(self):
        try:
            # Load config with environment variable resolution
            data = load_config_with_env(self.config_file)
            
            # Log masked configuration for debugging
            masked_config = mask_sensitive_data(data)
            logger.debug(f"Loaded configuration (masked): {json.dumps(masked_config, indent=2)}")
        except ValueError as e:
            logger.error(f"Configuration error: {e}")
            raise
        except FileNotFoundError as e:
            logger.error(f"Configuration file not found: {e}")
            raise

        self.use_ssh = data.get("use_ssh", False)
        if not self.use_ssh:
            logger.warning("SSH connections are globally disabled via 'use_ssh': false")
            return

        # Load SSH security settings
        ssh_settings = data.get("ssh_settings", {})
        self.auto_add_hosts = ssh_settings.get("auto_add_hosts", False)
        self.known_hosts_file = ssh_settings.get(
            "known_hosts_file", self.known_hosts_file
        )
        self.max_retries = ssh_settings.get("max_retries", self.max_retries)
        self.retry_delay = ssh_settings.get("retry_delay", self.retry_delay)

        if self.auto_add_hosts:
            logger.warning(
                "WARNING: auto_add_hosts is enabled. This is insecure and should only be used in development!"
            )

        for host in data.get("hosts", []):
            # Validate host configuration
            try:
                validate_host_config(host)
            except ValueError as e:
                logger.error(f"Invalid host configuration: {e}")
                raise
            
            # Expand paths for key files
            key_file = host.get("key_file")
            if key_file:
                key_file = os.path.expanduser(key_file)
                if not os.path.exists(key_file):
                    logger.warning(f"SSH key file not found for host '{host['name']}': {key_file}")
            
            host_cfg = SSHHostConfig(
                name=host["name"],
                hostname=host["hostname"],
                username=host["username"],
                key_file=key_file,
                password=host.get("password"),
                port=host.get("port", 22),
                namespace=host.get("namespace"),
            )
            self.host_configs.append(host_cfg)

    def _get_host_key_policy(self):
        """Returns appropriate host key policy based on configuration"""
        if self.auto_add_hosts:
            return paramiko.AutoAddPolicy()
        else:
            # Use a custom policy that prompts for unknown hosts
            class PromptPolicy(paramiko.MissingHostKeyPolicy):
                def missing_host_key(self, client, hostname, key):
                    key_type = key.get_name()
                    fingerprint = hashlib.sha256(key.asbytes()).hexdigest()
                    logger.warning(f"Unknown host: {hostname}")
                    logger.warning(f"Key type: {key_type}")
                    logger.warning(f"Key fingerprint: {fingerprint}")

                    # In production, this should either:
                    # 1. Reject the connection (raise paramiko.SSHException)
                    # 2. Check against a pre-configured list of known host keys
                    # For now, we'll reject unknown hosts for security
                    raise paramiko.SSHException(
                        f"Host key verification failed for {hostname}. "
                        f"Add the host key to known_hosts or enable auto_add_hosts in config "
                        f"(not recommended for production)."
                    )

            return PromptPolicy()

    def _connect_host(
        self, host_config: SSHHostConfig
    ) -> Tuple[str, Optional[paramiko.SSHClient]]:
        """Connect to a host with retry mechanism."""
        last_exception = None

        for attempt in range(self.max_retries):
            ssh = paramiko.SSHClient()

            try:
                # Load known hosts file if it exists
                if os.path.exists(self.known_hosts_file):
                    try:
                        ssh.load_host_keys(self.known_hosts_file)
                        logger.debug(f"Loaded known hosts from {self.known_hosts_file}")
                    except Exception as e:
                        logger.warning(f"Failed to load known hosts file: {e}")

                # Set the host key policy
                ssh.set_missing_host_key_policy(self._get_host_key_policy())

                # Attempt connection
                ssh.connect(
                    hostname=host_config.hostname,
                    port=host_config.port,
                    username=host_config.username,
                    key_filename=host_config.key_file if host_config.key_file else None,
                    password=host_config.password if not host_config.key_file else None,
                    timeout=10,
                )
                logger.debug(
                    f"Connected to {host_config.name} ({host_config.hostname}) on attempt {attempt + 1}"
                )
                return host_config.name, ssh

            except paramiko.SSHException as e:
                last_exception = e
                logger.warning(
                    f"SSH error connecting to {host_config.name} (attempt {attempt + 1}/{self.max_retries}): {e}"
                )
                ssh.close()
            except Exception as e:
                last_exception = e
                logger.warning(
                    f"Failed to connect to {host_config.name} (attempt {attempt + 1}/{self.max_retries}): {e}"
                )
                ssh.close()

            # Wait before retry (except on last attempt)
            if attempt < self.max_retries - 1:
                logger.debug(f"Waiting {self.retry_delay} seconds before retry...")
                time.sleep(self.retry_delay)

        # All attempts failed
        logger.error(
            f"Failed to connect to {host_config.name} after {self.max_retries} attempts. Last error: {last_exception}"
        )
        return host_config.name, None

    def connect_all(self, target_hosts: Optional[List[str]] = None) -> None:
        """Connect to all configured hosts or specific target hosts."""
        if not self.use_ssh:
            logger.warning("Skipping SSH connections due to use_ssh=false")
            return

        host_configs_to_connect = self.host_configs
        if target_hosts is not None:
            host_configs_to_connect = [
                hc for hc in self.host_configs if hc.name in target_hosts
            ]

        if not host_configs_to_connect:
            logger.warning("No host configurations found to connect to")
            return

        with ThreadPoolExecutor(max_workers=len(host_configs_to_connect)) as executor:
            futures = {
                executor.submit(self._connect_host, hc): hc.name
                for hc in host_configs_to_connect
            }
            for future in as_completed(futures):
                name, conn = future.result()
                if conn:
                    self.connections[name] = conn

    def run_command(self, command, target_hosts, timeout=30):
        """Execute command on target hosts with timeout protection"""
        results = {}

        def run_on_host(name, conn):
            try:
                # Set timeout for the command execution
                stdin, stdout, stderr = conn.exec_command(command, timeout=timeout)
                # Read with timeout
                stdout_data = stdout.read().decode().strip()
                stderr_data = stderr.read().decode().strip()
                return name, stdout_data, stderr_data
            except Exception as e:
                logger.error(f"Command execution failed on {name}: {e}")
                return name, "", str(e)

        # Validate connections exist
        valid_targets = [name for name in target_hosts if name in self.connections]
        if not valid_targets:
            logger.error("No valid SSH connections available for target hosts")
            return results

        with ThreadPoolExecutor(max_workers=len(valid_targets)) as executor:
            futures = {
                executor.submit(run_on_host, name, self.connections[name]): name
                for name in valid_targets
            }

            for future in as_completed(futures):
                try:
                    name, out, err = future.result(
                        timeout=timeout + 5
                    )  # Give extra time for cleanup
                    results[name] = {"output": out, "error": err}
                except Exception as e:
                    name = futures[future]
                    logger.error(f"Failed to get result from {name}: {e}")
                    results[name] = {"output": "", "error": str(e)}

        return results

    def get_connection(self, host_name):
        return self.connections.get(host_name)

    def get_all_connections(self):
        return self.connections

    def get_host_config(self, host_name):
        for hc in self.host_configs:
            if hc.name == host_name:
                return hc
        return None

    def close_all(self):
        for name, conn in self.connections.items():
            conn.close()
            logger.debug(f"Closed connection to {name}")
>>>>>>> sp-dev
