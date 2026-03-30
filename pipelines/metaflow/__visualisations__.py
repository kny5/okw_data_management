#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Oct 31 07:51:41 2024

Author: Antonio de Jesus Anaya Hernandez, DevOps eng. for the IoPA.

Author: The internet of Production Alliance, 2024.

The Open Know Where (OKW) Initiative is part of the Internet of Production Alliance and its members.

License: CC BY SA

![CC BY SA](https://mirrors.creativecommons.org/presskit/buttons/88x31/svg/by-sa.svg)

Description: Python code for processing data as maps and tables.
"""

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

opt.maxBytes = 0


def load_js_file(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        return file.read()


import numpy as np
import folium
from folium.plugins import FastMarkerCluster, FloatImage, MeasureControl, LocateControl, Fullscreen, HeatMap

# Assuming load_js_file is defined elsewhere in your script
# from __functions__ import load_js_file 

class Plot:
    def __init__(self, dataframe, lat_col="latitude", lon_col="longitude", popup_cols=None, weight_col=None, plot_type="cluster", max_cluster_rad=40):
        """
        :param dataframe: The pandas DataFrame containing geo data.
        :param lat_col: Name of the latitude column (default: "latitude").
        :param lon_col: Name of the longitude column (default: "longitude").
        :param popup_cols: List of column names to pass to the JS callback for popups (used in 'cluster' mode).
        :param weight_col: Column name to use for heatmap intensity (used in 'heatmap' mode).
        :param plot_type: Choose "cluster" or "heatmap".
        :param max_cluster_rad: Maximum radius for the marker cluster.
        """
        self.data = dataframe.copy()
        self.lat_col = lat_col
        self.lon_col = lon_col
        self.weight_col = weight_col
        self.plot_type = plot_type.lower()
        self.popup_cols = popup_cols if popup_cols is not None else []
        self.max_rad = max_cluster_rad
        
        # Assets 
        self.icon_cluster = load_js_file("pipelines/metaflow/assets/cluster_icon.js")
        self.callback = load_js_file("pipelines/metaflow/assets/cluster_mod.js")
        self.tiles_url = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}"
        self.tiles_attribution = "Tiles &copy; Esri &mdash; Source: Esri, DeLorme, NAVTEQ, USGS, Intermap, iPC, NRCAN, Esri Japan, METI, Esri China (Hong Kong), Esri (Thailand), TomTom, 2012"
        
        self.prep_data()
        self.set_map()
        self.add_points()
        self.add_legend()

    def prep_data(self):
        # Safely drop rows missing coordinates
        self.output_map = self.data.dropna(subset=[self.lat_col, self.lon_col])
        print(f"Data summary for mapping ({len(self.output_map)} valid rows):")
        
        # Prepare data for Cluster mode
        extract_columns = [self.lat_col, self.lon_col] + self.popup_cols
        missing_cols = [col for col in self.popup_cols if col not in self.output_map.columns]
        if missing_cols:
            print(f"Warning: The following popup columns were not found in the dataframe: {missing_cols}")
            extract_columns = [col for col in extract_columns if col not in missing_cols]

        self.zip_data = self.output_map[extract_columns].values.tolist()

        # Prepare data for Heatmap mode
        if self.plot_type == "heatmap":
            if self.weight_col and self.weight_col in self.output_map.columns:
                # Drop rows where the weight is NaN to avoid breaking the heatmap
                heat_df = self.output_map.dropna(subset=[self.weight_col])
                self.heat_data = heat_df[[self.lat_col, self.lon_col, self.weight_col]].values.tolist()
            else:
                if self.weight_col:
                    print(f"Warning: Weight column '{self.weight_col}' not found. Defaulting to density heatmap.")
                # If no weight column is provided, HeatMap just calculates density based on coordinates
                self.heat_data = self.output_map[[self.lat_col, self.lon_col]].values.tolist()

        # Safely calculate map bounds
        if not self.output_map.empty:
            self.bounds = [
                [self.output_map[self.lat_col].min(), self.output_map[self.lon_col].min()],
                [self.output_map[self.lat_col].max(), self.output_map[self.lon_col].max()],
            ]
        else:
            self.bounds = [[0, 0], [0, 0]]

    def set_map(self):
        if not self.output_map.empty:
            self.m = folium.Map(
                location=[
                    self.output_map[self.lat_col].mean(),
                    self.output_map[self.lon_col].mean(),
                ],
                zoom_start=2, # Zoomed out slightly more for heatmaps
                tiles=self.tiles_url,
                attr=self.tiles_attribution,
                max_zoom=15,
                zoomControl=False,
                prefer_canvas=True,
            )
            self.m.fit_bounds(self.bounds)
        else:
            print("Cannot generate map: No valid location values found.")
            self.m = folium.Map(location=[0,0], zoom_start=2, tiles=self.tiles_url, attr=self.tiles_attribution)

    def add_points(self):
        if not hasattr(self, 'zip_data') or not self.zip_data:
            return

        if self.plot_type == "heatmap":
            # Add the HeatMap layer
            HeatMap(
                self.heat_data,
                radius=12,      # Size of the heat points
                blur=15,        # Smoothness of the gradients
                max_zoom=10,    # At what zoom level the points reach maximum intensity
            ).add_to(self.m)
        else:
            # Add the standard Marker Cluster layer
            FastMarkerCluster(
                data=self.zip_data,
                icon_create_function=self.icon_cluster,
                callback=self.callback,
                options={"singleMarkerMode": True, "maxClusterRadius": self.max_rad},
            ).add_to(self.m)

    def add_legend(self):
        # We skip the standard cluster legend if we are drawing a heatmap
        if self.plot_type == "heatmap":
            return
            
        try:
            with open("pipelines/metaflow/assets/legend.html", "r") as f:
                legend_html = f.read()
            self.m.get_root().html.add_child(folium.Element(legend_html))
        except FileNotFoundError:
            print("Warning: 'legend.html' not found. Skipping legend generation.")

    def render(self):
        FloatImage(
            "https://github.com/iop-alliance/data_reports/blob/main/assets/img/iopa_logo_okw_sm.png?raw=true",
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
        
        return self.m.get_root().render()


class Tabular:
    def __init__(self, dataframe):
        self.data = dataframe

    def table_output(self):
        table_html = to_html_datatable(
            self.data,
            display_logo_when_loading=True,
            buttons=[
                "pageLength",
                {"extend": "csvHtml5", "title": "Manufacturing Locations"},
                {"extend": "excelHtml5", "title": "Manufacturing Locations"},
            ],
        )
        return table_html


# print(output["country_code"].value_counts().nlargest(10))

# import pycountry_convert as pcountry

# def get_continent(country_alpha2):
#     continent_code = pcountry.country_alpha2_to_continent_code(country_alpha2)
#     continent_name = pcountry.convert_continent_code_to_continent_name(continent_code)
#     return continent_name

# output_db['continent'] = output_db['country_code'].apply(get_continent)
# grouped_db = output_db.groupby(['continent', 'country_code']).size().reset_index(name='Location Count')
# top_three_db = (
#     grouped_db
#     .sort_values(['continent', 'Location Count'], ascending=[True, False])
#     .groupby('continent')
#     .head(3)
# )

# top_three_db
