from argparse import ArgumentParser
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any, Tuple
import os
import json
import datetime

import requests
import bs4
import time

import googlemaps
import pandas as pd

from fake_useragent import UserAgent


@dataclass
class Listing:
    url: str
    bedrooms: int
    bathrooms: int
    sqft: int
    rent: int
    ppsf: float
    address: str
    walkscore: float


HEADERS = {
    "Referer": "https://www.google.com",
    'User-Agent': UserAgent().random
}


GMAPS = None


def _load_gmaps_key() -> str:
    if os.path.exists("GMAPS_API_KEY"):
        with open("GMAPS_API_KEY", "r") as f:
            return f.read().strip()
    if "GMAPS_API_KEY" in os.environ:
        return os.environ["GMAPS_API_KEY"]
    raise ValueError("No GMAPS_API_KEY found in environment or file")


def _setup_gmaps():
    global GMAPS
    GMAPS = googlemaps.Client(key=_load_gmaps_key())


def _fetch_html(url: str, cache_file: Optional[str] = None) -> str:
    response = requests.get(url, headers=HEADERS)
    if cache_file is not None:
        with open(cache_file, "w", encoding="utf-8") as f:
            f.write(response.text)
    return response.text


def get_listing(url: str, cache_file: Optional[str] = None) -> Tuple[Listing, bool]:
    if GMAPS is None:
        _setup_gmaps()

    used_cache = False
    if cache_file is not None and os.path.exists(cache_file):
        with open(cache_file, "r", encoding="utf-8") as fin:
            html_text = fin.read()
            used_cache = True
    else:
        html_text = _fetch_html(url, cache_file)

    soup = bs4.BeautifulSoup(html_text, "html.parser")
    script = soup.find("script", id="__NEXT_DATA__")
    property_info = list(
        json.loads(
            json.loads(script.text)["props"]["pageProps"]["componentProps"][
                "gdpClientCache"
            ]
        ).values()
    )[0]["property"]

    address = (
        property_info["streetAddress"]
        + ", "
        + property_info["city"]
        + ", "
        + property_info["state"]
    )
    rent = property_info["price"]
    bedrooms = property_info["bedrooms"]
    bathrooms = property_info["bathrooms"]
    sqft = float(property_info["livingAreaValue"])
    walkscore = get_walkscore(address)

    return (
        Listing(
            url=url,
            bedrooms=bedrooms,
            bathrooms=bathrooms,
            sqft=sqft,
            rent=rent,
            ppsf=rent / sqft,
            address=address,
            walkscore=walkscore,
        ),
        used_cache,
    )


def _get_time(hr: int):
    # always to tomorrow, since otherwise departure time may be in past
    tomorrow = datetime.datetime.now().date() + datetime.timedelta(1)
    hr_obj = datetime.time(hr, 0)
    return datetime.datetime.combine(tomorrow, hr_obj)


def get_commute_time(
    from_address: str, to_address: str, when: datetime.datetime, how: str
) -> float:
    directions_result = GMAPS.directions(
        from_address, to_address, mode=how, departure_time=when
    )
    # use minutes
    return directions_result[0]["legs"][0]["duration"]["value"] / 60.0


def get_commute_times(
    listing: Listing,
    addresses: List[str],
    when: datetime.datetime,
    how: str = "driving",
) -> List[float]:
    to_address = listing.address
    ts = []
    for from_address in addresses:
        t = get_commute_time(from_address, to_address, when=when, how=how)
        ts.append(t)
    return ts


def get_walkscore(address: str) -> Optional[float]:
    address_str = "-".join([e.lower().replace(",", "") for e in address.split() if len(e.strip()) > 0])
    html = _fetch_html(f"https://www.walkscore.com/score/{address_str}")
    soup = bs4.BeautifulSoup(html, "html.parser")
    walk_scores = [i for i in soup.find_all("img", alt=True) if "Walk Score" in i['alt']]
    if len(walk_scores) < 2:
        return None
    walk_score_values = [t for t in walk_scores[1]['alt'].split(" ") if t.isdigit()]
    if len(walk_score_values) == 0:
        return None
    return float(walk_score_values[0])


def _get_cache_file_path(url: str, cache_folder: str) -> str:
    name = next(p for p in reversed(url.split("/")) if len(p.strip()) > 0)
    return os.path.join(cache_folder, name + ".html")


def get_output_df_record(
    url: str, cache_folder: str = None, addresses: Optional[List[str]] = None
) -> Tuple[Dict[str, Any], bool]:
    if cache_folder is not None:
        html_path = _get_cache_file_path(url, cache_folder)
    else:
        html_path = None

    used_cache = False
    try:
        listing, used_cache = get_listing(url, cache_file=html_path)
    except Exception as err:
        print(f"Failed when collecting {url}, you'll need to manually fill this...")
        print(err)
        return {"url": url}, used_cache

    record = asdict(listing)

    # add commuting information
    if addresses is not None and len(addresses) > 0:
        commute_times = {"morning": 8, "evening": 18}
        for timelabel, timevalue in commute_times.items():
            try:
                times = get_commute_times(
                    listing, addresses, when=_get_time(timevalue), how="driving"
                )
            except Exception as err:
                print(f"Failed to get commute times for {url}, default to None")
                times = [None] * len(addresses)
            for address, time in zip(addresses, times):
                record[address + "_" + timelabel] = time

    return record, used_cache


def get_args():
    parser = ArgumentParser(description="Rent management tool")
    parser.add_argument("--input", type=str, help="Input with URL listings")
    parser.add_argument("--cache", type=str, help="Cache the HTML files here")
    parser.add_argument("--output", type=str, help="Dump results here")
    parser.add_argument(
        "--sleep",
        type=int,
        help="Seconds to sleep between requests (avoid blocking)",
        default=10,
    )
    parser.add_argument(
        "--commute_addresses", type=str, nargs="+", help="Addresses to commute from"
    )
    return parser.parse_args()


def main():
    args = get_args()
    if args.cache is not None and not os.path.exists(args.cache):
        print(f"Creating caching directory {args.cache}")
        os.makedirs(args.cache)

    input_df = pd.read_csv(args.input)
    output_records = []
    for url in input_df["url"]:
        print(f"Processing {url}")
        record, used_cache = get_output_df_record(
            url, cache_folder=args.cache, addresses=args.commute_addresses
        )
        output_records.append(record)
        if not used_cache:
            time.sleep(args.sleep)

    output_df = pd.DataFrame(output_records)
    output_df.to_csv(args.output, index=False)


if __name__ == "__main__":
    try:
        main()
    except Exception as err:
        import pdb

        pdb.post_mortem()
