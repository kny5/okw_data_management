"""
Created on Thu Oct 31 07:51:41 2024

@author: kny5
"""

import pandas as pd
from __functions__ import ReverseGeocode, generate_blake2_uid
from __visualisations__ import Tabular
from metaflow import FlowSpec, card, step, Parameter, current
from okw_libs.dwld import req_data
from okw_libs.g_maps import extract_kml_data, kml_object_to_dict, parse_description
from __metasteps__ import TailSteps


class Source_03(FlowSpec, TailSteps):
    url = "https://www.google.com/maps/d/u/0/viewer?mid=10q6m1yyAUzFn2zqDcRwq-qInUmvoVz4q&ll=37.844558%2C-122.27696200000003&z=8"
    render_map_ = Parameter("render_map", default=True)

    @step
    def start(self):
        self.next(self.extract)

    @step
    def extract(self):
        self.raw = extract_kml_data(self.url, req_data)
        self.next(self.clean)

    @card(type="html")
    @step
    def clean(self):
        filter_10 = [
            kml_object_to_dict(record)
            for folder in list(list(self.raw.features)[0].features)
            for record in folder.features
        ]
        filter_20 = pd.DataFrame(filter_10)
        filter_30 = filter_20["description"].apply(parse_description).apply(pd.Series)
        self.data_input = pd.DataFrame()
        self.data_input = pd.concat([filter_20, filter_30], axis=1).drop(
            columns=["description", "ns", "styleUrl"], errors="ignore"
        )
        print(self.data_input.columns.tolist())
        self.html = Tabular(self.data_input).table_output()
        self.data_output = self.data_input[["name", "latitude", "longitude", "web_url"]]
        self.next(self.transform)

    @card(type="html")
    @step
    def transform(self):
        id = current.flow_name[-2:]
        self.data_output["source"] = id
        self.data_output["uid"] = self.data_output.apply(generate_blake2_uid, axis=1)
        self.geocode = ReverseGeocode(self.data_output).get()
        self.html = Tabular(self.geocode).table_output()
        self.data_output["record_source_url"] = "https://ggl.link/UkdBlHn"
        self.next(self.visualise)


if __name__ == "__main__":
    Source_03()
