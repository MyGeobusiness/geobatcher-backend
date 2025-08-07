from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
import pandas as pd
import aiohttp
import uuid
import os
import asyncio

# Load environment variables
load_dotenv()
LOCATIONIQ_API_KEY = os.getenv("LOCATIONIQ_API_KEY")

app = FastAPI()

# Serve static files (e.g., sample templates)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", response_class=RedirectResponse)
async def redirect_to_upload():
    return RedirectResponse(url="/upload")


@app.get("/upload", response_class=HTMLResponse)
async def upload_form():
    return """
    <html>
        <head>
            <title>Geobatcher Upload</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    background-color: #f4f7f9;
                    padding: 40px;
                    color: #333;
                }
                .container {
                    max-width: 600px;
                    margin: auto;
                    background: white;
                    padding: 30px;
                    border-radius: 8px;
                    box-shadow: 0 0 10px rgba(0,0,0,0.1);
                }
                h2 {
                    color: #2c3e50;
                }
                input[type=file] {
                    display: block;
                    margin-bottom: 15px;
                }
                .btn {
                    background-color: #3498db;
                    color: white;
                    padding: 10px 20px;
                    border: none;
                    cursor: pointer;
                    border-radius: 5px;
                }
                .btn:hover {
                    background-color: #2980b9;
                }
                .note, .footer {
                    font-size: 14px;
                    margin-top: 10px;
                    color: #888;
                }
                .template-links {
                    margin-top: 20px;
                }
                footer {
                    margin-top: 40px;
                    text-align: center;
                    font-size: 13px;
                    color: #aaa;
                }
            </style>
            <script>
                async function handleFormSubmit(event) {
                    event.preventDefault();
                    const form = event.target;
                    const fileInput = form.querySelector('input[name="file"]');
                    const msg = document.getElementById("msg");

                    if (!fileInput.files.length) {
                        msg.innerHTML = "❌ Please select a file.";
                        return;
                    }

                    const formData = new FormData(form);
                    msg.innerHTML = "⏳ Uploading and processing...";

                    const response = await fetch("/geocode-csv/", {
                        method: "POST",
                        body: formData
                    });

                    if (response.ok) {
                        const blob = await response.blob();
                        const url = window.URL.createObjectURL(blob);
                        const a = document.createElement("a");
                        a.href = url;
                        a.download = "geocoded.csv";
                        document.body.appendChild(a);
                        a.click();
                        a.remove();
                        msg.innerHTML = "✅ Success! Your geocoded file has been downloaded.";
                    } else {
                        const error = await response.json();
                        msg.innerHTML = `❌ Error: ${error.detail}`;
                    }
                }
            </script>
        </head>
        <body>
            <div class="container">
                <h2>Upload Your Address File</h2>
                <p class="note">Your file must include a column named <strong>"Street Address"</strong>.</p>

                <form onsubmit="handleFormSubmit(event)">
                    <input type="file" name="file" accept=".csv,.xlsx" required>
                    <button type="submit" class="btn">Upload and Geocode</button>
                </form>

                <div class="template-links">
                    <p><strong>Download Sample Templates:</strong></p>
                    <ul>
                        <li><a href="/static/sample_address_template.csv" download>Sample CSV Template</a></li>
                        <li><a href="/static/sample_address_template.xlsx" download>Sample Excel Template</a></li>
                    </ul>
                </div>

                <p id="msg" class="note"></p>

                <footer>
                    &copy; 2025 Geobatcher. All rights reserved.
                </footer>
            </div>
        </body>
    </html>
    """


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
            await asyncio.sleep(0.6)  # Stay within rate limit

    df["Latitude"] = latitudes
    df["Longitude"] = longitudes

    output_filename = f"geocoded_{uuid.uuid4()}.csv"
    df.to_csv(output_filename, index=False)

    os.remove(temp_filename)
    return FileResponse(output_filename, media_type="text/csv", filename=output_filename)






