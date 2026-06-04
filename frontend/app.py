from fastapi import FastAPI, Query, HTTPException
import httpx
import os
import logging

# Configuración de logs en history.txt
LOG_DIR = os.getenv("LOG_DIR", "/app/data")
try:
    os.makedirs(LOG_DIR, exist_ok=True)
    LOG_FILE = os.path.join(LOG_DIR, "history.txt")
except Exception:
    LOG_FILE = "history.txt"

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    encoding="utf-8"
)

app = FastAPI()

# URL del backend (por defecto apunta al servicio 'backend' en el puerto 8080 en Docker Compose)
BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8080")

@app.get("/generate")
async def generate_content(prompt: str = Query(..., description="The prompt to send to the backend service")):
    logging.info(f"Enviando prompt al servicio B en la URL {BACKEND_URL}/generate")
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(f"{BACKEND_URL}/generate", params={"prompt": prompt})
            response.raise_for_status()
            
            logging.info("Respuesta exitosa recibida del servicio B.")
            return response.json()
    except httpx.HTTPStatusError as e:
        logging.error(f"Error HTTP al comunicarse con servicio B: {e.response.status_code} - {e.response.text}")
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except Exception as e:
        logging.error(f"Error de comunicación inesperado con servicio B: {repr(e)}")
        raise HTTPException(status_code=500, detail=repr(e))

@app.get("/logs")
async def get_logs():
    if not os.path.exists(LOG_FILE):
        return {"logs": []}
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()
        return {"logs": lines}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al leer los logs: {str(e)}")

