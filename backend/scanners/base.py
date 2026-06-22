from abc import ABC, abstractmethod
from typing import Any


class ScannerError(Exception):
    """Base class for scanner failures."""


class CLINotInstalledError(ScannerError):
    """Raised when a cloud CLI is not available on PATH."""


class NotLoggedInError(ScannerError):
    """Raised when CLI authentication is missing."""


class ScopeNotFoundError(ScannerError):
    """Raised when requested scope/resource group is invalid."""


class CloudScanner(ABC):
    @abstractmethod
    def list_scopes(self) -> list[dict[str, Any]]:
        """Return available scopes for the cloud provider."""

    @abstractmethod
    def list_resources(self, scope: str) -> list[dict[str, Any]]:
        """Return resources for a given scope in normalized shape."""
