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
import networkx as nx
import matplotlib.colors as mcolors
import matplotlib.cm as cm
import pandas as pd
import pandas as pd
import seaborn as sns
from adjustText import adjust_text
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
        self.output_map["latitude"] = pd.to_numeric(
            self.output_map["latitude"], errors="coerce"
        )
        self.output_map["longitude"] = pd.to_numeric(
            self.output_map["longitude"], errors="coerce"
        )
        self.output_map = self.output_map.dropna(subset=["latitude", "longitude"])

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


def graph_dataframe_relationships(dataset, data_init):
    print("^" * 50)
    print(type(dataset))
    print(dataset.keys())
    # breakpoint()
    dataset_contents = {}
    for name, df in dataset.items():
        classified = set()
        for col in df["data_input"]:
            tax = get_taxonomy_for_pipeline(col, data_init)
            # Drop noise and unclassified — they corrupt similarity scores
            if not tax.startswith("Unclassified") and tax != "_noise":
                classified.add(tax)
        dataset_contents[name] = classified

    print("\nTaxonomy Mapping Complete. Generating Heatmap...")

    # 2. Build the Co-occurrence Matrix
    matrix = pd.DataFrame(
        index=dataset_contents.keys(), columns=dataset_contents.keys(), dtype=int
    )

    for name1 in dataset_contents.keys():
        for name2 in dataset_contents.keys():
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
        annot=True,  # Show the numbers in the boxes
        cmap="Blues",  # Use a clean blue gradient
        fmt="g",  # CHANGED: 'g' handles both ints and NaN-floats gracefully
        cbar_kws={"label": "Number of Shared Semantic Classes"},
    )

    plt.title("Semantic Intersection Between Sources", fontsize=16, pad=20)
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    buffer = io.BytesIO()

    fig.savefig(buffer, format="png", dpi=100, bbox_inches="tight")
    plt.close(fig)
    return dataset_contents, fig


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
        row = {
            concept: (1 if concept in dataset_contents[name] else 0)
            for concept in all_concepts
        }
        feature_data.append(row)

    feature_matrix = pd.DataFrame(feature_data, index=df_names)

    print("Calculating linkage and rendering Dendrogram...")

    # 3. Calculate distance and linkage
    distance_matrix = pdist(feature_matrix, metric="jaccard")
    linked = linkage(distance_matrix, method="average")

    # 4. Render the Dendrogram
    fig = plt.figure(figsize=(12, 8))

    dendrogram(
        linked,
        orientation="top",
        labels=df_names,
        distance_sort="descending",
        leaf_font_size=12,
        show_leaf_counts=True,
        color_threshold=0.3 * max(linked[:, 2]),
    )

    plt.title("Hierarchical Clustering of Sources", fontsize=16, pad=20)
    plt.xlabel("Data Sources", fontsize=14, labelpad=15)
    plt.ylabel("Jaccard Distance", fontsize=12)
    plt.xticks(rotation=45, ha="right")

    plt.gca().spines["top"].set_visible(False)
    plt.gca().spines["right"].set_visible(False)
    plt.tight_layout()

    # Save a physical copy to your machine
    fig.savefig("semantic_dendrogram.png", dpi=300, bbox_inches="tight")

    plt.close(fig)
    return fig


def plot_schema_network(dataset, data_init):
    """
    Creates a force-directed network graph linking
    Sources -> Original Columns -> Semantic Categories.
    """
    print("Building schema network graph...")

    # Initialize an undirected graph
    G = nx.Graph()

    # Track node types so we can color-code them later
    sources = set()
    columns = set()
    categories = set()

    for name, df in dataset.items():
        sources.add(name)
        G.add_node(name, type="source")

        for col in df["data_input"].columns.tolist():
            # Classify the column using your existing pipeline function
            # Ensure get_taxonomy_for_pipeline is imported/available in this scope
            category = get_taxonomy_for_pipeline(col, data_init)

            columns.add(col)
            categories.add(category)

            # Add nodes
            G.add_node(col, type="column")
            G.add_node(category, type="category")

            # Add edges linking them together
            G.add_edge(name, col)  # Connect Source to its Column
            G.add_edge(col, category)  # Connect Column to its Schema Category

    print(f"Network built: {len(G.nodes)} nodes and {len(G.edges)} edges.")

    # Render the graph
    fig = plt.figure(figsize=(18, 14))

    # spring_layout uses a force-directed algorithm to push apart unrelated nodes
    # and pull together highly connected ones. (k controls the distance between nodes)
    pos = nx.spring_layout(G, k=0.3, iterations=50)

    # Draw Nodes by type with distinct colors and sizes
    nx.draw_networkx_nodes(
        G,
        pos,
        nodelist=list(sources),
        node_color="#ff9999",
        node_size=1200,
        label="Data Sources",
    )

    nx.draw_networkx_nodes(
        G,
        pos,
        nodelist=list(categories),
        node_color="#99ff99",
        node_size=800,
        label="Semantic Categories",
    )

    nx.draw_networkx_nodes(
        G,
        pos,
        nodelist=list(columns),
        node_color="#99ccff",
        node_size=300,
        label="Original Columns",
    )

    # Draw Edges (make them light grey so they don't overpower the text)
    nx.draw_networkx_edges(G, pos, alpha=0.15, edge_color="gray")

    # Draw Labels (Column names, Source names, etc.)
    nx.draw_networkx_labels(G, pos, font_size=8, font_family="sans-serif")

    plt.title("Data Schema Relationship Network", fontsize=20, pad=20)

    # Add a legend
    plt.legend(scatterpoints=1, loc="upper right", fontsize=12)
    plt.axis("off")  # Hide the standard x/y graph box

    plt.tight_layout()

    # Close the figure background to save memory and return the object
    plt.close(fig)
    return fig


def plot_schema_network_2(dataset_contents, exclude_classes=None):
    import networkx as nx
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    import numpy as np

    exclude_classes = exclude_classes or {
        "_noise", "SystemField", "OnlinePresence", "Coordinates",
    }

    G = nx.Graph()
    for source, col_map in dataset_contents.items():
        G.add_node(source, kind="source")
        for col, cls in col_map.items():
            if cls in exclude_classes or str(cls).startswith("Review"):
                continue
            G.add_node(cls, kind="category")
            G.add_node(col, kind="column")
            G.add_edge(source, cls)
            G.add_edge(cls, col)

    # Remove categories connected to only one source
    categories_to_remove = [
        n for n, d in G.nodes(data=True)
        if d.get("kind") == "category"
        and sum(1 for nb in G.neighbors(n)
                if G.nodes[nb].get("kind") == "source") < 2
    ]
    G.remove_nodes_from(categories_to_remove)
    G.remove_nodes_from([n for n in list(G.nodes()) if G.degree(n) == 0])

    if len(G.nodes()) == 0:
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, "No shared categories found.", ha="center", va="center")
        return fig

    # ── Layout: spring with higher k pushes nodes apart ──────
    # Use kamada_kawai as base then spread category nodes outward
    pos = nx.kamada_kawai_layout(G, scale=3)

    # Push category nodes further from center to reduce label overlap
    center = np.mean(list(pos.values()), axis=0)
    for node, d in G.nodes(data=True):
        if d.get("kind") == "category":
            vec = pos[node] - center
            norm = np.linalg.norm(vec)
            if norm > 0:
                pos[node] = center + vec * 1.6  # push outward

    # ── Node styling ─────────────────────────────────────────
    color_map = {"source": "#C0392B", "category": "#27AE60", "column": "#85C1E9"}
    size_map  = {"source": 1200,      "category": 600,        "column": 60}
    alpha_map = {"source": 0.95,      "category": 0.90,       "column": 0.60}

    node_list   = list(G.nodes())
    node_colors = [color_map[G.nodes[n]["kind"]] for n in node_list]
    node_sizes  = [size_map[G.nodes[n]["kind"]] for n in node_list]
    node_alphas = [alpha_map[G.nodes[n]["kind"]] for n in node_list]

    fig, ax = plt.subplots(figsize=(20, 16))

    # ── Draw edges first ─────────────────────────────────────
    # Separate edge types for visual hierarchy
    source_cat_edges = [
        (u, v) for u, v in G.edges()
        if G.nodes[u].get("kind") in ("source", "category")
        and G.nodes[v].get("kind") in ("source", "category")
    ]
    cat_col_edges = [
        (u, v) for u, v in G.edges()
        if (u, v) not in source_cat_edges
    ]

    nx.draw_networkx_edges(G, pos, edgelist=source_cat_edges,
                           edge_color="#888888", width=1.0,
                           alpha=0.6, ax=ax)
    nx.draw_networkx_edges(G, pos, edgelist=cat_col_edges,
                           edge_color="#cccccc", width=0.3,
                           alpha=0.3, ax=ax)

    # ── Draw nodes by kind separately to control alpha ───────
    for kind in ("column", "category", "source"):
        nodelist = [n for n in node_list if G.nodes[n]["kind"] == kind]
        nx.draw_networkx_nodes(
            G, pos,
            nodelist=nodelist,
            node_color=[color_map[kind]] * len(nodelist),
            node_size=[size_map[kind]] * len(nodelist),
            alpha=alpha_map[kind],
            ax=ax,
        )

    # ── Labels: source and category only, NO draw_networkx ───
    # draw_networkx draws all labels — use draw_networkx_labels
    # with explicit node subsets to avoid double rendering and
    # column label clutter

    source_labels   = {n: n[-2:] for n, d in G.nodes(data=True)
                       if d["kind"] == "source"}
    category_labels = {n: n for n, d in G.nodes(data=True)
                       if d["kind"] == "category"}

    # Source labels — bold, white, inside node
    nx.draw_networkx_labels(
        G, pos,
        labels=source_labels,
        font_size=8,
        font_color="white",
        font_weight="bold",
        ax=ax,
    )

    # Category labels — offset above node to avoid overlap with node circle
    pos_above = {n: (x, y + 0.18) for n, (x, y) in pos.items()
                 if n in category_labels}
    nx.draw_networkx_labels(
        G, pos_above,
        labels=category_labels,
        font_size=9,
        font_color="#1A5E38",
        font_weight="bold",
        ax=ax,
    )

    # ── Legend ───────────────────────────────────────────────
    legend_handles = [
        mpatches.Patch(color="#C0392B", label="Data source"),
        mpatches.Patch(color="#27AE60", label="Semantic category"),
        mpatches.Patch(color="#85C1E9", label="Original column"),
    ]
    ax.legend(
        handles=legend_handles,
        loc="upper left",
        fontsize=9,
        frameon=True,
        framealpha=0.9,
        edgecolor="#cccccc",
    )

    plt.title(
        "Schema category network — shared categories only",
        fontsize=13, fontfamily="serif", fontweight="bold", pad=16
    )
    plt.axis("off")
    plt.tight_layout()
    return fig


def plot_category_lines(full_map):
    """Line plot of column count per category, one line per source."""

    # Collect all categories across all sources (excluding noise/review)
    all_categories = sorted(
        {
            cls
            for col_map in full_map.values()
            for cls in col_map.values()
            if cls != "_noise" and not str(cls).startswith("Review")
        }
    )

    # Build count matrix: source → {category: count}
    source_counts = {}
    for source_name, col_map in full_map.items():
        counter = {}
        for cls in col_map.values():
            if cls == "_noise" or str(cls).startswith("Review"):
                continue
            counter[cls] = counter.get(cls, 0) + 1
        source_counts[source_name] = counter

    # Plot
    fig, ax = plt.subplots(figsize=(14, 6))
    x = np.arange(len(all_categories))
    colors = plt.cm.tab10.colors

    for i, (source_name, counter) in enumerate(source_counts.items()):
        y = [counter.get(cat, 0) for cat in all_categories]
        if source_name == "Source_02":
            lw = 5
        else:
            lw = 1.5
        ax.plot(
            x,
            y,
            marker="o",
            linewidth=lw,
            markersize=4,
            label=source_name,
            color=colors[i % len(colors)],
        )

    ax.set_xticks(x)
    ax.set_xticklabels(all_categories, rotation=45, ha="right", fontsize=9)
    ax.set_ylabel("Number of columns", fontsize=11)
    ax.set_title("Category column count per source", fontsize=13)
    ax.legend(bbox_to_anchor=(1.01, 1), loc="upper left", fontsize=9)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.yaxis.grid(True, linestyle="--", alpha=0.5)
    ax.set_axisbelow(True)

    plt.tight_layout()
    return fig


def plot_category_bars(full_map):
    """Grouped bar chart of column count per category, one group per category."""
    # Collect all categories across all sources
    all_categories = sorted(
        {
            cls
            for col_map in full_map.values()
            for cls in col_map.values()
            if cls != "_noise" and not str(cls).startswith("Review")
        }
    )

    # Build count matrix
    source_names = list(full_map.keys())
    source_counts = {}
    for source_name, col_map in full_map.items():
        counter = {}
        for cls in col_map.values():
            if cls == "_noise" or str(cls).startswith("Review"):
                continue
            counter[cls] = counter.get(cls, 0) + 1
        source_counts[source_name] = counter

    # Layout
    x = np.arange(len(all_categories))
    n_sources = len(source_names)
    bar_width = 0.8 / n_sources
    colors = plt.cm.tab10.colors

    fig, ax = plt.subplots(figsize=(16, 6))

    for i, source_name in enumerate(source_names):
        counter = source_counts[source_name]
        y = [counter.get(cat, 0) for cat in all_categories]
        offset = (i - n_sources / 2 + 0.5) * bar_width
        ax.bar(
            x + offset,
            y,
            width=bar_width,
            label=source_name,
            color=colors[i % len(colors)],
            edgecolor="white",
        )

    ax.set_xticks(x)
    ax.set_xticklabels(all_categories, rotation=45, ha="right", fontsize=9)
    ax.set_ylabel("Number of columns", fontsize=11)
    ax.set_title("Category column count per source", fontsize=13)
    ax.legend(bbox_to_anchor=(1.01, 1), loc="upper left", fontsize=9)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.yaxis.grid(True, linestyle="--", alpha=0.5)
    ax.set_axisbelow(True)

    plt.tight_layout()
    return fig


def plot_category_heatmap(full_map):

    all_categories = sorted(
        {
            cls
            for col_map in full_map.values()
            for cls in col_map.values()
            if cls != "_noise" and not str(cls).startswith("Review")
        }
    )

    source_names = list(full_map.keys())
    matrix = pd.DataFrame(0, index=source_names, columns=all_categories)

    for source_name, col_map in full_map.items():
        for cls in col_map.values():
            if cls == "_noise" or str(cls).startswith("Review"):
                continue
            matrix.loc[source_name, cls] += 1

    # ── Sort rows by total richness (descending) ──
    matrix = matrix.loc[matrix.sum(axis=1).sort_values(ascending=False).index]

    # ── Sort columns by total presence (descending) ──
    matrix = matrix[matrix.sum(axis=0).sort_values(ascending=False).index]

    fig, ax = plt.subplots(figsize=(16, len(source_names) * 0.8 + 2))
    im = ax.imshow(matrix.values, aspect="auto", cmap="Blues")

    ax.set_xticks(range(len(matrix.columns)))
    ax.set_xticklabels(matrix.columns, rotation=45, ha="right", fontsize=9)
    ax.set_yticks(range(len(matrix.index)))
    ax.set_yticklabels(matrix.index, fontsize=9)

    for i in range(len(matrix.index)):
        for j in range(len(matrix.columns)):
            val = matrix.iloc[i, j]
            if val > 0:
                ax.text(
                    j,
                    i,
                    str(val),
                    ha="center",
                    va="center",
                    fontsize=8,
                    color="white" if val > matrix.values.max() * 0.6 else "black",
                )

    plt.colorbar(im, ax=ax, label="Number of columns")
    ax.set_title("Category column count per source", fontsize=13)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    plt.tight_layout()
    return fig


def create_bubble_density_plot(
    full_map, title="Bubble Density of Categories by Dataset"
):
    all_categories = sorted({
        cls
        for col_map in full_map.values()
        for cls in col_map.values()
        if cls != "_noise" and not str(cls).startswith("Review")
    })

    source_names = list(full_map.keys())
    df = pd.DataFrame(0, index=source_names, columns=all_categories)

    for source_name, col_map in full_map.items():
        for cls in col_map.values():
            if cls == "_noise" or str(cls).startswith("Review"):
                continue
            df.loc[source_name, cls] += 1

    # ── FAULT 1 FIX: drop empty rows before computing fill rate ──
    df = df.loc[(df > 0).any(axis=1)]

    # Sort
    df = df.loc[df.sum(axis=1).sort_values(ascending=False).index]
    df = df[df.sum(axis=0).sort_values(ascending=False).index]

    # ── FAULT 2 FIX: use fixed denominator ───────────────────────
    total_classes = len(all_categories)  # consistent across all sources
    source_fill_rate = (df > 0).sum(axis=1) / total_classes * 100

    # Melt
    df_melted = (
        df.reset_index()
          .melt(id_vars="index", var_name="Category", value_name="Count")
          .rename(columns={"index": "Source"})
    )

    df_melted["Source_Fill_Rate"] = df_melted["Source"].map(source_fill_rate)

    # ── FAULT 3 FIX: guard against silent NaN fill rates ─────────
    missing = df_melted["Source_Fill_Rate"].isna().sum()
    if missing > 0:
        print(f"Warning: {missing} rows have NaN fill rate — check source name alignment")

    df_plot = df_melted[df_melted["Count"] > 0].copy()

    fig, ax = plt.subplots(figsize=(16, len(df.index) * 0.8 + 2))

    if df_plot.empty:
        ax.text(0.5, 0.5, "No data to display after filtering.",
                ha="center", va="center")
        return fig

    sns.scatterplot(
        data=df_plot,
        x="Category",
        y="Source",
        size="Count",
        hue="Source_Fill_Rate",
        sizes=(50, 1000),
        palette="Blues",
        alpha=0.8,
        edgecolor="black",
        ax=ax,
    )

    ax.set_xticklabels(ax.get_xticklabels(), rotation=45, ha="right", fontsize=9)
    ax.set_title(title, fontsize=13, pad=15)
    ax.legend(bbox_to_anchor=(1.05, 1), loc="upper left",
              borderaxespad=0, title="Fill Rate (%) & Count")
    ax.grid(True, linestyle="--", alpha=0.3)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return fig


def heatmap_bubble_dri(full_map, title="Subset 1 Taxonomy Coverage"):
    """
    Bubble heatmap for DRI taxonomy coverage.
    Bubble size = column count, color = fill rate (% of DRI categories present).
    Styled for research paper publication.
    """

    DRI_CATEGORIES = {
        "Coordinates",
        "Identifier",
        "Contact",
        "OnlinePresence",
        "Equipment",
        "Product",
        "ManufacturingProcess",
        "Material",
        "fabricationCapability",
    }

    # ── Build matrix ─────────────────────────────────────────
    source_names = list(full_map.keys())
    existing = sorted({
        cls
        for col_map in full_map.values()
        for cls in col_map.values()
        if cls in DRI_CATEGORIES
    })

    matrix = pd.DataFrame(0, index=source_names, columns=existing)
    for source, col_map in full_map.items():
        for cls in col_map.values():
            if cls in DRI_CATEGORIES:
                matrix.loc[source, cls] += 1

    matrix = matrix.loc[(matrix > 0).any(axis=1)]
    matrix = matrix.loc[matrix.sum(axis=1).sort_values(ascending=False).index]
    matrix = matrix[matrix.sum(axis=0).sort_values(ascending=False).index]

    # ── FAULT 1 FIX: fixed denominator = full DRI definition size ─
    fill_rate = (matrix > 0).sum(axis=1) / len(DRI_CATEGORIES) * 100

    df_melted = (
        matrix.reset_index()
              .melt(id_vars="index", var_name="Category", value_name="Count")
              .rename(columns={"index": "Source"})
    )
    df_melted["Fill_Rate"] = df_melted["Source"].map(fill_rate)

    # Guard against silent NaN fill rates
    missing = df_melted["Fill_Rate"].isna().sum()
    if missing > 0:
        print(f"Warning: {missing} rows have NaN fill rate — check source name alignment")

    df_plot = df_melted[df_melted["Count"] > 0].copy()

    # ── FAULT 3 FIX: derive layout sizes after all filtering ──────
    cat_order    = list(matrix.columns)
    source_order = list(matrix.index)
    n_cats       = len(cat_order)
    n_sources    = len(source_order)

    fig, ax = plt.subplots(figsize=(n_cats * 1.2 + 2, n_sources * 0.65 + 2))

    if df_plot.empty:
        ax.text(0.5, 0.5, "No DRI data to display.",
                ha="center", va="center")
        return fig

    # ── Color map ─────────────────────────────────────────────
    cmap = cm.YlGn
    norm = mcolors.Normalize(vmin=0, vmax=100)
    # FAULT 2 FIX: removed dead apply() line — scatter handles color directly

    # ── Bubble size scaling ───────────────────────────────────
    max_count  = df_plot["Count"].max()
    size_scale = df_plot["Count"].apply(lambda c: (c / max_count) * 900 + 80)

    df_plot["x"] = df_plot["Category"].apply(lambda c: cat_order.index(c))
    df_plot["y"] = df_plot["Source"].apply(lambda s: source_order.index(s))

    scatter = ax.scatter(
        df_plot["x"],
        df_plot["y"],
        s=size_scale,
        c=df_plot["Fill_Rate"],
        cmap=cmap,
        norm=norm,
        alpha=0.85,
        edgecolors="#444444",
        linewidths=0.4,
    )

    # ── Annotate count inside bubble ─────────────────────────
    for _, row in df_plot.iterrows():
        ax.text(
            row["x"], row["y"],
            str(int(row["Count"])),
            ha="center", va="center",
            fontsize=7, fontweight="500",
            color="white" if row["Fill_Rate"] > 55 else "#333333",
        )

    # ── Axes ─────────────────────────────────────────────────
    ax.set_xticks(range(n_cats))
    ax.set_xticklabels(cat_order, rotation=40, ha="right",
                       fontsize=9, fontfamily="serif")
    ax.set_yticks(range(n_sources))
    ax.set_yticklabels(source_order, fontsize=9, fontfamily="serif")

    ax.set_xlim(-0.6, n_cats - 0.4)
    ax.set_ylim(-0.6, n_sources - 0.4)
    ax.invert_yaxis()

    ax.set_xlabel("Semantic category", fontsize=10,
                  fontfamily="serif", labelpad=10)
    ax.set_ylabel("Data source", fontsize=10,
                  fontfamily="serif", labelpad=10)
    ax.set_title(title, fontsize=12, fontfamily="serif",
                 fontweight="bold", pad=14)

    # ── Grid ─────────────────────────────────────────────────
    ax.set_axisbelow(True)
    ax.grid(True, linestyle=":", linewidth=0.5, color="#cccccc", alpha=0.8)
    for spine in ax.spines.values():
        spine.set_visible(False)

    # ── Colorbar ──────────────────────────────────────────────
    cbar = fig.colorbar(scatter, ax=ax, pad=0.02, fraction=0.025, aspect=30)
    cbar.set_label("DRI fill rate (%)", fontsize=9, fontfamily="serif")
    cbar.ax.tick_params(labelsize=8)
    cbar.outline.set_visible(False)

    # ── Bubble size legend ────────────────────────────────────
    legend_counts = sorted([c for c in [1, 2, 4, max_count] if c <= max_count])
    legend_handles = [
        plt.scatter([], [],
                    s=(c / max_count) * 900 + 80,
                    color="#888888", alpha=0.7,
                    edgecolors="#444444", linewidths=0.4,
                    label=str(c))
        for c in legend_counts
    ]
    legend = ax.legend(
        handles=legend_handles,
        title="Column\ncount",
        title_fontsize=8,
        fontsize=8,
        loc="lower right",
        frameon=True,
        framealpha=0.9,
        edgecolor="#cccccc",
        labelspacing=1.0,
        borderpad=0.8,
    )
    legend.get_frame().set_linewidth(0.5)

    fig.tight_layout()
    return fig


def plot_source_volume_vs_loss(dataset_dict, title="Source Benchmark: Data Loss vs. Input Volume"):
    """
    Parses a nested dictionary, robustly calculates data loss and input volume 
    regardless of strict data types, and generates a 4-quadrant scatter plot.
    """
    records = []
    
    # 1. Robustly parse the dictionary
    for source_name, nested_data in dataset_dict.items():
        # Ensure the value is actually a dictionary before trying to use .get()
        if not isinstance(nested_data, dict):
            continue 

        d_in = nested_data.get('data_input')
        d_out = nested_data.get('data_output')
        
        try:
            # Try to get row count via .shape[0] (Pandas), fallback to len() (Lists/Dicts)
            input_rows = d_in.shape[0] if hasattr(d_in, 'shape') else len(d_in) if d_in is not None else 0
            output_rows = d_out.shape[0] if hasattr(d_out, 'shape') else len(d_out) if d_out is not None else 0
            
            # Only append if we actually have input data
            if input_rows > 0:
                records.append({
                    'source': source_name,
                    'input_rows': input_rows,
                    'output_rows': output_rows
                })
        except TypeError as e:
            print(f"Skipping {source_name}: Unable to calculate length. Error: {e}")
            continue
            
    df = pd.DataFrame(records)
    
    # Trigger the error if parsing completely failed
    if df.empty:
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.text(0.5, 0.5, "Error: Could not extract valid row counts from dataset_dict.", ha='center', va='center')
        ax.axis('off')
        return fig
    
    # 2. Calculate Data Loss Percentage
    df['data_loss_pct'] = ((df['input_rows'] - df['output_rows']) / df['input_rows']) * 100
    df['data_loss_pct'] = df['data_loss_pct'].clip(lower=0)
    
    # 3. Calculate thresholds for the quadrants
    median_loss = df['data_loss_pct'].median()
    median_volume = df['input_rows'].median()

    # 4. Setup the figure
    # 4. Setup the figure
    fig, ax = plt.subplots(figsize=(12, 8))
    
    sns.scatterplot(
        data=df, 
        x='data_loss_pct', 
        y='input_rows', 
        s=150,             # Slightly smaller bubbles to reduce clutter
        color='steelblue',
        edgecolor='black',
        alpha=0.8,
        ax=ax
    )
    
    # --- FIX 1: Use a Logarithmic Scale for Volume ---
    ax.set_yscale('log')
    
    # 5. Add the Quadrant crosshairs (these will automatically map correctly to the log scale)
    ax.axvline(median_loss, color='gray', linestyle='--', alpha=0.7)
    ax.axhline(median_volume, color='gray', linestyle='--', alpha=0.7)
    
    # --- FIX 2: Use adjust_text to prevent label overlap ---
    texts = []
    for i in range(df.shape[0]):
        texts.append(
            ax.text(
                df['data_loss_pct'].iloc[i], 
                df['input_rows'].iloc[i], 
                df['source'].iloc[i], 
                fontsize=9,
                weight='bold'
            )
        )
    
    # This automatically repels the text away from each other and draws a tiny line if needed
    adjust_text(texts, arrowprops=dict(arrowstyle="-", color='gray', lw=0.5))

    # 7. Add Quadrant Annotations
    props = dict(boxstyle='round', facecolor='white', alpha=0.8, edgecolor='gray')
    
    ax.text(0.02, 0.96, 'High Volume, Low Loss\n(Core Sources)', transform=ax.transAxes, 
            fontsize=11, verticalalignment='top', bbox=props)
    ax.text(0.98, 0.96, 'High Volume, High Loss\n(Rich but Noisy)', transform=ax.transAxes, 
            fontsize=11, verticalalignment='top', horizontalalignment='right', bbox=props)
    ax.text(0.02, 0.04, 'Low Volume, Low Loss\n(Reliable Niche)', transform=ax.transAxes, 
            fontsize=11, verticalalignment='bottom', bbox=props)
    ax.text(0.98, 0.04, 'Low Volume, High Loss\n(Low Value)', transform=ax.transAxes, 
            fontsize=11, verticalalignment='bottom', horizontalalignment='right', bbox=props)

    # 8. Formatting
    ax.set_title(title, fontsize=15, pad=20)
    ax.set_xlabel("Data Loss After Filtering (%) ➔", fontsize=12)
    ax.set_ylabel("Input Row Volume (Log Scale) ➔", fontsize=12)
    
    # --- FIX 1: Widen the X-axis buffer ---
    # Pushes X=0 further right, and the max value further left
    x_min_val = df['data_loss_pct'].min()
    x_max_val = df['data_loss_pct'].max()
    ax.set_xlim(left=min(-10, x_min_val - 10), right=min(115, x_max_val + 20))
    
    # --- FIX 2: Multiply/Divide for Log Scale Y-axis buffer ---
    # This pulls Source_12 down from the ceiling and Source_08 up from the floor
    y_min_val = df['input_rows'].min()
    y_max_val = df['input_rows'].max()
    
    # Use 0.2 (divide by 5) for the floor and 4.0 (multiply by 4) for the ceiling 
    # to create massive visual breathing room on a log scale
    ax.set_ylim(bottom=y_min_val * 0.2, top=y_max_val * 4.0)
    
    # Push the quadrant labels to the absolute back so bubbles always float above them
    # if they do happen to get close.
    for text_obj in ax.texts:
        if 'Volume' in text_obj.get_text():  # Target only the quadrant labels
            text_obj.set_zorder(1)
            text_obj.set_alpha(0.85)

    ax.grid(True, linestyle=':', alpha=0.6)
    fig.tight_layout()
    
    return fig