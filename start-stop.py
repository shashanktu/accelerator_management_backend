import requests
def get_access_token():
    url = f"https://login.microsoftonline.com/5f3ec70f-0215-4f44-bdab-f5beda7cdd74/oauth2/v2.0/token"
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    payload = {
        "client_id": "2ce5f502-bff8-4cf0-9794-645e0739b742",
        "client_secret": "8WU8Q~oHiXDMI05OAGD_2SQ6SicPTRxhD_wjWdlp",
        "grant_type": "client_credentials",
        "scope":"https://management.azure.com/.default"
    }
    response = requests.post(url, headers=headers, data=payload)
    if response.status_code == 200:
        print("==========================")
        print(response.json())
        return response.json().get("access_token")
    else:
        print(f"Failed to get access token: {response.status_code}")
        print(response.text)
        return None

access_token = get_access_token()