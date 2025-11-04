"""
Globus SDK integration for archive storage.
Handles authentication, file queries, and verification.
"""

from globus_sdk import (
    ConfidentialAppAuthClient,
    TransferClient,
    ClientCredentialsAuthorizer,
    TransferAPIError,
)
from app.config.settings import Settings
import logging

logger = logging.getLogger(__name__)


class GlobusService:
    """Service for interacting with Globus storage"""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.endpoint_id = settings.globus.endpoint_id
        self.base_path = settings.globus.base_path
        self.client = self._get_transfer_client()

    def _get_transfer_client(self) -> TransferClient:
        """Initialize authenticated Globus Transfer Client"""
        if not self.settings.globus.enabled:
            raise GlobusServiceError("Globus is not enabled in settings")

        if not self.settings.globus.client_id or not self.settings.globus.client_secret:
            raise GlobusServiceError("Globus client_id and client_secret are required")

        try:
            # Use confidential app authentication (client credentials flow)
            auth_client = ConfidentialAppAuthClient(
                client_id=self.settings.globus.client_id,
                client_secret=self.settings.globus.client_secret,
            )

            # Get client credentials authorizer
            scopes = "urn:globus:auth:scope:transfer.api.globus.org:all"
            cc_authorizer = ClientCredentialsAuthorizer(auth_client, scopes)

            # Create transfer client
            transfer_client = TransferClient(authorizer=cc_authorizer)

            logger.info("Globus Transfer Client initialized successfully")
            return transfer_client

        except Exception as e:
            logger.error(f"Failed to initialize Globus client: {e}")
            raise GlobusServiceError(f"Globus authentication failed: {str(e)}")

    async def list_directory(self, path: str) -> list[dict]:
        """
        List files in a Globus directory.

        Args:
            path: Path relative to base_path or absolute path

        Returns:
            List of file dictionaries with name, size, type, modify_time
        """
        try:
            # Build full path
            full_path = path if path.startswith("/") else f"{self.base_path}{path}"

            # Use operation_ls to list directory
            response = self.client.operation_ls(
                self.endpoint_id,
                path=full_path,
            )

            files = []
            for item in response:
                files.append({
                    "name": item["name"],
                    "type": item["type"],  # "file" or "dir"
                    "size": item.get("size", 0),
                    "modify_time": item.get("last_modified"),
                })

            logger.info(f"Listed {len(files)} items in {full_path}")
            return files

        except TransferAPIError as e:
            logger.error(f"Failed to list directory {path}: {e}")
            raise GlobusServiceError(f"Failed to list directory: {str(e)}")

    async def get_file_info(self, path: str) -> dict:
        """
        Get metadata for a specific file.

        Args:
            path: Full path to file or relative to base_path

        Returns:
            File metadata (size, modify_time, type, etc.)
        """
        try:
            # Build full path
            full_path = path if path.startswith("/") else f"{self.base_path}{path}"

            # Use operation_stat to get file info
            response = self.client.operation_stat(
                self.endpoint_id,
                path=full_path,
            )

            file_info = {
                "name": response["name"],
                "type": response["type"],
                "size": response.get("size", 0),
                "modify_time": response.get("last_modified"),
                "permissions": response.get("permissions"),
            }

            logger.info(f"Retrieved file info for {full_path}")
            return file_info

        except TransferAPIError as e:
            # Log 404s at debug level (often expected when checking existence)
            # Log other errors at error level
            if "404" in str(e) or "NotFound" in str(e):
                logger.debug(f"Path not found: {path}")
            else:
                logger.error(f"Failed to get file info for {path}: {e}")
            raise GlobusServiceError(f"Failed to get file info: {str(e)}")

    async def verify_path_exists(self, path: str) -> bool:
        """Check if a path exists in Globus storage"""
        try:
            await self.get_file_info(path)
            return True
        except GlobusServiceError:
            return False

    async def calculate_directory_size(self, path: str) -> int:
        """
        Calculate total size of files in a directory.

        Args:
            path: Directory path

        Returns:
            Total size in bytes
        """
        try:
            files = await self.list_directory(path)
            total_size = 0

            for item in files:
                if item["type"] == "file":
                    total_size += item.get("size", 0)
                elif item["type"] == "dir":
                    # Recursively calculate subdirectory size
                    subdir_path = f"{path}/{item['name']}" if not path.endswith("/") else f"{path}{item['name']}"
                    total_size += await self.calculate_directory_size(subdir_path)

            logger.info(f"Calculated directory size for {path}: {total_size} bytes")
            return total_size

        except Exception as e:
            logger.error(f"Failed to calculate directory size for {path}: {e}")
            raise GlobusServiceError(f"Failed to calculate directory size: {str(e)}")

    async def create_directory(self, path: str, create_parents: bool = True) -> bool:
        """
        Create a directory in Globus storage.

        Args:
            path: Directory path to create
            create_parents: If True, create parent directories as needed (like mkdir -p)

        Returns:
            True if created successfully or already exists
        """
        try:
            # Build full path
            full_path = path if path.startswith("/") else f"{self.base_path}{path}"

            # Check if directory already exists
            try:
                info = await self.get_file_info(full_path)
                if info["type"] == "dir":
                    logger.info(f"Directory already exists: {full_path}")
                    return True
            except GlobusServiceError:
                # Directory doesn't exist, create it
                pass

            # Create parent directories if needed
            if create_parents:
                parent_path = "/".join(full_path.rstrip("/").split("/")[:-1])
                if parent_path and parent_path != "/":
                    await self._ensure_parent_directories(parent_path)

            # Use operation_mkdir to create directory
            self.client.operation_mkdir(
                self.endpoint_id,
                path=full_path,
            )

            logger.info(f"Created directory: {full_path}")
            return True

        except TransferAPIError as e:
            # Check if error is because directory already exists
            if "exists" in str(e).lower() or "file exists" in str(e).lower():
                logger.info(f"Directory already exists: {full_path}")
                return True

            logger.error(f"Failed to create directory {path}: {e}")
            raise GlobusServiceError(f"Failed to create directory: {str(e)}")

    async def _ensure_parent_directories(self, path: str) -> None:
        """
        Recursively ensure all parent directories exist.

        Args:
            path: Full directory path to ensure exists
        """
        # Check if path exists
        try:
            info = await self.get_file_info(path)
            if info["type"] == "dir":
                return  # Already exists
        except GlobusServiceError:
            pass  # Doesn't exist, need to create

        # Get parent path
        parent_path = "/".join(path.rstrip("/").split("/")[:-1])

        # Recursively ensure parent exists (but stop at root)
        if parent_path and parent_path != "/":
            await self._ensure_parent_directories(parent_path)

        # Create this directory
        try:
            self.client.operation_mkdir(self.endpoint_id, path=path)
            logger.info(f"Created parent directory: {path}")
        except TransferAPIError as e:
            # Ignore if already exists
            if "exists" not in str(e).lower() and "file exists" not in str(e).lower():
                raise

    async def check_required_files(self, path: str, required_files: list[str]) -> dict[str, bool]:
        """
        Check if required files exist in a directory.

        Args:
            path: Directory path
            required_files: List of required filenames

        Returns:
            Dictionary mapping filenames to existence status
        """
        try:
            files = await self.list_directory(path)
            file_names = {f["name"] for f in files if f["type"] == "file"}

            results = {filename: filename in file_names for filename in required_files}

            logger.info(f"Checked required files in {path}: {results}")
            return results

        except Exception as e:
            logger.error(f"Failed to check required files in {path}: {e}")
            raise GlobusServiceError(f"Failed to check required files: {str(e)}")


class GlobusServiceError(Exception):
    """Globus service exceptions"""
    pass
