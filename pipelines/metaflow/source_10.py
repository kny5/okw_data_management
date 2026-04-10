"""
Created on Thu Oct 31 07:51:41 2024

@author: kny5
"""

import pandas as pd
from __functions__ import (
    ReverseGeocode,
    filter_points_by_proximity,
    req_data,
    generate_blake2_uid,
)
from __visualisations__ import Tabular
from metaflow import FlowSpec, Parameter, card, step, current
from __metasteps__ import TailSteps


class Source_10(FlowSpec, TailSteps):
    url = Parameter("url", default="https://makery.gogocarto.fr/api/elements.json")
    radius_ = Parameter("radius", default=100)
    min_points_ = Parameter("min_points", default=2)
    render_map_ = Parameter("render_map", default=True)

    @step
    def start(self):
        self.next(self.extract)

    @step
    def extract(self):
        data = req_data(self.url).json()
        self.data_input = pd.json_normalize(data, "data")
        self.next(self.clean)

    @card(type="html")
    @step
    def clean(self):
        self.data_input.rename(
            columns={
                "id": "makery_id",
                "site_web": "web_url",
                "geo.latitude": "latitude",
                "geo.longitude": "longitude",
            },
            inplace=True,
        )
        filtered = self.data_input[self.data_input["status"] != "closed"]
        self.duplicates = filter_points_by_proximity(
            filtered, radius=int(self.radius_), min_points=int(self.min_points_)
        )
        self.html = Tabular(self.duplicates).table_output()
        self.data_output = filtered[
            ["name", "latitude", "longitude", "web_url", "makery_id"]
        ]
        print(self.data_output.columns.tolist())
        self.data_output = self.data_output[
            ~self.data_output.isin(self.duplicates).all(axis=1)
        ]

        self.next(self.transform)

    @card(type="html")
    @step
    def transform(self):
        id = current.flow_name[-2:]
        self.data_output["source"] = id
        self.data_output["record_source_url"] = (
            "https://makery.gogocarto.fr/map#/fiche/"
            + self.data_output.name.str.replace(" ", "-")
            + "/"
            + self.data_output.makery_id
        )
        self.data_output["uid"] = self.data_output.apply(generate_blake2_uid, axis=1)
        self.geocode = ReverseGeocode(self.data_output).get()
        self.html = Tabular(self.geocode).table_output()
        self.next(self.visualise)


if __name__ == "__main__":
    Source_10()
