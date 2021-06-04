from nimbo.core.cloud_provider.provider.services.storage import Storage


class GcpStorage(Storage):
    @staticmethod
    def push(directory: str, delete=False) -> None:
        ...

    @staticmethod
    def pull(directory: str, delete=False) -> None:
        ...

    @staticmethod
    def mk_bucket(bucket_name: str) -> None:
        ...

    @staticmethod
    def ls_bucket(bucket_name: str, prefix: str) -> None:
        ...
