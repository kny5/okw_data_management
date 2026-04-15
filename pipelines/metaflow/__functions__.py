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

import numpy as np
import pandas as pd
import requests
from fuzzywuzzy import fuzz
from scipy.spatial import KDTree
from sklearn.cluster import DBSCAN
import spacy
from spacy.util import is_package

import matplotlib.colors as mcolors
import math

_original_to_rgba = mcolors.to_rgba


MODEL = "en_core_web_sm"
if not is_package(MODEL):
    spacy.cli.download(MODEL)

nlp = spacy.load(MODEL)


def _safe_to_rgba(c, alpha=None):
    try:

        if isinstance(c, float) and math.isnan(c):
            return (0.0, 0.0, 0.0, 0.0)
    except Exception:
        pass
    return _original_to_rgba(c, alpha)


mcolors.to_rgba = _safe_to_rgba


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

    @retry_on_exception(max_retries=5, backoff_factor=2)
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

    return inner()


def filter_points_by_proximity(df, radius=100, min_points=2):

    df = df.dropna(subset=["latitude", "longitude"])

    radius_in_degrees = radius / 111_139

    coordinates = df[["latitude", "longitude"]].to_numpy()

    clustering = DBSCAN(eps=radius_in_degrees, min_samples=1).fit(coordinates)
    labels = clustering.labels_

    filtered_points = []
    unique_points = set()  # Keep track of unique points to remove duplicates

    for label in np.unique(labels):

        cluster_points = coordinates[labels == label]
        cluster_df = df[labels == label]

        tree = KDTree(cluster_points)
        for i, point in enumerate(cluster_points):

            neighbors = tree.query_ball_point(point, radius_in_degrees)

            if len(neighbors) >= min_points:

                point_tuple = tuple(cluster_df.iloc[i][["latitude", "longitude"]])

                if point_tuple not in unique_points:
                    unique_points.add(point_tuple)
                    filtered_points.append(cluster_df.iloc[i])

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

    text = text.lower()

    text = re.sub(r"[^\w]", "", text)

    text = "".join(
        c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn"
    )

    ngrams = [text[i : i + n] for i in range(len(text) - n + 1)]

    unique_ngrams = sorted(set(ngrams))

    fingerprint = "".join(unique_ngrams)

    return fingerprint


def normalize_name(name):
    """Normalize names by removing punctuation, extra spaces, accents, and sorting words."""

    name = name.lower()

    name = re.sub(r"[^\w\s]", "", name)

    name = "".join(
        c for c in unicodedata.normalize("NFD", name) if unicodedata.category(c) != "Mn"
    )

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

    df["normalized_name"] = df["name"].apply(ngram_fingerprint)

    coordinates = df[["latitude", "longitude"]].to_numpy()
    db = DBSCAN(
        eps=distance_threshold / 6371000, min_samples=1, metric="haversine"
    ).fit(coordinates)
    df["cluster"] = db.labels_

    aggregated_data = []
    processed_names = set()

    for cluster_id, cluster_df in df.groupby("cluster"):
        cluster_df = cluster_df.reset_index(drop=True)

        for idx, row in cluster_df.iterrows():
            norm_name = row["normalized_name"]

            if norm_name not in processed_names:

                similar_rows = cluster_df[
                    cluster_df["normalized_name"].apply(
                        lambda n: (
                            fuzz.token_sort_ratio(norm_name, n) / 100.0
                            >= similarity_threshold
                        )
                    )
                ]

                aggregated_data.append(
                    {
                        "name": row["name"],
                        "latitude": row["latitude"],
                        "longitude": row["longitude"],
                        "web_url": row["web_url"],
                        "source": row["source"],
                        "record_source_url": row["record_source_url"],
                    }
                )

                processed_names.update(similar_rows["normalized_name"])

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

    df["name_fingerprint"] = df["name"].apply(lambda x: ngram_fingerprint(x, n))

    coordinates = df[["latitude", "longitude"]].to_numpy()
    db = DBSCAN(
        eps=distance_threshold / 6371000, min_samples=1, metric="haversine"
    ).fit(coordinates)
    df["cluster"] = db.labels_

    aggregated_data = []

    for cluster_id, cluster_df in df.groupby("cluster"):
        cluster_df = cluster_df.reset_index(drop=True)
        fingerprint_groups = cluster_df.groupby("name_fingerprint")

        for fingerprint, group in fingerprint_groups:

            first_row = group.iloc[0]

            occurrences = group[["url", "source"]].to_dict(orient="records")
            print(occurrences.shape)
            aggregated_data.append(
                {
                    "name": first_row["name"],
                    "latitude": first_row["latitude"],
                    "longitude": first_row["longitude"],
                    "occurrences": occurrences,
                }
            )

    aggregated_df = pd.DataFrame(aggregated_data)
    return aggregated_df


def extract_link(html_text):

    match = re.search(r'href="(https?://[^"]+)"', html_text)
    return match.group(1) if match else None


SECRET_KEY = "kny5"


def obfuscate_text(text, key=SECRET_KEY):

    if isinstance(text, (list, tuple, set)):
        text = ", ".join([str(item) for item in text])
    elif hasattr(text, "__iter__") and not isinstance(text, str):

        text = ", ".join([str(item) for item in text])

    if pd.isna(text):
        return ""

    if not str(text).strip():
        return ""

    text_bytes = str(text).encode("utf-8")
    key_bytes = key.encode("utf-8")

    xored = bytes([b ^ key_bytes[i % len(key_bytes)] for i, b in enumerate(text_bytes)])
    return base64.b64encode(xored).decode("utf-8")


def generate_blake2_uid(row):
    """Generates a Blake2 hash for a given row."""

    combined_string = f"{row['latitude']}:{row['longitude']}:{row['name']}"

    encoded_string = combined_string.encode("utf-8")

    return blake2b(encoded_string, digest_size=8).hexdigest()


def inject_secure_map_logic(html_string, encrypted_payload):
    """
    Erases the plaintext data, injects a password UI overlay,
    and decrypts the map data purely based on user input.
    """

    cleansed_html = re.sub(
        r"var\s+data\s*=\s*\[.*?\];",
        "var data = []; /* Plaintext wiped by Python Encryptor */",
        html_string,
        flags=re.DOTALL,
    )

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

    
    document.getElementById('unlock-btn').addEventListener('click', function() {{
        let userSecretKey = document.getElementById('map-key-input').value;
        let rawJsonString = decryptData("{encrypted_payload}", userSecretKey);
        
        let mapData;
        
        
        try {{
            
            let cleanJsonString = rawJsonString.substring(rawJsonString.indexOf('['), rawJsonString.lastIndexOf(']') + 1);
            mapData = JSON.parse(cleanJsonString);
            
        }} catch (parseError) {{
           
            console.error("Password failed or JSON is corrupt:", parseError);
            document.getElementById('error-msg').style.display = 'block';
            return;
        }}

        
        document.getElementById('secure-overlay').style.display = 'none'; 
        
    
        try {{
            renderSecureMap(mapData, userSecretKey);
        }} catch (renderError) {{
            
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

            
            let marker = L.marker([row.latitude, row.longitude]);
            marker.bindPopup("<div style='font-family: monospace; color: #888;'>Decrypting...</div>");

            
            marker.on('click', function(e) {{
                let popup = e.target.getPopup();
                
                let realName = decryptData(row.name, validKey);
                let realUrl = decryptData(row.web_url, validKey);

                
                let secureContent = $(`<div id='pop_content' class='pop_custom' style='width: 100.0%; height: 100.0%;'>
                                        <a href="${{realUrl}}" target="_blank"><strong>${{realName}}</strong></a>
                                      </div>`)[0];
                
                popup.setContent(secureContent);
            }});
            secureCluster.addLayer(marker);
        }}
        
        
        myMap.addLayer(secureCluster);
    }}
    </script>
    """

    final_html = cleansed_html.replace("</body>", secure_js + "\n</body>")
    return final_html


def img_uri(img):
    image_file = img
    with open(image_file, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("UTF-8")
    return f"data:image/png;base64,{encoded}"


# Initialize Local Overrides
# Single lookup table. Priority: exact full column name → core concept → Schema.org fallback.
# Prefix keys with '*' to mark them as core-concept matches (post-NLP extraction).
# No prefix = exact full column name match (checked first, before NLP).

FIELD_TAXONOMY = {
    # ── IDENTITY ──────────────────────────────────────────────
    "*name": "Identifier",
    "*title": "Identifier",
    "*label": "Identifier",
    "*makery": "Identifier",
    "*parent": "Identifier",
    "*id": "Identifier",
    "*fid": "Identifier",
    "*uuid": "Identifier",
    "*uid": "Identifier",
    "*nsid": "Identifier",
    "*slug": "Identifier",
    "*ids": "Identifier",
    "*blurb": "Identifier",
    "*courte": "Identifier",
    # ── COLLECTION METADATA ─────────────────────────────────────────────
    "*updated": "collectionMetadata",
    "*created": "collectionMetadata",
    "*delete": "collectionMetadata",
    "*sourcekey": "collectionMetadata",
    "*createdat": "collectionMetadata",
    "*updatedat": "collectionMetadata",
    "*start": "collectionMetadata",
    "*end": "collectionMetadata",
    "*today": "collectionMetadata",
    "*date": "collectionMetadata",
    "*enumerator": "collectionMetadata",
    "*form": "collectionMetadata",
    # ── REGIONAL LOCATION ──────────────────────────────────────────────
    "*country": "RegionalLocation",
    "*governorate": "RegionalLocation",
    "*village": "RegionalLocation",
    "*district": "RegionalLocation",
    "*county": "RegionalLocation",
    "*city": "RegionalLocation",
    "*state": "RegionalLocation",
    "county": "RegionalLocation",
    "subcounty": "RegionalLocation",
    "dbdistrict": "RegionalLocation",
    # Address LOCATION (non-regional, more specific)
    "*parish": "Location",
    "*postcode": "Location",
    "*zip": "Location",
    "*address": "Location",
    "*street": "Location",
    "*fulladdress": "Location",
    "*code": "Location",
    "*location": "Location",
    # ── COORDINATES (some times its a rounded position)
    "*latitude": "Coordinates",
    "*longitude": "Coordinates",
    "*lat": "Coordinates",
    "*long": "Coordinates",
    "*lng": "Coordinates",
    "*altitude": "Coordinates",
    "*accuracy": "Coordinates",
    # ── CONTACT ───────────────────────────────────────────────
    "*phone": "Contact",
    "*telephone": "Contact",
    "*email": "Contact",
    "*contact": "Contact",
    "*subscriberemails": "Contact",
    "*jobtitle": "Contact",
    # ── ONLINE PRESENCE ───────────────────────────────────────
    "*url": "OnlinePresence",
    "*link": "OnlinePresence",
    "*website": "OnlinePresence",
    "*web": "OnlinePresence",
    "*twitter": "OnlinePresence",
    "*facebook": "OnlinePresence",
    "*instagram": "OnlinePresence",
    "*linkedin": "OnlinePresence",
    "*youtube": "OnlinePresence",
    "*flickr": "OnlinePresence",
    "*pinterest": "OnlinePresence",
    "*social": "OnlinePresence",
    "*fb": "OnlinePresence",
    "*insta": "OnlinePresence",
    "*links": "OnlinePresence",
    # ── DESCRIPTION ───────────────────────────────────────────
    "*description": "Description",
    "*intro": "Description",
    "*desc": "Description",
    "*bio": "Description",
    "*text": "Description",
    # ── MEDIA ─────────────────────────────────────────────────
    "*image": "Media",
    "*images": "Media",
    "*img": "Media",
    "*photo": "Media",
    "*portrait": "Media",
    "*logo": "Media",
    "*icon": "Media",
    "*film": "Media",
    "*video": "Media",
    "*background": "Media",
    # ── OPERATIONAL STATUS ────────────────────────────────────
    "*status": "OperationalStatus",
    "*condition": "OperationalStatus",
    "*activity": "OperationalStatus",
    "*ready": "OperationalStatus",
    # ── FACILITY METRICS ──────────────────────────────────────
    "*capacity": "FacilityMetrics",
    "*headcount": "FacilityMetrics",
    "*staff": "FacilityMetrics",
    "*surface": "FacilityMetrics",
    "*size": "FacilityMetrics",
    "*floor": "FacilityMetrics",
    "*there": "FacilityMetrics",
    "*number": "FacilityMetrics",
    "*year": "FacilityMetrics",
    "*founded": "FacilityMetrics",
    "*with": "FacilityMetrics",
    "*count": "FacilityMetrics",
    # ── OPERATING SCHEDULE ────────────────────────────────────
    "*hours": "Schedule",
    "*openhours": "Schedule",
    "*days": "Schedule",
    "*schedule": "Schedule",
    "*time": "Schedule",
    "*turnaround": "Schedule",
    # ── MANUFACTURING PROCESS ─────────────────────────────────
    "*process": "ManufacturingProcess",
    "*production": "ManufacturingProcess",
    "*run": "ManufacturingProcess",
    "*batch": "ManufacturingProcess",
    "*sample": "ManufacturingProcess",
    "*order": "ManufacturingProcess",
    "*types": "ManufacturingProcess",
    "*processes": "ManufacturingProcess",
    "capabilities": "ManufacturingProcess",
    "cats": "ManufacturingProcess",
    "*capabilities": "ManufacturingProcess",
    "*cats": "ManufacturingProcess",
    "*type": "ManufacturingProcess",
    "*category": "ManufacturingProcess",
    "*categories": "ManufacturingProcess",
    "*kind": "ManufacturingProcess",
    "*categoriesfull": "ManufacturingProcess",
    # ── EQUIPMENT ─────────────────────────────────────────────
    "*equipment": "Equipment",
    "*machine": "Equipment",
    "*generator": "Equipment",
    "*dock": "Equipment",
    "*maintenance": "Equipment",
    "*power": "Equipment",
    "*supply": "Equipment",
    "*model": "Equipment",
    "*serial": "Equipment",
    "*maker": "Equipment",
    "*machines": "Equipment",
    "*ups": "Equipment",
    # ── MATERIALS ─────────────────────────────────────────────
    "*material": "Material",
    "*materials": "Material",
    "*plastic": "Material",
    "*metal": "Material",
    "*wood": "Material",
    "*elastomer": "Material",
    "*ceramics": "Material",
    "*electronics": "Material",
    "*others": "Material",
    "*m_id": "Material",
    # ── FACILITY ACCESS ───────────────────────────────────────
    "*access": "FacilityAccess",
    "*wheelchair": "FacilityAccess",
    "*road": "FacilityAccess",
    # ── ORGANIZATION ──────────────────────────────────────────
    "*affiliation": "Organization",
    "*partner": "Organization",
    "*funder": "Organization",
    "*owner": "Organization",
    "*gestion": "Organization",
    # ── QUALITY / COMPLIANCE ──────────────────────────────────
    "*certification": "Compliance",
    "*certifications": "Compliance",
    # ── PRODUCT ───────────────────────────────────────────────
    "*product": "Product",
    "*products": "Product",
    # ── NOISE (excluded from analysis) ────────────────────────
    "*nan": "_noise",
    "*bucket": "_noise",
    "aai": "_noise",
    "icm": "_noise",
    "*at": "_noise",
    "*d": "_noise",
    "*i": "_noise",
    "*nr": "_noise",
}

COUNTRY_SUFFIXES = ["ke", "us", "fr", "de", "in", "cn", "jp", "br", "ru", "za"]
ACRONYM_MIN_LENGTH = 3


def extract_core_concept(column_name):
    clean = str(column_name).lower()
    clean = clean.split(".")[0]
    clean = re.sub(r"\d+$", "", clean)

    parts = clean.split("_")
    if len(parts) > 1 and parts[-1] in COUNTRY_SUFFIXES:
        parts = parts[:-1]
    clean = "_".join(parts)

    clean = clean.replace("-", " ").replace("_", " ").strip()

    if not clean:
        return str(column_name).lower()

    if len(clean.split()) == 1:
        return clean

    shortest_word = min(len(w) for w in clean.split())
    doc = nlp(clean)

    for chunk in doc.noun_chunks:
        root = chunk.root.text
        if len(root) >= max(shortest_word, 3):
            return root

    nouns = [token.text for token in doc if token.pos_ in ["NOUN", "PROPN"]]
    if nouns:
        candidate = nouns[-1]
        if len(candidate) >= max(shortest_word, 3):
            return candidate

    words = [w for w in clean.split() if len(w) >= 3]
    return words[-1] if words else clean.split()[-1]


def get_schema_taxonomy(column_name, init_data):
    """Classifies a column name using the loaded Schema.org DataFrames."""

    types_df = init_data["types_url"]
    props_df = init_data["props_url"]

    clean_name = str(column_name).lower().replace("_", "").replace(" ", "")

    prop_match = props_df[props_df["label"].str.lower() == clean_name]
    if not prop_match.empty:
        domain_raw = str(prop_match.iloc[0]["domainIncludes"]).split(",")[0]
        return domain_raw.replace("https://schema.org/", "")

    type_match = types_df[types_df["label"].str.lower() == clean_name]
    if not type_match.empty:
        parent_raw = str(type_match.iloc[0]["subTypeOf"]).split(",")[0]
        return parent_raw.replace("https://schema.org/", "")

    return f"Unclassified: {column_name}"


def get_taxonomy_for_pipeline(column_name, init_data):
    clean = str(column_name).lower().split(".")[0]  # strip dot-notation suffix
    clean = re.sub(r"\d+$", "", clean)  # strip trailing numbers
    clean = clean.replace("-", "_").strip()

    if clean in FIELD_TAXONOMY:
        return FIELD_TAXONOMY[clean]

    core = extract_core_concept(clean)
    prefixed = f"*{core}"
    if prefixed in FIELD_TAXONOMY:
        return FIELD_TAXONOMY[prefixed]

    return get_schema_taxonomy(core, init_data)


def inspect_classification(init_data, dataset):
    """
    Returns a readable breakdown of every column → class mapping,
    grouped by class, for human review.
    """
    full_map = {}
    for name, df in dataset.items():
        full_map[name] = {}
        for col in df["data_input"].columns:
            tax = get_taxonomy_for_pipeline(col, init_data)
            full_map[name][col] = tax

    for source, mapping in full_map.items():
        print(f"\n{'═'*50}")
        print(f"  {source}")
        print(f"{'═'*50}")

        by_class = {}
        for col, cls in mapping.items():
            by_class.setdefault(cls, []).append(col)

        for cls, cols in sorted(by_class.items()):
            flag = " ⚠" if cls.startswith("Unclassified") or cls == "nan" else ""
            print(f"  [{cls}]{flag}")
            for col in cols:
                print(f"      {col}")

    return full_map
