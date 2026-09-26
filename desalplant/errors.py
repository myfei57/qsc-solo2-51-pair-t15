"""Errors raised when a staged line contract is violated.

Every failure mode of the control service is expressed as one of these types so
that the HTTP console can map a violation onto a status code without inspecting
free-form messages.
"""


class ContractError(Exception):
    """Base class for every contract violation raised by the service."""


class FlowNotReadyError(ContractError):
    """Raised when pressure is requested before the feed flow is confirmed."""


class MembraneCrackedError(ContractError):
    """Raised when a membrane was pressurised below its minimum flow."""


class FlushNotEffectiveError(ContractError):
    """Raised when a pump stop is attempted without an effective flush."""


class PumpAlreadyStoppedError(ContractError):
    """Raised when a flush is demanded while the pump is not running."""


class ValveNotOpenError(ContractError):
    """Raised when the brine path is not open before a pressure ramp."""


class FeedAlreadyStoppedError(ContractError):
    """Raised when a feed shutdown is started after the feed has stopped."""


class ResidualAntiscalantError(ContractError):
    """Raised when residual antiscalant is left to scale the membrane."""


class PermeateRejectedError(ContractError):
    """Raised when a tank fill is attempted with rejected permeate."""


class SupplyInterruptedError(ContractError):
    """Raised when the supply count drops to zero during a tank handoff."""


class HandoffIncompleteError(ContractError):
    """Raised when a tank handoff finished without opening the standby tank."""


class AlarmNotActiveError(ContractError):
    """Raised when a recovery latch is cleared while it is not raised."""


class InvalidEfficiencyError(ContractError):
    """Raised when a pump efficiency factor falls outside its band."""


class InvalidStagesError(ContractError):
    """Raised when a membrane array is regrouped onto a non-positive stage count."""


class TransferFailedError(ContractError):
    """Raised when a tank transfer names an unknown endpoint or a bad amount."""


class RinseFailedError(ContractError):
    """Raised when a rack rinse completes without clearing the rack."""


class MediaNotReadyError(ContractError):
    """Raised when filtration is demanded before a media backwash."""


class UnknownKeyError(ContractError):
    """Raised when a committed value is required but the key was never written."""


class StoreError(ContractError):
    """Raised when the file-backed store cannot persist a write."""
