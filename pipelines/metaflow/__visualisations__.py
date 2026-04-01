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
from bs4 import BeautifulSoup as bs
from __functions__ import obfuscate_text

opt.maxBytes = 0


def load_js_file(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        return file.read()


class Plot:
    def __init__(self, dataframe, max_cluster_rad=40):
        self.icon_cluster = load_js_file("pipelines/metaflow/assets/cluster_icon.js")
        self.callback = load_js_file("pipelines/metaflow/assets/cluster_mod.js")
        # self.tiles_url = 'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}'
        self.tiles_url = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}"
        self.tiles_attribution = "Tiles &copy; Esri &mdash; Source: Esri, DeLorme, NAVTEQ, USGS, Intermap, iPC, NRCAN, Esri Japan, METI, Esri China (Hong Kong), Esri (Thailand), TomTom, 2012"
        self.data = dataframe
        self.max_rad = max_cluster_rad
        self.prep_data()
        self.set_map()
        self.add_points()
        self.add_legend()
        self.add_count()

    def prep_data(self):
        self.output_map = self.data.dropna(subset=["latitude", "longitude"])
        print(self.output_map.info(verbose=True))
        print(self.output_map.columns.tolist())
        # self.zip_data = [(row['latitude'], row['longitude'], row['name']
        #              # row['url'],
        #              # row['email']
        #              )
        #             for index, row in self.output_map.iterrows()]
        try:
            self.zip_data = list(
                zip(
                    self.output_map["latitude"],
                    self.output_map["longitude"],
                    obfuscate_text(self.output_map["name"], key="kny5"),
                    self.output_map["web_url"],
                    self.output_map["uid"],
                )
            )
        except KeyError:
            self.zip_data = list(
                zip(
                    self.output_map["latitude"],
                    self.output_map["longitude"],
                    obfuscate_text(self.output_map["name"], key="kny5"),
                    str(self.output_map["occurrences"]),
                )
            )
        self.bounds = [
            [self.output_map["latitude"].min(), self.output_map["longitude"].min()],
            [self.output_map["latitude"].max(), self.output_map["longitude"].max()],
        ]

    def set_map(self):
        # Check for NaN values in latitude and longitude before creating the
        # map
        if (
            not np.isnan(self.output_map["latitude"]).any()
            and not np.isnan(self.output_map["longitude"]).any()
        ):
            self.m = folium.Map(
                location=[
                    self.output_map["latitude"].mean(),
                    self.output_map["longitude"].mean(),
                ],
                zoom_start=1,
                tiles=self.tiles_url,
                attr=self.tiles_attribution,
                max_zoom=15,
                # worldCopyJump= False,
                zoomControl=False,
                prefer_canvas=True,
            )
            self.m.fit_bounds(self.bounds)
        else:
            print("Location values cannot contain NaNs.")

    def add_points(self):
        FastMarkerCluster(
            data=self.zip_data,
            icon_create_function=self.icon_cluster,
            callback=self.callback,
            options={"singleMarkerMode": True, "maxClusterRadius": self.max_rad},
        ).add_to(self.m)

    def add_legend(self):
        with open("pipelines/metaflow/assets/legend.html", "r") as f:
            legend_html = f.read()
        self.m.get_root().html.add_child(folium.Element(legend_html))
    
    def add_count(self):
        with open("pipelines/metaflow/assets/count.html", "r") as f:
            count_html = f.read()
        self.m.get_root().html.add_child(folium.Element(count_html))

    def render(self):
        FloatImage(
            "https://github.com/iop-alliance/data_reports/blob/main/assets/img/iopa_logo_okw_sm.png?raw=true",
            bottom=3,
            left=3,
        ).add_to(self.m)
        MeasureControl(position="bottomright").add_to(self.m)
        # Geocoder(position="topleft").add_to(self.m)
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

def extract_map_data_from_string(html_string, js_filename="cluster_data.js"):
    """
    Parses an HTML string, extracts the map data script containing 'var data =', 
    and updates the HTML to link to an external JS file.
    
    Returns:
        tuple: (modified_html_string, extracted_js_content)
               If the specific script is not found, extracted_js_content will be None.
    """
    # 1. Parse the HTML string directly
    soup = bs(html_string, 'html.parser')

    # 2. Find the target <script> tag containing 'var data ='
    target_script = None
    for script in soup.find_all('script'):
        if script.string and 'var data =' in script.string:
            target_script = script
            break

    # 3. Handle the case where the data isn't found
    if not target_script:
        print("Could not find a script block containing 'var data ='.")
        # Return the original HTML untouched, and None for the JS
        return html_string, None

    # 4. Extract the JavaScript content
    js_content = target_script.string.strip()

    # 5. Modify the HTML script tag to point to the external file
    target_script.string = ""  # Clear the inline data
    target_script['src'] = js_filename  # Link to the external file
    target_script['defer'] = "true" # Ensure it loads after the HTML

    # 6. Return the updated HTML string and the raw JS string
    return str(soup), js_content


def extract_map_data_to_js(html_filepath, output_js_filename="map_data.js"):
    """
    Extracts a specific script block containing 'var data =' from an HTML file, 
    saves it to an external .js file, and links it back to the HTML.
    """
    print(f"Processing: {html_filepath}...")

    # 1. Read the HTML file
    try:
        with open(html_filepath, 'r', encoding='utf-8') as file:
            soup = bs(file, 'html.parser')
    except FileNotFoundError:
        print(f"Error: Could not find the file {html_filepath}")
        return

    # 2. Find the target <script> tag containing 'var data ='
    target_script = None
    for script in soup.find_all('script'):
        # We check if the script has text inside and contains our specific variable
        if script.string and 'var data =' in script.string:
            target_script = script
            break

    if not target_script:
        print("Could not find a script block containing 'var data ='. No changes made.")
        return

    # 3. Extract the JavaScript content
    js_content = target_script.string.strip()

    # 4. Save the JS content to the external file
    directory = os.path.dirname(html_filepath)
    js_filepath = os.path.join(directory, output_js_filename)
    
    with open(js_filepath, 'w', encoding='utf-8') as js_file:
        js_file.write(js_content)
    
    print(f"Successfully saved data to: {js_filepath}")

    # 5. Modify the HTML to point to the new external JS file
    target_script.string = ""  # Clear the massive inline data
    target_script['src'] = output_js_filename  # Link to the new file

    # 6. Save the modified HTML back to the original file
    with open(html_filepath, 'w', encoding='utf-8') as file:
        file.write(str(soup))
        
    print(f"Successfully updated HTML file to link to {output_js_filename}.")

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
