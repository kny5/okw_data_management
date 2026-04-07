"""
Created on Thu Oct 31 07:51:41 2024

@author: kny5
"""

import json

import pandas as pd
from __functions__ import ReverseGeocode
from __visualisations__ import Plot, Tabular
from bs4 import BeautifulSoup
from metaflow import FlowSpec, card, step, Parameter
from okw_libs.dwld import req_data


def html_collector(html_content):
    soup = BeautifulSoup(html_content, "html.parser")

    title = soup.find("h2", class_="workshop-title").text.strip()
    location = soup.find("span", class_="city-country").text.strip()
    tags = [tag.text.strip() for tag in soup.find_all("span", class_="tag primary")]
    href = soup.find("a", class_="card-link")["href"].strip()

    return [title] + location.split(", ") + [tags, "https://www.makertour.fr" + href]


class Source_05(FlowSpec):
    url = "https://www.makertour.fr/map"
    render_map_ = Parameter("render_map", default=False)

    @step
    def start(self):
        self.next(self.extract)

    @step
    def extract(self):
        html = req_data(self.url).content.decode("utf-8")
        html_parse_json = (
            BeautifulSoup(html, "html.parser").find("div", id="map").get("data-markers")
        )
        json_data = json.loads(html_parse_json)

        self.raw = []
        for record in json_data:
            self.raw.append(
                html_collector(record["content"]) + [record["lat"], record["lng"]]
            )

        columns = [
            "name",
            "city",
            "country",
            "tags",
            "web_url",
            "latitude",
            "longitude",
        ]
        self.data_input = pd.DataFrame(self.raw, columns=columns)
        print(self.data_input.columns.tolist())
        self.next(self.clean)

    @step
    def clean(self):
        self.data_output = self.data_input[["name", "latitude", "longitude", "web_url"]]
        self.next(self.transform)

    @card(type="html")
    @step
    def transform(self):
        self.geocode = ReverseGeocode(self.data_output).get()
        self.html = Tabular(self.geocode).table_output()
        self.next(self.visualise)

    @step
    def visualise(self):
        self.next(self.data_table, self.data_map, self.data_stats)

    @card(type="html")
    @step
    def data_table(self):
        self.html = Tabular(self.data_output).table_output()
        self.next(self.wrapup)

    @card(type="html")
    @step
    def data_map(self):
        if self.render_map_:
            self.html = Plot(
                self.data_output.dropna(subset=["latitude", "longitude"])
            ).render()
        self.next(self.wrapup)

    @step
    def data_stats(self):
        self.count = "OKW entries: {r[0]}, columns: {r[1]}, info: {c}".format(
            r=self.data_output.shape, c=self.data_output.columns.tolist()
        )
        self.next(self.wrapup)

    @step
    def wrapup(self, inputs):
        self.data_output = inputs[0].data_output
        self.data_output["source"] = "05"
        print(self.data_output.shape)
        print(self.data_output.columns.tolist())
        self.next(self.end)



if __name__ == "__main__":
    Source_05()
