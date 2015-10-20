
import pkg_resources
pkg_resources.declare_namespace(__name__)

from client import (
    RestClient,
    TypeWrap,
    NotFoundException,
    PermissionDeniedException,
    InvalidRequestException
)

