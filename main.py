from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.responses import RedirectResponse
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
import pandas as pd
import aiohttp
import os
import uuid
import asyncio

app = FastAPI()

LOCATIONIQ_API_KEY = "pk.6153b90124c847b29ae6af3f451117df"  # Replace with your actual key

async def geocode_address(session, address):
    url = f"https://us1.locationiq.com/v1/search.php?key={LOCATIONIQ_API_KEY}&q={address}&format=json"
    try:
        async with session.get(url) as response:
            data = await response.json()
            if isinstance(data, list) and len(data) > 0:
                return data[0]["lat"], data[0]["lon"]
    except Exception:
        pass
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
            await asyncio.sleep(0.6)  # Stay within API rate limits

    df["Latitude"] = latitudes
    df["Longitude"] = longitudes

    output_filename = f"geocoded_{uuid.uuid4()}.csv"
    df.to_csv(output_filename, index=False)

    os.remove(temp_filename)
    return FileResponse(output_filename, media_type="text/csv", filename=output_filename)
@app.get("/")
async def root():
    return RedirectResponse(url="/docs")
@app.get("/")
async def root():
    return RedirectResponse(url="/upload")


from fastapi import FastAPI
from fastapi.responses import HTMLResponse, RedirectResponse

app = FastAPI()

@app.get("/upload", response_class=HTMLResponse)
async def upload_form():
    return """
    <html>
      <head>
        <title>GeoBatcher – Upload Addresses</title>
        <style>
          body {
            background-color: #eef2f7;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
          }
          .container {
            background-color: #ffffff;
            padding: 40px 50px;
            border-radius: 12px;
            box-shadow: 0 6px 12px rgba(0,0,0,0.1);
            text-align: center;
            width: 320px;
          }
          .logo {
            width: 120px;
            margin-bottom: 20px;
          }
          h2 {
            margin-bottom: 25px;
            color: #333333;
            font-size: 24px;
          }
          input[type="file"] {
            margin-bottom: 20px;
          }
          button {
            background-color: #1a73e8;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 16px;
          }
          button:hover {
            background-color: #1558b0;
          }
          footer {
            margin-top: 20px;
            font-size: 12px;
            color: #777;
          }
        </style>
      </head>
      <body>
        <div class="container">
          <img class="logo" src="https://cdn-icons-png.flaticon.com/512/684/684908.png" alt="GeoBatcher Logo">
          <h2>Upload Your Address File</h2>
          <form action="/geocode-csv/" enctype="multipart/form-data" method="post">
            <input type="file" name="file" accept=".csv,.xlsx" required><br>
            <button type="submit">Upload & Geocode</button>
          </form>
          <footer>© 2025 GeoBatcher • Simple. Fast. Reliable.</footer>
        </div>
      </body>
    </html>
    """

@app.get("/")
async def root():
    return RedirectResponse(url="/upload")
