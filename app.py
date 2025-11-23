# app_fastapi_prompt.py
from http.client import HTTPException
from dotenv import load_dotenv
from fastapi import FastAPI, Query
from google import genai
import os

# Load environment variables
load_dotenv()
client = genai.Client()

app = FastAPI()

# File to store responses

def append_to_txt(data):
    """Append a new entry to a text file."""
    output_file = os.getenv("OUTPUT_FILE", "responses.txt")
    with open(output_file, "a", encoding="utf-8") as f:
        f.write(data + "\n")

@app.get("/generate")
async def generate_content(prompt: str = Query(..., description="The prompt to send to Gemini")):
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )
    append_to_txt(response.text)
    return {"prompt": prompt, "text": response.text}

@app.get("/history")
async def read_history():
    """Read the log file and return its contents."""
    output_file = os.getenv("OUTPUT_FILE", "responses.txt")
    if not os.path.exists(output_file):
        raise HTTPException(status_code=404, detail="No history found.")
    try:
        with open(output_file, "r", encoding="utf-8") as f:
            content = f.read()
        return {"history": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading history: {str(e)}")