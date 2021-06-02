import abc


class Utils(abc.ABC):
    @staticmethod
    @abc.abstractmethod
    def ls_gpu_prices(dry_run=False) -> None:
        ...

    @staticmethod
    @abc.abstractmethod
    def ls_spot_gpu_prices(dry_run=False) -> None:
        ...

    @staticmethod
    @abc.abstractmethod
    def spending(qty: int, timescale: str, dry_run=False) -> None:
        ...
