from nimbo.core.cloud_provider.provider.services.permissions import Permissions


class GcpPermissions(Permissions):
    @staticmethod
    def allow_ingress_current_ip(target: str, dry_run=False) -> None:
        ...

    @staticmethod
    def setup(profile: str, full_s3_access=False) -> None:
        pass

    @staticmethod
    def add_user(username: str, profile: str) -> None:
        pass
