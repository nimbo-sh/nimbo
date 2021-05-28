from typing import Dict

from nimbo.core.cloud_provider.provider.services.instance import Instance


class GcpInstance(Instance):
    @staticmethod
    def run(job_cmd: str, dry_run=False) -> Dict[str, str]:
        pass

    @staticmethod
    def run_access_test(dry_run=False) -> None:
        pass

    @staticmethod
    def _block_until_instance_running(instance_id: str) -> None:
        pass

    @staticmethod
    def _get_host_from_instance_id(instance_id: str, dry_run=False) -> str:
        pass

    @staticmethod
    def stop_instance(instance_id: str, dry_run=False) -> None:
        pass

    @staticmethod
    def resume_instance(instance_id: str, dry_run=False) -> None:
        pass

    @staticmethod
    def delete_instance(instance_id: str, dry_run=False) -> None:
        pass

    @staticmethod
    def delete_all_instances(dry_run=False) -> None:
        pass

    @staticmethod
    def get_status(instance_id: str, dry_run=False) -> str:
        pass

    @staticmethod
    def ls_active_instances(dry_run=False) -> None:
        pass

    @staticmethod
    def ls_stopped_instances(dry_run=False) -> None:
        pass
