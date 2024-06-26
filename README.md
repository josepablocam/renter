# Rent info collection

I got sick of copy/pasting things from zillow into a spreadsheet and then google maps searching
for commute times.

With this, you can just prepare a csv with URLs from Zillow and then
get a new CSV with info (rooms, rent, etc) and commute times.

Why this and not the Zillow renter hub? The renter hub only allows up to 5 listing comparison.
And it also doesn't seem to support exporting to CSV.


## Setup

First install package requirements (assuming you already
have Python installed.)
```
source build.sh
```

Get a google maps API key (see https://developers.google.com/maps/documentation/directions/overview) and then you
can save it down in a file called "GMAPS_API_KEY". You should enable:

* Distance Matrix API
* Directions API


## Usage

```
python ./renter.py \
    --input <starting-csv> \
    --cache <folder-to-save-html> \
    --output <resulting-csv> --commute_addresses "<address1>" "<address2>" ...
```

See `fetch.ps1` for a full example
and `fetch-example.ps1 (.sh)` for an example you can actually execute.


## Possible issues
* Zillow changes their HTML: this is the most likely long term issue.
If this happens, you should (1) navigate to a link you want to extract info from, download the HTML, and then inspect and figure out the right
path to the data you want. Then you can update `get_listing` accordingly.
