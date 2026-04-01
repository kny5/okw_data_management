#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Oct 31 07:51:41 2024

@author: kny5
"""

import json

import pandas as pd
from __functions__ import ReverseGeocode, extract_link
from __visualisations__ import Plot, Tabular
from bs4 import BeautifulSoup as soup
from metaflow import FlowSpec, Parameter, card, step


class Source_09(FlowSpec):
    url = Parameter("url", default="data/hackerspaces_list.json")

    @step
    def start(self):
        self.next(self.extract)

    @step
    def extract(self):
        with open(self.url, "r", encoding="utf-8") as f:
            api_response = json.load(f)
        raw_html = api_response.get("parse", {}).get("text", {}).get("*", "")
        html_parser = soup(raw_html, "html.parser")
        data = html_parser.find("div", {"class": "mapdata"}).text
        # print(data)
        self.raw = json.loads(data).get("locations", [])
        self.data = pd.DataFrame(self.raw)
        print(self.data.columns.tolist())
        self.next(self.clean)

    @card(type="html")
    @step
    def clean(self):
        self.html = Tabular(self.data).table_output()

        self.data.rename(
            columns={
                "lat": "latitude",
                "lon": "longitude",
                "title": "name",
                "link": "web_url",
            },
            inplace=True,
        )
        self.data["web_url"] = self.data["text"].apply(extract_link)
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
