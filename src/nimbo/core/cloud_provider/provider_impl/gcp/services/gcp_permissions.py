from nimbo.core.cloud_provider.provider.services.permissions import Permissions


class GcpPermissions(Permissions):
    @staticmethod
    def mk_instance_key(dry_run=False) -> None:
        pass

    @staticmethod
    def allow_ingress_current_ip(target: str, dry_run=False) -> None:
        ...

    @staticmethod
    def setup(profile: str, no_s3_access=False) -> None:
        pass

    @staticmethod
    def add_user(profile: str, username: str) -> None:
        pass
