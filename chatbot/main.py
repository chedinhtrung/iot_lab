from openai import OpenAI
from secret import OPENAI_KEY
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

client = OpenAI(
    api_key=OPENAI_KEY
)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

class ChatRequest(BaseModel):
    messages: list[dict]

def chat(req:ChatRequest): 
    resp = client.responses.create(
        model="gpt-4.1-mini",
        input=req.messages
    )
    return resp.output_text or ""