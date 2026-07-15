import os
import json
import requests

RECORD_ID = "21382870"
OUTDIR = "../data/"

record = requests.get(
    f"https://zenodo.org/api/records/{RECORD_ID}"
).json()

print(json.dumps(record["files"], indent=2))

os.makedirs(OUTDIR, exist_ok=True)

for f in record["files"]:
    filename = f["key"]
    url = f["links"]["self"]

    print(f"Downloading {filename}")

    r = requests.get(url, stream=True)
    r.raise_for_status()

    with open(os.path.join(OUTDIR, filename), "wb") as out:
        for chunk in r.iter_content(1024 * 1024):
            out.write(chunk)

print("Done.")