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

@app.get("/generate")
async def generate_content(prompt: str = Query(..., description="The prompt to send to Gemini")):
    if client is None:
        raise HTTPException(status_code=500, detail="Gemini Client is not initialized. Check GEMINI_API_KEY.")
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        return {"prompt": prompt, "text": response.text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
