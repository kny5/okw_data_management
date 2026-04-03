#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Oct 31 07:51:41 2024

@author: kny5
"""

import sqlite3

import pandas as pd
from __functions__ import ReverseGeocode, filter_points_by_proximity, req_data, generate_blake2_uid
from __visualisations__ import Plot, Tabular
from metaflow import FlowSpec, Parameter, card, step, current
from metaflow_extensions.profiler.plugins.profile_decorator import profile_card


class Source_12(FlowSpec):
    url = Parameter(
        "url",
        default="https://github.com/kny5/db/raw/refs/heads/db_global/Global.sqlite",
    )
    radius_ = Parameter("radius", default=100)
    min_points_ = Parameter("min_points", default=2)
    render_map_ = Parameter("render_map", default=False)
    benchmark_products = Parameter("find", default="facemask|mask|respirator|ventilator")

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
        con.close()

        print(self.raw.info())
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
        filter_0 = self.raw[
            ~self.raw["country"].isin(["iraq", "somalia", "somaliland"])
        ]
        filter_a = pd.concat([filter_0, self.patch], ignore_index=True)

        filter_a = filter_a.dropna(subset=["latitude", "longitude"])
        filter_1 = filter_a[filter_a["name"].str.len() >= 4]
        filter_1.rename(columns={"social_fb": "web_url"}, inplace=True)
        

        filter_2 = filter_1.map(lambda x: x.lower() if isinstance(x, str) else x)
        
        noise_keywords = (
            "barber|nail|salon|beauty|spa|boutique|cosmetics|hair|massage|restaurant|"
            "cafe|bar|pub|club|hotel|lodge|motel|grocery|supermarket|pharmacy|bakery|"
            "laundry|church|mosque|parish|coiffure|alimentation|boulangerie|église"
        )
        filter_b = filter_2[~filter_2["name"].str.contains(noise_keywords, na=False)]

        # Expanded Positive: Added informal sector terms, Francophone trades, and tech hubs
        positive_keywords = (
            "institute|faculty|college|univeristy|school|workshop|metal|wood|hardware|tailor|lab|innovation|welding|welder|works|"
            "atelier|fablab|maker|tech|hub|repair|garage|mechanic|carpentry|artisan|"
            "sewing|electronics|engineering|machine|fabrication|forge|foundry|cnc|3d|"
            "jua kali|fundi|menuiserie|soudure|mécanique|quincaillerie|usine"
        )
        filter_c = filter_b[filter_b["name"].str.contains(positive_keywords, na=False)]

        filter_3 = filter_c.drop_duplicates(subset=["name", "latitude", "longitude", "web_url"], keep="last")
        
        filter_4 = filter_points_by_proximity(
            filter_3, radius=self.radius_, min_points=self.min_points_
        )
        print(filter_4.columns.tolist())

        self.output = filter_3[~filter_3.isin(filter_4).all(axis=1)]
        self.output.columns = self.output.columns.str.lower()

        self.html = Tabular(self.output).table_output()
        self.next(self.transform)

    @card(type="html")
    @step
    def transform(self):
        self.geocode = ReverseGeocode(self.output).get()
        self.html = Tabular(self.geocode).table_output()
        self.next(self.give_uid)

    @step
    def give_uid(self):
        self.output["uid"] = self.output.apply(generate_blake2_uid, axis=1)
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
        self.output["source"] = "12"
        self.output["record_source_url"] = None
        print(self.output.columns.to_list())
        self.next(self.find)
    
    @card(type='html', id='first')
    # @card(type='html', id='second')
    @step
    def find(self):
        print(self.output.columns.to_list())
        self.benchmark = self.output[self.output["typical_products_of_the_facility"].str.contains(self.benchmark_products, na=False, case=False)].dropna(subset=["latitude", "longitude"])
        print(self.output.shape)
        current.card['first'](Table(self.benchmark))
        # self.map = Plot(self.benchmark).render()
        
        # current.card['first'].append(self.table)
        # current.card['second'].append(self.map)
        
        self.next(self.end)
    @step
    def end(self):
        print("Success")


if __name__ == "__main__":
    Source_12()
