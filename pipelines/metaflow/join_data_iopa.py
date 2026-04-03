#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Oct 28 06:17:15 2024

@author: kny5
"""

# create workspaces/tag prod, test and dev
# get flows from each workspace/tag
# run merge join strategy on each workspace/tag

import pandas as pd
from __functions__ import (
    ReverseGeocode,
    cluster_and_aggregate,
    obfuscate_text,
    inject_secure_map_logic,
    generate_blake2_uid,
)
from __visualisations__ import Plot, Tabular
from metaflow import Flow, FlowSpec, card, resources, step, Parameter, Runner

LOAD_HTML = None


class JoinData01(FlowSpec):
    encrypt_key = Parameter("encrypt_key", default="kny5")
    recreate = Parameter("recreate", default=False)
    render_map = Parameter("render_map", default=True)
    cypher = Parameter("cypher", default=False)

    # @catch(var='failure')
    @resources(memory=20000, cpu=18, gpu=1)
    @step
    def start(self):
        # Define the sources from which to fetch data
        self.sources = [
            "Source_02",
            "Source_03",
            "Source_04",
            # "Source_05",
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
        print("->"*50)
        print(self.input)
        print("->"*50)
        source_name = self.input
        print(f"Processing source: {source_name}")

        try:
            # Force recreation if requested
            if self.recreate:
                raise Exception("Recreation requested")
            
            # Try to fetch existing data
            self.data = Flow(source_name).latest_successful_run.data.output
            print(f"✅ Fetched existing data for {source_name}")

        except Exception:
            # Run the flow using the terminal-friendly Runner
            path = f"pipelines/metaflow/{source_name.lower()}.py"
            print(f"🔄 Running {path} via Runner...")
            
            with Runner(path).run() as running:
                if running.status == 'successful':
                    print(f"✅ {running.run} finished successfully.")
                    # Assign to self.data instead of returning!
                    self.data = running.run.data.output
                else:
                    raise Exception(f"❌ {running.run} failed with status: {running.status}")
        
        # Metaflow is now guaranteed to reach this transition
        self.next(self.concatenate)

    @step
    def concatenate(self, inputs):
        # Concatenate the data collected from each input in get_data step
        # self.merge_artifacts(inputs)
        self.append_source = pd.concat(
            [inp.data for inp in inputs if not inp.data.empty], ignore_index=True
        )
        self.next(self.clean)

    @step
    def clean(self):
        # Drop duplicates by latitude and longitude
        # .drop_duplicates(subset=['name', 'latitude', 'longitude'], keep='last')
        filter_0 = self.append_source.dropna(subset=["latitude", "longitude"])
        # filter_a = clean_and_cluster_records(filter_0, distance_threshold=6000, name_similarity_threshold=0.8)
        # filter_1 = filter_points_by_proximity(filter_0, radius=100, min_points=4)
        filter_1 = cluster_and_aggregate(
            filter_0, distance_threshold=6000, similarity_threshold=0.7
        )
        # filter_1 = cluster_and_key_collision_sim(filter_0, distance_threshold=6000, n=3, similarity_threshold=0.8)
        # self.output = cluster_and_key_collision(filter_0, distance_threshold=6000, n=2)
        # self.output = filter_0[~filter_0.isin(filter_1).all(axis=1)]
        self.output = filter_1
        print(self.output.shape)
        print(self.output.columns.tolist())
        print(self.output.tail(5))
        self.next(self.give_uid)

    @step
    def give_uid(self):
        self.output["uid"] = self.output.apply(generate_blake2_uid, axis=1)
        self.next(self.visualise)

    @step
    def visualise(self):
        self.next(
            self.data_table,
            self.data_map,
            self.data_stats,
            self.territories,
        )

    @step
    def territories(self):
        self.countries = ["MX", "BR", "SG", "IN", "NL", "US", "GB", "DE"]
        self.geocode = ReverseGeocode(self.output).get()
        self.next(self.spaces_by_country, foreach="countries")

    @card(type="html")
    @step
    def spaces_by_country(self):
        current_country = self.input
        self.country = self.geocode[self.geocode["cc2"] == current_country]
        self.html = Plot(self.country, max_cluster_rad=60).render()
        self.next(self.joint)

    @card(type="html")
    @step
    def data_table(self):
        # Generate HTML table output for the data
        self.html = Tabular(self.output).table_output()
        self.next(self.wrap_up)

    @card(type="html")
    @step
    def data_map(self):
        if self.render_map:
            global LOAD_HTML
            LOAD_HTML = Plot(self.output, max_cluster_rad=60).render()
            self.html = LOAD_HTML
        self.next(self.wrap_up)

    @card(type="html")
    @step
    def data_stats(self):
        # Generate map visualization
        print("Stats missing WIP")
        most_common_words = self.output['name'].str.split().explode().value_counts().head(20)
        # self.html = Statistics(self.output).render()
        print(most_common_words)
        self.next(self.wrap_up)

    @step
    def joint(self, inputs):
        self.output = inputs[0].output
        self.next(self.encryption_map)

    @card(type="html")
    @step
    def encryption_map(self):
        if self.cypher and self.render_map:
            self.output["name"] = self.output["name"].apply(
                lambda x: obfuscate_text(x, key=self.encrypt_key)
            )

            self.output["web_url"] = self.output["web_url"].apply(
                lambda x: obfuscate_text(x, key=self.encrypt_key)
            )

            json_string = self.output[["latitude", "longitude", "name", "web_url"]].to_json(
                orient="records"
            )

            final_payload = obfuscate_text(json_string, key=self.encrypt_key)

            if LOAD_HTML:
                self.html = inject_secure_map_logic(LOAD_HTML, final_payload)

        self.next(self.wrap_up)

    @step
    def wrap_up(self, inputs):
        # Combine any additional required outputs from data_table and data_map
        # steps
        self.output = inputs[
            0
        ].output  # Ensuring `self.output` is carried forward to end
        self.next(self.end)

    @step
    def end(self):
        print(self.output)  # Now `self.output` will be available here
        print(self.output.shape)
        print(self.output.columns.tolist())
        print(self.output.tail(5))

if __name__ == "__main__":
    JoinData01()
