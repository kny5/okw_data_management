"""
Created on Mon Oct 28 06:17:15 2024

@author: kny5
"""

import pandas as pd
from __functions__ import (
    ReverseGeocode,
    cluster_and_aggregate,
    obfuscate_text,
    inject_secure_map_logic,
    generate_blake2_uid,
)
from __visualisations__ import Plot, Tabular
from metaflow import Flow, FlowSpec, card, resources, step, NBRunner


class JoinData01(FlowSpec):

    @resources(memory=8000, cpu=11, gpu=1)
    @step
    def start(self):

        self.sources = [
            "Source_02",
            "Source_03",
            "Source_04",
            "Source_06",
            "Source_07",
            "Source_08",
            "Source_09",
            "Source_10",
            "Source_11",
            "Source_12",
        ]

        self.next(self.get_or_generate_data, foreach="sources")

    @step
    def get_or_generate_data(self):
        source_name = self.input
        print(f"Processing source: {source_name}")

        try:

            self.data_input = Flow(source_name).latest_successful_run.data.output
            print(f"Successfully fetched existing data for {source_name}")

        except Exception as e:

            print(
                f"Data fetch failed for {source_name} with error: {e}. Running notebook..."
            )

            NBRunner(Flow(source_name))

            self.data_input = Flow(source_name).latest_successful_run.data.output
            print(f"Successfully fetched newly generated data for {source_name}")

        self.next(self.concatenate)

    @step
    def concatenate(self, inputs):

        self.append_source = pd.concat(
            [inp.data for inp in inputs if not inp.data.empty], ignore_index=True
        )
        self.next(self.clean)

    @step
    def clean(self):

        filter_0 = self.append_source.dropna(subset=["latitude", "longitude"])

        filter_1 = cluster_and_aggregate(
            filter_0, distance_threshold=6000, similarity_threshold=0.7
        )

        self.data_output = filter_1
        self.next(self.protect)

    @step
    def protect(self):
        self.data_output["name"] = self.data_output["name"].apply(
            lambda x: obfuscate_text(x, key="kny5")
        )
        self.data_output["web_url"] = self.data_output["web_url"].apply(
            lambda x: obfuscate_text(x, key="kny5")
        )
        self.next(self.give_uid)

    @step
    def give_uid(self):
        self.data_output["uid"] = self.data_output.apply(generate_blake2_uid, axis=1)
        self.next(self.geocoding)

    @step
    def geocoding(self):
        self.geocode = ReverseGeocode(self.data_output).get()
        self.next(self.visualise)

    @step
    def visualise(self):
        self.next(
            self.data_table,
            self.data_map,
            self.data_stats,
            self.make_africa_eu,
            self.territories,
        )

    @step
    def territories(self):
        self.countries = ["MX", "BR", "SG", "IN", "NL", "US", "GB", "DE"]
        self.next(self.spaces_by_country, foreach="countries")

    @card(type="html")
    @step
    def spaces_by_country(self):
        current_country = self.input
        self.country = self.geocode[self.geocode["cc2"] == current_country]
        self.html = Plot(self.country, max_cluster_rad=30).render()
        self.next(self.joint)

    @card(type="html")
    @step
    def make_africa_eu(self):

        self.makeafricaeu = self.geocode[
            self.geocode["continent"].isin(["Africa", "Europe"])
        ]
        self.html = Plot(self.makeafricaeu, max_cluster_rad=60).render()
        self.next(self.wrap_up)

    @card(type="html")
    @step
    def data_table(self):

        self.html = Tabular(self.data_output).table_output()
        self.next(self.wrap_up)

    @card(type="html")
    @step
    def data_map(self):

        json_string = self.data_output[
            ["latitude", "longitude", "name", "web_url"]
        ].to_json(orient="records")
        final_payload = obfuscate_text(json_string, key="kny5")

        self.html = Plot(self.data_output, max_cluster_rad=30).render()

        self.crypto_html = inject_secure_map_logic(self.html, final_payload)

        self.next(self.wrap_up)

    @card(type="html")
    @step
    def data_stats(self):

        print("test")

        self.next(self.wrap_up)

    @step
    def joint(self, inputs):
        self.data_output = inputs[0].data_output
        self.next(self.wrap_up)

    @step
    def wrap_up(self, inputs):

        self.data_output = inputs[
            0
        ].output  # Ensuring `self.data_output` is carried forward to end
        self.next(self.end)

    @step
    def end(self):
        print(self.data_output)  # Now `self.data_output` will be available here


if __name__ == "__main__":
    JoinData01()
