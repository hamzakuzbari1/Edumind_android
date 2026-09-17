"""Provider-local live conversation errors (S7.5) — translated at runtime/API boundary."""


class SpeakingProviderLiveError(Exception):
    code: str = "live_runtime_error"

    def __init__(self, message: str, *, detail: str = "") -> None:
        self.detail = detail
        super().__init__(message)


class ProviderLiveUnavailableError(SpeakingProviderLiveError):
    code = "live_provider_unavailable"


class ProviderLiveAuthenticationFailedError(SpeakingProviderLiveError):
    code = "live_authentication_failed"


class ProviderLiveConfigurationInvalidError(SpeakingProviderLiveError):
    code = "live_configuration_invalid"


class ProviderLiveConnectionFailedError(SpeakingProviderLiveError):
    code = "live_connection_failed"


class ProviderLiveConnectionClosedError(SpeakingProviderLiveError):
    code = "live_connection_closed"


class ProviderLiveProtocolError(SpeakingProviderLiveError):
    code = "live_protocol_error"
