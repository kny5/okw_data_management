#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import requests
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

# Dynamically add parent directory to path so imports work perfectly
parent_dir = str(Path(__file__).resolve().parent.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from __visualisations__ import Plot, Tabular
from metaflow import FlowSpec, Parameter, card, step

class Ref_03(FlowSpec):
    """
    Downloads global Flooding and Drought data from the UN/EU GDACS API.
    Generates a severity-weighted heatmap of water extremes.
    """
    # FL = Floods, DR = Droughts. Use a semicolon to request multiple.
    hazards_ = Parameter("hazards", default="FL;DR", help="Disaster types: FL (Floods), DR (Droughts)")
    days_back_ = Parameter("days_back", default=365, help="Number of days of historical data to pull")

    @step
    def start(self):
        print(self.__class__.__name__)
        
        # Calculate our date window for the query
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=self.days_back_)
        
        # Format dates for the GDACS API (YYYY-MM-DD)
        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")
        
        # GDACS Search API
        self.url = f"https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH?eventlist={self.hazards_}&fromdate={start_str}&todate={end_str}"
        self.next(self.extract)

    @card(type="html")
    @step
    def extract(self):
        print(f"[*] Fetching GDACS data: {self.url}")
        
        response = requests.get(self.url, timeout=30)
        
        if response.status_code == 200:
            self.raw = response.json()
            
            # NEW: GDACS returns GeoJSON! 
            # We extract the 'features' array and use json_normalize to instantly flatten the nested dictionaries.
            features = self.raw.get("features", [])
            self.data = pd.json_normalize(features)
        else:
            print(f"[!] API Error {response.status_code}: {response.text}")
            self.data = pd.DataFrame()

        if not self.data.empty:
            self.html = Tabular(self.data.head(10)).table_output()
        else:
            self.html = "<h3>No water extreme events found for this time period.</h3>"
            
        self.next(self.clean)

    @step
    def clean(self):
        cleaned_records = []
        
        for index, row in self.data.iterrows():
            coords = row.get("geometry.coordinates")
            
            if not isinstance(coords, list) or len(coords) < 2:
                continue
                
            lon = coords[0]
            lat = coords[1]
            
            alert_score = row.get("properties.alertscore", 1.0)
            try:
                alert_score = float(alert_score)
                if alert_score <= 0:
                    alert_score = 0.5 
            except (TypeError, ValueError):
                alert_score = 1.0
                
            evt_code = row.get("properties.eventtype")
            evt_name = "Flood" if evt_code == "FL" else "Drought" if evt_code == "DR" else evt_code

            # NEW: Handle the multi-country strings
            raw_country = row.get("properties.country", "Unknown")
            if isinstance(raw_country, str):
                # Split by comma and remove any accidental extra spaces
                country_list = [c.strip() for c in raw_country.split(",") if c.strip()]
            else:
                country_list = ["Unknown"]

            cleaned_records.append({
                "country": country_list, # We save it as a Python list temporarily
                "event_name": row.get("properties.eventname"),
                "hazard_type": evt_name,
                "alert_level": row.get("properties.alertlevel"),
                "severity_score": alert_score,
                "start_date": row.get("properties.fromdate"),
                "latitude": lat,
                "longitude": lon
            })
                
        self.cleaned = pd.DataFrame(cleaned_records)
        
        # NEW: Explode the list! 
        # If an event has 3 countries, this instantly turns it into 3 separate rows.
        self.cleaned = self.cleaned.explode("country")
        
        # Reset the index so the dataframe is perfectly clean
        self.cleaned.reset_index(drop=True, inplace=True)
        
        self.next(self.transform)

    @card(type="html")
    @step
    def transform(self):
        # Formalize the output dataframe
        self.output = self.cleaned[
            ["country", "event_name", "hazard_type", "alert_level", "severity_score", "start_date", "latitude", "longitude"]
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
        # We leverage the Plot class heatmap, weighted by the GDACS disaster severity score
        self.html = Plot(
            self.output, 
            plot_type="heatmap", 
            weight_col="severity_score"
        ).render()
        self.next(self.wrapup)

    @step
    def data_stats(self):
        self.count = "GDACS Water Extremes: {r[0]} events, columns: {r[1]}, info: {c}".format(
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
        print("Success: GDACS Water Extremes Pipeline Complete.")

if __name__ == "__main__":
    Ref_03()