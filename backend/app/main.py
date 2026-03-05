from fastapi import FastAPI, Header, HTTPException, Request, Response
from pydantic import list
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# we are yet to add the origin urls, on hold as of now.
origins = []

app.add_middleware(
    CORSMiddleware,
    allow_origins = origins,
    allow_credentials = True,
    allow_methods = ["*"],
    allow_headers = ["*"]
)

@app.get("/api/health")
async def health_check():
    return {"status" : "Healthy"}


# creating an endpoint for templates from its repsctive folder.
from templates.compose_templates import TEMPLATES

@app.get("/api/templates")
async def get_templates():
    return TEMPLATES

from core.yaml_generator import YAMLGenerator
from models import ComposeConfig

@app.post("/api/generate_yaml")
async def generate_yaml(request: Request):
    try:
        data = await request.json()
        compose_config = ComposeConfig(**data)
        yaml_generator = YAMLGenerator()
        yaml_output = yaml_generator.generate_yaml(compose_config)
        return Response(content=yaml_output, media_type="text/yaml")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
from core.validator import validate_compose_config

#endpoint for validating the compose configuration sent by the frontend, it will return a response with valid flag and list of errors if any.

@app.post("/api/validate")
async def validate(request: Request):
    data = await request.json()
    compose_config = ComposeConfig(**data)
    errors = validate_compose_config(compose_config.services)
    return {
        "valid": len(errors) == 0,
        "errors": errors
    }