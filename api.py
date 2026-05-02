import json
import os
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from agent import run_pipeline


APP_API_KEY = os.getenv("APP_API_KEY")
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "")

allowed_origins = []
if FRONTEND_ORIGIN:
    allowed_origins.append(FRONTEND_ORIGIN)

allowed_origins.append("http://localhost:3000")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-App-Key"],
)


class PrepRequest(BaseModel):
    company_name: str = Field(min_length=1, max_length=120)
    role_name: str = Field(min_length=1, max_length=120)
    job_description: str = Field(min_length=1, max_length=20000)
    cv: str = Field(min_length=1, max_length=20000)
    extra: str = Field(default="", max_length=8000)


def require_app_key(x_app_key: str = Header(default="")):
    if not APP_API_KEY:
        raise HTTPException(status_code=500, detail="Server key is not configured")
    if x_app_key != APP_API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")


@app.get("/")
def home():
    return {"status": "running", "message": "Interview Intel API is live"}


@app.post("/prepare", dependencies=[Depends(require_app_key)])
def prepare(req: PrepRequest):
    output_file = run_pipeline(
        job_description=req.job_description,
        cv=req.cv,
        extra=req.extra,
        company_name=req.company_name,
        role_name=req.role_name,
    )

    output_path = Path(output_file)
    markdown_file = output_path.with_suffix(".md")
    product_json_file = Path(str(output_path).replace("interview_prep_", "product_brief_"))

    markdown = markdown_file.read_text() if markdown_file.exists() else ""
    product_json = None

    if product_json_file.exists():
        product_json = json.loads(product_json_file.read_text())

    return {
        "status": "done",
        "output_file": output_file,
        "markdown": markdown,
        "product_json": product_json,
    }
