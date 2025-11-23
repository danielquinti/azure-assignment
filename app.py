# app_fastapi_prompt.py
from dotenv import load_dotenv
from fastapi import FastAPI, Query
from google import genai

# Load environment variables
load_dotenv()
client = genai.Client()

app = FastAPI()

@app.get("/generate")
async def generate_content(prompt: str = Query(..., description="The prompt to send to Gemini")):
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )
    return {"prompt": prompt, "text": response.text}
