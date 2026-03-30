#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Oct 31 07:51:41 2024

@author: kny5
"""

import json

import pandas as pd
from __functions__ import ReverseGeocode, req_data
from __visualisations__ import Plot, Tabular
from bs4 import BeautifulSoup as soup
from metaflow import FlowSpec, Parameter, card, step


class Source_09(FlowSpec):
    api_url = Parameter(
        "url", default="https://wiki.hackerspaces.org/w/api.php?action=parse&oldid=95416&prop=text&format=json&origin=*"
    )

    @step
    def start(self):
        self.next(self.extract)

    @step
    def extract(self):
        print(f"Fetching from API: {self.api_url}")
        
        response = req_data(self.api_url)
        
        # DEBUG: Print the first 500 characters of whatever we got
        print("--- RAW RESPONSE START ---")
        print(response.text[:500])
        print("--- RAW RESPONSE END ---")
        
        # This is where it's currently crashing
        api_json = response.json()

        # 3. Extract the HTML string from the 'parse' -> 'text' -> '*' path
        raw_html = api_json.get('parse', {}).get('text', {}).get('*', '')
        
        if not raw_html:
            print("Error: API response did not contain page text.")
            self.data = pd.DataFrame()
            self.next(self.clean)
            return

        # 4. Use BeautifulSoup to find the 'mapdata' div hidden in that HTML
        html_parser = soup(raw_html, "html.parser")
        div_data = html_parser.find("div", {"class": "mapdata"})

        if not div_data:
            print("Error: The 'mapdata' div was not found in the page HTML.")
            self.data = pd.DataFrame()
        else:
            try:
                # 5. Parse the INNER JSON string found inside the div
                map_json = json.loads(div_data.text)
                locations = map_json.get("locations", [])
                
                # 6. Convert to DataFrame
                self.data = pd.DataFrame(locations)
                print(f"Success! Extracted {len(self.data)} hackerspaces.")
                
            except json.JSONDecodeError:
                print("Error: The text inside mapdata was not valid JSON.")
                self.data = pd.DataFrame()

        self.next(self.clean)

    @step
    def clean(self):
        self.data.rename(
            columns={
                "lat": "latitude",
                "lon": "longitude",
                "title": "name",
                "link": "web_url",
            },
            inplace=True,
        )
        self.output = self.data[["name", "latitude", "longitude", "web_url"]]
        self.next(self.transform)

    @card(type="html")
    @step
    def transform(self):
        self.geocode = ReverseGeocode(self.output).get()
        self.html = Tabular(self.geocode).table_output()
        self.next(self.visualise)

    @step
    def visualise(self):
        self.next(self.data_table, self.data_map, self.data_stats)

    @card(type="html")
    @step
    def data_table(self):
        self.html = Tabular(self.output).table_output()
        self.next(self.wrapup)

    @card(type="html")
    @step
    def data_map(self):
        self.html = Plot(self.output.dropna(subset=["latitude", "longitude"])).render()
        self.next(self.wrapup)

    @step
    def data_stats(self):
        self.count = "OKW entries: {r[0]}, columns: {r[1]}, info: {c}".format(
            r=self.output.shape, c=self.output.columns.tolist()
        )
        self.next(self.wrapup)

    @step
    def wrapup(self, inputs):
        self.output = inputs[0].output
        self.next(self.end)

    @step
    def end(self):
        print("Success")


if __name__ == "__main__":
    Source_09()
