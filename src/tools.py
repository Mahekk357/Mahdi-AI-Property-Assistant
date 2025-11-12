from langchain.tools import tool
import re
import pandas as pd
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS

from src.data_utils import normalize_area_name
from src.vectorstore_setup import load_vectorstore


PROPERTY_DATASETS = [
    "data/listing_sample1.csv",
    "data/listings_sample.csv",
]


def _format_property_results(df: pd.DataFrame) -> str:
    """
    Convert DataFrame of properties to readable text format.
    Prevents formatting issues when LangChain converts DataFrames to strings.
    """
    if df.empty:
        return "No properties found matching your criteria."

    output_lines = []
    for idx, row in df.iterrows():
        address = row.get("address", "Unknown address")
        neighbourhood = row.get("neighbourhood", "Unknown area")
        bedrooms = row.get("bedrooms", "?")
        bathrooms = row.get("bathrooms", "?")
        price = row.get("price", "?")

        line = f"- {address} ({neighbourhood}): {bedrooms} bed, {bathrooms} bath, ${price}/month"
        output_lines.append(line)

    return "\n".join(output_lines)


def _detect_area_from_values(values):
    ordered = []
    for value in values:
        if value is None:
            continue
        ordered.append(value)

    # Prefer address-derived values before neighbourhood fragments
    for value in ordered:
        city = normalize_area_name(value)
        if city:
            return city
    return None


def _normalize_area_query(area_text: str) -> str:
    if not area_text:
        return ""
    normalized = normalize_area_name(area_text)
    if normalized:
        return normalized
    return ""


def _normalize_property_dataframe(raw_df: pd.DataFrame) -> pd.DataFrame:
    if raw_df is None or raw_df.empty:
        return pd.DataFrame()

    df = raw_df.copy()
    df.columns = [c.strip().lower() for c in df.columns]

    column_aliases = {
        "price($)": "price",
        "monthlyrentalprice": "price",
        "rent": "price",
        "location": "neighbourhood",
    }
    for source, target in column_aliases.items():
        if source in df.columns:
            if target not in df.columns or df[target].isna().all():
                df[target] = df[source]
            df = df.drop(columns=[source])

    if "neighbourhood" not in df.columns:
        if "address" in df.columns:
            df["neighbourhood"] = (
                df["address"]
                .astype(str)
                .str.split(",", n=2)
                .str[1]
                .str.strip()
            ).fillna("Unknown")
        else:
            df["neighbourhood"] = "Unknown"

    if "price" not in df.columns:
        df["price"] = pd.NA

    if "bedrooms" not in df.columns:
        bedrooms_alt = next((col for col in ["beds", "bedrooms_count"] if col in df.columns), None)
        if bedrooms_alt:
            df["bedrooms"] = df[bedrooms_alt]
        else:
            df["bedrooms"] = pd.NA

    if "bathrooms" not in df.columns:
        baths_alt = next((col for col in ["baths", "bathrooms_count"] if col in df.columns), None)
        if baths_alt:
            df["bathrooms"] = df[baths_alt]
        else:
            df["bathrooms"] = pd.NA

    df["price_numeric"] = pd.to_numeric(df["price"], errors="coerce")
    df.loc[(df["price_numeric"] < 200) | (df["price_numeric"] > 50000), "price_numeric"] = pd.NA
    bedroom_numeric_series = (
        df["bedrooms"]
        .astype(str)
        .str.extract(r"(\d+)")
        .squeeze()
    )
    df["bedrooms_numeric"] = pd.to_numeric(bedroom_numeric_series, errors="coerce")
    bathroom_numeric_series = (
        df["bathrooms"]
        .astype(str)
        .str.extract(r"(\d+(?:\.\d+)?)")
        .squeeze()
    )
    df["bathrooms_numeric"] = pd.to_numeric(bathroom_numeric_series, errors="coerce")

    if "area" not in df.columns:
        df["area"] = df.apply(
            lambda row: _detect_area_from_values(
                [row.get(col) for col in ["city", "address", "neighbourhood", "title"] if col in df.columns]
            ),
            axis=1,
        )
    else:
        df["area"] = df["area"].fillna(
            df.apply(
                lambda row: _detect_area_from_values(
                    [row.get(col) for col in ["city", "address", "neighbourhood", "title"] if col in df.columns]
                ),
                axis=1,
            )
        )
    df["area"] = df["area"].apply(normalize_area_name)

    if "city" not in df.columns:
        df["city"] = df["area"]
    else:
        df["city"] = df["city"].apply(normalize_area_name)

    return df


def _load_property_dataframe() -> pd.DataFrame:
    frames = []
    for path in PROPERTY_DATASETS:
        try:
            raw = pd.read_csv(path)
        except FileNotFoundError:
            continue
        frames.append(_normalize_property_dataframe(raw))

    if not frames:
        return pd.DataFrame(columns=["address", "neighbourhood", "bedrooms", "bathrooms", "price"])

    df = pd.concat(frames, ignore_index=True, sort=False)
    for col in ["address", "neighbourhood", "bedrooms", "bathrooms", "price", "price_numeric", "bedrooms_numeric", "bathrooms_numeric", "area", "city"]:
        if col not in df.columns:
            df[col] = pd.NA

    return df

@tool("search_properties")
def search_properties(query: str):
    """
    Hybrid property search:
    1. Uses regex + pandas for structured filters.
    2. Falls back to FAISS semantic similarity if no direct matches.
    """

    # --- Load data ---
    df = _load_property_dataframe()
    if df.empty:
        return pd.DataFrame(columns=["address", "neighbourhood", "bedrooms", "bathrooms", "price"])

    # --- Enhanced structured filters with expanded patterns ---

    # BEDROOMS: Support "2 bed", "2 bedrooms", "2+ beds", "at least 2", etc.
    bedrooms = None
    bedrooms_minimum = False

    bed_patterns = [
        r"(\d+)\s*\+?\s*(?:bed(?:room)?s?)",  # "2 beds", "2 bedrooms", "2+ beds"
        r"(?:at\s*least|minimum|min)\s*(\d+)\s*(?:bed(?:room)?s?)?",  # "at least 2 bedrooms"
    ]
    for pattern in bed_patterns:
        match = re.search(pattern, query, re.I)
        if match:
            bedrooms = match
            if "at least" in match.group(0).lower() or "minimum" in match.group(0).lower() or "+" in match.group(0):
                bedrooms_minimum = True
            break

    # BATHROOMS: Similar enhancement
    bathrooms = None
    bathrooms_minimum = False

    bath_patterns = [
        r"(\d+(?:\.\d+)?)\s*\+?\s*(?:bath(?:room)?s?)",  # "1.5 bath", "2 bathrooms", "1+ baths"
        r"(?:at\s*least|minimum|min)\s*(\d+(?:\.\d+)?)\s*(?:bath(?:room)?s?)?",  # "at least 1.5 bathrooms"
    ]
    for pattern in bath_patterns:
        match = re.search(pattern, query, re.I)
        if match:
            bathrooms = match
            if "at least" in match.group(0).lower() or "minimum" in match.group(0).lower() or "+" in match.group(0):
                bathrooms_minimum = True
            break

    # PRICE: Support ranges, "under", "around", "between", etc.
    min_price = None
    max_price = None

    # Price range: "$2000-$3000", "$2000 to $3000", "between $2k and $3k"
    price_range = re.search(r"\$?(\d+)(?:k|000)?\s*(?:-|to|and)\s*\$?(\d+)(?:k|000)?", query, re.I)
    if price_range:
        min_val = int(price_range.group(1))
        max_val = int(price_range.group(2))
        # Handle 'k' notation (2k = 2000)
        if "k" in price_range.group(0).lower():
            if min_val < 100:  # Likely "2k" format
                min_val *= 1000
            if max_val < 100:
                max_val *= 1000
        min_price = min_val
        max_price = max_val
    else:
        # Single price constraints
        under_match = re.search(r"(?:under|below|less\s*than|max(?:imum)?)\s*\$?(\d+)(?:k|000)?", query, re.I)
        if under_match:
            val = int(under_match.group(1))
            if "k" in under_match.group(0).lower() and val < 100:
                val *= 1000
            max_price = val

        over_match = re.search(r"(?:over|above|more\s*than|at\s*least)\s*\$?(\d+)(?:k|000)?", query, re.I)
        if over_match:
            val = int(over_match.group(1))
            if "k" in over_match.group(0).lower() and val < 100:
                val *= 1000
            min_price = val

        # "around $2500"
        around_match = re.search(r"(?:around|approximately|about|roughly)\s*\$?(\d+)(?:k|000)?", query, re.I)
        if around_match:
            val = int(around_match.group(1))
            if "k" in around_match.group(0).lower() and val < 100:
                val *= 1000
            # Create range ±20%
            min_price = int(val * 0.8)
            max_price = int(val * 1.2)

    # AMENITIES: Extract amenity requirements
    amenities_filters = {}

    # Parking
    if re.search(r"\b(?:parking|garage)\b", query, re.I):
        amenities_filters["parking"] = True

    # Pet-friendly
    if re.search(r"\b(?:pet[- ]?friendly|pets?\s*(?:allowed|ok|welcome))\b", query, re.I):
        amenities_filters["pet_friendly"] = True

    # Furnished
    if re.search(r"\b(?:furnished|furniture)\b", query, re.I):
        amenities_filters["furnished"] = True

    # Air conditioning
    if re.search(r"\b(?:air\s*condition(?:ing)?|a/?c|climate\s*control)\b", query, re.I):
        amenities_filters["air_conditioning"] = True

    # Gym/Fitness
    if re.search(r"\b(?:gym|fitness|workout)\b", query, re.I):
        amenities_filters["gym"] = True

    # Balcony/Outdoor space
    if re.search(r"\b(?:balcony|patio|terrace|outdoor\s*space)\b", query, re.I):
        amenities_filters["outdoor_space"] = True

    city = None
    def _collect_candidate_areas(series):
        names = set()
        for value in series.dropna():
            normalized = normalize_area_name(value) if isinstance(value, str) else None
            if normalized:
                names.add(normalized)
        return names

    available_areas = _collect_candidate_areas(df["area"])
    if "city" in df.columns:
        available_areas.update(_collect_candidate_areas(df["city"]))

    neighbourhood_candidates = _collect_candidate_areas(df["neighbourhood"]) if "neighbourhood" in df.columns else set()
    available_area_set = available_areas | neighbourhood_candidates
    available_area_lower = {area.lower() for area in available_area_set}

    for area_name in sorted(available_areas, key=len, reverse=True):
        pattern = rf"\b{re.escape(area_name)}\b"
        if re.search(pattern, query, re.I):
            city = area_name
            break

    if city is None:
        tokens = [
            token.strip()
            for token in re.split(r"[,&;/]|\band\b|\bin\b", query, flags=re.I)
            if token.strip()
        ]
        for token in tokens:
            normalized = _normalize_area_query(token)
            if not normalized:
                continue

            if normalized in available_area_set:
                city = normalized
                break

            normalized_lower = normalized.lower()
            if normalized_lower in available_area_lower:
                city = next(area for area in available_area_set if area.lower() == normalized_lower)
                break

            for area in available_area_set:
                if normalized_lower in area.lower():
                    city = area
                    break
            if city:
                break

    filtered_df = df.copy()

    # Apply bedroom filter
    if bedrooms:
        bed_value = int(bedrooms.group(1))
        if bedrooms_minimum:
            filtered_df = filtered_df[filtered_df["bedrooms_numeric"] >= bed_value]
        else:
            filtered_df = filtered_df[filtered_df["bedrooms_numeric"] == bed_value]

    # Apply bathroom filter
    if bathrooms:
        bath_value = float(bathrooms.group(1))
        if bathrooms_minimum:
            filtered_df = filtered_df[filtered_df["bathrooms_numeric"] >= bath_value]
        else:
            filtered_df = filtered_df[filtered_df["bathrooms_numeric"] == bath_value]

    # Apply price filters
    if min_price is not None:
        filtered_df = filtered_df[filtered_df["price_numeric"] >= min_price]
    if max_price is not None:
        filtered_df = filtered_df[filtered_df["price_numeric"] <= max_price]

    # Apply location filter
    if city:
        if "area" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["area"].str.contains(city, case=False, na=False)]
        elif "city" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["city"].str.contains(city, case=False, na=False)]

    # Apply amenity filters
    if amenities_filters.get("parking"):
        if "Parking Included" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["Parking Included"].str.lower().isin(["yes", "true", "included"])]

    if amenities_filters.get("pet_friendly"):
        if "Pet Friendly" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["Pet Friendly"].str.lower().isin(["yes", "true", "allowed"])]

    if amenities_filters.get("furnished"):
        if "Furnished" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["Furnished"].str.lower().isin(["yes", "true", "furnished"])]

    if amenities_filters.get("air_conditioning"):
        if "Air Conditioning" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["Air Conditioning"].str.lower().isin(["yes", "true", "included"])]

    if amenities_filters.get("gym"):
        if "Amenities" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["Amenities"].str.contains("gym|fitness", case=False, na=False)]

    if amenities_filters.get("outdoor_space"):
        if "Personal Outdoor Space" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["Personal Outdoor Space"].notna() &
                                     (filtered_df["Personal Outdoor Space"] != "None")]

    # --- TRUE HYBRID SEARCH: Combine semantic + structured filtering ---
    # Strategy:
    # 1. If we have structured filters AND structured results, return those (fast path)
    # 2. If structured filters but no results, OR if query is more semantic, use hybrid approach:
    #    a) Semantic search for top candidates
    #    b) Apply structured filters to candidates
    #    c) Return filtered, relevance-ranked results

    has_structured_filters = any([bedrooms, bathrooms, min_price, max_price, city, amenities_filters])

    # Fast path: If we have structured results and they're good, return them
    if not filtered_df.empty and has_structured_filters:
        return _format_property_results(filtered_df.head(5))

    # Hybrid path: Use semantic search + structured filtering
    print("Performing hybrid semantic + structured search...")

    try:
        # Load pre-computed vectorstore
        vectorstore = load_vectorstore()

        # Get more candidates for better filtering (top 50 instead of 5)
        k = 50 if has_structured_filters else 10
        results = vectorstore.similarity_search(query, k=k)

        if results:
            # Extract property data from semantic results
            semantic_properties = []
            for doc in results:
                metadata = doc.metadata
                semantic_properties.append({
                    "address": metadata.get("Address", ""),
                    "neighbourhood": metadata.get("City", metadata.get("Area", "")),
                    "bedrooms": metadata.get("Bedrooms", ""),
                    "bathrooms": metadata.get("Bathrooms", ""),
                    "price": metadata.get("Price($)", ""),
                    "bedrooms_numeric": metadata.get("bedrooms_numeric"),
                    "bathrooms_numeric": metadata.get("bathrooms_numeric"),
                    "price_numeric": metadata.get("price_numeric"),
                    "Parking Included": metadata.get("Parking Included", ""),
                    "Pet Friendly": metadata.get("Pet Friendly", ""),
                    "Furnished": metadata.get("Furnished", ""),
                    "Air Conditioning": metadata.get("Air Conditioning", ""),
                    "Amenities": metadata.get("Amenities", ""),
                    "Personal Outdoor Space": metadata.get("Personal Outdoor Space", ""),
                })

            semantic_df = pd.DataFrame(semantic_properties)

            # Apply structured filters to semantic results
            if has_structured_filters:
                # Bedroom filter
                if bedrooms:
                    bed_value = int(bedrooms.group(1))
                    if bedrooms_minimum:
                        semantic_df = semantic_df[semantic_df["bedrooms_numeric"] >= bed_value]
                    else:
                        semantic_df = semantic_df[semantic_df["bedrooms_numeric"] == bed_value]

                # Bathroom filter
                if bathrooms:
                    bath_value = float(bathrooms.group(1))
                    if bathrooms_minimum:
                        semantic_df = semantic_df[semantic_df["bathrooms_numeric"] >= bath_value]
                    else:
                        semantic_df = semantic_df[semantic_df["bathrooms_numeric"] == bath_value]

                # Price filters
                if min_price is not None:
                    semantic_df = semantic_df[semantic_df["price_numeric"] >= min_price]
                if max_price is not None:
                    semantic_df = semantic_df[semantic_df["price_numeric"] <= max_price]

                # Amenity filters
                if amenities_filters.get("parking"):
                    semantic_df = semantic_df[semantic_df["Parking Included"].str.lower().isin(["yes", "true", "included"])]

                if amenities_filters.get("pet_friendly"):
                    semantic_df = semantic_df[semantic_df["Pet Friendly"].str.lower().isin(["yes", "true", "allowed"])]

                if amenities_filters.get("furnished"):
                    semantic_df = semantic_df[semantic_df["Furnished"].str.lower().isin(["yes", "true", "furnished"])]

                if amenities_filters.get("air_conditioning"):
                    semantic_df = semantic_df[semantic_df["Air Conditioning"].str.lower().isin(["yes", "true", "included"])]

                if amenities_filters.get("gym"):
                    semantic_df = semantic_df[semantic_df["Amenities"].str.contains("gym|fitness", case=False, na=False)]

                if amenities_filters.get("outdoor_space"):
                    semantic_df = semantic_df[semantic_df["Personal Outdoor Space"].notna() &
                                            (semantic_df["Personal Outdoor Space"] != "None")]

            # Return top results (already ranked by semantic similarity)
            if not semantic_df.empty:
                return _format_property_results(semantic_df.head(5))

    except FileNotFoundError:
        print("Warning: Pre-computed vectorstore not found. Run 'python -m src.vectorstore_setup' to create it.")
    except Exception as e:
        print(f"Warning: Error loading vectorstore: {e}")

    return "No properties found matching your criteria."


@tool("compare_prices")
def compare_prices(neighbourhood: str, df_path="data/listings_sample.csv"):
    """
    Average rent per neighbourhood with bedroom segmentation.
    Provides more accurate comparisons by grouping properties by bedroom count.
    """
    df = _load_property_dataframe()
    if df.empty:
        return f"No data available for {neighbourhood}."

    if neighbourhood is None:
        return "Please specify at least one area."

    tokens = [token.strip() for token in re.split(r"[,&;/]|\band\b", neighbourhood, flags=re.I) if token.strip()]
    if not tokens:
        tokens = [neighbourhood.strip()]

    normalized_targets = [_normalize_area_query(token) for token in tokens]
    normalized_targets = [target for target in normalized_targets if target]
    seen = set()
    normalized_targets = [t for t in normalized_targets if not (t in seen or seen.add(t))]
    if not normalized_targets:
        return f"No data available for {neighbourhood}."

    results = []
    missing = []

    for target in normalized_targets:
        mask = pd.Series(False, index=df.index)
        target_lower = target.lower()
        if "area" in df.columns:
            mask = mask | (df["area"].astype(str).str.lower() == target_lower)
        if "city" in df.columns:
            mask = mask | (df["city"].astype(str).str.lower() == target_lower)
        for col in ["neighbourhood"]:
            if col in df.columns:
                mask = mask | df[col].astype(str).str.contains(target, case=False, na=False)

        sub = df[mask]
        if sub.empty:
            missing.append(target)
            continue

        # Group by bedrooms for more accurate comparisons
        if "bedrooms_numeric" in sub.columns:
            bedroom_groups = sub.groupby("bedrooms_numeric")

            for bedrooms, group in bedroom_groups:
                if pd.isna(bedrooms):
                    continue

                price_series = group["price_numeric"].dropna()
                if price_series.empty:
                    continue

                # Calculate statistics for this bedroom segment
                if price_series.size == 1:
                    avg = price_series.iloc[0]
                    median = avg
                    min_price = avg
                    max_price = avg
                else:
                    # Trim outliers (5th-95th percentile)
                    q1 = price_series.quantile(0.05)
                    q3 = price_series.quantile(0.95)
                    trimmed = price_series[(price_series >= q1) & (price_series <= q3)]
                    if trimmed.empty:
                        trimmed = price_series

                    avg = trimmed.mean()
                    median = trimmed.median()
                    min_price = trimmed.min()
                    max_price = trimmed.max()

                results.append({
                    "area": target,
                    "bedrooms": int(bedrooms),
                    "average_rent": float(avg),
                    "median_rent": float(median),
                    "min_rent": float(min_price),
                    "max_rent": float(max_price),
                    "count": len(price_series)
                })
        else:
            # Fallback: Overall average if bedroom data not available
            price_series = sub["price_numeric"].dropna()
            if price_series.empty:
                missing.append(target)
                continue

            if price_series.size == 1:
                avg = price_series.iloc[0]
            else:
                q1 = price_series.quantile(0.05)
                q3 = price_series.quantile(0.95)
                trimmed = price_series[(price_series >= q1) & (price_series <= q3)]
                if trimmed.empty:
                    trimmed = price_series
                avg = trimmed.mean()

            results.append({
                "area": target,
                "bedrooms": "All",
                "average_rent": float(avg),
                "count": len(price_series)
            })

    if not results:
        missing_str = ", ".join(sorted(set(missing))) if missing else neighbourhood
        return f"No price data available for {missing_str}."

    df_results = pd.DataFrame(results)

    # Sort by area and bedrooms for readability
    if "bedrooms" in df_results.columns:
        df_results = df_results.sort_values(["area", "bedrooms"])

    # Convert to readable text format instead of DataFrame to avoid formatting issues
    output_lines = []

    for _, row in df_results.iterrows():
        area = row["area"]
        bedrooms = row.get("bedrooms", "All")
        avg_rent = row["average_rent"]

        if "median_rent" in row:
            # Detailed stats available
            median = row["median_rent"]
            min_rent = row["min_rent"]
            max_rent = row["max_rent"]
            count = row["count"]

            line = f"{area} ({bedrooms} bed): Average ${avg_rent:.0f}, Median ${median:.0f}, Range ${min_rent:.0f}-${max_rent:.0f} ({count} listings)"
        else:
            # Simple average only
            count = row.get("count", "")
            count_str = f" ({count} listings)" if count else ""
            line = f"{area} ({bedrooms} bed): Average ${avg_rent:.0f}{count_str}"

        output_lines.append(line)

    return "\n".join(output_lines) if output_lines else "No price data available."


@tool("area_lowest_rents")
def area_lowest_rents(areas: str = "", top_n: int = 5):
    """
    Find the lowest rent listing for each area.
    Provide a comma-separated list in `areas` to limit the search.
    """
    df = _load_property_dataframe()
    if df.empty:
        return "No property data available."

    if "area" not in df.columns or df["area"].isna().all():
        return "Area information is unavailable in the dataset."

    valid = df[(df["price_numeric"].notna()) & (df["area"].notna())].copy()
    if valid.empty:
        return "Price data is missing for all areas."

    valid["area"] = valid["area"].apply(normalize_area_name)
    valid = valid[valid["area"].notna()]

    requested = {
        _normalize_area_query(a.strip())
        for a in re.split(r"[;,]", areas)
        if a.strip()
    }
    requested = {area for area in requested if area}
    if requested:
        valid = valid[valid["area"].isin(requested)]
        if valid.empty:
            return f"No matching areas found for: {', '.join(sorted(requested))}"
    else:
        # Limit to top_n cheapest areas overall when no filter provided
        cheapest_areas = (
            valid.groupby("area")["price_numeric"].min().sort_values().head(top_n).index.tolist()
        )
        valid = valid[valid["area"].isin(cheapest_areas)]

    summaries = []
    for area in sorted(valid["area"].unique()):
        area_df = valid[valid["area"] == area]
        if area_df.empty:
            continue
        q1 = area_df["price_numeric"].quantile(0.05)
        trimmed_area = area_df[area_df["price_numeric"] >= q1]
        if trimmed_area.empty:
            trimmed_area = area_df
        idx = trimmed_area["price_numeric"].idxmin()
        row = trimmed_area.loc[idx]
        summaries.append(
            {
                "area": area,
                "address": row.get("address", "Unknown"),
                "bedrooms": row.get("bedrooms"),
                "bathrooms": row.get("bathrooms"),
                "price": float(row["price_numeric"]),
            }
        )

    if not summaries:
        return "No listings found for the specified areas."

    return pd.DataFrame(summaries)
