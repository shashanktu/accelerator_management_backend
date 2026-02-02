from fastapi import FastAPI, HTTPException
import json
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List
from pydantic import BaseModel
import requests
from datetime import datetime, timedelta
import psycopg2
import json

from sql import get_all_applications,insert_application,get_application_by_id,get_devops_by_id,insert_devops_details,get_infrastructure_by_id,get_infra_components_by_env_and_component



app = FastAPI(title="Bots Dashboard API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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


def get_credentials(subscription_id):
    with open("secrets.json") as f:
        credentials = json.load(f)
    
    # Search for matching subscription ID
    for cred in credentials:
        if cred["subscriptionid"] == subscription_id:
            # print(f"Found credentials for subscription: {subscription_id}")
            return cred["values"]
    
    print(f"No credentials found for subscription: {subscription_id}")
    return None
    

def get_access_token(values):
    # print(values.get("tenant_id"),"\n",values.get("client_id"),"\n",values.get("client_secret"))
    url = f"https://login.microsoftonline.com/{values.get('tenant_id')}/oauth2/v2.0/token"
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    payload = {
        "client_id": values.get("client_id"),
        "client_secret": values.get("client_secret"),
        "grant_type": "client_credentials",
        "scope":"https://management.azure.com/.default"
    }
    response = requests.post(url, headers=headers, data=payload)
    if response.status_code == 200:
        # print("==========================")
        # print(response.json())
        return response.json().get("access_token")
    else:
        print(f"Failed to get access token: {response.status_code}")
        print(response.text)
        return None
    

def start_app_service(access_token, subscription_id, resource_group, app_name):
    url = f"https://management.azure.com/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/Microsoft.Web/sites/{app_name}/start?api-version=2025-03-01"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    response = requests.post(url, headers=headers)
    return {"status_code": response.status_code, "response": response.text}

def stop_app_service(access_token, subscription_id, resource_group, app_name):
    url = f"https://management.azure.com/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/Microsoft.Web/sites/{app_name}/stop?api-version=2025-03-01"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    response = requests.post(url, headers=headers)
    return {"status_code": response.status_code, "response": response.text}

def dynamic_action(access_token,result):
    print("\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\")
    if result:
        try:
            components = json.loads(result) if isinstance(result, str) else result
            print(components.keys())
        except (json.JSONDecodeError, TypeError):
            print("Failed to parse components JSON")
    else:
        print("No components found")

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.get("/app")
def list_application_details():
    details = get_all_applications()
    if details:
        return details
    else:
        raise HTTPException(status_code=404, detail="Application not found")


@app.post("/applications")
def create_application(app_request: ApplicationRequest):
    result = insert_application(app_request.dict())
    return result
@app.get("/applications/{identifier}")
def get_application_details(identifier: str):
    details = get_application_by_id(identifier)
    if details:
        return details
    else:
        raise HTTPException(status_code=404, detail="Application not found")
    
@app.get("/devops/{identifier}")
def get_devops_details(identifier: str):
    details = get_devops_by_id(identifier)
    if details:
        return details
    else:
        raise HTTPException(status_code=404, detail="DevOps details not found")


@app.post("/devops")
def create_devops_details(devops_request: DevOpsRequest):
    result = insert_devops_details(devops_request.dict())
    return result

@app.get("/infrastructure/{identifier}")
def get_infrastructure_details(identifier: str):
    details = get_infrastructure_by_id(identifier)
    if details:
        return details
    else:
        raise HTTPException(status_code=404, detail="Infrastructure details not found")


def get_app_service_details(identifier: str, environment: str):
    """Extract app service details from infrastructure data"""
    infra_details = get_infrastructure_by_id(identifier)
    if not infra_details:
        raise HTTPException(status_code=404, detail="Infrastructure details not found")
    
    env_data = infra_details["environments"].get(environment)
    if not env_data:
        raise HTTPException(status_code=404, detail=f"Environment {environment} not found")
    
    subscription_id = env_data["subscriptionId"]
    resource_group = env_data["resourceGroup"]
    app_name = env_data["components"].get("appService", {}).get("name", "")
    
    if not app_name:
        raise HTTPException(status_code=400, detail="App service name not found in components")
    
    return subscription_id, resource_group, app_name

@app.post("/services/{identifier}/{environment}/{action}")
def perform_action(identifier: str, environment: str, action: str):
    if action not in ["start", "stop"]:
        raise HTTPException(status_code=400, detail="Invalid action")
    
    # Get app service details
    subscription_id, resource_group, app_name = get_app_service_details(identifier, environment)
    
    # Get credentials and access token
    values = get_credentials(subscription_id)
    access_token = get_access_token(values)
    
    # Call appropriate Azure API
    if action == "start":
        api_result = start_app_service(access_token, subscription_id, resource_group, app_name)
        message = f"Starting application {identifier} in {environment}"
    else:
        api_result = stop_app_service(access_token, subscription_id, resource_group, app_name)
        message = f"Stopping application {identifier} in {environment}"
    
    return {"message": message, "api_result": api_result}