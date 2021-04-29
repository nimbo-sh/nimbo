import abc


class Permissions(abc.ABC):
    @staticmethod
    @abc.abstractmethod
    def allow_ingress_current_ip(target: str, dry_run=False) -> None:
        """
        Adds the IP of the current machine to the allowed ingress rules of
        instances that

        :param target: group name for AWS or VPC name for GCP
        :param dry_run: perform dry run
        """
        ...

    @staticmethod
    @abc.abstractmethod
    def setup_as_user(role_name: str = "", dry_run=False) -> None:
        ...

    @staticmethod
    @abc.abstractmethod
    def setup_as_admin(dry_run=False) -> None:
        ...
