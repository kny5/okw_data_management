"""
Created on Thu Oct 31 07:51:41 2024

@author: kny5
"""

import pandas as pd
from __functions__ import ReverseGeocode, generate_blake2_uid
from __visualisations__ import Tabular
from metaflow import FlowSpec, Parameter, card, step, current
from okw_libs.dwld import req_data
from __metasteps__ import TailSteps


class Source_02(FlowSpec, TailSteps):
    url = "https://api.fablabs.io/0/labs.json"
    radius_ = Parameter("radius", default=100)
    min_points_ = Parameter("min_points", default=2)
    render_map_ = Parameter("render_map", default=False)

    @step
    def start(self):
        print(self.__class__.__name__)
        self.next(self.extract)

    @card(type="html")
    @step
    def extract(self):
        self.raw = req_data(self.url).json()
        self.data_input = pd.DataFrame(self.raw)
        self.html = Tabular(self.data_input).table_output()
        print(self.data_input.columns.tolist())
        self.next(self.clean)

    @step
    def clean(self):
        remove_notactive = self.data_input[~self.data_input["activity_status"].isin(["closed", "planned"])]

        self.cleaned = remove_notactive.drop_duplicates(subset=["name"], keep="last")
        self.next(self.transform)

    @card(type="html")
    @step
    def transform(self):
        self.cleaned["record_source_url"] = (
            "https://www.fablabs.io/labs/" + self.cleaned.slug
        )

        self.cleaned["web_url"] = self.cleaned["links"].apply(
            lambda x: x[0]["url"] if isinstance(x, list) and len(x) > 0 else None
        )
        self.data_output = self.cleaned[
            ["name", "latitude", "longitude", "record_source_url", "web_url"]
        ]
        self.data_output["uid"] = self.data_output.apply(generate_blake2_uid, axis=1)
        self.geocode = ReverseGeocode(self.data_output).get()
        self.html = Tabular(self.geocode).table_output()
        id = current.flow_name[-2:]
        self.data_output["source"] = id
        self.next(self.visualise)


if __name__ == "__main__":
    Source_02()
