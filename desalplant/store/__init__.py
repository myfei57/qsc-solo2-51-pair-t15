"""File-backed key space with stable encoding and content digests."""

from . import keys
from .store import Store

__all__ = ["Store", "keys"]
