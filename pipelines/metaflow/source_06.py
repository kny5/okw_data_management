"""
Created on Thu Oct 31 07:51:41 2024

Author: Antonio de Jesus Anaya Hernandez
Role: DevOps Engineer
Organization: Internet of Production Alliance
Description:
This script implements a Metaflow pipeline for extracting, transforming,
and visualizing data from the Make.Works API. The data is processed into a
cleaned format suitable for visualization in tabular and map formats.
"""

import pandas as pd
from __functions__ import ReverseGeocode, generate_blake2_uid
from __visualisations__ import Tabular
from metaflow import FlowSpec, Parameter, card, step, current
from okw_libs.dwld import iter_request
from __metasteps__ import TailSteps


class Source_06(FlowSpec, TailSteps):
    """
    Metaflow pipeline class to manage the data flow:
    Extract, clean, and visualize data from the Make.Works API.
    """

    url = "https://make.works/companies"
    api_url = "https://make.works/companies?page={n}&format=json"

    radius_ = Parameter(
        "radius", default=1, help="Radius value for proximity filtering"
    )
    min_points_ = Parameter(
        "min_points", default=3, help="Minimum number of points for proximity filtering"
    )

    render_map_ = Parameter(
        "render_map", default=False, help="Whether to render the map visualization"
    )

    @step
    def start(self):
        """
        Initial step of the pipeline.
        Prepares for data extraction.
        """
        print("Starting...")
        self.next(self.extract)

    @card
    @step
    def extract(self):
        """
        Extract step.
        Fetches raw data from the Make.Works API and converts it into a DataFrame.
        """
        self.raw = iter_request(self.api_url)  # Fetch data from API
        self.data_input = pd.DataFrame(self.raw)  # Convert to DataFrame
        print(self.data_input.columns.tolist())  # Print column names for debugging
        self.next(self.clean)

    @card(type="html")
    @step
    def clean(self):
        """
        Clean step.
        Renames and filters columns to create a standardized output dataset.
        """

        self.data_input.rename(
            columns={
                "url": "record_source_url",
                "lat": "latitude",
                "lng": "longitude",
                "website": "web_url",
            },
            inplace=True,
        )
        print(self.data_input.columns.tolist())

        self.data_input["record_source_url"] = self.data_input["record_source_url"].str[:-5]
        self.data_output = self.data_input[
            ["name", "latitude", "longitude", "record_source_url", "web_url"]
        ]
        print(self.data_output.columns.tolist())  # Print column names for debugging
        self.next(self.transform)

    @card(type="html")
    @step
    def transform(self):
        """Trandforms the cleaned data by performing reverse geocoding to enrich it with location information, and prepares it for visualization."""
        id = current.flow_name[-2:]
        self.data_output["source"] = id
        self.data_output["uid"] = self.data_output.apply(generate_blake2_uid, axis=1)
        self.geocode = ReverseGeocode(self.data_output).get()
        self.html = Tabular(self.geocode).table_output()
        self.next(self.visualise)




if __name__ == "__main__":
    Source_06()
