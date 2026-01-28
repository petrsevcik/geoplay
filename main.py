"""
Main demo script for GeoPlay - Playwright with geolocation.
"""

from loguru import logger
from playwright.sync_api import Page
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from geo_factory import PlaywrightGeoFactory
from profile_manager import ProfileManager


def accept_cookies(page: Page, timeout: int = 5000) -> bool:
    """
    Try to accept cookie consent popup if present.

    Args:
        page: Playwright Page instance
        timeout: How long to wait for the button (in ms)

    Returns:
        True if cookies were accepted, False if popup not found
    """
    try:
        # Try multiple selectors (sites use different IDs/classes)
        selectors = [
            "button#accept",  # Notino
            'button[data-action-type="accept"]',
            "button.uc-accept-button",
        ]

        for selector in selectors:
            try:
                button = page.locator(selector).first
                if button.is_visible(timeout=timeout):
                    logger.info(f"Found cookie consent button: {selector}")
                    button.click()
                    logger.success("✅ Cookie consent accepted")
                    page.wait_for_timeout(1000)  # Wait for popup to close
                    return True
            except PlaywrightTimeoutError:
                continue

        logger.debug("No cookie consent popup found (might be already accepted)")
        return False

    except Exception as e:
        logger.debug(f"Error handling cookie consent: {e}")
        return False


def scrape_notino_with_profiles():
    """
    Scrape Notino websites using persistent profiles with geolocation.

    - notino.cz → CZ profile (country code "cz")
    - notino.de → DE profile (IP address from Hetzner server)
    - notino.fr → FR profile (IP address from French proxy)
    """

    logger.info("=" * 60)
    logger.info("Notino Scraper with Geo Profiles")
    logger.info("=" * 60)

    # Create profile manager
    profile_mgr = ProfileManager()

    # Define scraping targets with their geo identifiers
    targets = [
        {
            "site": "notino.cz",
            "url": "https://www.notino.cz/",
            "identifier": "cz",
            "profile": "user_01",
            "method": "country code",
        },
        {
            "site": "notino.de",
            "url": "https://www.notino.de/",
            "identifier": "116.203.33.18",  # IP address (Hetzner DE)
            "profile": "user_01",
            "method": "IP address",
        },
        {
            "site": "notino.fr",
            "url": "https://www.notino.fr/",
            "identifier": "92.204.164.15",  # IP address (French proxy)
            "profile": "user_01",
            "method": "IP address",
        },
        {
            "site": "notino.pl",
            "url": "https://www.notino.pl/",
            "identifier": "pl",
            "profile": "user_01",
            "method": "IP address",
        },
    ]

    with sync_playwright() as p:
        for target in targets:
            logger.info(f" Scraping: {target['site']}")
            logger.info(f" Method: {target['method']} ({target['identifier']})")

            # Create factory with profile manager
            factory = PlaywrightGeoFactory(
                target["identifier"], profile_manager=profile_mgr
            )

            config = factory.config
            logger.info(f"   Country: {config.country_code}")
            logger.info(f"   Timezone: {config.timezone_id}")
            logger.info(f"   Locale: {config.locale}")
            logger.info(
                f"   Coordinates: {config.latitude:.4f}, {config.longitude:.4f}"
            )

            # Create persistent context (will create or load profile)
            # Set clear_cookies=True to avoid geo mismatches from previous sessions
            context = factory.create_persistent_context(
                playwright=p,
                profile_name=target["profile"],
                headless=False,
                clear_cookies=True,
            )

            # Get or create page
            page = context.pages[0] if context.pages else context.new_page()

            logger.info(f"Navigating to {target['url']}...")
            page.goto(target["url"], wait_until="domcontentloaded")

            # Wait for page to load
            page.wait_for_timeout(2_000)

            # Try to accept cookie consent if present
            accept_cookies(page)

            # Extract some basic info
            try:
                title = page.title()
                url = page.url
                logger.success("Page loaded successfully")
                logger.info(f"Title: {title}")
                logger.info(f"URL: {url}")

                # Check if we can detect the language/country indicator
                # Most sites have some indicator in the HTML
                html_lang = page.locator("html").get_attribute("lang")
                if html_lang:
                    logger.info(f"HTML lang: {html_lang}")

            except Exception as e:
                logger.error(f"Error extracting page info: {e}")

            # Keep page open a bit longer so you can see it
            page.wait_for_timeout(3_000)

            # Close context
            context.close()
            logger.success(f"Completed scraping {target['site']}")

    # Show existing profiles
    logger.info("Created/Updated Profiles:")
    profiles = profile_mgr.list_profiles()
    for country_code, profile_list in profiles.items():
        logger.info(f"   {country_code}: {', '.join(profile_list)}")

    logger.success("All scraping completed!")


if __name__ == "__main__":
    # Run Notino scraper with persistent profiles
    scrape_notino_with_profiles()
    logger.success("All demos completed!")
