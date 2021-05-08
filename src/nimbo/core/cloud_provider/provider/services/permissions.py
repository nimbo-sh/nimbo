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
    def setup(profile: str, full_s3_access=False) -> None:
        ...

    @staticmethod
    @abc.abstractmethod
    def add_user(username: str, profile: str) -> None:
        ...
