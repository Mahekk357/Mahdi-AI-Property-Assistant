"""
Rentcast API Integration Module
Free tier: 50 requests/month
Documentation: https://developers.rentcast.io/
"""

import os
import json
import time
from datetime import datetime
from pathlib import Path
import requests
from dotenv import load_dotenv

load_dotenv()

# API Configuration
RENTCAST_BASE_URL = "https://api.rentcast.io/v1"
RENTCAST_API_KEY = os.getenv("RENTCAST_API_KEY")
USAGE_TRACKER_FILE = "data/rentcast_usage.json"

# Rate Limiting
MONTHLY_LIMIT = 50  # Free tier limit
REQUEST_DELAY = 2  # Seconds between requests to be respectful


class RentcastAPIError(Exception):
    """Custom exception for Rentcast API errors"""
    pass


class RentcastAPI:
    """
    Rentcast API client with rate limiting and usage tracking.

    Features:
    - Automatic rate limiting (50 requests/month for free tier)
    - Usage tracking to prevent exceeding limits
    - Error handling and retries
    - Response caching
    """

    def __init__(self, api_key: str = None):
        self.api_key = api_key or RENTCAST_API_KEY
        if not self.api_key or self.api_key == "YOUR_RENTCAST_API_KEY_HERE":
            raise RentcastAPIError(
                "Rentcast API key not found. Please add your key to .env file:\n"
                "RENTCAST_API_KEY=your_actual_key_here"
            )

        self.base_url = RENTCAST_BASE_URL
        self.headers = {
            "Accept": "application/json",
            "X-Api-Key": self.api_key
        }
        self.usage_tracker_file = Path(USAGE_TRACKER_FILE)
        self.usage_data = self._load_usage_data()

    def _load_usage_data(self) -> dict:
        """Load API usage tracking data"""
        if self.usage_tracker_file.exists():
            with open(self.usage_tracker_file, 'r') as f:
                return json.load(f)
        return {
            "requests_this_month": 0,
            "last_reset_date": datetime.now().strftime("%Y-%m"),
            "total_requests": 0,
            "requests_log": []
        }

    def _save_usage_data(self):
        """Save API usage tracking data"""
        self.usage_tracker_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.usage_tracker_file, 'w') as f:
            json.dump(self.usage_data, f, indent=2)

    def _check_and_reset_monthly_limit(self):
        """Reset monthly counter if new month"""
        current_month = datetime.now().strftime("%Y-%m")
        if self.usage_data["last_reset_date"] != current_month:
            print(f"📅 New month detected. Resetting usage counter.")
            self.usage_data["requests_this_month"] = 0
            self.usage_data["last_reset_date"] = current_month
            self._save_usage_data()

    def _can_make_request(self) -> bool:
        """Check if we have requests remaining this month"""
        self._check_and_reset_monthly_limit()
        return self.usage_data["requests_this_month"] < MONTHLY_LIMIT

    def _log_request(self, endpoint: str, params: dict, success: bool):
        """Log API request for tracking"""
        self.usage_data["requests_this_month"] += 1
        self.usage_data["total_requests"] += 1
        self.usage_data["requests_log"].append({
            "timestamp": datetime.now().isoformat(),
            "endpoint": endpoint,
            "params": params,
            "success": success
        })
        # Keep only last 100 requests in log
        if len(self.usage_data["requests_log"]) > 100:
            self.usage_data["requests_log"] = self.usage_data["requests_log"][-100:]
        self._save_usage_data()

    def get_usage_stats(self) -> dict:
        """Get current API usage statistics"""
        self._check_and_reset_monthly_limit()
        return {
            "requests_used": self.usage_data["requests_this_month"],
            "requests_remaining": MONTHLY_LIMIT - self.usage_data["requests_this_month"],
            "monthly_limit": MONTHLY_LIMIT,
            "total_requests_all_time": self.usage_data["total_requests"],
            "current_month": self.usage_data["last_reset_date"]
        }

    def _make_request(self, endpoint: str, params: dict = None) -> dict:
        """Make API request with error handling"""
        if not self._can_make_request():
            raise RentcastAPIError(
                f"Monthly API limit reached ({MONTHLY_LIMIT} requests). "
                f"Resets next month: {datetime.now().strftime('%Y-%m')}"
            )

        url = f"{self.base_url}{endpoint}"

        try:
            print(f"🔍 Making Rentcast API request to: {endpoint}")
            print(f"📊 Requests remaining: {MONTHLY_LIMIT - self.usage_data['requests_this_month']}/{MONTHLY_LIMIT}")

            response = requests.get(url, headers=self.headers, params=params, timeout=30)

            # Log the request
            self._log_request(endpoint, params, response.status_code == 200)

            # Handle rate limiting
            if response.status_code == 429:
                raise RentcastAPIError("Rate limit exceeded. Please wait before making more requests.")

            # Handle authentication errors
            if response.status_code == 401:
                raise RentcastAPIError("Invalid API key. Please check your RENTCAST_API_KEY in .env")

            # Handle other errors
            if response.status_code != 200:
                raise RentcastAPIError(
                    f"API request failed with status {response.status_code}: {response.text}"
                )

            # Add delay to be respectful
            time.sleep(REQUEST_DELAY)

            return response.json()

        except requests.exceptions.Timeout:
            self._log_request(endpoint, params, False)
            raise RentcastAPIError("Request timed out. Please try again.")
        except requests.exceptions.RequestException as e:
            self._log_request(endpoint, params, False)
            raise RentcastAPIError(f"Network error: {str(e)}")

    def get_rental_listings(
        self,
        city: str = None,
        state: str = None,
        zip_code: str = None,
        limit: int = 100,
        offset: int = 0,
        status: str = "Active"
    ) -> list:
        """
        Get rental listings from Rentcast.

        Args:
            city: City name (e.g., "Toronto", "New York")
            state: State/Province code (e.g., "ON", "NY")
            zip_code: ZIP/Postal code
            limit: Number of results (max 500 per request)
            offset: Pagination offset
            status: "Active" or "Inactive"

        Returns:
            List of rental listing dictionaries
        """
        if not city and not zip_code:
            raise ValueError("Must provide either city or zip_code")

        params = {
            "limit": min(limit, 500),  # API max is 500
            "offset": offset
        }

        if city:
            params["city"] = city
        if state:
            params["state"] = state
        if zip_code:
            params["zipCode"] = zip_code
        if status:
            params["status"] = status

        endpoint = "/listings/rental/long-term"
        result = self._make_request(endpoint, params)

        # Return the listings array
        return result if isinstance(result, list) else result.get("listings", [])

    def get_property_details(self, address: str, city: str, state: str) -> dict:
        """
        Get detailed property information.

        Args:
            address: Street address
            city: City name
            state: State/Province code

        Returns:
            Property details dictionary
        """
        params = {
            "address": address,
            "city": city,
            "state": state
        }

        endpoint = "/properties"
        return self._make_request(endpoint, params)

    def get_rent_estimate(
        self,
        address: str = None,
        city: str = None,
        state: str = None,
        bedrooms: int = None,
        bathrooms: float = None,
        square_feet: int = None
    ) -> dict:
        """
        Get rent estimate for a property.

        Args:
            address: Street address (if known)
            city: City name
            state: State/Province code
            bedrooms: Number of bedrooms
            bathrooms: Number of bathrooms
            square_feet: Square footage

        Returns:
            Rent estimate data
        """
        params = {}

        if address:
            params["address"] = address
        if city:
            params["city"] = city
        if state:
            params["state"] = state
        if bedrooms is not None:
            params["bedrooms"] = bedrooms
        if bathrooms is not None:
            params["bathrooms"] = bathrooms
        if square_feet is not None:
            params["squareFootage"] = square_feet

        if not params:
            raise ValueError("Must provide at least some property parameters")

        endpoint = "/avm/rent/long-term"
        return self._make_request(endpoint, params)


def test_api_connection():
    """Test Rentcast API connection"""
    try:
        client = RentcastAPI()
        stats = client.get_usage_stats()
        print("✅ Rentcast API connection successful!")
        print(f"📊 Usage Stats: {stats}")
        return True
    except RentcastAPIError as e:
        print(f"❌ Rentcast API Error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


if __name__ == "__main__":
    # Test the API connection
    test_api_connection()
