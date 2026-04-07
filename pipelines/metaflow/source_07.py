"""
Created on Thu Oct 31 07:51:41 2024

@author: kny5
"""

import json
import re

import pandas as pd
from __functions__ import ReverseGeocode, req_data, generate_blake2_uid
from __visualisations__ import Tabular
from bs4 import BeautifulSoup as soup
from metaflow import FlowSpec, Parameter, card, step, current
from __metasteps__ import TailSteps


class Source_07(FlowSpec, TailSteps):
    url = Parameter(
        "url",
        default="https://www.offene-werkstaetten.org/widgets/search?colorA=74ac61&colorB=0489B1&customMarkerSrc=https://cdn0.iconfinder.com/data/icons/map-location-solid-style/91/Map_-_Location_Solid_Style_06-48.png&customClusterSrc=https://cdn4.iconfinder.com/data/icons/ionicons/512/icon-ios7-circle-filled-48.png",
    )
    radius_ = Parameter("radius", default=5)
    min_points_ = Parameter("min_points", default=4)
    render_map_ = Parameter("render_map", default=False)

    @step
    def start(self):
        print("Starting...")
        self.next(self.extract)

    @step
    def extract(self):
        html_parser = [
            x.text
            for x in soup(req_data(self.url).text, "html.parser").find_all("script")
            if "vow.Map" in x.text
        ][-1]
        data = '[{"' + re.findall(r'\[{"(.*?)"\}\]\,', html_parser)[0] + '"}]'
        self.raw = json.loads(data)
        self.data_input = pd.DataFrame(self.raw)
        print(self.data_input.columns.tolist())
        self.next(self.clean)

    @step
    def clean(self):
        self.data_input.rename(
            columns={"lat": "latitude", "lng": "longitude", "web": "web_url"},
            inplace=True,
        )
        self.data_output = self.data_input[["name", "latitude", "longitude", "web_url"]]
        self.next(self.transform)

    @card(type="html")
    @step
    def transform(self):
        id = current.flow_name[-2:]
        self.data_output["source"] = id
        self.data_output["record_source_url"] = self.data_output.web_url.apply(
            lambda x: "https://offene-werkstaetten.org/werkstatt/" + x
        )
        self.data_output["uid"] = self.data_output.apply(generate_blake2_uid, axis=1)
        self.geocode = ReverseGeocode(self.data_output).get()
        self.html = Tabular(self.geocode).table_output()
        self.next(self.visualise)




if __name__ == "__main__":
    Source_07()
