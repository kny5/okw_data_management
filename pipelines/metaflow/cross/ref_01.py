#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Created on Mon Mar 30 04:22:45 2026

@author: kny5
"""

import sys
from pathlib import Path
import pandas as pd

parent_dir = str(Path(__file__).resolve().parent.parent)

if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

import pandas as pd
from __visualisations__ import Plot, Tabular
from metaflow import FlowSpec, Parameter, card, step

class Ref_01(FlowSpec):
    """
    Downloads and processes the last 24 hours of global active fire data 
    from NASA's FIRMS (MODIS or VIIRS).
    """
    # Parameters to let you swap satellites or filter fire confidence from the CLI
    satellite_ = Parameter("satellite", default="VIIRS", help="Choose 'MODIS' or 'VIIRS'")
    min_confidence_ = Parameter("min_confidence", default=80, help="Minimum fire detection confidence (0-100) or 'nominal'/'high'")

    @step
    def start(self):
        print(self.__class__.__name__)
        # Define the URLs based on the satellite parameter
        if self.satellite_.upper() == "MODIS":
            self.url = "https://firms.modaps.eosdis.nasa.gov/data/active_fire/modis-c6.1/csv/MODIS_C6_1_Global_24h.csv"
        else:
            self.url = "https://firms.modaps.eosdis.nasa.gov/data/active_fire/suomi-npp-viirs-c2/csv/SUOMI_VIIRS_C2_Global_24h.csv"
            
        self.next(self.extract)

    @card(type="html")
    @step
    def extract(self):
        # NASA FIRMS provides raw CSVs, so pandas can read the URL directly
        print(f"Downloading {self.satellite_} data from: {self.url}")
        self.raw = pd.read_csv(self.url)
        self.data = pd.DataFrame(self.raw)
        
        # Render the raw table to the Metaflow card
        self.html = Tabular(self.data).table_output()
        print(f"Columns found: {self.data.columns.tolist()}")
        self.next(self.clean)

    @step
    def clean(self):
        # VIIRS confidence is string-based ('low', 'nominal', 'high')
        # MODIS confidence is integer-based (0-100)
        if self.satellite_.upper() == "VIIRS":
            # Filter out 'low' confidence detections for VIIRS
            valid_conf = ["nominal", "high"]
            self.cleaned = self.data[self.data["confidence"].isin(valid_conf)]
        else:
            # Filter by numeric parameter for MODIS
            self.cleaned = self.data[self.data["confidence"] >= int(self.min_confidence_)]
            
        # Drop exact duplicate coordinates reported at the exact same time
        self.cleaned = self.cleaned.drop_duplicates(subset=["latitude", "longitude", "acq_time"], keep="last")
        self.next(self.transform)

    @card(type="html")
    @step
    def transform(self):
        # Combine acquisition date and time into a single standard datetime column
        # FIRMS acq_time is an integer like 1435 (14:35 UTC)
        self.cleaned['acq_time_str'] = self.cleaned['acq_time'].astype(str).str.zfill(4)
        self.cleaned['datetime_utc'] = pd.to_datetime(
            self.cleaned['acq_date'] + ' ' + self.cleaned['acq_time_str'], 
            format='%Y-%m-%d %H%M'
        )
        
        # Select the most useful columns for downstream mapping
        self.output = self.cleaned[
            ["latitude", "longitude", "bright_ti4", "confidence", "datetime_utc", "frp"]
        ]
        
        # Render the transformed table to the card
        self.html = Tabular(self.output).table_output()
        self.next(self.visualise)

    @step
    def visualise(self):
        # Branch out into table, map, and stats just like Source_02
        self.next(self.data_table, self.data_map, self.data_stats)

    @card(type="html")
    @step
    def data_table(self):
        self.html = Tabular(self.output).table_output()
        self.next(self.wrapup)

    @card(type="html")
    @step
    def data_map(self):
        # Assuming your Plot class expects 'latitude' and 'longitude' columns
        self.html = Plot(
            self.output, 
            plot_type="heatmap", 
            weight_col="frp"
            ).render()
        self.next(self.wrapup)

    @step
    def data_stats(self):
        self.count = "NASA FIRMS entries: {r[0]}, columns: {r[1]}, info: {c}".format(
            r=self.output.shape, c=self.output.columns.tolist()
        )
        print(self.count)
        self.next(self.wrapup)

    @step
    def wrapup(self, inputs):
        # Join the branches. Grab the output dataframe from the first input branch.
        self.output = inputs[0].output
        self.next(self.end)

    @step
    def end(self):
        print("Success: NASA FIRMS Pipeline Complete.")

if __name__ == "__main__":
    Ref_01()