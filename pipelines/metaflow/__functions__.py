#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Oct 31 07:51:41 2024

@author: kny5
"""

import functools
import logging
import re
import unicodedata
from time import sleep
from hashlib import blake2b
import base64

import _blake2

import numpy as np
import pandas as pd
import requests
from fuzzywuzzy import fuzz
from scipy.spatial import KDTree
from sklearn.cluster import DBSCAN


def retry_on_exception(max_retries=3, backoff_factor=1):
    """
    Decorator to retry a function on exception.

    Args:
        max_retries:
        backoff_factor:
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            while True:
                try:
                    return func(
                        *args, **kwargs
                    )  # Execute and return the function result
                except requests.exceptions.RequestException as e:
                    if retries < max_retries:
                        sleep(backoff_factor * (retries + 1))
                        retries += 1
                    else:
                        raise e

        return wrapper

    return decorator


def req_data(
    url,
    timer=1,
    verbose=False,
    head={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0"
    },
):
    """
    Sends a GET request to the specified URL and returns the response.

    Args:
        url:
        timer:
        recursive:
        verbose:
    """

    @retry_on_exception(
        max_retries=5, backoff_factor=2
    )  # Increase max retries and backoff factor
    def inner():
        response = requests.get(url, headers=head)
        if response.status_code == 200:
            sleep(timer)
            if verbose:
                logging.info(f"URL: {url}")
                logging.info(f"Status Code: {response.status_code}")
            return response
        else:
            logging.error(f"Error Response: {response.status_code} ({url})")
            raise Exception("Request failed")

    return inner()  # Directly return the response


def marsh_json(dataframe):
    from data_models import ParserSchema

    _schema = ParserSchema()

    location_json_mapping = []
    for index, row in dataframe.iterrows():
        data_dict = {
            "latitude": row["latitude"],
            "longitude": row["longitude"],
            "zip_code": row["postal_code"],
            "extended": row["address_1"],
            "country": row["country_code"],
            "state_region": row["county"],
            "city_town": row["city"],
            "org_id": row["org_id"],
            "description": "fablab",
            "name": row["name"],
            "url": row["url"],
        }
        location_json_mapping.append(_schema.dumping(data_dict))

    return location_json_mapping


def filter_points_by_proximity(df, radius=100, min_points=2):
    # Drop rows with missing values in 'latitude' or 'longitude'
    df = df.dropna(subset=["latitude", "longitude"])

    # Convert radius from meters to degrees
    # Approximation for latitude/longitude degrees
    radius_in_degrees = radius / 111_139

    # Step 1: Extract latitude and longitude as a 2D numpy array
    coordinates = df[["latitude", "longitude"]].to_numpy()

    # Step 2: Cluster points with DBSCAN to find nearby groups
    clustering = DBSCAN(eps=radius_in_degrees, min_samples=1).fit(coordinates)
    labels = clustering.labels_

    # Step 3: Filter points based on proximity count within each cluster
    filtered_points = []
    unique_points = set()  # Keep track of unique points to remove duplicates

    for label in np.unique(labels):
        # Select points and subset of DataFrame in this cluster
        cluster_points = coordinates[labels == label]
        cluster_df = df[labels == label]

        # Use KDTree for efficient neighbor lookup within the cluster
        tree = KDTree(cluster_points)
        for i, point in enumerate(cluster_points):
            # Get neighbors within the 10-meter radius
            neighbors = tree.query_ball_point(point, radius_in_degrees)

            # Filter if it has enough nearby points
            if len(neighbors) >= min_points:
                # Convert the point to a tuple (latitude, longitude) for
                # hashing
                point_tuple = tuple(cluster_df.iloc[i][["latitude", "longitude"]])

                # Check for duplicates; keep only the latest
                if point_tuple not in unique_points:
                    unique_points.add(point_tuple)
                    filtered_points.append(cluster_df.iloc[i])

    # Return the filtered, non-duplicate points as a DataFrame
    return pd.DataFrame(filtered_points)


def iter_request(url):
    data = []
    x = 0

    while True:
        response = requests.get(url.format(n=x))
        json_data = response.json()
        if not json_data:
            break
        data += json_data
        x += 1
        print("Pages: {p}".format(p=x))
        print("Entries: {e}".format(e=len(data)))
    return data


class ReverseGeocode:
    column_names = [
        "geonameid",
        "name",
        "asciiname",
        "alternatenames",
        "latitude",
        "longitude",
        "feature class",
        "feature code",
        "country code",
        "cc2",
        "admin1 code",
        "admin2 code",
        "admin3 code",
        "admin4 code",
        "population",
        "elevation",
        "dem",
        "timezone",
        "modification date",
    ]

    def __init__(self, dataframe, output=["cc2", "city"]):
        self.df = dataframe.dropna(subset=["latitude", "longitude"])
        read_cities = pd.read_csv(
            "data/cities500.txt", names=self.column_names, delimiter="\t"
        )
        self.geocodes = read_cities[
            ["name", "country code", "latitude", "longitude", "timezone"]
        ].rename(columns={"country code": "cc2"})
        # Initialize KDTree once for fast lookups
        self.tree = KDTree(self.geocodes[["latitude", "longitude"]])

    def nearest_neighbor(self, latitude, longitude):
        """Get nearest location info based on latitude and longitude."""
        _, idx = self.tree.query([latitude, longitude])
        row = self.geocodes.iloc[idx]
        return row["cc2"], row["name"], row["timezone"]

    def get(self):
        """Process merged data for reverse geocoding."""
        self.df[["cc2", "city", "timezone"]] = self.df.apply(
            lambda row: pd.Series(
                self.nearest_neighbor(row["latitude"], row["longitude"])
            ),
            axis=1,
        )
        self.df["continent"] = self.df["timezone"].str.split("/").str[0]
        return self.df


def ngram_fingerprint(text, n=3):
    """
    Generate an n-gram fingerprint for a given text following specific normalization steps.

    Steps:
        1. Change all characters to lowercase.
        2. Remove all punctuation, whitespace, and control characters.
        3. Obtain all n-grams of the specified length.
        4. Sort the n-grams and remove duplicates.
        5. Join the sorted n-grams back together.
        6. Normalize extended Western characters to their ASCII representation.

    Parameters:
        text (str): The input text to be fingerprinted.
        n (int): The size of n-grams.

    Returns:
        str: The n-gram fingerprint.
    """
    # Step 1: Change all characters to lowercase
    text = text.lower()

    # Step 2: Remove all punctuation, whitespace, and control characters
    text = re.sub(r"[^\w]", "", text)

    # Step 3: Normalize extended Western characters to their ASCII
    # representation
    text = "".join(
        c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn"
    )

    # Step 4: Obtain all n-grams
    ngrams = [text[i : i + n] for i in range(len(text) - n + 1)]

    # Step 5: Sort the n-grams and remove duplicates
    unique_ngrams = sorted(set(ngrams))

    # Step 6: Join the sorted n-grams back together
    fingerprint = "".join(unique_ngrams)

    return fingerprint


def normalize_name(name):
    """Normalize names by removing punctuation, extra spaces, accents, and sorting words."""
    # Convert to lowercase
    name = name.lower()
    # Remove punctuation and extra spaces
    name = re.sub(r"[^\w\s]", "", name)
    # Remove accents
    name = "".join(
        c for c in unicodedata.normalize("NFD", name) if unicodedata.category(c) != "Mn"
    )
    # Sort words to handle reordering
    name = " ".join(sorted(name.split()))
    return name


def cluster_and_aggregate(df, distance_threshold=100, similarity_threshold=0.8):
    """
    Clusters GPS points and aggregates URLs and sources of similar locations.

    Parameters:
        df (pd.DataFrame): DataFrame with columns 'name', 'lat', 'long', 'url', and 'source'.
        distance_threshold (float): Maximum distance (in meters) for clustering.
        similarity_threshold (float): Minimum similarity ratio (0.0 - 1.0) for names to be considered similar.

    Returns:
        pd.DataFrame: DataFrame with columns 'name', 'lat', 'long', and 'occurrences', where occurrences
                      is a list of dictionaries containing 'url' and 'source' for each similar occurrence.
    """
    # Step 1: Normalize names in the DataFrame
    df["normalized_name"] = df["name"].apply(ngram_fingerprint)

    # Step 2: Cluster based on geographical coordinates using DBSCAN
    coordinates = df[["latitude", "longitude"]].to_numpy()
    db = DBSCAN(
        eps=distance_threshold / 6371000, min_samples=1, metric="haversine"
    ).fit(coordinates)
    df["cluster"] = db.labels_

    # Step 3: Group by cluster and process each cluster
    aggregated_data = []
    processed_names = set()  # Track processed names

    for cluster_id, cluster_df in df.groupby("cluster"):
        cluster_df = cluster_df.reset_index(drop=True)

        for idx, row in cluster_df.iterrows():
            norm_name = row["normalized_name"]

            # Only process if the normalized name is not in processed_names
            if norm_name not in processed_names:
                # Filter for similar normalized names within the cluster
                similar_rows = cluster_df[
                    cluster_df["normalized_name"].apply(
                        lambda n: (
                            fuzz.token_sort_ratio(norm_name, n) / 100.0
                            >= similarity_threshold
                        )
                    )
                ]

                # Collect URLs and sources for each similar name

                aggregated_data.append(
                    {
                        "name": row["name"],
                        "latitude": row["latitude"],
                        "longitude": row["longitude"],
                        "web_url": row["web_url"],
                    }
                )

                # Add processed names to avoid duplications
                processed_names.update(similar_rows["normalized_name"])

    # Convert to DataFrame for output
    aggregated_df = pd.DataFrame(aggregated_data)
    return aggregated_df


def cluster_and_key_collision(df, distance_threshold=100, n=3):
    """
    Clusters GPS points, applies n-gram fingerprinting for collision detection, and aggregates URLs and sources.

    Parameters:
        df (pd.DataFrame): DataFrame with columns 'name', 'lat', 'long', 'url', and 'source'.
        distance_threshold (float): Maximum distance (in meters) for clustering.
        n (int): The n-gram size for fingerprinting.

    Returns:
        pd.DataFrame: DataFrame with columns 'name', 'lat', 'long', and 'occurrences', where occurrences
                      is a list of dictionaries containing 'url' and 'source' for each similar occurrence.
    """
    # Step 1: Apply n-gram fingerprinting to the 'name' column
    df["name_fingerprint"] = df["name"].apply(lambda x: ngram_fingerprint(x, n))

    # Step 2: Cluster based on geographical coordinates using DBSCAN
    coordinates = df[["latitude", "longitude"]].to_numpy()
    db = DBSCAN(
        eps=distance_threshold / 6371000, min_samples=1, metric="haversine"
    ).fit(coordinates)
    df["cluster"] = db.labels_

    # Step 3: Group by cluster and process each cluster
    aggregated_data = []

    for cluster_id, cluster_df in df.groupby("cluster"):
        cluster_df = cluster_df.reset_index(drop=True)
        fingerprint_groups = cluster_df.groupby("name_fingerprint")

        for fingerprint, group in fingerprint_groups:
            # Get the first occurrence for latitude and longitude
            first_row = group.iloc[0]

            # Collect URLs and sources for each entry with the same fingerprint
            occurrences = group[['url', 'source']].to_dict(orient='records')
            print(occurrences.shape)
            aggregated_data.append(
                {
                    "name": first_row["name"],
                    "latitude": first_row["latitude"],
                    "longitude": first_row["longitude"],
                    'occurrences': occurrences
                }
            )

    # Convert to DataFrame for output
    aggregated_df = pd.DataFrame(aggregated_data)
    return aggregated_df


def extract_link(html_text):
    # Search for an external https link
    match = re.search(r'href="(https?://[^"]+)"', html_text)
    return match.group(1) if match else None


# This must match the key in your JavaScript!
SECRET_KEY = "kny5"

def obfuscate_text(text, key=SECRET_KEY):
    # 1. Flatten lists or numpy arrays into a single string
    if isinstance(text, (list, tuple, set)):
        text = ", ".join([str(item) for item in text])
    elif hasattr(text, '__iter__') and not isinstance(text, str):
        # Catches other iterables like numpy arrays
        text = ", ".join([str(item) for item in text])
        
    # 2. Now that we guarantee 'text' is a single value or string, 
    # we can safely check for NaNs
    if pd.isna(text): 
        return ""
        
    # 3. Check for empty strings after cleaning
    if not str(text).strip():
        return ""
        
    # 4. Convert to bytes AFTER cleaning!
    text_bytes = str(text).encode('utf-8')
    key_bytes = key.encode('utf-8')
        
    # 5. Encrypt!
    xored = bytes([b ^ key_bytes[i % len(key_bytes)] for i, b in enumerate(text_bytes)])
    return base64.b64encode(xored).decode('utf-8')

def generate_blake2_uid(row):
    """Generates a Blake2 hash for a given row."""
    # Concatenate values with a separator to avoid collisions (e.g., hash('01') == hash('0'+'1'))
    # Ensure all values are converted to string
    combined_string = f"{row['latitude']}:{row['longitude']}:{row['name']}"
    # Encode the string to bytes before hashing
    encoded_string = combined_string.encode('utf-8')
    # Calculate the Blake2 hash and return the hexadecimal digest
    return blake2b(encoded_string, digest_size=8).hexdigest()


def inject_secure_map_logic(html_string, encrypted_payload):
    """
    Erases the plaintext data, injects a password UI overlay, 
    and decrypts the map data purely based on user input.
    """
    
    # 1. WIPE THE PLAINTEXT DATA
    cleansed_html = re.sub(
        r"var\s+data\s*=\s*\[.*?\];", 
        "var data = []; /* Plaintext wiped by Python Encryptor */", 
        html_string, 
        flags=re.DOTALL
    )

    # 2. PREPARE THE SECURE JAVASCRIPT & UI OVERLAY
    secure_js = f"""
    <div id="secure-overlay" style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; z-index: 99999; background: rgba(0, 0, 0, 0.85); display: flex; justify-content: center; align-items: center; font-family: sans-serif;">
        <div style="background: white; padding: 30px; border-radius: 8px; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.5); width: 300px;">
            <h3 style="margin-top: 0; color: #333;">Secure Map</h3>
            <p style="font-size: 14px; color: #666;">Please enter the decryption key to view this data.</p>
            <input type="password" id="map-key-input" style="width: 100%; padding: 8px; margin: 10px 0; border: 1px solid #ccc; border-radius: 4px;" placeholder="Enter Key..." />
            <button id="unlock-btn" style="width: 100%; padding: 10px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; font-weight: bold;">Unlock Map</button>
            <p id="error-msg" style="color: red; font-size: 13px; display: none; margin-bottom: 0;">Incorrect key. Please try again.</p>
        </div>
    </div>

    <script>
    function decryptData(b64Text, key) {{
        try {{
            if (!b64Text) return "";
            
            while (b64Text.length % 4 !== 0) {{
                b64Text += "=";
            }}
            
            let binaryStr = atob(b64Text);
            
            let keyBytes = new TextEncoder().encode(key);
            
            let xoredBytes = new Uint8Array(binaryStr.length);
            for (let i = 0; i < binaryStr.length; i++) {{
                xoredBytes[i] = binaryStr.charCodeAt(i) ^ keyBytes[i % keyBytes.length];
            }}
            return new TextDecoder().decode(xoredBytes);
        }} catch (e) {{
            return "Decryption Error";
        }}
    }}

    // --- 2. UI INTERACTION & RENDERING LOGIC ---
    document.getElementById('unlock-btn').addEventListener('click', function() {{
        let userSecretKey = document.getElementById('map-key-input').value;
        let rawJsonString = decryptData("{encrypted_payload}", userSecretKey);
        
        let mapData;
        
        // --- TEST 1: IS THE JSON VALID? ---
        try {{
            // Snip both leading AND trailing garbage just in case
            let cleanJsonString = rawJsonString.substring(rawJsonString.indexOf('['), rawJsonString.lastIndexOf(']') + 1);
            mapData = JSON.parse(cleanJsonString);
            
        }} catch (parseError) {{
            // If it fails here, the password was genuinely wrong
            console.error("Password failed or JSON is corrupt:", parseError);
            document.getElementById('error-msg').style.display = 'block';
            return; // Stop the script
        }}

        // --- IF WE REACH HERE, THE PASSWORD IS CORRECT! ---
        document.getElementById('secure-overlay').style.display = 'none'; // Hide the login box
        
        // --- TEST 2: IS THE MAP CRASHING? ---
        try {{
            renderSecureMap(mapData, userSecretKey);
        }} catch (renderError) {{
            // If it fails here, your custom JS or Leaflet is crashing!
            console.error("The map crashed while trying to draw the pins:");
            console.error(renderError);
        }}
    }});

    document.getElementById('map-key-input').addEventListener('keypress', function(e) {{
        if (e.key === 'Enter') document.getElementById('unlock-btn').click();
    }});

    function renderSecureMap(mapData, validKey) {{
        var myMap;
        for (var key in window) {{
            if (window[key] && window[key] instanceof L.Map) {{
                myMap = window[key];
                break;
            }}
        }}
        
        if (!myMap) return;

        let secureCluster = L.markerClusterGroup({{ maxClusterRadius: 40 }});

        for (let i = 0; i < mapData.length; i++) {{
            let row = mapData[i];
            
            if (!row.latitude || !row.longitude) continue;

            // 1. BRIDGE TO YOUR EXTERNAL JS:
            // Format the object back into the array your script expects
            let marker = L.marker([row.latitude, row.longitude]);
            marker.bindPopup("<div style='font-family: monospace; color: #888;'>Decrypting...</div>");

            // 3. SECURE OVERRIDE: 
            // Intercept the click to decrypt the text and rewrite the popup on the fly
            marker.on('click', function(e) {{
                let popup = e.target.getPopup();
                
                let realName = decryptData(row.name, validKey);
                let realUrl = decryptData(row.web_url, validKey);

                // Rebuild your exact jQuery template with the clean text
                let secureContent = $(`<div id='pop_content' class='pop_custom' style='width: 100.0%; height: 100.0%;'>
                                        <a href="${{realUrl}}" target="_blank"><strong>${{realName}}</strong></a>
                                      </div>`)[0];
                
                popup.setContent(secureContent);
            }});
            secureCluster.addLayer(marker);
        }}
        
        // FIX 3: Add the cluster layer back to the main map!
        myMap.addLayer(secureCluster);
    }}
    </script>
    """

    final_html = cleansed_html.replace("</body>", secure_js + "\n</body>")
    return final_html