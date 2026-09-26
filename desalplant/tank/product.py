"""Product tank that only fills with accepted permeate."""

from ..errors import PermeateRejectedError
from ..ro.permeate import Permeate


class ProductTank:
    """Product tank with a filling and a dumping state."""

    def __init__(self) -> None:
        self.filling = False
        self.dumping = False

    def fill(self, permeate: Permeate) -> None:
        """Accept permeate, or divert it to the dump while the latch is set."""
        if permeate.rejecting_now() or not permeate.conductivity_normal() or not permeate.recovered():
            self.dumping = True
            self.filling = False
            raise PermeateRejectedError("permeate rejected")
        self.filling = True
        self.dumping = False
