
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import StreamingResponse
import pandas as pd
import aiohttp
import asyncio
import io

app = FastAPI()

# Replace with your real LocationIQ API Key
LOCATIONIQ_API_KEY = "pk.6153b90124c847b29ae6af3f451117df"

async def fetch_coordinates(session, address):
    url = "https://us1.locationiq.com/v1/search.php"
    params = {
        "key": LOCATIONIQ_API_KEY,
        "q": address,
        "format": "json"
    }
    try:
        async with session.get(url, params=params) as response:
            data = await response.json()
            if isinstance(data, list) and len(data) > 0:
                return data[0]["lat"], data[0]["lon"]
    except Exception:
        pass
    return None, None

async def geocode_all(addresses):
    async with aiohttp.ClientSession() as session:
        results = []
        for i, address in enumerate(addresses):
            lat, lon = await fetch_coordinates(session, address)
            results.append((lat, lon))
            await asyncio.sleep(0.6)  # ~2 requests/second for free LocationIQ tier
        return results

@app.post("/geocode-csv/")
async def geocode_csv(file: UploadFile = File(...)):
    df = pd.read_excel(file.file)
    if "Street Address" not in df.columns:
        return {"error": "Missing 'Street Address' column in file."}

    addresses = df["Street Address"].tolist()
    results = await geocode_all(addresses)

    df["Latitude"] = [lat for lat, _ in results]
    df["Longitude"] = [lon for _, lon in results]

    output = io.StringIO()
    df.to_csv(output, index=False)
    output.seek(0)

    return StreamingResponse(output, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=geocoded.csv"})
