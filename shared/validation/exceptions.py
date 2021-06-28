class InvalidYamlException(Exception):
    def __init__(
        self, error_location, error_message, error_dict=None, original_exc=None
    ):
        self.error_location = error_location
        self.error_message = error_message
        self.error_dict = error_dict
        self.original_exc = original_exc
