"""
Created on Thu Oct 31 07:51:41 2024

@author: kny5
"""

import pandas as pd
from __functions__ import ReverseGeocode, generate_blake2_uid
from __visualisations__ import Tabular
from metaflow import FlowSpec, Parameter, card, step, current
from okw_libs.dwld import req_data
from __metasteps__ import TailSteps
import requests
from bs4 import BeautifulSoup
import concurrent.futures

FABLABS_BASE = "https://fablabs.io"


def get_lab_machine_ids(lab_slug):
    machine_ids = []

    url = f"https://www.fablabs.io/labs/{lab_slug}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        r = requests.get(url, headers=headers, timeout=10)

        if r.status_code == 200:
            soup = BeautifulSoup(r.content, "html.parser")

            machine_divs = soup.find_all("div", class_="machine")

            for div in machine_divs:
                div_id = div.get("id")
                if div_id and div_id.startswith("machine_"):
                    machine_ids.append(div_id.replace("machine_", ""))
        else:
            print(f"Failed to fetch {lab_slug} - Status Code: {r.status_code}")

    except Exception as e:
        print(f"Error fetching {lab_slug}: {e}")

    return list(set(machine_ids))


class Source_02(FlowSpec, TailSteps):
    url = "https://api.fablabs.io/0/labs.json"
    radius_ = Parameter("radius", default=100)
    min_points_ = Parameter("min_points", default=2)
    render_map_ = Parameter("render_map", default=True)

    @step
    def start(self):
        print(self.__class__.__name__)
        self.next(self.extract)

    @card(type="html")
    @step
    def extract(self):
        self.raw = req_data(self.url).json()
        self.data_input = pd.DataFrame(self.raw)
        self.html = Tabular(self.data_input).table_output()
        print(self.data_input.columns.tolist())
        self.next(self.enrich)

    @step
    def enrich(self):
        """Fetches machine IDs for each lab using concurrent workers and merges onto data_output."""

        def get_lab_machine_ids(lab_slug):
            machine_ids = []
            url = f"https://www.fablabs.io/labs/{lab_slug}"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }

            try:
                r = requests.get(url, headers=headers, timeout=10)
                if r.status_code == 200:
                    soup = BeautifulSoup(r.content, "html.parser")
                    machine_divs = soup.find_all("div", class_="machine")

                    for div in machine_divs:
                        div_id = div.get("id")
                        if div_id and div_id.startswith("machine_"):
                            machine_ids.append(div_id.replace("machine_", ""))
            except Exception:
                pass

            return list(set(machine_ids))

        results_dict = {}
        max_workers = 40

        print(f"Starting concurrent machine fetching with {max_workers} workers...")

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:

            future_to_slug = {
                executor.submit(get_lab_machine_ids, slug): slug
                for slug in self.data_input["slug"].dropna()
            }

            for future in concurrent.futures.as_completed(future_to_slug):
                slug = future_to_slug[future]
                try:
                    ids = future.result()
                    results_dict[slug] = ids

                    parsed_machines = ", ".join(ids) if ids else "None"
                    print(f"[{slug}] Found {len(ids)} machines: {parsed_machines}")

                except Exception as exc:
                    print(f"[{slug}] generated an exception: {exc}")
                    results_dict[slug] = []

        self.data_input["machines"] = (
            self.data_input["slug"]
            .map(results_dict)
            .apply(lambda x: x if isinstance(x, list) else [])
        )
        self.data_input["machine_count"] = self.data_input["machines"].apply(len)

        print(
            f"Done. {self.data_input['machine_count'].sum()} machines found across {len(self.data_input)} labs."
        )
        self.next(self.clean)

    @step
    def clean(self):
        remove_notactive = self.data_input[
            ~self.data_input["activity_status"].isin(["closed", "planned"])
        ]

        self.cleaned = remove_notactive.drop_duplicates(subset=["name"], keep="last")
        self.next(self.transform)

    @card(type="html")
    @step
    def transform(self):
        self.cleaned["record_source_url"] = (
            "https://www.fablabs.io/labs/" + self.cleaned.slug
        )

        self.cleaned["web_url"] = self.cleaned["links"].apply(
            lambda x: x[0]["url"] if isinstance(x, list) and len(x) > 0 else None
        )
        self.data_output = self.cleaned[
            ["name", "latitude", "longitude", "record_source_url", "web_url"]
        ]
        self.data_output["uid"] = self.data_output.apply(generate_blake2_uid, axis=1)
        self.geocode = ReverseGeocode(self.data_output).get()
        self.html = Tabular(self.geocode).table_output()
        id = current.flow_name[-2:]
        self.data_output["source"] = id
        self.next(self.visualise)


if __name__ == "__main__":
    Source_02()
