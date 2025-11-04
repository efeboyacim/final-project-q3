import os, json, urllib.parse, urllib3

API_URL = os.environ["API_URL"]  # https://<domain>/internal/s3-callback
TOKEN   = os.environ["SHARED_SECRET"]
BUCKET  = os.environ["BUCKET"]

http = urllib3.PoolManager(retries=urllib3.util.retry.Retry(total=3, backoff_factor=0.5))

def _post(data: dict):
    body = json.dumps(data).encode()
    r = http.request(
        "POST", API_URL,
        body=body,
        headers={"Content-Type": "application/json", "x-internal-token": TOKEN},
        timeout=urllib3.Timeout(connect=3.0, read=10.0),
    )
    if r.status >= 300:
        raise RuntimeError(f"callback failed {r.status}: {r.data}")

def handler(event, _ctx):
    for rec in event["Records"]:
        event_name = rec["eventName"]
        b = rec["s3"]["bucket"]["name"]
        k = urllib.parse.unquote(rec["s3"]["object"]["key"])
        if b != BUCKET:
            continue
        if event_name.startswith("ObjectCreated:"):
            _post({"type": "created", "bucket": b, "key": k})
        elif event_name.startswith("ObjectRemoved:"):
            _post({"type": "removed", "bucket": b, "key": k})
    return {"ok": True}
