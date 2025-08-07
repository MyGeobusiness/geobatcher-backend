from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
import pandas as pd
import aiohttp
import os
import uuid

app = FastAPI()

LOCATIONIQ_API_KEY = "pk.6153b90124c847b29ae6af3f451117df"  # Replace with your actual key


async def geocode_address(session, address):
    url = f"https://us1.locationiq.com/v1/search.php?key={LOCATIONIQ_API_KEY}&q={address}&format=json"
    try:
        async with session.get(url) as response:
            data = await response.json()
            if isinstance(data, list) and len(data) > 0:
                return data[0]["lat"], data[0]["lon"]
            else:
                return None, None
    except Exception:
        return None, None


@app.post("/geocode-csv/")
async def geocode_csv(file: UploadFile = File(...)):
    filename = file.filename.lower()
    contents = await file.read()
    temp_filename = f"temp_{uuid.uuid4()}"
    
    with open(temp_filename, "wb") as f:
        f.write(contents)

    try:
        if filename.endswith(".csv"):
            df = pd.read_csv(temp_filename)
        elif filename.endswith((".xlsx", ".xls")):
            df = pd.read_excel(temp_filename)
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format. Upload a CSV or Excel file.")
    except Exception:
        raise HTTPException(status_code=400, detail="Failed to read the uploaded file. Make sure it has a column named 'Street Address'.")

    if "Street Address" not in df.columns:
        raise HTTPException(status_code=400, detail="Missing 'Street Address' column.")

    addresses = df["Street Address"].tolist()
    latitudes = []
    longitudes = []

    async with aiohttp.ClientSession() as session:
        for address in addresses:
            lat, lon = await geocode_address(session, address)
            latitudes.append(lat)
            longitudes.append(lon)

    df["Latitude"] = latitudes
    df["Longitude"] = longitudes

    output_filename = f"geocoded_{uuid.uuid4()}.csv"
    df.to_csv(output_filename, index=False)

    os.remove(temp_filename)
    return FileResponse(output_filename, media_type="text/csv", filename=output_filename)




