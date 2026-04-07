"""
Created on Thu Oct 31 07:51:41 2024

@author: kny5
"""

import pandas as pd
from __functions__ import ReverseGeocode, req_data, generate_blake2_uid
from __visualisations__ import Tabular
from metaflow import FlowSpec, Parameter, card, step, current
from __metasteps__ import TailSteps


class Source_11(FlowSpec, TailSteps):
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
        self.raw = req_data(self.url).json()
        self.data_input = pd.json_normalize(self.raw, "Makerspaces")
        print(self.data_input.columns.tolist())
        self.html = Tabular(self.data_input).table_output()
        self.next(self.clean)

    @card(type="html")
    @step
    def clean(self):
        self.data_input["latitude"] = pd.to_numeric(self.data_input["lat"], errors="coerce")
        self.data_input["longitude"] = pd.to_numeric(self.data_input["long"], errors="coerce")
        self.data_input.rename(columns={"website": "web_url"}, inplace=True)
        self.data_input["record_source_url"] = "https://makerspace.com" + self.data_input["link"]
        self.data_output = self.data_input[
            ["name", "latitude", "longitude", "web_url", "record_source_url"]
        ]
        self.html_2 = Tabular(self.data_output).table_output()
        self.next(self.transform)

    @card(type="html")
    @step
    def transform(self):
        id = current.flow_name[-2:]
        self.data_output["source"] = id
        self.data_output["uid"] = self.data_output.apply(generate_blake2_uid, axis=1)
        self.geocode = ReverseGeocode(self.data_output).get()
        self.html = Tabular(self.geocode).table_output()
        self.next(self.visualise)




if __name__ == "__main__":
    Source_11()
