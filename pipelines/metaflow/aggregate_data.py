"""
Created on Thu Oct 28 07:51:41 2024

    Legacy:

    Author: Antonio de Jesus Anaya Hernandez, DevOps eng. for the IoPA, 2024.

    Author: The internet of Production Alliance, 2024.

    The Open Know Where (OKW) Initiative is part of the Internet of Production Alliance and its members.

    License: CC BY SA

    ![CC BY SA](https://mirrors.creativecommons.org/presskit/buttons/88x31/svg/by-sa.svg)

Forked and adapted by: The Distributed Manufacturing Data Kit, 2026.

License: CC BY SA

The Distributed Manufacturing Data Kit (DM-DK) is a collection of tools, libraries,
and resources designed to facilitate the management, processing, and visualization of distributed manufacturing data.
It is developed and maintained by Antonio de Jesus Anaya Hernandez.

Description: Metaflow pipeline for aggregating data from multiple sources, cleaning and processing it, and visualizing it on a map and as a table. The pipeline includes steps for fetching or generating data from various sources, concatenating the data, cleaning it by filtering and clustering, giving unique identifiers, and visualizing the results. It also includes optional encryption of the data for secure visualization.
"""

import pandas as pd
from __functions__ import (
    ReverseGeocode,
    cluster_and_aggregate,
    inspect_classification,
    obfuscate_text,
    inject_secure_map_logic,
    generate_blake2_uid,
)
from __visualisations__ import Plot, Tabular, graph_dataframe_relationships, plot_semantic_dendrogram, plot_schema_network, plot_schema_network_2, plot_category_lines, plot_category_bars, plot_category_heatmap
from metaflow import Flow, FlowSpec, card, resources, step, Parameter, Runner, current
from metaflow.cards import Markdown, Image
LOAD_HTML = None

TYPES_URL = "https://raw.githubusercontent.com/schemaorg/schemaorg/main/data/releases/29.4/schemaorg-current-https-types.csv"
PROPS_URL = "https://raw.githubusercontent.com/schemaorg/schemaorg/main/data/releases/29.4/schemaorg-current-https-properties.csv"
print("Loading Schema.org vocabulary into memory...")

types_df = pd.read_csv(TYPES_URL)
props_df = pd.read_csv(PROPS_URL)


INIT_DATA = {'types_url': types_df, 'props_url': props_df}

SOURCES = [
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

class JoinData01(FlowSpec):
    """Metaflow pipeline for aggregating and visualizing distributed manufacturing data."""

    encrypt_key = Parameter("encrypt_key", default="kny5")
    recreate = Parameter("recreate", default=False)
    render_map = Parameter("render_map", default=True)
    cypher = Parameter("cypher", default=False)

    @resources(memory=20000, cpu=19, gpu=1)
    @step
    def start(self):
        """Start step for initializing the list of data sources to process."""

        self.sources = SOURCES

        self.next(self.get_or_generate_data, foreach="sources")
    
    @step
    def get_or_generate_data(self):
        source_name = self.input
        print(f"Processing source: {source_name}")
        
        try:
            if getattr(self, 'recreate', False): # Safely check recreate flag
                raise Exception("Recreation requested")
            
            run_data = Flow(source_name).latest_successful_run.data
            print(f"✅ Fetched existing data for {source_name}")
            
        except Exception:
            path = f"pipelines/metaflow/{source_name.lower()}.py"
            print(f"🔄 Running {path} via Runner...")
            with Runner(path).run() as running:
                if running.status == "successful":
                    print(f"✅ {running.run} finished successfully.")
                    run_data = running.run.data
                else:
                    raise Exception(f"❌ {running.run} failed with status: {running.status}")

        # ✅ ACTUALLY unwrap into top-level artifacts so the join step can find them
        self.data_output = run_data.data_output
        self.data_input = run_data.data_input
        
        self.next(self.concatenate)


    @card
    @step
    def concatenate(self, inputs):
        """Concatenates data from all sources into a single DataFrame."""
        lazy_output_dfs = []
        lazy_input_dfs = []
        self.dataset = {}

        # 1. Iterate correctly over the Metaflow Inputs iterable
        for inp in inputs:
            # 2. Extract the source_name (which was the foreach 'input')
            key = inp.input 

            # 3. Safely check for the top-level artifact 'data_output'
            if hasattr(inp, 'data_output'):
                out_df = inp.data_output
                if isinstance(out_df, pd.DataFrame) and not out_df.empty:
                    lazy_output_dfs.append(out_df)
                else:
                    print(f"Skipping data_output from {key}: not a DataFrame or empty")
            else:
                print(f"No data_output on branch: {key}")

            # 4. Safely check for the top-level artifact 'data_input'
            if hasattr(inp, 'data_input'):
                in_df = inp.data_input
                if isinstance(in_df, pd.DataFrame) and not in_df.empty:
                    lazy_input_dfs.append(in_df)
            # Safely store the DataFrame (not the Metaflow object)
            self.dataset[key] = {'data_output': out_df, 'data_input': in_df}

        # 5. Final Safety Catch
        if not lazy_output_dfs:
            raise ValueError("No valid data_output DataFrames found. Check upstream steps.")

        self.append_source_output = pd.concat(lazy_output_dfs, ignore_index=True)
        self.next(self.clean)

    @step
    def clean(self):
        """Cleans the concatenated data by filtering out rows with missing latitude or longitude, and then applies clustering and aggregation to group nearby points."""

        filter_0 = self.append_source_output.dropna(subset=["latitude", "longitude"])

        filter_1 = cluster_and_aggregate(
            filter_0, distance_threshold=6000, similarity_threshold=0.7
        )

        self.data_output = filter_1
        print(self.data_output.shape)
        print(self.data_output.columns.tolist())
        print(self.data_output.tail(5))
        self.next(self.give_uid)

    @step
    def give_uid(self):
        """Generates a unique identifier for each row in the output DataFrame using a Blake2 hash of the row's contents."""
        self.data_output["uid"] = self.data_output.apply(generate_blake2_uid, axis=1)
        self.next(self.visualise)

    @step
    def visualise(self):
        """Proceeds to the visualization steps for rendering the data as a table, a map, and generating statistics."""
        self.next(
            self.data_table,
            self.data_map,
            self.data_stats,
            self.territories,
        )

    @step
    def territories(self):
        """Prepares the data for visualization by country and initiates the geocoding process to obtain country codes for each data point."""
        self.countries = ["MX", "BR", "SG", "IN", "NL", "US", "GB", "DE"]
        self.geocode = ReverseGeocode(self.data_output).get()
        self.next(self.spaces_by_country, foreach="countries")

    @card(type="html")
    @step
    def spaces_by_country(self):
        """Renders the data for a specific country on a map."""
        current_country = self.input
        self.country = self.geocode[self.geocode["cc2"] == current_country]
        self.html = Plot(self.country, max_cluster_rad=60).render()
        self.next(self.joint)

    @card(type="html")
    @step
    def data_table(self):
        """Renders the entire output DataFrame as an interactive HTML table."""
        self.html = Tabular(self.data_output).table_output()
        self.next(self.wrap_up)


    @card(type="html")
    @step
    def data_map(self):
        """Renders the entire output DataFrame on a map if the render_map parameter is set to True."""
        if self.render_map:
            global LOAD_HTML
            LOAD_HTML = Plot(self.data_output, max_cluster_rad=60).render()
            self.html = LOAD_HTML
        self.next(self.wrap_up)


    @card
    @step
    def data_stats(self):
        global types_df, props_df
        """Generates statistics about the output data, such as the count of entries and the most common words in the 'name' column."""
        self.most_common_words = (
            self.data_output["name"].str.split().explode().value_counts().head(20)
        )

        self.classified_data = graph_dataframe_relationships(
            self.dataset,
            data_init=INIT_DATA,
        )

        print(self.most_common_words)

        """Calculates metrics and generates the Dendrogram card."""
        
        current.card.append(Markdown("# DataFrame Taxonomy Clustering"))

        dendrogram_fig = plot_semantic_dendrogram(self.classified_data[0])
        
        current.card.append(Markdown("The dendrogram above shows how the datasets cluster together based on the semantic similarity of their columns. Datasets that share more similar column names and concepts are grouped closer together."))
        current.card.append(Image.from_matplotlib(dendrogram_fig))

        current.card.append(Markdown("# DataFrame Relationship Graph"))
        current.card.append(Markdown("This graph visualizes the relationships between the different datasets based on shared columns and semantic similarity."))
        current.card.append(Image.from_matplotlib(self.classified_data[1]))

        current.card.append(Markdown(str(self.classified_data[0])))

        full_map = inspect_classification(INIT_DATA, self.dataset)

        current.card.append(Markdown("# Full Classification Map"))
        current.card.append(Markdown("This map shows the classification of all columns across the datasets to inspect how they relate to each other and to common concepts in the manufacturing domain."))
        current.card.append(Markdown(str(full_map)))

        current.card.append(Markdown("# Network Graph of DataFrame Relationships"))
        network_fig = plot_schema_network(self.dataset, INIT_DATA)
        current.card.append(Image.from_matplotlib(network_fig))

        current.card.append(Markdown("# Network Graph of DataFrame Relationships ALTERNATIVE LAYOUT"))
        network_fig_2 = plot_schema_network_2(full_map)
        current.card.append(Image.from_matplotlib(network_fig_2))


        current.card.append(Markdown("# Category Relationship Lines"))
        network_fig_3 = plot_category_lines(full_map)
        current.card.append(Image.from_matplotlib(network_fig_3))

        current.card.append(Markdown("# Category Column Count"))
        category_fig = plot_category_heatmap(full_map)
        current.card.append(Image.from_matplotlib(category_fig))


        self.next(self.wrap_up)


    @step
    def joint(self, inputs):
        """Joins the outputs from the different visualization steps and prepares the data for the final wrap-up step."""
        self.data_output = inputs[0].data_output
        self.next(self.encryption_map)


    @card(type="html")
    @step
    def encryption_map(self):
        """If the cypher parameter is set to True, obfuscates the 'name' and 'web_url' columns of the output DataFrame using the specified encryption key, and then prepares a secure map visualization with the obfuscated data."""
        if self.cypher and self.render_map:
            self.data_output["name"] = self.data_output["name"].apply(
                lambda x: obfuscate_text(x, key=self.encrypt_key)
            )

            self.data_output["web_url"] = self.data_output["web_url"].apply(
                lambda x: obfuscate_text(x, key=self.encrypt_key)
            )

            json_string = self.data_output[
                ["latitude", "longitude", "name", "web_url"]
            ].to_json(orient="records")

            final_payload = obfuscate_text(json_string, key=self.encrypt_key)

            if LOAD_HTML:
                self.html = inject_secure_map_logic(LOAD_HTML, final_payload)

        self.next(self.wrap_up)


    @card
    @step
    def wrap_up(self, inputs):
        """Finalizes the output data by safely propagating the dataframes."""
        
        self.next(self.end)


    @step
    def end(self):
        """Final step to print the output DataFrame and its details for verification."""



if __name__ == "__main__":
    JoinData01()
