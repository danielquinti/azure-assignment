from fastapi import FastAPI, Query, HTTPException
import httpx
import os

app = FastAPI()

# URL del backend (por defecto apunta al servicio 'backend' en el puerto 8080 en Docker Compose)
BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8080")

@app.get("/generate")
async def generate_content(prompt: str = Query(..., description="The prompt to send to the backend service")):
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(f"{BACKEND_URL}/generate", params={"prompt": prompt})
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=repr(e))

@app.get("/history")
async def get_history():
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(f"{BACKEND_URL}/history")
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=repr(e))

