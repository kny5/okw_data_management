# @title
import requests
import os
%cd data
def download_nasa_firms_data():
    """
    Downloads the last 24 hours of global active fire data from NASA FIRMS.
    No API key is required for these public rolling 24h CSVs.
    """
    print("[*] Starting NASA FIRMS 24-hour data download...")

    # The direct URLs for the 24-hour global CSV files
    datasets = {
        "MODIS_24h": "https://firms.modaps.eosdis.nasa.gov/data/active_fire/modis-c6.1/csv/MODIS_C6_1_Global_24h.csv",
        "VIIRS_24h": "https://firms.modaps.eosdis.nasa.gov/data/active_fire/suomi-npp-viirs-c2/csv/SUOMI_VIIRS_C2_Global_24h.csv"
    }

    for name, url in datasets.items():
        try:
            print(f"[*] Downloading {name}...")
            response = requests.get(url, timeout=30)
            response.raise_for_status() # Check for HTTP errors

            filename = f"{name}.csv"
            with open(filename, "w", encoding="utf-8") as file:
                file.write(response.text)
                
            print(f"[+] Saved successfully to {filename}")

        except requests.exceptions.RequestException as e:
            print(f"[!] Failed to download {name}: {e}")

if __name__ == "__main__":
    download_nasa_firms_data()
    print("[*] All downloads complete!")