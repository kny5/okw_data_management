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
import requests
from bs4 import BeautifulSoup


def scrape_makeworks_page(url):
    """Scrapes structured data from a Make.Works company HTML page."""
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')

        def get_list(heading):
            """Find a section heading and return its list items."""
            h4 = soup.find('h4', string=heading)
            if not h4:
                return []
            ul = h4.find_next('ul')
            return [li.get_text(strip=True) for li in ul.find_all('li')] if ul else []

        def get_production_field(label):
            """Find a labelled production detail field."""
            h5 = soup.find('h5', string=lambda t: t and label.lower() in t.lower())
            if not h5:
                return None
            span = h5.find_next('span')
            return span.get_text(strip=True) if span else None

        return {
            'materials':            get_list('Materials'),
            'processes':            get_list('Processes'),
            'machines':             get_list('Machines'),
            'products':             get_list('Products'),
            'works_with':           get_list('Works With'),
            'capacity_type':        get_list('Capacity'),
            'production_access':    get_production_field('Production Access'),
            'industry':             get_production_field('Industry'),
        }
    except Exception as e:
        print(f"Scrape failed for {url}: {e}")
        return {}
    

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
                "m_id": "material_id",
            },
            inplace=True,
        )
        print(self.data_input.columns.tolist())

        self.data_input["record_source_url"] = self.data_input["record_source_url"].str[:-5]
        self.data_output = self.data_input[
            ["name", "latitude", "longitude", "record_source_url", "web_url"]
        ]
        print(self.data_output.columns.tolist())  # Print column names for debugging
        self.next(self.enrich)

    @card
    @step
    def enrich(self):
        """
        Enrich step.
        Fills missing fields by scraping the HTML page for each record.
        Adds materials, processes, machines, products from the company page.
        """
        enriched_rows = []

        for _, row in self.data_input.iterrows():
            page_url = row.get('record_source_url')
            if not page_url:
                enriched_rows.append(row)
                continue

            scraped = scrape_makeworks_page(page_url)

            # Merge scraped fields into row — only fill if currently empty/null
            for field, value in scraped.items():
                if field not in row or not row[field] or row[field] == [] or row[field] == '':
                    row[field] = value

            enriched_rows.append(row)

        self.data_input = pd.DataFrame(enriched_rows)

        # Fill lat/lng from address using geocoding if still missing
        missing_coords = self.data_input[
            self.data_input['latitude'].isna() | (self.data_input['latitude'] == '')
        ]
        print(f"Records missing coordinates: {len(missing_coords)}")
        print(f"New columns added: {[c for c in self.data_input.columns if c in ['materials','processes','machines','products','works_with']]}")

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
