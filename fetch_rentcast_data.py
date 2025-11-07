"""
Fetch rental listings from Rentcast API and convert to CSV format.

Usage:
    python fetch_rentcast_data.py --city "Toronto" --state "ON" --limit 100
    python fetch_rentcast_data.py --cities "Toronto,Mississauga,Brampton" --state "ON"
"""

import argparse
import pandas as pd
from datetime import datetime
from pathlib import Path
from src.rentcast_api import RentcastAPI, RentcastAPIError


def convert_rentcast_to_dataframe(listings: list) -> pd.DataFrame:
    """
    Convert Rentcast API listings to DataFrame matching existing schema.

    Rentcast fields → Your schema mapping
    """
    rows = []

    for listing in listings:
        try:
            # Extract address components
            address_info = listing.get("address", {})
            full_address = f"{address_info.get('addressLine1', '')}, {address_info.get('city', '')}, {address_info.get('state', '')} {address_info.get('zipCode', '')}"

            # Map Rentcast fields to your existing schema
            row = {
                # Basic Info
                "Title": listing.get("listingType", "Rental") + " - " + full_address,
                "Address": full_address,
                "Price($)": listing.get("price", ""),

                # Date
                "Date Posted": listing.get("listedDate", ""),

                # Property Details
                "Building Type": listing.get("propertyType", ""),
                "Bedrooms": listing.get("bedrooms", ""),
                "Bathrooms": listing.get("bathrooms", ""),

                # Utilities (Rentcast may not have this, set defaults)
                "Utilities": "Not Specified",
                "Wi-Fi and More": "Not Specified",

                # Amenities
                "Parking Included": "Yes" if listing.get("parking") else "No",
                "Agreement Type": listing.get("leaseType", ""),
                "Move-In Date": listing.get("availableDate", ""),
                "Pet Friendly": "Yes" if listing.get("petPolicy", {}).get("allowed") else "No",

                # Size and Features
                "Size (sqft)": listing.get("squareFootage", ""),
                "Furnished": "Yes" if listing.get("furnished") else "No",
                "Air Conditioning": "Yes" if "AC" in listing.get("cooling", "") or "air" in listing.get("cooling", "").lower() else "No",
                "Personal Outdoor Space": "Balcony" if listing.get("balcony") else ("Yard" if listing.get("yard") else "None"),
                "Smoking Permitted": "No",  # Default assumption

                # Appliances and Amenities
                "Appliances": ", ".join(listing.get("appliances", [])) if listing.get("appliances") else "",
                "Amenities": ", ".join(listing.get("amenities", [])) if listing.get("amenities") else "",

                # Description
                "Description": listing.get("description", ""),

                # Metadata
                "Visit Counter": 0,
                "url": listing.get("listingUrl", ""),

                # Rentcast-specific fields (for reference)
                "rentcast_id": listing.get("id", ""),
                "last_seen_date": listing.get("lastSeenDate", ""),
                "status": listing.get("status", "Active")
            }

            rows.append(row)

        except Exception as e:
            print(f"⚠️  Warning: Failed to process listing {listing.get('id', 'unknown')}: {e}")
            continue

    df = pd.DataFrame(rows)

    # Clean up price field (remove non-numeric characters)
    if "Price($)" in df.columns:
        df["Price($)"] = df["Price($)"].astype(str).str.replace(r"[^\d.]", "", regex=True)

    return df


def fetch_and_save_listings(
    cities: list,
    state: str,
    limit_per_city: int = 100,
    output_file: str = None
):
    """
    Fetch listings from Rentcast and save to CSV.

    Args:
        cities: List of city names
        state: State/Province code
        limit_per_city: Max listings per city
        output_file: Output CSV filename (auto-generated if None)
    """
    try:
        # Initialize API client
        client = RentcastAPI()

        # Show usage stats
        stats = client.get_usage_stats()
        print(f"\n📊 Rentcast API Usage:")
        print(f"   Used: {stats['requests_used']}/{stats['monthly_limit']}")
        print(f"   Remaining: {stats['requests_remaining']}")
        print(f"   Current Month: {stats['current_month']}\n")

        # Estimate requests needed
        requests_needed = len(cities)
        if requests_needed > stats['requests_remaining']:
            print(f"⚠️  WARNING: This operation will need {requests_needed} requests,")
            print(f"   but you only have {stats['requests_remaining']} remaining this month.")
            response = input("   Continue anyway? (y/n): ")
            if response.lower() != 'y':
                print("Cancelled.")
                return

        # Fetch listings for each city
        all_listings = []
        for city in cities:
            print(f"\n🏙️  Fetching listings for {city}, {state}...")
            try:
                listings = client.get_rental_listings(
                    city=city,
                    state=state,
                    limit=limit_per_city,
                    status="Active"
                )

                if listings:
                    print(f"   ✅ Found {len(listings)} listings in {city}")
                    all_listings.extend(listings)
                else:
                    print(f"   ⚠️  No listings found in {city}")

            except RentcastAPIError as e:
                print(f"   ❌ Error fetching {city}: {e}")
                continue

        if not all_listings:
            print("\n❌ No listings fetched. Exiting.")
            return

        print(f"\n📦 Total listings fetched: {len(all_listings)}")

        # Convert to DataFrame
        print("🔄 Converting to DataFrame...")
        df = convert_rentcast_to_dataframe(all_listings)

        # Generate output filename if not provided
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            cities_str = "_".join(cities[:3])  # Max 3 city names
            output_file = f"data/rentcast_{cities_str}_{timestamp}.csv"

        # Save to CSV
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_path, index=False)

        print(f"\n✅ Successfully saved {len(df)} listings to: {output_file}")
        print(f"\n📊 Data Summary:")
        print(f"   Bedrooms: {df['Bedrooms'].value_counts().to_dict()}")
        print(f"   Price range: ${df['Price($)'].astype(str).str.extract(r'(\d+)')[0].astype(float).min():.0f} - ${df['Price($)'].astype(str).str.extract(r'(\d+)')[0].astype(float).max():.0f}")

        # Show updated usage
        stats = client.get_usage_stats()
        print(f"\n📊 Updated API Usage:")
        print(f"   Remaining: {stats['requests_remaining']}/{stats['monthly_limit']}")

        return df

    except RentcastAPIError as e:
        print(f"\n❌ Rentcast API Error: {e}")
        return None
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    parser = argparse.ArgumentParser(description="Fetch rental listings from Rentcast API")
    parser.add_argument("--city", type=str, help="Single city name (e.g., 'Toronto')")
    parser.add_argument("--cities", type=str, help="Comma-separated cities (e.g., 'Toronto,Mississauga')")
    parser.add_argument("--state", type=str, required=True, help="State/Province code (e.g., 'ON', 'NY')")
    parser.add_argument("--limit", type=int, default=100, help="Max listings per city (default: 100)")
    parser.add_argument("--output", type=str, help="Output CSV filename (default: auto-generated)")

    args = parser.parse_args()

    # Parse cities
    if args.cities:
        cities = [c.strip() for c in args.cities.split(",")]
    elif args.city:
        cities = [args.city]
    else:
        print("❌ Error: Must provide either --city or --cities")
        parser.print_help()
        return

    print("🚀 Rentcast Data Fetcher")
    print("=" * 50)
    print(f"Cities: {', '.join(cities)}")
    print(f"State: {args.state}")
    print(f"Limit per city: {args.limit}")
    print("=" * 50)

    # Fetch and save
    fetch_and_save_listings(
        cities=cities,
        state=args.state,
        limit_per_city=args.limit,
        output_file=args.output
    )


if __name__ == "__main__":
    main()
