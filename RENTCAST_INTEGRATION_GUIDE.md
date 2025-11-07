# Rentcast API Integration Guide

## 🎯 Overview

The Rentcast integration allows you to fetch fresh rental property data from Rentcast's API (140+ million property records).

**Free Tier Limits:**
- 50 API requests per month
- Automatic rate limiting and usage tracking
- Resets monthly

---

## 🔧 Setup

### Step 1: Add Your API Key

Edit `.env` file and replace the placeholder with your actual Rentcast API key:

```bash
RENTCAST_API_KEY=your_actual_api_key_here
```

Get your key from: https://app.rentcast.io/app/api

### Step 2: Install Dependencies

All required dependencies should already be installed. If not:

```bash
source .venv/bin/activate
pip install requests python-dotenv pandas
```

---

## 📥 Fetching Data

### Basic Usage

Fetch listings for a single city:

```bash
source .venv/bin/activate
python fetch_rentcast_data.py --city "Toronto" --state "ON" --limit 100
```

### Fetch Multiple Cities

Save API requests by fetching multiple cities (uses 1 request per city):

```bash
python fetch_rentcast_data.py --cities "Toronto,Mississauga,Brampton" --state "ON" --limit 100
```

### Custom Output File

```bash
python fetch_rentcast_data.py --city "Toronto" --state "ON" --output "data/toronto_rentals_2024.csv"
```

---

## 📊 Usage Tracking

The integration automatically tracks your API usage to prevent exceeding the 50 request/month limit.

### Check Usage Stats

```bash
source .venv/bin/activate
python -c "from src.rentcast_api import RentcastAPI; client = RentcastAPI(); print(client.get_usage_stats())"
```

**Output:**
```json
{
  "requests_used": 5,
  "requests_remaining": 45,
  "monthly_limit": 50,
  "total_requests_all_time": 127,
  "current_month": "2024-11"
}
```

### Usage Log Location

All requests are logged to: `data/rentcast_usage.json`

This includes:
- Timestamp of each request
- Endpoint called
- Parameters used
- Success/failure status

---

## 🗺️ Supported Locations

### Canadian Cities (Supported)

**Ontario:**
- Toronto
- Mississauga
- Brampton
- Hamilton
- Ottawa
- London
- Windsor
- Kitchener
- Vaughan
- Markham

**British Columbia:**
- Vancouver
- Surrey
- Burnaby
- Richmond
- Victoria

**Alberta:**
- Calgary
- Edmonton

**Quebec:**
- Montreal (use "Montreal")
- Quebec City

### US Cities

Rentcast also supports US cities. Use 2-letter state codes:
- New York, NY
- Los Angeles, CA
- Chicago, IL
- etc.

---

## 📋 Data Format

The fetched data is automatically converted to match your existing CSV schema:

### Fields Included

| Field | Source | Notes |
|-------|--------|-------|
| Title | Rentcast listing type + address | Auto-generated |
| Address | Full address from Rentcast | Street, city, state, zip |
| Price($) | Monthly rent | Numeric value |
| Date Posted | Listing date | ISO format |
| Building Type | Property type | Apartment, House, Condo, etc. |
| Bedrooms | Number of bedrooms | Numeric |
| Bathrooms | Number of bathrooms | Numeric (supports decimals like 1.5) |
| Parking Included | Has parking | Yes/No |
| Pet Friendly | Pet policy | Yes/No |
| Size (sqft) | Square footage | Numeric |
| Furnished | Furnishing status | Yes/No |
| Air Conditioning | Has AC | Yes/No |
| Amenities | List of amenities | Comma-separated |
| Description | Property description | Full text |
| url | Listing URL | Direct link |

### Additional Fields

The integration also preserves Rentcast-specific fields:
- `rentcast_id` - Unique listing ID
- `last_seen_date` - When listing was last active
- `status` - Active/Inactive

---

## 🔄 Updating Your Dataset

### Strategy 1: Monthly Refresh (Recommended)

Use all 50 requests at the start of each month:

```bash
# Fetch ~5000 listings (50 cities × 100 listings each)
python fetch_rentcast_data.py \
  --cities "Toronto,Mississauga,Brampton,Hamilton,Ottawa,London,Windsor,Kitchener,Vaughan,Markham" \
  --state "ON" \
  --limit 100
```

### Strategy 2: Targeted Updates

Use requests sparingly throughout the month for specific needs:

```bash
# Fetch just Toronto (1 request)
python fetch_rentcast_data.py --city "Toronto" --state "ON" --limit 200
```

### Strategy 3: Combine with Existing Data

```bash
# 1. Fetch new data
python fetch_rentcast_data.py --cities "Toronto,Mississauga" --state "ON"

# 2. The script saves to data/rentcast_*.csv
# 3. Your existing tools.py automatically loads all CSVs from data/ folder
# 4. Just rebuild embeddings:
python -m src.vectorstore_setup
```

---

## 🧪 Testing the Integration

### Test API Connection

```bash
source .venv/bin/activate
python -c "from src.rentcast_api import test_api_connection; test_api_connection()"
```

**Expected Output:**
```
✅ Rentcast API connection successful!
📊 Usage Stats: {'requests_used': 1, 'requests_remaining': 49, 'monthly_limit': 50, ...}
```

### Test Data Fetching

Fetch a small sample to verify everything works:

```bash
python fetch_rentcast_data.py --city "Toronto" --state "ON" --limit 10
```

---

## 💡 Best Practices

### 1. Plan Your Requests

With only 50 requests/month:
- Each city = 1 request
- Focus on high-value cities (Toronto, Vancouver, Montreal)
- Fetch max listings per request (limit=500)

### 2. Monitor Usage

Check usage before fetching:
```bash
python -c "from src.rentcast_api import RentcastAPI; print(RentcastAPI().get_usage_stats())"
```

### 3. Combine Data Sources

Don't rely only on Rentcast:
- Keep your existing CSVs
- Add Rentcast data as supplement
- Consider web scraping for free alternatives (Kijiji, etc.)

### 4. Update Embeddings After Fetching

After fetching new data, rebuild the FAISS index:

```bash
python -m src.vectorstore_setup
```

### 5. Schedule Monthly Updates

Set a monthly reminder or cron job:

```bash
# Add to crontab (runs 1st of each month at 2 AM)
0 2 1 * * cd /path/to/project && source .venv/bin/activate && python fetch_rentcast_data.py --cities "Toronto,Vancouver,Montreal" --state "ON"
```

---

## 🚨 Error Handling

### Common Errors

**1. Invalid API Key**
```
❌ Rentcast API Error: Invalid API key
```
**Fix:** Check your `.env` file and ensure RENTCAST_API_KEY is set correctly.

**2. Monthly Limit Reached**
```
❌ Rentcast API Error: Monthly API limit reached (50 requests)
```
**Fix:** Wait until next month or upgrade to paid plan.

**3. No Listings Found**
```
⚠️  No listings found in [City]
```
**Fix:**
- Verify city name spelling
- Try different state code
- City may not have listings in Rentcast database

**4. Network Timeout**
```
❌ Rentcast API Error: Request timed out
```
**Fix:** Check internet connection and try again.

---

## 📈 Upgrade Options

If you need more than 50 requests/month, Rentcast offers paid plans:

- **Starter:** $49/month - 500 requests
- **Pro:** $99/month - 2,000 requests
- **Business:** $299/month - 10,000 requests

Visit: https://www.rentcast.io/api

---

## 🔍 Troubleshooting

### Check API Key
```bash
cat .env | grep RENTCAST
```

### Test Import
```bash
python -c "from src.rentcast_api import RentcastAPI; print('Import successful')"
```

### View Usage Log
```bash
cat data/rentcast_usage.json
```

### Clear Usage Tracking (if needed)
```bash
rm data/rentcast_usage.json
```

---

## 📞 Support

- **Rentcast API Docs:** https://developers.rentcast.io/
- **Rentcast Support:** https://www.rentcast.io/contact
- **Your API Dashboard:** https://app.rentcast.io/app/api

---

## ✅ Quick Reference

```bash
# Setup
1. Add API key to .env
2. source .venv/bin/activate

# Fetch data
python fetch_rentcast_data.py --city "Toronto" --state "ON"

# Check usage
python -c "from src.rentcast_api import RentcastAPI; print(RentcastAPI().get_usage_stats())"

# Rebuild embeddings
python -m src.vectorstore_setup

# Run app
streamlit run app.py
```

---

**Happy property hunting! 🏠**
