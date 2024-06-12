import asyncio


class LuxosBaseException(Exception):
    pass


class MinerConnectionError(LuxosBaseException):
    def __init__(self, host: str, port: int, *args, **kwargs):
        super().__init__(host, port, *args, **kwargs)
        self.address = (host, port)

    def __str__(self):
        msg = "unknown reason"
        if getattr(self, "__cause__"):
            msg = repr(self.__cause__)
        elif self.args[2:]:
            msg = str(self.args[2])
        return (
            f"<{self.address[0]}:{self.address[1]}>: {self.__class__.__name__}, "
            f"{msg}"
        )


class MinerCommandTimeoutError(MinerConnectionError, asyncio.TimeoutError):
    pass


class MinerCommandSessionAlreadyActive(MinerConnectionError):
    pass


class MinerCommandMalformedMessageError(MinerConnectionError):
    pass


class LuxosLaunchError(MinerConnectionError):
    def __init__(self, tback: str, host: str, port: int, *args, **kwargs):
        self.tback = tback
        super().__init__(host, port, *args, **kwargs)

    def __str__(self):
        from .text import indent

        msg = indent(str(self.tback), "| ")
        return f"{self.address}: \n{msg}"


class LuxosLaunchTimeoutError(LuxosLaunchError, asyncio.TimeoutError):
    pass
