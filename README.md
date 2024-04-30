# Rent info collection

I got sick of copy/pasting things from zillow into a spreadsheet and then google maps searching
for commute times.

With this, you can just prepare a csv with URLs from Zillow and then
get a new CSV with info (rooms, rent, etc) and commute times.


## Setup

First install package requirements (assuming you already
have Python installed.)
```
pip install -r requirements.txt
```

Get a google maps API key (see https://developers.google.com/maps/documentation/directions/overview) and then you
can save it down in a file called "GMAPS_API_KEY". You should enable:

* Distance Matrix API
* Directions API


## Usage

```
python ./renter.py --input <starting-csv> --cache <folder-to-save-html> --output <resulting-csv> --commute_addresses "<address1>" "<address2>" ...
```

See `fetch.ps1` for a full example.


## Possible issues
* Zillow changes their HTML: this is the most likely long term issue.
If this happens, you should (1) navigate to a link you want to extract info from, download the HTML, and then inspect and figure out the right
path to the data you want. Then you can update `get_listing` accordingly.

* Zillow rejects your requests: you may need to update the `HEADERS`
value. To do so, open chrome, open the developer tools, navigate
to the zillow link. In the requests, get the first request,
copy as `curl`. Then you can google for tools that
change `curl` to Python requests form. You should just take
the headers reported and update in `renter.py`.
