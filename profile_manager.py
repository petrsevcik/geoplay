"""
Profile manager for persistent Playwright browser contexts.
"""

from pathlib import Path
from typing import Optional

from loguru import logger


class ProfileManager:
    """Manages persistent browser profiles for different countries"""

    def __init__(self, base_dir: str = "playwright_profiles"):
        """
        Initialize profile manager.

        Args:
            base_dir: Base directory for storing profiles
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)

    def get_profile_path(
        self, country_code: str, profile_name: str = "user_01"
    ) -> Path:
        """
        Get path to a profile directory, creating it if necessary.

        Args:
            country_code: Country code (e.g., "CZ", "DE", "GB")
            profile_name: Profile name (e.g., "user_01", "user_02")

        Returns:
            Path to the profile directory
        """
        profile_path = self.base_dir / country_code.upper() / profile_name

        if profile_path.exists():
            logger.info(f"Loading existing profile: {profile_path}")
        else:
            logger.info(f"Creating new profile: {profile_path}")
            profile_path.mkdir(parents=True, exist_ok=True)

        return profile_path

    def profile_exists(self, country_code: str, profile_name: str = "user_01") -> bool:
        """
        Check if a profile already exists.

        Args:
            country_code: Country code (e.g., "CZ", "DE", "GB")
            profile_name: Profile name (e.g., "user_01", "user_02")

        Returns:
            True if profile exists, False otherwise
        """
        profile_path = self.base_dir / country_code.upper() / profile_name
        return profile_path.exists()

    def list_profiles(self, country_code: Optional[str] = None) -> dict:
        """
        List all profiles, optionally filtered by country.

        Args:
            country_code: Optional country code to filter by

        Returns:
            Dictionary of country_code -> list of profile names
        """
        profiles = {}

        if country_code:
            # List profiles for specific country
            country_dir = self.base_dir / country_code.upper()
            if country_dir.exists():
                profiles[country_code.upper()] = [
                    p.name for p in country_dir.iterdir() if p.is_dir()
                ]
        else:
            # List all profiles
            for country_dir in self.base_dir.iterdir():
                if country_dir.is_dir():
                    profiles[country_dir.name] = [
                        p.name for p in country_dir.iterdir() if p.is_dir()
                    ]

        return profiles

    def delete_profile(self, country_code: str, profile_name: str = "user_01") -> bool:
        """
        Delete a profile.

        Args:
            country_code: Country code (e.g., "CZ", "DE", "GB")
            profile_name: Profile name (e.g., "user_01", "user_02")

        Returns:
            True if deleted successfully, False if profile didn't exist
        """
        profile_path = self.base_dir / country_code.upper() / profile_name

        if not profile_path.exists():
            logger.warning(f"Profile does not exist: {profile_path}")
            return False

        try:
            # Remove all files in the profile directory
            import shutil

            shutil.rmtree(profile_path)
            logger.info(f"Deleted profile: {profile_path}")
            return True
        except Exception as e:
            logger.error(f"Error deleting profile {profile_path}: {e}")
            return False
