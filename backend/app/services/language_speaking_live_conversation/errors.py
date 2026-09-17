"""Structured live conversation runtime errors (S7.5)."""


class SpeakingLiveRuntimeError(Exception):
    code: str = "live_runtime_error"

    def __init__(self, message: str, *, detail: str = "") -> None:
        self.detail = detail
        super().__init__(message)


class LiveProviderUnavailableError(SpeakingLiveRuntimeError):
    code = "live_provider_unavailable"


class LiveAuthenticationFailedError(SpeakingLiveRuntimeError):
    code = "live_authentication_failed"


class LiveConfigurationInvalidError(SpeakingLiveRuntimeError):
    code = "live_configuration_invalid"


class LiveConnectionFailedError(SpeakingLiveRuntimeError):
    code = "live_connection_failed"


class LiveConnectionClosedError(SpeakingLiveRuntimeError):
    code = "live_connection_closed"


class LiveProtocolError(SpeakingLiveRuntimeError):
    code = "live_protocol_error"


class LiveAudioFormatInvalidError(SpeakingLiveRuntimeError):
    code = "live_audio_format_invalid"


class LiveTurnTooLargeError(SpeakingLiveRuntimeError):
    code = "live_turn_too_large"


class LiveTurnTimeoutError(SpeakingLiveRuntimeError):
    code = "live_turn_timeout"


class LiveTurnFinalizationFailedError(SpeakingLiveRuntimeError):
    code = "live_turn_finalization_failed"


class LiveEvaluationHandoffFailedError(SpeakingLiveRuntimeError):
    code = "live_evaluation_handoff_failed"


class LiveReconnectFailedError(SpeakingLiveRuntimeError):
    code = "live_reconnect_failed"
