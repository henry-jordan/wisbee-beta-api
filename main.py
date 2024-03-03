from fastapi import FastAPI
from mangum import Mangum
import uvicorn

# 1. pip install -t dependencies -r requirements.txt
# 2. (cd dependencies; zip ../aws_lambda_artifact.zip -r .)
# 3. zip aws_lambda_artifact.zip -u main.py

app = FastAPI()
handler = Mangum(app)

@app.get('/')
async def root():
    return {"message": "Hello World 🤩"}

@app.get('/status')
async def status():
    return {"message": "👍"}