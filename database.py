import sqlite3
import json
from typing import Dict, Any

def create_database_tables():
    """Create all database tables based on JSON structures"""
    conn = sqlite3.connect('application_management.db')
    cursor = conn.cursor()
    
    # Applications table (from application_details.json)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS applications (
            id TEXT PRIMARY KEY,
            applicationName TEXT NOT NULL,
            displayName TEXT,
            type TEXT,
            description TEXT,
            version TEXT,
            status TEXT,
            owner TEXT,
            maintainer TEXT,
            applicationUrl TEXT,
            tags TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # DevOps table (from devops_details.json)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS devops_details (
            id TEXT PRIMARY KEY,
            applicationName TEXT NOT NULL,
            repositoryUrl TEXT,
            provider TEXT,
            buildPipeline TEXT,
            buildPipelineUrl TEXT,
            releasePipeline TEXT,
            releasePipelineUrl TEXT,
            deploymentStrategy TEXT,
            sonarQube TEXT,
            codeCoverage TEXT,
            securityScan TEXT,
            applicationInsights TEXT,
            logAnalytics TEXT,
            alerts TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (id) REFERENCES applications(id)
        )
    ''')
    
    # Infrastructure environments table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS infrastructure_details (
            id TEXT,
            applicationName TEXT NOT NULL,
            environment TEXT NOT NULL,
            cloud TEXT,
            subscriptionName TEXT,
            subscriptionId TEXT,
            region TEXT,
            resourceGroup TEXT,
            components TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (id, environment),
            FOREIGN KEY (id) REFERENCES applications(id)
        )
    ''')
    
    conn.commit()
    conn.close()

def insert_application_data(app_data: Dict[str, Any]):
    """Insert application data into database"""
    conn = sqlite3.connect('application_management.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT OR REPLACE INTO applications 
        (id, applicationName, displayName, type, description, version, status, owner, maintainer, applicationUrl, tags)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        app_data.get('id'),
        app_data.get('applicationName'),
        app_data.get('displayName'),
        app_data.get('type'),
        app_data.get('description'),
        app_data.get('version'),
        app_data.get('status'),
        app_data.get('owner'),
        app_data.get('maintainer'),
        app_data.get('applicationUrl'),
        json.dumps(app_data.get('tags', []))
    ))
    
    conn.commit()
    conn.close()

def insert_devops_data(devops_data: Dict[str, Any]):
    """Insert DevOps data into database"""
    conn = sqlite3.connect('application_management.db')
    cursor = conn.cursor()
    
    cicd = devops_data.get('cicdPipeline', {})
    quality = devops_data.get('codeQuality', {})
    monitoring = devops_data.get('monitoring', {})
    
    cursor.execute('''
        INSERT OR REPLACE INTO devops_details 
        (id, applicationName, repositoryUrl, provider, buildPipeline, buildPipelineUrl, 
         releasePipeline, releasePipelineUrl, deploymentStrategy, sonarQube, codeCoverage, 
         securityScan, applicationInsights, logAnalytics, alerts)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        devops_data.get('id'),
        devops_data.get('applicationName'),
        cicd.get('repositoryUrl'),
        cicd.get('provider'),
        cicd.get('buildPipeline'),
        cicd.get('buildPipelineUrl'),
        cicd.get('releasePipeline'),
        cicd.get('releasePipelineUrl'),
        cicd.get('deploymentStrategy'),
        quality.get('sonarQube'),
        quality.get('codeCoverage'),
        quality.get('securityScan'),
        monitoring.get('applicationInsights'),
        monitoring.get('logAnalytics'),
        json.dumps(monitoring.get('alerts', []))
    ))
    
    conn.commit()
    conn.close()

def insert_infrastructure_data(infra_data: Dict[str, Any], environment: str):
    """Insert infrastructure data into database"""
    conn = sqlite3.connect('application_management.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT OR REPLACE INTO infrastructure_details 
        (id, applicationName, environment, cloud, subscriptionName, subscriptionId, 
         region, resourceGroup, components)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        infra_data.get('id'),
        infra_data.get('applicationName'),
        environment,
        infra_data.get('cloud'),
        infra_data.get('subscriptionName'),
        infra_data.get('subscriptionId'),
        infra_data.get('region'),
        infra_data.get('resourceGroup'),
        json.dumps(infra_data.get('components', {}))
    ))
    
    conn.commit()
    conn.close()

def get_application_by_name(app_name: str):
    """Get application data from database"""
    conn = sqlite3.connect('application_management.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM applications WHERE applicationName = ?', (app_name,))
    result = cursor.fetchone()
    
    conn.close()
    return result

def update_application_status(app_name: str, status: str):
    """Update application status in database"""
    conn = sqlite3.connect('application_management.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE applications 
        SET status = ? 
        WHERE applicationName = ?
    ''', (status, app_name))
    
    conn.commit()
    conn.close()
    return cursor.rowcount > 0

def get_infrastructure_by_app_and_env(app_name: str, environment: str):
    """Get infrastructure data by application and environment"""
    conn = sqlite3.connect('application_management.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM infrastructure_details 
        WHERE applicationName = ? AND environment = ?
    ''', (app_name, environment))
    
    result = cursor.fetchone()
    conn.close()
    return result

def migrate_json_to_database():
    """Migrate existing JSON data to database"""
    create_database_tables()
    
    # Migrate application_details.json
    try:
        with open('application_details.json', 'r') as f:
            app_data = json.load(f)
            for app in app_data.get('applications', []):
                insert_application_data(app)
    except FileNotFoundError:
        pass
    
    # Migrate devops_details.json
    try:
        with open('devops_details.json', 'r') as f:
            devops_data = json.load(f)
            for devops in devops_data.get('applications', []):
                insert_devops_data(devops)
    except FileNotFoundError:
        pass
    
    # Migrate infrastructure_details.json
    try:
        with open('infrastructure_details.json', 'r') as f:
            infra_data = json.load(f)
            for env_name, env_apps in infra_data.get('environments', {}).items():
                for infra in env_apps:
                    insert_infrastructure_data(infra, env_name)
    except FileNotFoundError:
        pass

if __name__ == "__main__":
    migrate_json_to_database()
    print("Database tables created and data migrated successfully!")