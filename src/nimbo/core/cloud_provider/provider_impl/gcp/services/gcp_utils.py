from nimbo.core.cloud_provider.provider.services.utils import Utils


class GcpUtils(Utils):
    @staticmethod
    def ls_gpu_prices(dry_run=False) -> None:
        pass

    @staticmethod
    def ls_spot_gpu_prices(dry_run=False) -> None:
        pass

    @staticmethod
    def spending(qty: int, timescale: str, dry_run=False) -> None:
        pass
