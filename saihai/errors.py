class SaihaiError(Exception):
    def __init__(self, message: str) -> None:
        Exception.__init__(self, message)
        self.message = message


class CommandDefinitionError(SaihaiError):
    pass


class CommandError(SaihaiError):
    def __init__(self, message: str, *, code: int) -> None:
        SaihaiError.__init__(self, message)
        self.code = code


class CommandHelpError(CommandError):
    def __init__(self, message: str, *, code: int = 1) -> None:
        CommandError.__init__(self, message, code=code)


class CommandUsageError(CommandError):
    def __init__(self, message: str, *, code: int = 2) -> None:
        CommandError.__init__(self, message, code=code)
