from nimbo import CONFIG
from nimbo.core.cloud_provider.provider_impl.aws.aws_provider import AwsProvider
from nimbo.core.cloud_provider.provider_impl.gcp.gcp_provider import GcpProvider

if CONFIG.provider == "aws":
    Cloud = AwsProvider()
else:
    Cloud = GcpProvider()
