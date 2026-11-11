class ApplicationError(Exception):
    code = "INTERNAL_ERROR"
    def __init__(self, message: str, data=None): self.message, self.data = message, dict(data or {})
class NotFound(ApplicationError): code = "NOT_FOUND"
class ResyncRequired(ApplicationError): code = "RESYNC_REQUIRED"
class InvalidSource(ApplicationError): code = "INVALID_SOURCE"
class NotComparable(ApplicationError): code = "NOT_COMPARABLE"
