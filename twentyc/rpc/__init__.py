
import pkg_resources
pkg_resources.declare_namespace(__name__)

# namespace imports
from client import ( # noqa
    RestClient,
    TypeWrap,
    NotFoundException,
    PermissionDeniedException,
    InvalidRequestException
)

