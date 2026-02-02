import sqlite3
import psycopg2
import json
from datetime import datetime

def connect_to_retool():
    return psycopg2.connect(
        host="ep-wandering-firefly-afii3dov-pooler.c-2.us-west-2.retooldb.com",
        database="retool",
        user="retool",
        password="npg_Wui0EmLg6xeA",
        sslmode="require"
    )

def list_retool_tables():
    conn = connect_to_retool()
    cursor = conn.cursor()
    cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';")
    tables = [row[0] for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return tables

def get_all_applications():
    conn = connect_to_retool()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM applications")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    
    applications = []
    for row in rows:
        app = {
            "id": row[0],
            "applicationName": row[1],
            "displayName": row[2],
            "type": row[3],
            "description": row[4],
            "version": row[5],
            "status": row[6],
            "owner": row[7],
            "maintainer": row[8],
            "applicationUrl": row[9],
            "tags": json.loads(row[10]) if row[10] else []
        }
        applications.append(app)
    
    return applications


def migrate_data():
    sqlite_conn = sqlite3.connect('application_management.db')
    retool_conn = connect_to_retool()
    
    sqlite_cursor = sqlite_conn.cursor()
    retool_cursor = retool_conn.cursor()
    
    # Create tables
    retool_cursor.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id VARCHAR(50) PRIMARY KEY,
            applicationName VARCHAR(255),
            displayName VARCHAR(255),
            type VARCHAR(100),
            description TEXT,
            version VARCHAR(50),
            status VARCHAR(50),
            owner VARCHAR(255),
            maintainer VARCHAR(255),
            applicationUrl VARCHAR(500),
            tags TEXT
        )
    """)
    
    retool_cursor.execute("""
        CREATE TABLE IF NOT EXISTS devops_details (
            id VARCHAR(50) PRIMARY KEY,
            applicationname VARCHAR(255),
            repositoryurl VARCHAR(500),
            provider VARCHAR(100),
            buildpipeline VARCHAR(255),
            buildpipelineurl VARCHAR(500),
            releasepipeline VARCHAR(255),
            releasepipelineurl VARCHAR(500),
            deploymentstrategy VARCHAR(100),
            sonarqube VARCHAR(50),
            codecoverage VARCHAR(50),
            securityscan VARCHAR(50),
            applicationinsights VARCHAR(255),
            loganalytics VARCHAR(255),
            alerts TEXT
        )
    """)
    
    retool_cursor.execute("""
        CREATE TABLE IF NOT EXISTS infrastructure_details (
            id VARCHAR(50),
            applicationName VARCHAR(255),
            environment VARCHAR(100),
            cloud VARCHAR(100),
            subscriptionName VARCHAR(255),
            subscriptionId VARCHAR(255),
            region VARCHAR(100),
            resourceGroup VARCHAR(255),
            components TEXT,
            PRIMARY KEY (id, environment)
        )
    """)
    
    # Migrate applications
    sqlite_cursor.execute("SELECT * FROM applications")
    for row in sqlite_cursor.fetchall():
        data = list(row) + [None] * (11 - len(row))
        retool_cursor.execute("""
            INSERT INTO applications VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (id) DO UPDATE SET status = EXCLUDED.status
        """, data[:11])
    
    # Migrate devops_details
    try:
        sqlite_cursor.execute("SELECT * FROM devops_details")
        for row in sqlite_cursor.fetchall():
            data = list(row) + [None] * (15 - len(row))
            retool_cursor.execute("""
                INSERT INTO devops_details VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (id) DO NOTHING
            """, data[:15])
    except sqlite3.OperationalError:
        pass
    
    # Migrate infrastructure_details
    try:
        sqlite_cursor.execute("SELECT * FROM infrastructure_details")
        for row in sqlite_cursor.fetchall():
            data = list(row) + [None] * (9 - len(row))
            retool_cursor.execute("""
                INSERT INTO infrastructure_details VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (id, environment) DO NOTHING
            """, data[:9])
    except sqlite3.OperationalError:
        pass
    
    retool_conn.commit()
    sqlite_cursor.close()
    retool_cursor.close()
    sqlite_conn.close()
    retool_conn.close()

def insert_application(app_details):
    try:
        conn = connect_to_retool()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO applications (id, applicationName, displayName, type, description, version, status, owner, maintainer, applicationUrl, tags)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            app_details["id"],
            app_details["applicationName"],
            app_details["displayName"],
            app_details["type"],
            app_details["description"],
            app_details["version"],
            app_details["status"],
            app_details["owner"],
            app_details["maintainer"],
            app_details["applicationUrl"],
            json.dumps(app_details["tags"])
        ))
        conn.commit()
        cursor.close()
        conn.close()
        return {"success": True, "message": "Application inserted successfully"}
    except Exception as e:
        return {"success": False, "message": f"Failed to insert application: {str(e)}"}

def get_application_by_id(identifier: str):
    try:
        conn = connect_to_retool()
        cursor = conn.cursor()

        query = """
            SELECT *
            FROM applications
            WHERE id = %s OR applicationName = %s
            LIMIT 1
        """
        cursor.execute(query, (identifier, identifier))
        result = cursor.fetchone()

        cursor.close()
        conn.close()

        if result:
            return {
                "id": result[0],
                "applicationName": result[1],
                "displayName": result[2],
                "type": result[3],
                "description": result[4],
                "version": result[5],
                "status": result[6],
                "owner": result[7],
                "maintainer": result[8],
                "applicationUrl": result[9],
                "tags": json.loads(result[10]) if result[10] else []
            }

        return None

    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to retrieve application: {str(e)}"
        }

def get_devops_by_id(identifier):
    try:
        conn = connect_to_retool()
        cursor = conn.cursor()

        query = """
            SELECT *
            FROM devops_details
            WHERE id = %s OR applicationname = %s
            LIMIT 1
        """
        cursor.execute(query, (identifier, identifier))
        result = cursor.fetchone()

        cursor.close()
        conn.close()

        if result:
            print("=========================\n", result,"=========================",len(result))
            # Parse alerts JSON string
            alerts = []
            if result[14]:  # alerts field
                try:
                    alerts = json.loads(result[14])
                except (json.JSONDecodeError, TypeError):
                    alerts = []
            
            return {
                "id": result[0],
                "applicationName": result[1],
                "cicdPipeline": {
                    "repositoryUrl_frontend": result[2],
                    "repositoryUrl_backend":result[-1],
                    "provider": result[3],
                    "buildPipeline": result[4],
                    "buildPipelineUrl": result[5],
                    "releasePipeline": result[6],
                    "releasePipelineUrl": result[7],
                    "deploymentStrategy": result[8]
                },
                "codeQuality": {
                    "sonarQube": result[9],
                    "codeCoverage": result[10],
                    "securityScan": result[11]
                },
                "monitoring": {
                    "applicationInsights": result[12],
                    "logAnalytics": result[13],
                    "alerts": alerts
                }
            }

        return None

    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to retrieve application: {str(e)}"
        }
    

def insert_devops_details(devops_details):
    conn = connect_to_retool()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO devops_details (id, applicationname, repositoryurl_frontend, provider, buildpipeline, buildpipelineurl, releasepipeline, releasepipelineurl, deploymentstrategy, sonarqube, codecoverage, securityscan, applicationinsights, loganalytics, alerts, repositoryurl_backend)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        devops_details["applicationName"],
        devops_details["applicationName"],
        devops_details["repositoryUrl_frontend"],
        devops_details["cicdPipeline"]["provider"],
        devops_details["cicdPipeline"]["buildPipeline"],
        "",
        devops_details["cicdPipeline"]["releasePipeline"],
        "",
        devops_details["cicdPipeline"]["deploymentStrategy"],
        devops_details["codeQuality"]["sonarQube"],
        devops_details["codeQuality"]["codeCoverage"],
        devops_details["codeQuality"]["securityScan"],
        devops_details["monitoring"]["applicationInsights"],
        devops_details["monitoring"]["logAnalytics"],
        devops_details["repositoryUrl_backend"],
        json.dumps(devops_details["monitoring"]["alerts"])
    ))
    conn.commit()
    cursor.close()
    conn.close()
    return {"success": True, "message": "DevOps details inserted successfully"}


def get_azure_resource_group_cost(subscription_id: str, resource_group: str) -> dict:
    """Mock function to simulate Azure Cost Management API call"""
    try:
        # Mock cost data - in production, replace with actual Azure Cost Management API
        mock_costs = {
            "totalCost": round(150.75 + hash(resource_group) % 500, 2),
            "currency": "USD",
            "billingPeriod": "Current Month",
            "lastUpdated": datetime.now().isoformat(),
            "breakdown": {
                "compute": round(80.25 + hash(resource_group) % 200, 2),
                "storage": round(25.50 + hash(resource_group) % 50, 2),
                "networking": round(15.00 + hash(resource_group) % 30, 2),
                "database": round(30.00 + hash(resource_group) % 100, 2)
            }
        }
        return mock_costs
    except Exception as e:
        return {
            "error": f"Failed to fetch cost data: {str(e)}",
            "totalCost": 0,
            "currency": "USD"
        }


def get_infrastructure_by_id(identifier):
    conn = connect_to_retool()
    cursor = conn.cursor()

    query = """
        SELECT *
        FROM infrastructure_details
        WHERE id = %s OR applicationName = %s
    """
    cursor.execute(query, (identifier, identifier))
    results = cursor.fetchall()

    cursor.close()
    conn.close()

    if results:
        environments = {}
        application_name = results[0][1]  # Get application name from first result
        
        for result in results:
            try:
                components = json.loads(result[8]) if result[8] and result[8].strip() else {}
            except (json.JSONDecodeError, TypeError):
                components = {}
            
            # Get cost details for this environment
            cost_details = get_azure_resource_group_cost(result[5], result[7])
            
            environment_data = {
                "id": result[0],
                "applicationName": result[1],
                "cloud": result[3],
                "subscriptionName": result[4],
                "subscriptionId": result[5],
                "region": result[6],
                "resourceGroup": result[7],
                "components": components,
                "costDetails": cost_details
            }
            
            environments[result[2]] = environment_data  # Use environment as key
        
        return {
            "applicationName": application_name,
            "environments": environments
        }

    return None

def get_infra_components_by_env_and_component(env: str, identifier: str):
    try:
        conn = connect_to_retool()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT components,cloud,subscriptionname,subscriptionid
            FROM infrastructure_details
            WHERE (id = %s OR applicationName = %s) AND environment = %s
        """, (identifier, identifier, env))

        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if result and result[0]:
            return {
                "components": result[0],
                "cloud": result[1],
                "subscriptionName": result[2],
                "subscriptionId": result[3]
            }
        
        return None
        
    except Exception as e:
        return {"error": f"Failed to retrieve components: {str(e)}"}

if __name__ == "__main__":
    # migrate_data()
    # tables = list_retool_tables()
    # print("Retool tables:", tables)
    get_all_applications()