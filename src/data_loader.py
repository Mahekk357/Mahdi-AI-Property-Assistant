import pandas as pd
from langchain_community.document_loaders import DataFrameLoader

from src.data_utils import extract_city, normalize_area_name

def load_property_data(file_path: str):
    # Load CSV carefully to avoid encoding and delimiter issues
    df = pd.read_csv(file_path, encoding="utf-8", on_bad_lines="skip")

    # Derive city/area information directly from the address
    df["City"] = df["Address"].apply(extract_city).fillna("Unknown")
    df["Area"] = df["City"].apply(normalize_area_name).fillna("Unknown")

    # Combine key columns into one rich text field for semantic search
    # Include ALL important fields for better matching
    df["combined_text"] = (
        "Title: " + df["Title"].fillna("").astype(str) + "\n"
        + "Address: " + df["Address"].fillna("").astype(str) + "\n"
        + "City: " + df["City"].fillna("").astype(str) + "\n"
        + "Price: $" + df["Price($)"].fillna("").astype(str) + " per month\n"
        + "Bedrooms: " + df["Bedrooms"].fillna("").astype(str) + "\n"
        + "Bathrooms: " + df["Bathrooms"].fillna("").astype(str) + "\n"
        + "Building Type: " + df["Building Type"].fillna("").astype(str) + "\n"
        + "Parking Included: " + df["Parking Included"].fillna("").astype(str) + "\n"
        + "Pet Friendly: " + df["Pet Friendly"].fillna("").astype(str) + "\n"
        + "Furnished: " + df["Furnished"].fillna("").astype(str) + "\n"
        + "Size: " + df["Size (sqft)"].fillna("").astype(str) + " sqft\n"
        + "Amenities: " + df["Amenities"].fillna("").astype(str) + "\n"
        + "Air Conditioning: " + df["Air Conditioning"].fillna("").astype(str) + "\n"
        + "Description: " + df["Description"].fillna("").astype(str)
    )

    # Use LangChain's DataFrameLoader to treat each row as ONE complete document
    # NO CHUNKING - each property listing is atomic and should not be split
    loader = DataFrameLoader(df, page_content_column="combined_text")
    docs = loader.load()

    # Return documents directly without chunking
    # This preserves property integrity and improves semantic search accuracy
    return docs
