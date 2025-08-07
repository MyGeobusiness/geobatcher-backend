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


from fastapi.responses import HTMLResponse, RedirectResponse

@app.get("/", response_class=HTMLResponse)
async def root():
    return RedirectResponse(url="/upload")

@app.get("/upload", response_class=HTMLResponse)
async def upload_form():
    return """
    <html>
        <head>
            <title>Geobatcher Upload</title>
            <style>
                body {
                    background-color: #f5f7fa;
                    font-family: Arial, sans-serif;
                    color: #333;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    padding-top: 50px;
                }
                .upload-container {
                    background-color: white;
                    padding: 40px;
                    border-radius: 12px;
                    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
                    max-width: 500px;
                    width: 90%;
                    text-align: center;
                }
                h2 {
                    margin-bottom: 20px;
                }
                input[type="file"] {
                    margin-bottom: 20px;
                }
                .note {
                    color: #cc0000;
                    font-size: 0.9em;
                    margin-top: 10px;
                }
                .logo {
                    width: 100px;
                    margin-bottom: 20px;
                }
            </style>
        </head>
        <body>
            <div class="upload-container">
                <img src="https://static.vecteezy.com/system/resources/previews/028/282/402/non_2x/geo-logo-design-inspiration-for-a-unique-identity-modern-elegance-and-creative-design-watermark-your-success-with-the-striking-this-logo-vector.jpg" class="logo" alt="Geo Logo">
                <h2>Upload Your Address File (.csv or .xlsx)</h2>
                <form action="/geocode-csv/" enctype="multipart/form-data" method="post">
                    <input type="file" name="file" accept=".csv,.xlsx" required><br>
                    <button type="submit">Upload and Geocode</button>
                </form>
                <p class="note">⚠️ Note: Your file must contain a column titled <strong>"Street Address"</strong>.</p>
            </div>
        </body>
    </html>
    """


