"""
Created on Wed Nov 13 22:38:11 2024

@author: kny5
"""

import hashlib
import re
import unicodedata


def normalize_text(text):
    """
    Normalizes text by removing accents, converting to lowercase,
    stripping whitespace, and removing non-alphanumeric characters.
    """
    text = str(text)
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ASCII", "ignore").decode("ASCII")
    text = text.lower()
    text = text.strip()
    text = re.sub(r"\W+", "", text)  # Remove non-alphanumeric characters
    return text


def generate_unique_identifier(row):
    """
    Generates a deterministic unique identifier for each entry,
    combining the specified fields and hashing them.
    """

    lat = round(float(row["lat"]), 2)
    long = round(float(row["long"]), 2)

    lat_str = str(lat)
    long_str = str(long)

    lat_norm = normalize_text(lat_str)
    long_norm = normalize_text(long_str)
    country = normalize_text(row["country"])  # Should be ISO alpha-2 code
    name = normalize_text(row["name"])
    town = normalize_text(row["town"])  # Replace with town code if available
    type_ = normalize_text(row["type"])

    unique_string = f"{lat_norm}|{long_norm}|{country}|{name}|{town}|{type_}"

    uid_hash = hashlib.sha256(unique_string.encode("utf-8")).hexdigest()

    uid = uid_hash[:12]

    unique_identifier = f"{uid}"

    return unique_identifier
