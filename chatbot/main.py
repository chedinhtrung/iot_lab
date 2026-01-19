from openai import OpenAI
from secret import OPENAI_KEY
from fastapi import FastAPI

client = OpenAI(
    api_key=OPENAI_KEY
)

response = client.responses.create(
    model="gpt-5 nano",
    input=""
)

print(response.output_text)