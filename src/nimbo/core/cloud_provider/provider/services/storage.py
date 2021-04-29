import abc


class Storage(abc.ABC):
    @staticmethod
    @abc.abstractmethod
    def allow_ingress_current_ip(target: str, dry_run=False) -> None:
        ...
