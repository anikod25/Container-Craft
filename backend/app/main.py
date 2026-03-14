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
from models import ValidationResponse

#endpoint for validating the compose configuration sent by the frontend, it will return a response with valid flag and list of errors if any.


@app.post("/api/validate", response_model=ValidationResponse)
async def validate(request: Request):
    data = await request.json()
    compose_config = ComposeConfig(**data)
    result = validate_compose_config(compose_config.services)
    return result


# get endpoint api/stacks to get the list from stack templates in compose_templates.py
@app.get("/api/stacks")
async def get_stacks():
    return TEMPLATES["stacks"]



# endpoints for saving and loading compose file 

from models import ProjectSave, ValidationResponse as ProjectValidationResponse
from core.validator import validate_compose_config

@app.post("/api/projects/export")
async def export_project(project: ProjectSave):
    """
    Export a project to the .containercraft JSON save format.
    Accepts a ProjectSave body and returns the same structure as JSON,
    ready to be written to a .containercraft file by the frontend.
    """
    return project.model_dump()
 
 
@app.post("/api/projects/import")
async def import_project(request: Request):
    """
    Import a project from a .containercraft JSON file.
    Parses and validates the payload against the ProjectSave schema.
    Returns the fully parsed project object so the frontend can restore canvas state.
    """
    try:
        data = await request.json()
        project = ProjectSave(**data)
        return project.model_dump()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid project file: {str(e)}")
 
 
@app.post("/api/projects/validate", response_model=ProjectValidationResponse)
async def validate_import(request: Request):
    """
    Validate the services inside an imported project file without fully loading it.
    Runs the same checks as /api/validate (port conflicts, image names, etc.)
    so the frontend can surface errors before committing the import to canvas state.
    """
    try:
        data = await request.json()
        project = ProjectSave(**data)
        result = validate_compose_config(project.services)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not parse project for validation: {str(e)}")
 