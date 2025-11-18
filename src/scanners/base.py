"""Base scanner class."""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from datetime import datetime


class BaseScanner(ABC):
    """Base class for all infrastructure scanners."""

    def __init__(self, config: Any):
        """Initialize scanner.

        Args:
            config: Configuration object
        """
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.errors: List[str] = []

    @abstractmethod
    async def scan(self, *args, **kwargs) -> Any:
        """Perform the scan operation.

        Returns:
            Scan results
        """
        pass

    def add_error(self, error: str) -> None:
        """Add an error to the error list.

        Args:
            error: Error message
        """
        self.logger.error(error)
        self.errors.append(error)

    def clear_errors(self) -> None:
        """Clear the error list."""
        self.errors = []

    def get_errors(self) -> List[str]:
        """Get all errors encountered during scanning.

        Returns:
            List of error messages
        """
        return self.errors.copy()

    def has_errors(self) -> bool:
        """Check if any errors occurred.

        Returns:
            bool: True if errors occurred
        """
        return len(self.errors) > 0

    async def safe_scan(self, *args, **kwargs) -> Optional[Any]:
        """Safely execute scan with error handling.

        Returns:
            Scan results or None if errors occurred
        """
        try:
            return await self.scan(*args, **kwargs)
        except Exception as e:
            self.add_error(f"Scan failed: {str(e)}")
            return None

    def get_scan_metadata(self) -> Dict[str, Any]:
        """Get metadata about the scan.

        Returns:
            Dictionary with scan metadata
        """
        return {
            "scanner": self.__class__.__name__,
            "timestamp": datetime.now().isoformat(),
            "errors": self.errors,
            "error_count": len(self.errors),
        }
