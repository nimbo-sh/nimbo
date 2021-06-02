import abc


class Storage(abc.ABC):
    @staticmethod
    @abc.abstractmethod
    def push(folder: str, delete=False) -> None:
        ...

    @staticmethod
    @abc.abstractmethod
    def pull(folder: str, delete=False) -> None:
        ...

    @staticmethod
    @abc.abstractmethod
    def ls_bucket(path: str) -> None:
        ...

    @staticmethod
    @abc.abstractmethod
    def mk_bucket(bucket_name: str, dry_run=False) -> None:
        ...
