from dotenv import load_dotenv
from fastapi import FastAPI

from app.core.db import Base, engine

load_dotenv()  # .env dosyasındaki AWS bilgilerini yükler
import os

import boto3

s3 = boto3.client(
    "s3",
    region_name=os.getenv("AWS_REGION"),
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
)
BUCKET = os.getenv("S3_BUCKET")

app = FastAPI(title="Final Project API")
Base.metadata.create_all(bind=engine)

from fastapi import FastAPI

from app.api import auth, projects

app = FastAPI()

app.include_router(auth.router)
app.include_router(projects.router)

@app.get("/health")
def health(): return {"status": "ok"}
