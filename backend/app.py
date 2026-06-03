# app_fastapi_prompt.py
from dotenv import load_dotenv
from fastapi import FastAPI, Query, HTTPException
from google import genai
import os

# Load environment variables
load_dotenv()
try:
    client = genai.Client()
except Exception as e:
    client = None
    print(f"Warning: genai.Client initialization failed: {e}")

app = FastAPI()

# Definir la ruta del archivo de historial
HISTORY_DIR = os.getenv("HISTORY_DIR", "/app/data")
os.makedirs(HISTORY_DIR, exist_ok=True)
HISTORY_FILE = os.path.join(HISTORY_DIR, "history.txt")

@app.get("/generate")
async def generate_content(prompt: str = Query(..., description="The prompt to send to Gemini")):
    if client is None:
        raise HTTPException(status_code=500, detail="Gemini Client is not initialized. Check GEMINI_API_KEY.")
    try:
        # Guardar la consulta en texto plano en el historial
        with open(HISTORY_FILE, "a", encoding="utf-8") as f:
            f.write(f"{prompt}\n")

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        return {"prompt": prompt, "text": response.text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/history")
async def get_history():
    if not os.path.exists(HISTORY_FILE):
        return {"history": []}
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()
        return {"history": lines}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

