from nimbo.core.cloud_provider.provider_impl.aws.services import (
    aws_instance,
    aws_permissions,
    aws_storage,
)


class AwsProvider(
    aws_instance.AwsInstance, aws_permissions.AwsPermissions, aws_storage.AwsStorage
):
    ...
