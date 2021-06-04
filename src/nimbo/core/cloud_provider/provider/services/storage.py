import abc


class Storage(abc.ABC):
    @staticmethod
    @abc.abstractmethod
    def push(directory: str, delete=False) -> None:
        ...

    @staticmethod
    @abc.abstractmethod
    def pull(directory: str, delete=False) -> None:
        ...

    @staticmethod
    @abc.abstractmethod
    def mk_bucket(bucket_name: str) -> None:
        ...

    @staticmethod
    @abc.abstractmethod
    def ls_bucket(bucket_name: str, prefix: str) -> None:
        ...
