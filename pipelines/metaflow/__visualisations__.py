"""
Created on Thu Oct 31 07:51:41 2024

Author: Antonio de Jesus Anaya Hernandez, DevOps eng. for the IoPA.

Author: The internet of Production Alliance, 2024.

The Open Know Where (OKW) Initiative is part of the Internet of Production Alliance and its members.

License: CC BY SA

![CC BY SA](https://mirrors.creativecommons.org/presskit/buttons/88x31/svg/by-sa.svg)

Description: Python code for processing data as maps and tables.
"""

import os
import folium
import itables.options as opt
import numpy as np
from folium.plugins import (
    FastMarkerCluster,
    FloatImage,
    Fullscreen,
    LocateControl,
    MeasureControl,
)
from itables import to_html_datatable
from bs4 import BeautifulSoup as bs
from __functions__ import img_uri, get_taxonomy_for_pipeline
import itertools
import matplotlib.pyplot as plt
import base64
import io

import pandas as pd
import seaborn as sns

opt.maxBytes = 0


def load_js_file(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        return file.read()


class Plot:
    """
    Plot class for rendering geospatial data on an interactive map using Folium.
    It includes methods for preparing data, setting up the map, adding points with clustering,
    and adding legends and counts.

    The class also allows for customization of map tiles and cluster icons through external JavaScript files.
    """

    def __init__(self, dataframe, max_cluster_rad=40, colorful=False):
        self.icon_cluster = load_js_file("pipelines/metaflow/assets/cluster_icon.js")
        self.callback = load_js_file("pipelines/metaflow/assets/cluster_mod.js")

        if colorful:
            self.tiles_url = (
                "https://server.arcgisonline.com/ArcGIS/rest/services/"
                "World_Street_Map/MapServer/tile/{z}/{y}/{x}"
            )
            self.tiles_attribution = (
                "Tiles &copy; Esri &mdash; Source: Esri, DeLorme, "
                "NAVTEQ, USGS, Intermap, iPC, NRCAN, Esri Japan, METI, Esri China (Hong Kong), Esri (Thailand), TomTom, 2012"
            )
        else:
            self.tiles_url = (
                "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
            )
            self.tiles_attribution = (
                '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> '
                'contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
            )

        self.data_input = dataframe
        self.max_rad = max_cluster_rad
        self.prep_data()
        self.set_map()
        self.add_points()
        self.add_legend()
        self.add_count()
        self.get_map()

    def prep_data(self):
        """Prepares the data for mapping by ensuring that latitude and longitude values are numeric,
        and by creating a zip of the relevant columns for clustering."""

        self.output_map = self.data_input.dropna(subset=["latitude", "longitude"])

        print(self.output_map.info(verbose=True))
        print(self.output_map.columns.tolist())

        sources = (
            self.output_map["source"]
            if "source" in self.output_map.columns
            else [None] * len(self.output_map)
        )
        uids = (
            self.output_map["uid"]
            if "uid" in self.output_map.columns
            else [None] * len(self.output_map)
        )
        record_urls = (
            self.output_map["record_source_url"]
            if "record_source_url" in self.output_map.columns
            else [None] * len(self.output_map)
        )

        web_urls = (
            self.output_map["web_url"]
            if "web_url" in self.output_map.columns
            else [None] * len(self.output_map)
        )

        self.output_map = self.data_input.dropna(subset=["latitude", "longitude"])

        try:
            self.zip_data = list(
                zip(
                    self.output_map["latitude"],
                    self.output_map["longitude"],
                    self.output_map["name"],
                    sources,
                    web_urls,
                    uids,
                    record_urls,
                )
            )
            print(len(self.zip_data))
            print(self.zip_data[-5:])

            self.bounds = [
                [self.output_map["latitude"].min(), self.output_map["longitude"].min()],
                [self.output_map["latitude"].max(), self.output_map["longitude"].max()],
            ]

        except Exception as e:

            print(f"CRITICAL ERROR: {e}")
            return False

    def set_map(self):
        """Initializes the Folium map centered around the mean latitude and longitude of the data points,
        with specified tiles and attributes."""
        try:
            self.m = folium.Map(
                location=[
                    self.output_map["latitude"].mean(),
                    self.output_map["longitude"].mean(),
                ],
                zoom_start=1,
                tiles=self.tiles_url,
                attr=self.tiles_attribution,
                max_zoom=15,
                world_copy_jump=False,
                worldCopyJump=False,
                zoomControl=False,
                prefer_canvas=True,
            )
            self.m.fit_bounds(self.bounds)
        except Exception as e:
            print(e)

    def add_points(self):
        """Adds points to the map using FastMarkerCluster for efficient rendering of large datasets,
        with custom cluster icons and callbacks defined in external JavaScript files."""

        FastMarkerCluster(
            data=self.zip_data,
            icon_create_function=self.icon_cluster,
            callback=self.callback,
            options={"singleMarkerMode": True, "maxClusterRadius": self.max_rad},
        ).add_to(self.m)

    def add_legend(self):
        """Adds a legend to the map by reading an HTML file and embedding it as a Folium element."""
        with open("pipelines/metaflow/assets/legend.html", "r") as f:
            legend_html = f.read()
        self.m.get_root().html.add_child(folium.Element(legend_html))

    def add_count(self):
        """Adds a count of the data points to the map by reading an HTML file and embedding it as a Folium element."""
        with open("pipelines/metaflow/assets/count.html", "r") as f:
            count_html = f.read()
        self.m.get_root().html.add_child(folium.Element(count_html))

    def get_map(self):
        """Renders the map as an HTML string, with an additional floating image and controls for measuring and locating."""
        FloatImage(
            img_uri("pipelines/metaflow/assets/dm_odk.gif"),
            bottom=3,
            left=3,
        ).add_to(self.m)
        MeasureControl(position="bottomright").add_to(self.m)

        LocateControl(position="topleft").add_to(self.m)
        Fullscreen(
            position="topright",
            title="Fullscreen",
            title_cancel="Exit",
            force_separate_button=True,
        ).add_to(self.m)

    def render(self):
        return self.m.get_root().render()

    def into_html(self):
        """Renders the map as an HTML string."""
        return self.m._repr_html_()

    def base64_iframe(self):
        """Renders the map as a base64-encoded HTML string suitable for embedding in an iframe."""
        map_html = self.render()
        b64_html = base64.b64encode(map_html.encode("utf-8")).decode("utf-8")

        iframe = f"""
                <div style="display: flex; justify-content: center; align-items: center; width: 100%;">
                    <iframe src="data:text/html;base64,{b64_html}" 
                            width="100%" 
                            height="800px" 
                            style="border:none;">
                    </iframe>
                </div>
                """
        return iframe


class Tabular:
    """Tabular class for rendering a DataFrame as an interactive HTML table using itables."""

    def __init__(self, dataframe):
        self.data_input = dataframe

    def table_output(self):
        table_html = to_html_datatable(
            self.data_input,
            display_logo_when_loading=True,
            buttons=[
                "pageLength",
                {"extend": "csvHtml5", "title": "Manufacturing Locations"},
                {"extend": "excelHtml5", "title": "Manufacturing Locations"},
            ],
        )
        return table_html
    
    def base64_iframe(self):
        """Renders the map as a base64-encoded HTML string suitable for embedding in an iframe."""
        tab_html = self.table_output()
        b64_html = base64.b64encode(tab_html.encode("utf-8")).decode("utf-8")

        iframe = f"""
                <div style="display: flex; justify-content: center; align-items: center; width: 100%;">
                    <iframe src="data:text/html;base64,{b64_html}" 
                            width="100%" 
                            height="300px" 
                            style="border:none;">
                    </iframe>
                </div>
                """
        return iframe


def extract_map_data_from_string(html_string, js_filename="cluster_data.js"):
    """
    Parses an HTML string, extracts the map data script containing 'var data =',
    and updates the HTML to link to an external JS file.

    Returns:
        tuple: (modified_html_string, extracted_js_content)
               If the specific script is not found, extracted_js_content will be None.
    """

    soup = bs(html_string, "html.parser")

    target_script = None
    for script in soup.find_all("script"):
        if script.string and "var data =" in script.string:
            target_script = script
            break

    if not target_script:
        print("Could not find a script block containing 'var data ='.")

        return html_string, None

    js_content = target_script.string.strip()

    target_script.string = ""  # Clear the inline data
    target_script["src"] = js_filename  # Link to the external file
    target_script["defer"] = "true"  # Ensure it loads after the HTML

    return str(soup), js_content


def extract_map_data_to_js(html_filepath, output_js_filename="map_data.js"):
    """
    Extracts a specific script block containing 'var data =' from an HTML file,
    saves it to an external .js file, and links it back to the HTML.
    """
    print(f"Processing: {html_filepath}...")

    try:
        with open(html_filepath, "r", encoding="utf-8") as file:
            soup = bs(file, "html.parser")
    except FileNotFoundError:
        print(f"Error: Could not find the file {html_filepath}")
        return

    target_script = None
    for script in soup.find_all("script"):

        if script.string and "var data =" in script.string:
            target_script = script
            break

    if not target_script:
        print("Could not find a script block containing 'var data ='. No changes made.")
        return

    js_content = target_script.string.strip()

    directory = os.path.dirname(html_filepath)
    js_filepath = os.path.join(directory, output_js_filename)

    with open(js_filepath, "w", encoding="utf-8") as js_file:
        js_file.write(js_content)

    print(f"Successfully saved data to: {js_filepath}")

    target_script.string = ""  # Clear the massive inline data
    target_script["src"] = output_js_filename  # Link to the new file

    with open(html_filepath, "w", encoding="utf-8") as file:
        file.write(str(soup))

    print(f"Successfully updated HTML file to link to {output_js_filename}.")


def generate_sparsity_plots(source_list, labels=None):
    """
    Generates sparsity plots for a list of source objects.

    Args:
        source_list (list): List of objects, each containing '.data' and '.output' DataFrames.
        labels (list, optional): List of strings to label each source.
    """
    plt.rcParams["font.family"] = "sans-serif"
    plt.rcParams["font.size"] = 8
    plt.rcParams["axes.linewidth"] = 1

    colors = itertools.cycle(
        ["black", "#1f77b4", "#d62728", "#2ca02c", "#9467bd", "#ff7f0e"]
    )

    fig1, ax1 = plt.subplots(figsize=(6.5, 3))

    bar_labels = []
    avg_row_nulls_pct = []
    bar_colors = []
    bar_hatches = []

    for i, source in enumerate(source_list):
        current_color = next(colors)

        data_df = source.data_input
        output_df = source.data_output

        stages = [("Input", data_df, "--"), ("Output", output_df, "-")]

        for stage_name, df, linestyle in stages:
            if not df.empty:
                col_nulls = (df.isnull().mean() * 100).sort_values(ascending=False)
                x = np.arange(len(col_nulls))

                label_text = f"({stage_name})"
                ax1.plot(
                    x,
                    col_nulls,
                    label=label_text,
                    color=current_color,
                    linestyle=linestyle,
                    linewidth=1.5,
                )
                ax1.fill_between(x, col_nulls, color=current_color, alpha=0.05)

            bar_labels.append(f"({stage_name})")
            avg_pct = (df.isnull().mean(axis=1).mean() * 100) if not df.empty else 0
            avg_row_nulls_pct.append(avg_pct)

            bar_colors.append(current_color)
            bar_hatches.append("" if stage_name == "Input" else "///")

    ax1.set_ylabel("% Nulls")
    ax1.set_xlabel("Columns (Sorted by Sparsity)")
    ax1.set_title("Column Sparsity Profile")
    ax1.set_xticks([])
    ax1.set_ylim(0, 105)

    ax1.legend(loc="center left", bbox_to_anchor=(1, 0.5), frameon=False, fontsize=7)
    plt.tight_layout()
    fig1.savefig("nulls_by_column_profile.png", dpi=100, bbox_inches="tight")

    fig2, ax2 = plt.subplots(figsize=(6, 3))

    bars = ax2.bar(
        bar_labels, avg_row_nulls_pct, color="white", linewidth=1.5, width=0.6
    )

    for bar, hatch, color in zip(bars, bar_hatches, bar_colors):
        bar.set_hatch(hatch)
        bar.set_edgecolor(color)

    ax2.set_ylabel("Avg % Nulls / Row")
    ax2.set_title("Row-Level Sparsity Reduction")
    ax2.set_ylim(0, 105)

    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()

    print("Dynamic visualizations generated successfully.")

    buffer = io.BytesIO()
    fig2.savefig(buffer, format="png", dpi=100, bbox_inches="tight")

    return fig2, fig1



def graph_dataframe_relationships(dataframes, data_init, df_names=None):
    n = len(dataframes)
    if df_names is None:
        df_names = [f"DF {i+1}" for i in range(n)]

    dataset_contents = {}
    for name, df in zip(df_names, dataframes):
        classified = set()
        for col in df.columns:
            tax = get_taxonomy_for_pipeline(col, data_init)
            # Drop noise and unclassified — they corrupt similarity scores
            if not tax.startswith('Unclassified') and tax != '_noise':
                classified.add(tax)
        dataset_contents[name] = classified

    print("\nTaxonomy Mapping Complete. Generating Heatmap...")

    # 2. Build the Co-occurrence Matrix
    matrix = pd.DataFrame(index=df_names, columns=df_names, dtype=int)
    
    for name1 in df_names:
        for name2 in df_names:
            # Count how many semantic concepts these two dataframes share
            overlap = len(dataset_contents[name1].intersection(dataset_contents[name2]))
            matrix.loc[name1, name2] = overlap

    # 3. Visualize using Seaborn
    fig = plt.figure(figsize=(12, 10))
    
    # Optional: Mask the top right triangle since it's a mirrored matrix
    mask = np.triu(np.ones_like(matrix, dtype=bool), k=1)

    sns.heatmap(
        matrix, 
        mask=mask, 
        annot=True,     # Show the numbers in the boxes
        cmap="Blues",   # Use a clean blue gradient
        fmt="g",        # CHANGED: 'g' handles both ints and NaN-floats gracefully
        cbar_kws={'label': 'Number of Shared Semantic Classes'}
    )
    
    plt.title("Semantic Intersection Between DataFrames", fontsize=16, pad=20)
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    buffer = io.BytesIO()
    
    fig.savefig(buffer, format="png", dpi=100, bbox_inches="tight")
    plt.close(fig)
    return dataset_contents, fig

import pandas as pd
import matplotlib.pyplot as plt
from scipy.cluster.hierarchy import dendrogram, linkage
from scipy.spatial.distance import pdist

def plot_semantic_dendrogram(dataset_contents):
    """
    Takes the dataset_contents dictionary and plots a hierarchical 
    clustering dendrogram based on semantic concept overlap.
    """
    print("Extracting features for hierarchical clustering...")
    
    # 1. Get all unique semantic concepts across all dataframes
    all_concepts = set()
    # FIXED: Iterate over the dictionary values, not .columns
    for concepts in dataset_contents.values():
        all_concepts.update(concepts)
        
    # 2. Build a binary feature matrix
    # Rows: DataFrames, Columns: Concepts (1 = has concept, 0 = missing)
    feature_data = []
    # FIXED: Explicitly grab the dictionary keys
    df_names = list(dataset_contents.keys())
    
    for name in df_names:
        row = {concept: (1 if concept in dataset_contents[name] else 0) for concept in all_concepts}
        feature_data.append(row)
        
    feature_matrix = pd.DataFrame(feature_data, index=df_names)
    
    print("Calculating linkage and rendering Dendrogram...")

    # 3. Calculate distance and linkage
    distance_matrix = pdist(feature_matrix, metric='jaccard')
    linked = linkage(distance_matrix, method='average')
    
    # 4. Render the Dendrogram
    fig = plt.figure(figsize=(12, 8))
    
    dendrogram(
        linked,
        orientation='top',
        labels=df_names,
        distance_sort='descending',
        leaf_font_size=12,
        show_leaf_counts=True,
        color_threshold=0.3 * max(linked[:, 2]) 
    )
    
    plt.title("Hierarchical Clustering of DataFrames", fontsize=16, pad=20)
    plt.xlabel("Data Sources", fontsize=14, labelpad=15)
    plt.ylabel("Jaccard Distance", fontsize=12)
    plt.xticks(rotation=45, ha='right')
    
    plt.gca().spines['top'].set_visible(False)
    plt.gca().spines['right'].set_visible(False)
    plt.tight_layout()
    
    # Save a physical copy to your machine
    fig.savefig("semantic_dendrogram.png", dpi=300, bbox_inches='tight')
    
    plt.close(fig)
    return fig