from fastapi import FastAPI, HTTPException
import json
from typing import Optional, List
from pydantic import BaseModel

app = FastAPI(title="Bots Dashboard API", version="1.0.0")

class ApplicationRequest(BaseModel):
    applicationName: str
    displayName: str
    type: str
    description: str
    version: str
    status: str
    owner: str
    maintainer: str
    tags: List[str]

class CICDPipeline(BaseModel):
    provider: str
    buildPipeline: str
    releasePipeline: str
    deploymentStrategy: str

class CodeQuality(BaseModel):
    sonarQube: str
    codeCoverage: str
    securityScan: str

class Monitoring(BaseModel):
    applicationInsights: str
    logAnalytics: str
    alerts: List[str]

class DevOpsRequest(BaseModel):
    applicationName: str
    repositoryUrl: str
    cicdPipeline: CICDPipeline
    codeQuality: CodeQuality
    monitoring: Monitoring

class InfrastructureRequest(BaseModel):
    applicationName: str
    environment: str
    cloud: str
    region: str
    resourceGroup: str
    components: dict

class CompleteOnboardingRequest(BaseModel):
    applicationName: str
    devops: DevOpsRequest
    infrastructure: List[InfrastructureRequest]

def load_json_file(filename: str):
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File {filename} not found")
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail=f"Invalid JSON in {filename}")

def find_app_by_id_or_name(data: list, identifier: str):
    for app in data:
        if app.get("id") == identifier or app.get("applicationName") == identifier:
            return app
    return None

def save_json_file(filename: str, data: dict):
    try:
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving {filename}: {str(e)}")

def generate_next_id(applications: list) -> str:
    if not applications:
        return "app-001"
    
    max_id = 0
    for app in applications:
        if app.get("id", "").startswith("app-"):
            try:
                num = int(app["id"].split("-")[1])
                max_id = max(max_id, num)
            except (ValueError, IndexError):
                continue
    
    return f"app-{max_id + 1:03d}"

@app.get("/")
def read_root():
    return {"message": "Bots Dashboard API", "version": "1.0.0"}

# List all applications
@app.get("/applications")
def list_applications():
    data = load_json_file("application_details.json")
    return data["applications"]

# Get application details by ID or name
@app.get("/applications/{identifier}")
def get_application_details(identifier: str):
    data = load_json_file("application_details.json")
    app = find_app_by_id_or_name(data["applications"], identifier)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    return app

# Onboard new application
@app.post("/applications")
def create_application(app_request: ApplicationRequest):
    data = load_json_file("application_details.json")
    
    # Check if application already exists
    existing_app = find_app_by_id_or_name(data["applications"], app_request.applicationName)
    if existing_app:
        raise HTTPException(status_code=409, detail=f"Application '{app_request.applicationName}' already exists")
    
    # Generate new ID
    new_id = generate_next_id(data["applications"])
    
    # Create new application
    new_app = {
        "id": new_id,
        "applicationName": app_request.applicationName,
        "displayName": app_request.displayName,
        "type": app_request.type,
        "description": app_request.description,
        "version": app_request.version,
        "status": app_request.status,
        "owner": app_request.owner,
        "maintainer": app_request.maintainer,
        "tags": app_request.tags
    }
    
    # Add to applications list
    data["applications"].append(new_app)
    
    # Save updated data
    save_json_file("application_details.json", data)
    
    return {
        "message": "Application created successfully",
        "application": new_app
    }

# Get DevOps details by ID or name
@app.get("/devops/{identifier}")
def get_devops_details(identifier: str):
    data = load_json_file("devops_details.json")
    app = find_app_by_id_or_name(data["applications"], identifier)
    if not app:
        raise HTTPException(status_code=404, detail="DevOps details not found")
    return app

# Onboard DevOps details
@app.post("/devops")
def create_devops_details(devops_request: DevOpsRequest):
    # Verify application exists
    app_data = load_json_file("application_details.json")
    app = find_app_by_id_or_name(app_data["applications"], devops_request.applicationName)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    
    # Load DevOps data
    devops_data = load_json_file("devops_details.json")
    
    # Check if DevOps details already exist
    existing_devops = find_app_by_id_or_name(devops_data["applications"], devops_request.applicationName)
    if existing_devops:
        raise HTTPException(status_code=409, detail=f"DevOps details for '{devops_request.applicationName}' already exist")
    
    # Create new DevOps entry
    new_devops = {
        "id": app["id"],
        "applicationName": devops_request.applicationName,
        "repositoryUrl": devops_request.repositoryUrl,
        "cicdPipeline": devops_request.cicdPipeline.dict(),
        "codeQuality": devops_request.codeQuality.dict(),
        "monitoring": devops_request.monitoring.dict()
    }
    
    # Add to DevOps list
    devops_data["applications"].append(new_devops)
    
    # Save updated data
    save_json_file("devops_details.json", devops_data)
    
    return {
        "message": "DevOps details created successfully",
        "devops": new_devops
    }

# Onboard Infrastructure details
@app.post("/infrastructure")
def create_infrastructure_details(infra_request: InfrastructureRequest):
    # Verify application exists
    app_data = load_json_file("application_details.json")
    app = find_app_by_id_or_name(app_data["applications"], infra_request.applicationName)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    
    # Load Infrastructure data
    infra_data = load_json_file("infrastructure_details.json")
    
    # Validate environment
    if infra_request.environment not in infra_data["environments"]:
        raise HTTPException(status_code=400, detail=f"Invalid environment '{infra_request.environment}'. Valid environments: {list(infra_data['environments'].keys())}")
    
    # Check if infrastructure already exists for this app in this environment
    existing_infra = find_app_by_id_or_name(infra_data["environments"][infra_request.environment], infra_request.applicationName)
    if existing_infra:
        raise HTTPException(status_code=409, detail=f"Infrastructure details for '{infra_request.applicationName}' in '{infra_request.environment}' already exist")
    
    # Create new Infrastructure entry
    new_infra = {
        "id": app["id"],
        "applicationName": infra_request.applicationName,
        "cloud": infra_request.cloud,
        "region": infra_request.region,
        "resourceGroup": infra_request.resourceGroup,
        "components": infra_request.components
    }
    
    # Add to Infrastructure list for the specified environment
    infra_data["environments"][infra_request.environment].append(new_infra)
    
    # Save updated data
    save_json_file("infrastructure_details.json", infra_data)
    
    return {
        "message": f"Infrastructure details created successfully for {infra_request.environment} environment",
        "infrastructure": new_infra
    }

# Onboard DevOps and Infrastructure details for an application
@app.post("/onboard/{application_name}")
def onboard_application_details(application_name: str, devops_request: DevOpsRequest, infrastructure_requests: List[InfrastructureRequest]):
    # Verify application exists
    app_data = load_json_file("application_details.json")
    app = find_app_by_id_or_name(app_data["applications"], application_name)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    
    results = {"devops": None, "infrastructure": []}
    
    # Onboard DevOps details
    try:
        devops_data = load_json_file("devops_details.json")
        existing_devops = find_app_by_id_or_name(devops_data["applications"], application_name)
        
        if existing_devops:
            results["devops"] = {"status": "exists", "message": "DevOps details already exist"}
        else:
            new_devops = {
                "id": app["id"],
                "applicationName": application_name,
                "repositoryUrl": devops_request.repositoryUrl,
                "cicdPipeline": devops_request.cicdPipeline.dict(),
                "codeQuality": devops_request.codeQuality.dict(),
                "monitoring": devops_request.monitoring.dict()
            }
            devops_data["applications"].append(new_devops)
            save_json_file("devops_details.json", devops_data)
            results["devops"] = {"status": "created", "data": new_devops}
    except Exception as e:
        results["devops"] = {"status": "error", "message": str(e)}
    
    # Onboard Infrastructure details for each environment
    infra_data = load_json_file("infrastructure_details.json")
    
    for infra_request in infrastructure_requests:
        try:
            if infra_request.environment not in infra_data["environments"]:
                results["infrastructure"].append({
                    "environment": infra_request.environment,
                    "status": "error",
                    "message": f"Invalid environment '{infra_request.environment}'"
                })
                continue
            
            existing_infra = find_app_by_id_or_name(infra_data["environments"][infra_request.environment], application_name)
            
            if existing_infra:
                results["infrastructure"].append({
                    "environment": infra_request.environment,
                    "status": "exists",
                    "message": "Infrastructure details already exist"
                })
            else:
                new_infra = {
                    "id": app["id"],
                    "applicationName": application_name,
                    "cloud": infra_request.cloud,
                    "region": infra_request.region,
                    "resourceGroup": infra_request.resourceGroup,
                    "components": infra_request.components
                }
                infra_data["environments"][infra_request.environment].append(new_infra)
                results["infrastructure"].append({
                    "environment": infra_request.environment,
                    "status": "created",
                    "data": new_infra
                })
        except Exception as e:
            results["infrastructure"].append({
                "environment": infra_request.environment,
                "status": "error",
                "message": str(e)
            })
    
    # Save infrastructure changes
    try:
        save_json_file("infrastructure_details.json", infra_data)
    except Exception as e:
        return {"message": "Partial success - DevOps saved but infrastructure save failed", "error": str(e), "results": results}
    
    return {
        "message": "Application onboarding completed",
        "applicationName": application_name,
        "results": results
    }

# List all DevOps configurations
# @app.get("/devops")
# def list_devops():
#     data = load_json_file("devops_details.json")
#     return data["applications"]

# Get infrastructure details by app name/ID across all environments
@app.get("/infrastructure/app/{identifier}")
def get_app_infrastructure_all_environments(identifier: str):
    data = load_json_file("infrastructure_details.json")
    result = {}
    
    for env_name, env_apps in data["environments"].items():
        app = find_app_by_id_or_name(env_apps, identifier)
        if app:
            result[env_name] = app
    
    if not result:
        raise HTTPException(status_code=404, detail=f"Infrastructure details not found for '{identifier}'")
    
    return {
        "applicationName": identifier,
        "environments": result
    }

# Get infrastructure details by ID or name and environment
# @app.get("/infrastructure/{environment}/{identifier}")
# def get_infrastructure_details(environment: str, identifier: str):
#     data = load_json_file("infrastructure_details.json")
#     if environment not in data["environments"]:
#         raise HTTPException(status_code=404, detail=f"Environment '{environment}' not found")
    
#     app = find_app_by_id_or_name(data["environments"][environment], identifier)
#     if not app:
#         raise HTTPException(status_code=404, detail=f"Infrastructure details not found for '{identifier}' in '{environment}'")
#     return app

# List infrastructure for specific environment
# @app.get("/infrastructure/{environment}")
# def list_infrastructure_by_environment(environment: str):
#     data = load_json_file("infrastructure_details.json")
#     if environment not in data["environments"]:
#         raise HTTPException(status_code=404, detail=f"Environment '{environment}' not found")
#     return data["environments"][environment]

# List all environments
# @app.get("/infrastructure")
# def list_all_infrastructure():
#     data = load_json_file("infrastructure_details.json")
#     return data["environments"]

# Get complete application profile (all details combined)
@app.get("/profile/{identifier}")
def get_complete_profile(identifier: str, environment: Optional[str] = "production"):
    # Get application details
    app_data = load_json_file("application_details.json")
    app_details = find_app_by_id_or_name(app_data["applications"], identifier)
    if not app_details:
        raise HTTPException(status_code=404, detail="Application not found")
    
    # Get DevOps details
    devops_data = load_json_file("devops_details.json")
    devops_details = find_app_by_id_or_name(devops_data["applications"], identifier)
    
    # Get infrastructure details
    infra_data = load_json_file("infrastructure_details.json")
    infra_details = None
    if environment in infra_data["environments"]:
        infra_details = find_app_by_id_or_name(infra_data["environments"][environment], identifier)
    
    return {
        "application": app_details,
        "devops": devops_details,
        "infrastructure": infra_details,
        "environment": environment
    }

