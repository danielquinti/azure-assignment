# app_fastapi_relay.py
from fastapi import FastAPI, Query, HTTPException
import httpx
import os

app = FastAPI()

# ServiceA URL, can be overridden with environment variable
SERVICE_A_URL = os.getenv("API_SERVICE_URL")

@app.get("/generate")
async def relay_generate(prompt: str = Query(..., description="The prompt to send to ServiceA")):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{SERVICE_A_URL}/generate", params={"prompt": prompt})
            response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/history")
async def relay_history():
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{SERVICE_A_URL}/history")
            response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
