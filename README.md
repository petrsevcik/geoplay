# GeoPlay

Configure Playwright browser profiles with geolocation settings based on country codes or IP addresses.

## Features

- Configure browser with **country code** (e.g., "cz", "de") or **IP address**
- Automatic geolocation via MaxMind GeoLite2 database
- Persistent browser profiles per country
- Anti-detection features

## Installation

```bash
# Install dependencies
uv sync

# Add MaxMind license key to .env
echo "GEO_IP_LICENCE_KEY=your_key" > .env

# Download GeoLite2 database
python geolite_suite.py
```

## Usage

### Country Code

```python
from playwright.sync_api import sync_playwright
from geo_factory import PlaywrightGeoFactory
from profile_manager import ProfileManager

with sync_playwright() as p:
    factory = PlaywrightGeoFactory("cz", profile_manager=ProfileManager())
    
    context = factory.create_persistent_context(
        playwright=p,
        profile_name="user_01",
        headless=False
    )
    
    page = context.new_page()
    page.goto("https://example.com")
    context.close()
```

### IP Address

```python
# Auto-detect location from IP
factory = PlaywrightGeoFactory("116.222.33.11", profile_manager=ProfileManager())
```

Run demo: `python main.py`
