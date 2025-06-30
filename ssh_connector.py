import json
import paramiko
from concurrent.futures import ThreadPoolExecutor, as_completed
from logger import get_logger

logger = get_logger("SSHConnector")

class SSHHostConfig:
    def __init__(self, name, hostname, username, key_file=None, password=None, port=22, namespace=None):
        self.name = name
        self.hostname = hostname
        self.username = username
        self.key_file = key_file
        self.password = password
        self.port = port
        self.namespace = namespace


class SSHConnector:
    def __init__(self, config_file):
        self.config_file = config_file
        self.use_ssh = False
        self.host_configs = []
        self.connections = {}
        self._load_config()

    def _load_config(self):
        with open(self.config_file, 'r') as f:
            data = json.load(f)

        self.use_ssh = data.get("use_ssh", False)
        if not self.use_ssh:
            logger.warning("SSH connections are globally disabled via 'use_ssh': false")
            return

        for host in data.get("hosts", []):
            host_cfg = SSHHostConfig(
                name=host["name"],
                hostname=host["hostname"],
                username=host["username"],
                key_file=host.get("key_file"),
                password=host.get("password"),
                port=host.get("port", 22),
                namespace=host.get("namespace")
            )
            self.host_configs.append(host_cfg)

    def _connect_host(self, host_config):
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            ssh.connect(
                hostname=host_config.hostname,
                port=host_config.port,
                username=host_config.username,
                key_filename=host_config.key_file if host_config.key_file else None,
                password=host_config.password if not host_config.key_file else None,
                timeout=10
            )
            logger.info(f"Connected to {host_config.name} ({host_config.hostname})")
            return host_config.name, ssh
        except Exception as e:
            logger.error(f"Failed to connect to {host_config.name}: {e}")
            return host_config.name, None

    def connect_all(self, target_hosts=None):
        if not self.use_ssh:
            logger.warning("Skipping SSH connections due to use_ssh=false")
            return

        host_configs_to_connect = self.host_configs
        if target_hosts is not None:
            host_configs_to_connect = [hc for hc in self.host_configs if hc.name in target_hosts]

        with ThreadPoolExecutor(max_workers=len(host_configs_to_connect)) as executor:
            futures = {
                executor.submit(self._connect_host, hc): hc.name
                for hc in host_configs_to_connect
            }
            for future in as_completed(futures):
                name, conn = future.result()
                if conn:
                    self.connections[name] = conn

    def run_command(self, command, target_hosts):
        results = {}

        def run_on_host(name, conn):
            stdin, stdout, stderr = conn.exec_command(command)
            return name, stdout.read().decode().strip(), stderr.read().decode().strip()

        with ThreadPoolExecutor(max_workers=len(target_hosts)) as executor:
            futures = {
                executor.submit(run_on_host, name, self.connections[name]): name
                for name in target_hosts
                if name in self.connections
            }

            for future in as_completed(futures):
                name, out, err = future.result()
                results[name] = {"output": out, "error": err}

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
            logger.info(f"Closed connection to {name}")
