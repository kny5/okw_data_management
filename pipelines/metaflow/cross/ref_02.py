#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import requests
import pandas as pd
from pathlib import Path

# Dynamically add parent directory to path so imports work perfectly
parent_dir = str(Path(__file__).resolve().parent.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from __visualisations__ import Plot, Tabular
from metaflow import FlowSpec, Parameter, card, step

class Ref_02(FlowSpec):
    """
    Downloads the latest global Air Quality data from the OpenAQ v3 API.
    Generates a heatmap of a specific pollutant.
    """
    # V3 Requires an API Key! 
    # Run with: python flow.py run --api_key "YOUR_KEY" --pollutant "pm25"
    api_key_ = Parameter("api_key", help="OpenAQ V3 API Key", required=True)
    pollutant_ = Parameter("pollutant", default="pm25", help="Target pollutant: pm10, pm25, o3, no2, so2, co")

    @step
    def start(self):
        print(self.__class__.__name__)
        
        # OpenAQ V3 uses specific integer IDs for parameters
        param_map = {
            "pm10": 1,
            "pm25": 2,
            "o3": 3,
            "no2": 4,
            "so2": 5,
            "co": 6
        }
        
        # Default to PM2.5 (id 2) if the user types something weird
        param_id = param_map.get(self.pollutant_.lower(), 2)
        
        # V3 Endpoint for the latest global readings of a specific parameter
        self.url = f"https://api.openaq.org/v3/parameters/{param_id}/latest?limit=1000"
        self.next(self.extract)

    @card(type="html")
    @step
    def extract(self):
        print(f"[*] Fetching V3 air quality data: {self.url}")
        
        # Pass the API key securely in the headers
        headers = {
            "X-API-Key": self.api_key_
        }
        
        response = requests.get(self.url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            self.raw = response.json().get("results", [])
        else:
            print(f"[!] API Error {response.status_code}: {response.text}")
            self.raw = []

        self.data = pd.DataFrame(self.raw)
        
        if not self.data.empty:
            self.html = Tabular(self.data.head(10)).table_output()
        else:
            self.html = "<h3>No data found or API Key is invalid.</h3>"
            
        self.next(self.clean)

    @step
    def clean(self):
        # V3 JSON structure is different. The payload is much flatter, 
        # but coordinates are still nested in a dictionary.
        cleaned_records = []
        
        for index, row in self.data.iterrows():
            coords = row.get("coordinates")
            if not isinstance(coords, dict):
                continue
                
            lat = coords.get("latitude")
            lon = coords.get("longitude")
            val = row.get("value")
            
            # Extract UTC time safely
            dt = row.get("datetime", {}).get("utc")
            
            if lat and lon and val is not None:
                # Floor negative calibration values to 0 for the heatmap
                if val < 0:
                    val = 0
                    
                cleaned_records.append({
                    "locationsId": row.get("locationsId"),
                    "latitude": lat,
                    "longitude": lon,
                    "pollutant": self.pollutant_.upper(),
                    "value": val,
                    "last_updated": dt
                })
                
        self.cleaned = pd.DataFrame(cleaned_records)
        self.next(self.transform)

    @card(type="html")
    @step
    def transform(self):
        self.output = self.cleaned[
            ["locationsId", "latitude", "longitude", "pollutant", "value", "last_updated"]
        ]
        
        if not self.output.empty:
            self.html = Tabular(self.output).table_output()
        else:
            self.html = "<h3>No valid records remaining after cleaning.</h3>"
            
        self.next(self.visualise)

    @step
    def visualise(self):
        self.next(self.data_table, self.data_map, self.data_stats)

    @card(type="html")
    @step
    def data_table(self):
        if not self.output.empty:
            self.html = Tabular(self.output).table_output()
        self.next(self.wrapup)

    @card(type="html")
    @step
    def data_map(self):
        # Utilizing our upgraded Plot class to generate the heatmap
        self.html = Plot(
            self.output, 
            plot_type="heatmap", 
            weight_col="value"
        ).render()
        self.next(self.wrapup)

    @step
    def data_stats(self):
        self.count = "OpenAQ V3 entries: {r[0]}, columns: {r[1]}, info: {c}".format(
            r=self.output.shape, c=self.output.columns.tolist()
        )
        print(self.count)
        self.next(self.wrapup)

    @step
    def wrapup(self, inputs):
        self.output = inputs[0].output
        self.next(self.end)

    @step
    def end(self):
        print("Success: OpenAQ V3 Pipeline Complete.")

if __name__ == "__main__":
    Ref_02()