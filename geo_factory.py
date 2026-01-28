"""
Geo configuration dataclass and factory for Playwright.
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from loguru import logger
from playwright.sync_api import Browser, BrowserContext, Playwright

from geolite_suite import get_ip_geolocation
from profile_manager import ProfileManager


@dataclass
class GeoConfig:
    """Configuration for browser geolocation"""

    timezone_id: str
    locale: str
    accept_language: str
    latitude: float
    longitude: float
    country_code: str


class PlaywrightGeoFactory:
    """Factory class for creating Playwright browser contexts with geolocation settings"""

    # Predefined configurations for different countries
    COUNTRY_CONFIGS = {
        "cz": GeoConfig(
            timezone_id="Europe/Prague",
            locale="cs-CZ",
            accept_language="cs-CZ,cs;q=0.9,en;q=0.8",
            latitude=50.0755,  # Prague
            longitude=14.4378,
            country_code="CZ",
        ),
        "de": GeoConfig(
            timezone_id="Europe/Berlin",
            locale="de-DE",
            accept_language="de-DE,de;q=0.9,en;q=0.8",
            latitude=52.5200,  # Berlin
            longitude=13.4050,
            country_code="DE",
        ),
        "en": GeoConfig(
            timezone_id="Europe/London",
            locale="en-GB",
            accept_language="en-GB,en;q=0.9",
            latitude=51.5074,  # London
            longitude=-0.1278,
            country_code="GB",
        ),
    }

    # Mapping of country codes to locale settings
    LOCALE_MAPPING = {
        "CZ": {"locale": "cs-CZ", "accept_language": "cs-CZ,cs;q=0.9,en;q=0.8"},
        "DE": {"locale": "de-DE", "accept_language": "de-DE,de;q=0.9,en;q=0.8"},
        "GB": {"locale": "en-GB", "accept_language": "en-GB,en;q=0.9"},
        "FR": {"locale": "fr-FR", "accept_language": "fr-FR,fr;q=0.9,en;q=0.8"},
        "US": {"locale": "en-US", "accept_language": "en-US,en;q=0.9"},
        "ES": {"locale": "es-ES", "accept_language": "es-ES,es;q=0.9,en;q=0.8"},
        "IT": {"locale": "it-IT", "accept_language": "it-IT,it;q=0.9,en;q=0.8"},
        "NL": {"locale": "nl-NL", "accept_language": "nl-NL,nl;q=0.9,en;q=0.8"},
        "PL": {"locale": "pl-PL", "accept_language": "pl-PL,pl;q=0.9,en;q=0.8"},
    }

    def __init__(
        self, identifier: str, profile_manager: Optional[ProfileManager] = None
    ):
        """
        Initialize factory with country code or IP address

        Args:
            identifier: Either a country code (e.g., "cz", "de", "en") or an IP address (e.g., "116.333.22.11")
            profile_manager: Optional ProfileManager instance for persistent contexts
        """
        # Check if identifier is an IP address
        if self._is_ip_address(identifier):
            self.config = self._create_config_from_ip(identifier)
        else:
            # Treat as country code
            identifier_lower = identifier.lower()
            if identifier_lower not in self.COUNTRY_CONFIGS:
                # Fallback to UK/GB configuration
                logger.warning(
                    f"Country code '{identifier}' not in predefined configs. "
                    f"Supported: {', '.join(self.COUNTRY_CONFIGS.keys())}. "
                    f"Falling back to UK (en) configuration."
                )
                identifier_lower = "en"  # Use UK as fallback
            self.config = self.COUNTRY_CONFIGS[identifier_lower]

        self.profile_manager = profile_manager

    @staticmethod
    def _is_ip_address(text: str) -> bool:
        """Check if string is a valid IP address"""
        ip_pattern = r"^(\d{1,3}\.){3}\d{1,3}$"
        return bool(re.match(ip_pattern, text))

    def _create_config_from_ip(self, ip_address: str) -> GeoConfig:
        """
        Create GeoConfig from IP address using GeoLite2 database

        Args:
            ip_address: IP address to query

        Returns:
            GeoConfig with settings from IP geolocation
        """
        geo_data = get_ip_geolocation(ip_address)

        if not geo_data:
            raise ValueError(
                f"Could not retrieve geolocation data for IP: {ip_address}"
            )

        # Get locale settings for this country (with fallback to English)
        country_code = geo_data["country_code"]
        locale_settings = self.LOCALE_MAPPING.get(
            country_code, {"locale": "en-US", "accept_language": "en-US,en;q=0.9"}
        )

        return GeoConfig(
            timezone_id=geo_data["timezone"],
            locale=locale_settings["locale"],
            accept_language=locale_settings["accept_language"],
            latitude=geo_data["latitude"],
            longitude=geo_data["longitude"],
            country_code=country_code,
        )

    def get_context_options(self) -> Dict[str, Any]:
        """
        Returns dictionary with settings for browser.new_context()

        Returns:
            Dict with configuration for Playwright context
        """
        return {
            "timezone_id": self.config.timezone_id,
            "locale": self.config.locale,
            "extra_http_headers": {"Accept-Language": self.config.accept_language},
            "geolocation": {
                "latitude": self.config.latitude,
                "longitude": self.config.longitude,
            },
            "permissions": ["geolocation"],
        }

    def create_context(self, browser: Browser) -> BrowserContext:
        """
        Creates new browser context with geolocation settings (non-persistent)

        Args:
            browser: Playwright Browser instance

        Returns:
            BrowserContext with configured geolocation
        """
        return browser.new_context(**self.get_context_options())

    def create_persistent_context(
        self,
        playwright: Playwright,
        profile_name: str = "user_01",
        headless: bool = False,
        clear_cookies: bool = False,
        **kwargs,
    ) -> BrowserContext:
        """
        Creates persistent browser context with geolocation settings.
        Loads existing profile if available, creates new one if not.

        Args:
            playwright: Playwright instance
            profile_name: Name of the profile (e.g., "user_01", "user_02")
            headless: Whether to run in headless mode
            clear_cookies: Clear cookies/storage before launching (helps avoid geo mismatches)
            **kwargs: Additional arguments to pass to launch_persistent_context

        Returns:
            BrowserContext with configured geolocation and persistent profile
        """
        if not self.profile_manager:
            raise ValueError(
                "ProfileManager not provided. Initialize factory with profile_manager argument."
            )

        # Get profile path
        profile_path = self.profile_manager.get_profile_path(
            self.config.country_code, profile_name
        )

        # Optionally clear profile cookies/storage to avoid geo mismatches
        if clear_cookies and profile_path.exists():
            logger.info(f"Clearing cookies/storage from profile: {profile_path}")
            self._clear_profile_data(profile_path)

        # Anti-detection arguments
        anti_detection_args = [
            "--disable-blink-features=AutomationControlled",  # Hide automation
        ]

        # Prepare context options
        context_options = {
            "user_data_dir": str(profile_path),
            "headless": headless,
            "locale": self.config.locale,
            "timezone_id": self.config.timezone_id,
            "geolocation": {
                "latitude": self.config.latitude,
                "longitude": self.config.longitude,
            },
            "permissions": ["geolocation"],
            "args": anti_detection_args,
            **kwargs,
        }

        # Launch persistent context
        context = playwright.chromium.launch_persistent_context(**context_options)

        # Additional anti-detection: Remove webdriver flag
        context.add_init_script(
            """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """
        )

        return context

    @staticmethod
    def _clear_profile_data(profile_path: Path) -> None:
        """
        Clear cookies and storage from profile to avoid geo mismatches.
        Keeps the profile structure but removes session data.

        Args:
            profile_path: Path to the profile directory
        """
        import shutil

        # Files/folders to clear (common browser profile artifacts)
        patterns_to_clear = [
            "Cookies",
            "Cookies-journal",
            "Local Storage",
            "Session Storage",
            "IndexedDB",
            "Service Worker",
            "Cache",
            "Code Cache",
        ]

        for item in profile_path.rglob("*"):
            if item.is_file() or item.is_dir():
                if any(pattern in item.name for pattern in patterns_to_clear):
                    try:
                        if item.is_file():
                            item.unlink()
                        elif item.is_dir():
                            shutil.rmtree(item)
                    except Exception as e:
                        logger.debug(f"Could not clear {item}: {e}")
