#!/usr/bin/env python3
"""
Scraper for 4camping.cz product pages to extract JavaScript var data.
"""

import json
import re
from pathlib import Path

from curl_cffi import requests
from loguru import logger


def scrape_4camping_product(url: str, output_file: str = "4camping_data.json") -> dict:
    """
    Scrape a 4camping.cz product page and extract JavaScript var data.

    Args:
        url: The product page URL to scrape
        output_file: Path to save the extracted JSON data

    Returns:
        dict: The extracted JavaScript var data
    """
    logger.info(f"Fetching page: {url}")

    try:
        # Use curl_cffi with browser impersonation to avoid detection
        response = requests.get(url, impersonate="chrome", timeout=30)
        response.raise_for_status()
        logger.info(f"Successfully fetched page (status: {response.status_code})")

        html_content = response.text

        # Pattern to match: var data = {...}
        pattern = r"<script>\s*//<!--\s*var data\s*=\s*(\{.*?\});"
        match = re.search(pattern, html_content, re.DOTALL)

        if not match:
            logger.warning("No 'var data' found in the page")
            # Try alternative pattern without comment
            pattern = r"var data\s*=\s*(\{.*?\});"
            match = re.search(pattern, html_content, re.DOTALL)

        if not match:
            logger.error("Could not find 'var data' declaration in the page")
            return {}

        # Parse the JSON data
        json_str = match.group(1)
        data = json.loads(json_str)

        logger.info("Successfully parsed data")


        print("\n" + "=" * 60)
        print("VARIANT URLS")
        print("=" * 60)


        for variant_id, variant_data in data["variantsInfo"].items():
            if "url" in variant_data:
                full_url = f"https://www.4camping.cz{variant_data['url']}"
                print(full_url)



        # Print last variant info as example
        print("\n" + "=" * 60)
        print(f"FIRST VARIANT EXAMPLE (ID: {variant_id})")
        print("=" * 60)
        print(json.dumps(variant_data, indent=2, ensure_ascii=False))
        print("=" * 60 + "\n")

        output_path = Path(output_file)
        with output_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.success(f"Saved data to {output_file}")
        return data

    except requests.RequestException as e:
        logger.error(f"Request failed: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise


def main():
    url = "https://www.4camping.cz/p/detske-boty-reima-wetter-2-0/#31-cerna"
    scrape_4camping_product(url)


if __name__ == "__main__":
    main()
