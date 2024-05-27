import asyncio


class LuxosBaseException(Exception):
    pass


class MinerConnectionError(LuxosBaseException):
    def __init__(self, host: str, port: int, *args, **kwargs):
        super().__init__(host, port, *args, **kwargs)
        self.address = (host, port)

    def __str__(self):
        return (
            f"<{self.address[0]}:{self.address[1]}>: {self.__class__.__name__}, "
            f"{self.args[2] if self.args[2:] else 'unknown reason'}"
        )


class MinerCommandSessionAlreadyActive(MinerConnectionError):
    pass


class MinerCommandTimeoutError(MinerConnectionError, asyncio.TimeoutError):
    pass


class MinerCommandMalformedMessageError(MinerConnectionError):
    pass
