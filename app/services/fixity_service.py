import hashlib
from datetime import datetime
from typing import BinaryIO
from app.models.metadata import FixityInfo, FixityAlgorithm


class FixityService:
    """
    Service for calculating and verifying file checksums for integrity checking.
    Implements stream-based processing to avoid loading entire files into memory.
    """

    # Chunk size for reading files (8MB chunks)
    CHUNK_SIZE = 8 * 1024 * 1024

    def __init__(self):
        pass

    async def calculate_checksums(
        self, file_stream: BinaryIO, algorithms: list[FixityAlgorithm] | None = None
    ) -> dict[str, str]:
        """
        Calculate checksums for a file stream using specified algorithms.
        Stream-based processing to handle large files efficiently.

        Args:
            file_stream: Binary file stream to calculate checksums for
            algorithms: List of algorithms to use (defaults to MD5 and SHA-256)

        Returns:
            Dictionary mapping algorithm names to checksum values
        """
        if algorithms is None:
            algorithms = [FixityAlgorithm.MD5, FixityAlgorithm.SHA256]

        # Initialize hash objects
        hashers = {}
        for algo in algorithms:
            if algo == FixityAlgorithm.MD5:
                hashers["md5"] = hashlib.md5()
            elif algo == FixityAlgorithm.SHA256:
                hashers["sha256"] = hashlib.sha256()
            elif algo == FixityAlgorithm.SHA512:
                hashers["sha512"] = hashlib.sha512()

        # Read file in chunks and update all hashers
        while True:
            chunk = file_stream.read(self.CHUNK_SIZE)
            if not chunk:
                break
            for hasher in hashers.values():
                hasher.update(chunk)

        # Return hexadecimal digest for each algorithm
        return {name: hasher.hexdigest() for name, hasher in hashers.items()}

    def calculate_checksums_sync(
        self, file_stream: BinaryIO, algorithms: list[FixityAlgorithm] | None = None
    ) -> dict[str, str]:
        """
        Synchronous version of calculate_checksums for compatibility.

        Args:
            file_stream: Binary file stream to calculate checksums for
            algorithms: List of algorithms to use (defaults to MD5 and SHA-256)

        Returns:
            Dictionary mapping algorithm names to checksum values
        """
        if algorithms is None:
            algorithms = [FixityAlgorithm.MD5, FixityAlgorithm.SHA256]

        # Initialize hash objects
        hashers = {}
        for algo in algorithms:
            if algo == FixityAlgorithm.MD5:
                hashers["md5"] = hashlib.md5()
            elif algo == FixityAlgorithm.SHA256:
                hashers["sha256"] = hashlib.sha256()
            elif algo == FixityAlgorithm.SHA512:
                hashers["sha512"] = hashlib.sha512()

        # Read file in chunks and update all hashers
        while True:
            chunk = file_stream.read(self.CHUNK_SIZE)
            if not chunk:
                break
            for hasher in hashers.values():
                hasher.update(chunk)

        # Return hexadecimal digest for each algorithm
        return {name: hasher.hexdigest() for name, hasher in hashers.items()}

    def generate_fixity_info(self, checksums: dict[str, str]) -> FixityInfo:
        """
        Generate a FixityInfo object from calculated checksums.

        Args:
            checksums: Dictionary of algorithm:checksum pairs

        Returns:
            FixityInfo object with checksums and metadata

        Raises:
            FixityServiceError: If required checksums are missing
        """
        if "md5" not in checksums or "sha256" not in checksums:
            raise FixityServiceError(
                "Both MD5 and SHA-256 checksums are required for FixityInfo"
            )

        algorithms = []
        if "md5" in checksums:
            algorithms.append(FixityAlgorithm.MD5)
        if "sha256" in checksums:
            algorithms.append(FixityAlgorithm.SHA256)
        if "sha512" in checksums:
            algorithms.append(FixityAlgorithm.SHA512)

        return FixityInfo(
            checksum_md5=checksums["md5"],
            checksum_sha256=checksums["sha256"],
            algorithm=algorithms,
            calculated_at=datetime.utcnow(),
        )

    def verify_checksums(
        self, expected: dict[str, str], actual: dict[str, str]
    ) -> tuple[bool, list[str]]:
        """
        Verify that calculated checksums match expected values.

        Args:
            expected: Dictionary of expected checksums
            actual: Dictionary of actual calculated checksums

        Returns:
            Tuple of (all_match: bool, mismatches: list[str])
        """
        mismatches = []

        for algo, expected_value in expected.items():
            if algo not in actual:
                mismatches.append(f"{algo}: not calculated")
            elif actual[algo] != expected_value:
                mismatches.append(
                    f"{algo}: expected {expected_value}, got {actual[algo]}"
                )

        return len(mismatches) == 0, mismatches

    async def calculate_file_checksums(
        self, file_path: str, algorithms: list[FixityAlgorithm] | None = None
    ) -> dict[str, str]:
        """
        Calculate checksums for a file at the given path.

        Args:
            file_path: Path to the file
            algorithms: List of algorithms to use

        Returns:
            Dictionary mapping algorithm names to checksum values

        Raises:
            FixityServiceError: If file cannot be read
        """
        try:
            with open(file_path, "rb") as f:
                return await self.calculate_checksums(f, algorithms)
        except FileNotFoundError:
            raise FixityServiceError(f"File not found: {file_path}")
        except PermissionError:
            raise FixityServiceError(f"Permission denied: {file_path}")
        except Exception as e:
            raise FixityServiceError(f"Error calculating checksums: {str(e)}")


class FixityServiceError(Exception):
    """Exception raised by FixityService"""

    pass
