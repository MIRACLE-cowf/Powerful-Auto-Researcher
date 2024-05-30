

class PAR_ERROR(Exception):
    """
    Custom exception class for PAR project errors.

    This exception is raised when there is an error related to PAR (Parameter).
    It inherits from the built-in Exception class.

    Attributes:
        message (str): The error message associated with the exception.
    """
    def __init__(self, message: str):
        self.message = message


class PAR_SUCCESS:
    """
    Represents a successful result of a PAR operation.

    :param result: The result of the PAR operation.
    """
    def __init__(self, result: any):
        self.result = result


