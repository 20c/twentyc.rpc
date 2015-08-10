
__import__('pkg_resources').declare_namespace(__name__)

from client import (
    RestClient, 
    NotFoundException,
    PermissionDeniedException,
    InvalidRequestException
)

