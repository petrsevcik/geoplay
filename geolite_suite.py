"""
Script to download GeoLite2-City database from MaxMind.
"""

import tarfile
from pathlib import Path

import geoip2.database
from curl_cffi import requests
from decouple import config
from loguru import logger

LICENSE_KEY = config("GEO_IP_LICENCE_KEY")
EDITION_ID = "GeoLite2-City"
DOWNLOAD_URL = f"https://download.maxmind.com/app/geoip_download?edition_id={EDITION_ID}&license_key={LICENSE_KEY}&suffix=tar.gz"
DATA_DIR = Path(__file__).parent / "data"
DB_FILE = DATA_DIR / f"{EDITION_ID}.mmdb"

TEST_IPS = [
    "116.203.33.18",  # My hetzner server (DE)
    "86.49.245.36",  # My home IP (CZ)
    "92.204.164.15",  # My geondoe proxy (FR)
]


def download_database() -> None:
    """Download and extract GeoLite2-City database."""

    logger.info(f"Downloading {EDITION_ID} database...")

    # Create data directory if it doesn't exist
    DATA_DIR.mkdir(exist_ok=True)

    response = requests.get(DOWNLOAD_URL, stream=True)
    response.raise_for_status()

    # Save to temporary file
    tar_path = DATA_DIR / f"{EDITION_ID}.tar.gz"

    logger.info(f"Saving to {tar_path}...")
    with open(tar_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

    logger.info("Extracting database...")
    with tarfile.open(tar_path, "r:gz") as tar:
        # Find the .mmdb file in the archive
        for member in tar.getmembers():
            if member.name.endswith(".mmdb"):
                # Extract to data directory
                member.name = DB_FILE.name
                tar.extract(member, DATA_DIR)

    logger.info(f"Database extracted to: {DB_FILE}")

    # Check the size of the downloaded file
    mmdb_path = DATA_DIR / DB_FILE.name
    if mmdb_path.exists():
        size_mb = mmdb_path.stat().st_size / (1024 * 1024)
        logger.info(f"Extracted database file size: {size_mb:.2f} MB")
        logger.info("Download complete!")
    else:
        logger.error("Database file was not extracted.")


def get_ip_geolocation(ip_address: str) -> dict | None:
    """
    Query geolocation data for a given IP address.

    Args:
        ip_address: IP address to query
    """
    logger.info(f"Querying IP: {ip_address}")

    try:
        # Open the database and query
        with geoip2.database.Reader(str(DB_FILE)) as reader:
            response = reader.city(ip_address)

            # Extract data
            country = response.country.name
            country_code = response.country.iso_code
            city = response.city.name if response.city.name else "Unknown"
            latitude = response.location.latitude
            longitude = response.location.longitude
            timezone = response.location.time_zone

            # Display results
            logger.success("Found location data:")
            logger.info(f"   Country:     {country} ({country_code})")
            logger.info(f"   City:        {city}")
            logger.info(f"   Latitude:    {latitude}")
            logger.info(f"   Longitude:   {longitude}")
            logger.info(f"   Timezone:    {timezone}")

            return {
                "ip": ip_address,
                "country": country,
                "country_code": country_code,
                "city": city,
                "latitude": latitude,
                "longitude": longitude,
                "timezone": timezone,
            }

    except geoip2.errors.AddressNotFoundError:
        logger.error(f"IP address {ip_address} not found in database")
        return None
    except Exception as e:
        logger.error(f"Error querying IP {ip_address}: {e}")
        return None


def test_ip_geolocation(ip_list: list = TEST_IPS) -> None:
    if not DB_FILE.exists():
        logger.error(f"Database not found at: {DB_FILE}")
        logger.info("Please download database first. Run download_database() function")
        return

    logger.info("GeoLite2 Database Test")
    logger.info(f"Testing {len(TEST_IPS)} IP addresses...")

    results = []
    for ip in ip_list:
        result = get_ip_geolocation(ip)
        if result:
            results.append(result)

    logger.success(f"Successfully queried {len(results)}/{len(ip_list)} IPs")


if __name__ == "__main__":
    download_database()
    test_ip_geolocation()
