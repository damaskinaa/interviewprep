from fastapi import FastAPI
from pydantic import BaseModel
from agent import run_pipeline
from pathlib import Path
import json

app = FastAPI()

class PrepRequest(BaseModel):
    company_name: str
    role_name: str
    job_description: str
    cv: str
    extra: str = ""

@app.get("/")
def home():
    return {"status": "running", "message": "Interview Intel API is live"}

@app.post("/prepare")
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
        "product_json": product_json
    }