class LuxosBaseExceptio(Exception):
    pass


class MinerMalformedMessageError(LuxosBaseExceptio):
    pass


class MinerSessionAlreadyActive(LuxosBaseExceptio):
    pass