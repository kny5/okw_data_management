"""
Created on Thu Oct 31 07:51:41 2024

@author: kny5
"""

import sqlite3

import pandas as pd
from __functions__ import (
    ReverseGeocode,
    filter_points_by_proximity,
    req_data,
    generate_blake2_uid,
)
from __visualisations__ import Plot, Tabular
from metaflow import FlowSpec, Parameter, card, step, current
from __metasteps__ import TailSteps


class Source_12(FlowSpec, TailSteps):
    url = Parameter(
        "url",
        default="https://github.com/kny5/db/raw/refs/heads/db_global/Global.sqlite",
    )
    radius_ = Parameter("radius", default=100)
    min_points_ = Parameter("min_points", default=2)
    
    bypass_geo_filter = Parameter("bypass_geo_filter", default=False)
    
    render_map_ = Parameter("render_map", default=True)
    benchmark_products = Parameter(
        "find", default="facemask|mask|respirator|ventilator"
    )
    keep_data = Parameter("keep_data", default=True)


    @step
    def start(self):
        self.next(self.extract)

    @card(type="html")
    @step
    def extract(self):
        response = req_data(self.url)
        local_file = "Global.sqlite"

        with open(local_file, "wb") as f:
            f.write(response.content)

        con = sqlite3.connect(local_file)
        self.raw = pd.read_sql_query("SELECT * from field_ready_verified", con)
        self.patch = pd.read_sql_query("SELECT * from patch_01", con)
        print(self.raw.columns.to_list())
        print(self.raw.shape)
        con.close()

        self.html = Tabular(self.raw).table_output()
        self.next(self.clean)

    @card(type="html")
    @step
    def clean(self):
        self.patch["latitude"] = pd.to_numeric(self.patch["latitude"], errors="coerce")
        self.patch["longitude"] = pd.to_numeric(
            self.patch["longitude"], errors="coerce"
        )
        self.raw["latitude"] = pd.to_numeric(
            self.raw["location-Latitude"], errors="coerce"
        )
        self.raw["longitude"] = pd.to_numeric(
            self.raw["location-Longitude"], errors="coerce"
        )
        drop_unverifiable_data = self.raw[
            ~self.raw["country"].isin(["iraq", "somalia", "somaliland"])
        ]

        self.data_input = pd.concat([self.raw, self.patch], ignore_index=True)

        patch_verified_data = pd.concat(
            [drop_unverifiable_data, self.patch], ignore_index=True
        )

        patch_verified_data = patch_verified_data.dropna(
            subset=["latitude", "longitude"]
        )
        filter_name_len = patch_verified_data[
            patch_verified_data["name"].str.len() >= 4
        ]
        filter_name_len.rename(columns={"social_fb": "web_url"}, inplace=True)

        lower_case_all_strs = filter_name_len.map(
            lambda x: x.lower() if isinstance(x, str) else x
        )

        noise_keywords = (
            "barber|nail|salon|beauty|spa|boutique|cosmetics|hair|massage|restaurant|"
            "cafe|bar|pub|club|hotel|lodge|motel|grocery|supermarket|pharmacy|bakery|"
            "laundry|church|mosque|parish|coiffure|alimentation|boulangerie|église|cosmetics"
        )
        filter_negative_keys = lower_case_all_strs[
            ~lower_case_all_strs["name"].str.contains(noise_keywords, na=False)
        ]

        positive_keywords = (
            "institute|faculty|college|univeristy|school|workshop|metal|wood|hardware|tailor|lab|innovation|welding|welder|works|"
            "atelier|fablab|maker|tech|hub|repair|garage|mechanic|carpentry|artisan|"
            "sewing|electronics|engineering|machine|fabrication|forge|foundry|cnc|3d|"
            "jua kali|fundi|menuiserie|soudure|mécanique|quincaillerie|usine"
        )
        filter_positive_keys = filter_negative_keys[
            filter_negative_keys["name"].str.contains(positive_keywords, na=False)
        ]

        filter_duplicates = filter_positive_keys.drop_duplicates(
            subset=["name", "latitude", "longitude", "web_url"], keep="last"
        )

        if not self.bypass_geo_filter:
            filter_by_geo_proximity = filter_points_by_proximity(
                filter_duplicates, radius=self.radius_, min_points=self.min_points_
            )
        else:
            filter_by_geo_proximity = pd.DataFrame()

        self.data_output = filter_duplicates[
            ~filter_duplicates.isin(filter_by_geo_proximity).all(axis=1)
        ]
        self.data_output.columns = self.data_output.columns.str.lower()

        self.html = Tabular(self.data_output).table_output()
        self.next(self.transform)

    @card(type="html")
    @step
    def transform(self):
        id = current.flow_name[-2:]
        self.data_output["source"] = id
        self.data_output["uid"] = self.data_output.apply(generate_blake2_uid, axis=1)
        self.data_output["record_source_url"] = "https://ggl.link/UkdBlHn"
        self.geocode = ReverseGeocode(self.data_output).get()
        self.html = Tabular(self.geocode).table_output()
        self.next(self.find)

    @card(type="html")
    @step
    def find(self):
        self.benchmark = self.data_input[
            self.data_input["Typical_products_of_the_facility"].str.contains(
                self.benchmark_products, na=False, case=False
            )
        ].dropna(subset=["latitude", "longitude"])

        self.table = Tabular(self.benchmark).table_output()
        self.html = Plot(self.benchmark).render()

        self.next(self.visualise)


if __name__ == "__main__":
    Source_12()
