"""
Created on Thu Oct 31 07:51:41 2024

@author: kny5
"""

import json
import wget
import pandas as pd
from __functions__ import ReverseGeocode, extract_link, generate_blake2_uid
from __visualisations__ import Tabular
from bs4 import BeautifulSoup as soup
from metaflow import FlowSpec, Parameter, card, step, current
from __metasteps__ import TailSteps


class Source_09(FlowSpec, TailSteps):
    url = Parameter(
        "url",
        default="https://wiki.hackerspaces.org/w/api.php?action=parse&oldid=95416&prop=text&format=json&origin=*",
    )
    render_map_ = Parameter("render_map", default=True)

    @step
    def start(self):
        self.next(self.extract)

    @step
    def extract(self):

        data_file = wget.download(self.url, out="data/hackerspaces_list.json")

        print("Download complete.")

        with open(data_file, "r", encoding="utf-8") as f:
            api_response = json.load(f)
        raw_html = api_response.get("parse", {}).get("text", {}).get("*", "")
        html_parser = soup(raw_html, "html.parser")
        data = html_parser.find("div", {"class": "mapdata"}).text

        self.raw = json.loads(data).get("locations", [])
        self.data_input = pd.json_normalize(self.raw)
        print(self.data_input.columns.tolist())
        self.next(self.clean)

    @card(type="html")
    @step
    def clean(self):
        self.html = Tabular(self.data_input).table_output()

        self.data_input.rename(
            columns={
                "lat": "latitude",
                "lon": "longitude",
                "title": "name",
                "link": "web_url",
            },
            inplace=True,
        )
        self.data_input["web_url"] = self.data_input["text"].apply(extract_link)
        self.data_output = self.data_input[["name", "latitude", "longitude", "web_url"]]
        self.next(self.transform)

    @card(type="html")
    @step
    def transform(self):
        id = current.flow_name[-2:]
        self.data_output["source"] = id
        self.data_output["record_source_url"] = self.data_output.name.apply(
            lambda x: "https://wiki.hackerspaces.org/" + x.replace(" ", "_")
        )
        self.data_output["uid"] = self.data_output.apply(generate_blake2_uid, axis=1)
        self.geocode = ReverseGeocode(self.data_output).get()
        self.html = Tabular(self.geocode).table_output()
        self.next(self.visualise)


if __name__ == "__main__":
    Source_09()
