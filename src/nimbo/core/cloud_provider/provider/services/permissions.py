import abc


class Permissions(abc.ABC):
    @staticmethod
    @abc.abstractmethod
    def mk_instance_key(dry_run=False) -> None:
        """Create and download an instance key to the current directory."""
        ...

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
    def setup(profile: str, no_s3_access=False) -> None:
        ...

    @staticmethod
    @abc.abstractmethod
    def add_user(profile: str, username: str) -> None:
        ...
