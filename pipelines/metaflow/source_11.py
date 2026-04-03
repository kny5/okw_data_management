#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Oct 31 07:51:41 2024

@author: kny5
"""

import pandas as pd
from __functions__ import ReverseGeocode, req_data
from __visualisations__ import Plot, Tabular
from metaflow import FlowSpec, Parameter, card, step


class Source_11(FlowSpec):
    url = Parameter(
        "url", default="https://makerspace.com/wp-json/makerspaces/v1/spacedata/5/"
    )
    radius_ = Parameter("radius", default=100)
    min_points_ = Parameter("min_points", default=2)
    render_map_ = Parameter("render_map", default=False)

    @step
    def start(self):
        self.next(self.extract)

    @card(type="html")
    @step
    def extract(self):
        data = req_data(self.url).json()
        self.raw = pd.json_normalize(data, "Makerspaces")
        print(self.raw.columns.tolist())
        self.html = Tabular(self.raw).table_output()
        self.next(self.clean)

    @card(type="html")
    @step
    def clean(self):
        self.raw["latitude"] = pd.to_numeric(self.raw["lat"], errors="coerce")
        self.raw["longitude"] = pd.to_numeric(self.raw["long"], errors="coerce")
        self.raw.rename(columns={"website": "web_url"}, inplace=True)
        self.raw["record_source_url"] = "https://makerspace.com" + self.raw["link"]
        self.output = self.raw[["name", "latitude", "longitude", "web_url", "record_source_url"]]
        self.html_2 = Tabular(self.output).table_output()
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
        if self.render_map_:
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
        # self.output['record_source_url'] = self.output.link.apply(lambda x: 'https://makerspace.com' + x)
        self.output["source"] = "11"
        print(self.output.shape)
        print(self.output.columns.tolist())
        self.next(self.end)

    @step
    def end(self):
        print("Success")


if __name__ == "__main__":
    Source_11()
