from nimbo.core.cloud_provider.provider.services.storage import Storage


class GcpStorage(Storage):
    @staticmethod
    def push(folder: str, delete=False) -> None:
        ...

    @staticmethod
    def pull(folder: str, delete=False) -> None:
        ...

    @staticmethod
    def ls_bucket(path: str) -> None:
        ...

    @staticmethod
    def mk_bucket(bucket_name: str, dry_run=False) -> None:
        ...
