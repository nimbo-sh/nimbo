import abc

from nimbo.core.cloud_provider.provider.services.instance import Instance
from nimbo.core.cloud_provider.provider.services.permissions import Permissions
from nimbo.core.cloud_provider.provider.services.storage import Storage


class Provider(abc.ABC, Instance, Permissions, Storage):
    ...
