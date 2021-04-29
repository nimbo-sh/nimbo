from nimbo.core.cloud_provider.provider.services.permissions import Permissions


class GcpPermissions(Permissions):
    @staticmethod
    def allow_ingress_current_ip(target: str, dry_run=False) -> None:
        ...

    @staticmethod
    def setup_as_user(role_name: str = "", dry_run=False) -> None:
        pass

    @staticmethod
    def setup_as_admin(dry_run=False) -> None:
        ...
