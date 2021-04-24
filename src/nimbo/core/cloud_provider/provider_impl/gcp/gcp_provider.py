from nimbo.core.cloud_provider.provider_impl.gcp.services import (
    gcp_instance,
    gcp_permissions,
    gcp_storage,
)


class GcpProvider(
    gcp_instance.GcpInstance, gcp_permissions.GcpPermissions, gcp_storage.GcpStorage
):
    ...
