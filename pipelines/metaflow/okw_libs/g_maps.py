"""
Created on Fri Nov  8 01:40:20 2024

@author: kny5
"""

import re

from fastkml import kml


def kml_object_to_dict(kml_obj):

    attributes = {}

    for attr in dir(kml_obj):
        if not attr.startswith("__"):  # Skip built-in attributes
            try:
                value = getattr(kml_obj, attr)
            except AttributeError:
                continue

            if attr == "geometry" and value:
                try:
                    attributes["latitude"] = value.y
                    attributes["longitude"] = value.x
                except AttributeError:
                    continue  # Skip if `geometry` does not have x or y attributes

            elif (
                not callable(value)
                and isinstance(value, str)
                and value not in [None, "", [], {}, ()]
            ):
                attributes[attr] = value

    return attributes


def extract_kml_data(gmap_URL, func):
    pattern = r"mid=(\w+-\w+)"
    match = re.search(pattern, gmap_URL)
    mid_value = ""

    if not match:
        print("No 'mid' value found in the URL.")
    else:
        mid_value += match.group(1)
        print(f"The extracted 'mid' value is: {mid_value}")

    kml_url = (
        "https://www.google.com/maps/d/u/0/kml?mid="
        + mid_value
        + "&resourcekey&forcekml=1"
    )
    g_map = func(kml_url)
    kml_file = kml.KML.from_string(g_map.content)

    return kml_file


def parse_description(desc):
    result = {}

    main_desc = re.split(r"Website:", desc, maxsplit=1)[0].strip()
    result["main_description"] = main_desc

    website = re.search(r"Website:\s*(https?://\S+)", desc)
    facebook = re.search(r"Facebook:\s*(https?://\S+)", desc)
    twitter = re.search(r"Twitter:\s*(https?://\S+)", desc)
    instagram = re.search(r"Instagram:\s*(https?://\S+)", desc)

    result["web_url"] = website.group(1) if website else None
    result["facebook"] = facebook.group(1) if facebook else None
    result["twitter"] = twitter.group(1) if twitter else None
    result["instagram"] = instagram.group(1) if instagram else None

    return result


def extract_urls(text):

    if isinstance(text, str):
        url_pattern = r"https?://\S+|ftp://\S+|file://\S+|www\.\S+"
        return re.findall(url_pattern, text)
    else:
        return None
