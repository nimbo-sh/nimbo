import abc
import os
import socket
import subprocess
import time
from typing import Dict

from nimbo import CONFIG
from nimbo.core.constants import NIMBO_ROOT
from nimbo.core.print import nprint, nprint_header


class Instance(abc.ABC):
    @staticmethod
    @abc.abstractmethod
    def run(job_cmd: str, dry_run=False) -> Dict[str, str]:
        ...

    @staticmethod
    @abc.abstractmethod
    def run_access_test(dry_run=False) -> None:
        ...

    @staticmethod
    @abc.abstractmethod
    def _block_until_instance_running(instance_id: str) -> None:
        ...

    @staticmethod
    @abc.abstractmethod
    def _get_host_from_instance_id(instance_id: str, dry_run=False) -> str:
        ...

    @staticmethod
    @abc.abstractmethod
    def stop_instance(instance_id: str, dry_run=False) -> None:
        ...

    @staticmethod
    @abc.abstractmethod
    def resume_instance(instance_id: str, dry_run=False) -> None:
        ...

    @staticmethod
    @abc.abstractmethod
    def delete_instance(instance_id: str, dry_run=False) -> None:
        ...

    @staticmethod
    @abc.abstractmethod
    def delete_all_instances(dry_run=False) -> None:
        ...

    @staticmethod
    @abc.abstractmethod
    def get_status(instance_id: str, dry_run=False) -> str:
        ...

    @staticmethod
    @abc.abstractmethod
    def ls_active_instances(dry_run=False) -> None:
        ...

    @staticmethod
    @abc.abstractmethod
    def ls_stopped_instances(dry_run=False) -> None:
        ...

    @classmethod
    def ssh(cls, instance_id: str, dry_run=False) -> None:
        host = cls._get_host_from_instance_id(instance_id, dry_run)

        if dry_run:
            return

        subprocess.Popen(
            f"ssh -i {CONFIG.instance_key} "
            f"-o 'StrictHostKeyChecking no' -o ServerAliveInterval=20 "
            f"ubuntu@{host}",
            shell=True,
        ).communicate()

    @classmethod
    def sync_notebooks(cls, instance_id: str):
        host = cls._get_host_from_instance_id(instance_id)

        subprocess.Popen(
            f"rsync -avm -e 'ssh -i {CONFIG.instance_key}' "
            f"--include '*/' --include '*.ipynb' --exclude '*' "
            f"ubuntu@{host}:/home/ubuntu/project/ .",
            shell=True,
        ).communicate()

    @staticmethod
    def _sync_code(host: str) -> None:
        if ".git" not in os.listdir():
            nprint(
                "No git repo found. Syncing all python and bash files as a fallback.",
                style="warning",
            )
            nprint(
                "Please consider using git to track the files to sync.", style="warning"
            )
            subprocess.Popen(
                f"rsync -avm -e 'ssh -i {CONFIG.instance_key}' "
                f"--include '*/' --include '*.py' --include '*.ipynb' --include '*.sh' "
                f"--exclude '*' "
                f". ubuntu@{host}:/home/ubuntu/project",
                shell=True,
            ).communicate()
        else:
            output, error = subprocess.Popen(
                "git ls-tree -r HEAD --name-only",
                stdout=subprocess.PIPE,
                shell=True,
            ).communicate()
            git_tracked_files = output.decode("utf-8").strip().splitlines()
            include_files = [
                f"--include '{file_name}'" for file_name in git_tracked_files
            ]
            include_string = " ".join(include_files)
            subprocess.Popen(
                f"rsync -amr -e 'ssh -i {CONFIG.instance_key}' "
                f"--include '*/' {include_string} --exclude '*' "
                f". ubuntu@{host}:/home/ubuntu/project",
                shell=True,
            ).communicate()

    @staticmethod
    def _block_until_ssh_ready(host: str) -> None:
        nprint_header(
            f"Waiting for instance to be ready for ssh at {host}. "
            "This can take up to 2 minutes... "
        )

        start = time.monotonic()

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)

        reconnect_count = 0
        while reconnect_count < CONFIG.ssh_timeout:
            error_num = sock.connect_ex((host, 22))

            if error_num == 0:
                break

            time.sleep(1)
            reconnect_count += 1
        else:
            raise RuntimeError(
                "Something went wrong while connecting to the instance.\n"
                "Please verify your security groups, instance key and "
                "instance profile, and try again.\n"
                "More info at docs.nimbo.sh/common-issues#cant-ssh.\n"
            )

        nprint_header(f"Ready. (%0.3f s)" % (time.monotonic() - start))

    @staticmethod
    def _run_remote_script(
        ssh_cmd: str,
        scp_cmd: str,
        host: str,
        instance_id: str,
        job_cmd: str,
        script: str,
    ) -> None:

        remote_script = os.path.join(NIMBO_ROOT, "scripts", script)
        subprocess.check_output(
            f"{scp_cmd} {remote_script} ubuntu@{host}:/home/ubuntu/", shell=True
        )

        nimbo_log = "/home/ubuntu/nimbo-log.txt"
        bash_cmd = f"bash {script}"
        if CONFIG.run_in_background:
            full_command = (
                f"nohup {bash_cmd} {instance_id} {job_cmd}"
                f" </dev/null >{nimbo_log} 2>&1 &"
            )
        else:
            full_command = f"{bash_cmd} {instance_id} {job_cmd}"

        subprocess.Popen(
            f'{ssh_cmd} ubuntu@{host} "{full_command}"', shell=True
        ).communicate()
