import os
import requests
import urllib.parse
from dotenv import load_dotenv

load_dotenv()

class MyobAuth:
    def __init__(self, client_id=None, client_secret=None, redirect_uri=None):
        self.client_id = client_id or os.getenv('MYOB_CLIENT_ID')
        self.client_secret = client_secret or os.getenv('MYOB_CLIENT_SECRET')
        self.redirect_uri = redirect_uri or os.getenv('MYOB_REDIRECT_URI', 'http://localhost:8080/callback')
        self.token_url = 'https://secure.myob.com/oauth2/v1/authorize/'
        self.access_token_url = 'https://secure.myob.com/oauth2/v1/authorize/'
        
        if not self.client_id or not self.client_secret:
            raise ValueError("MYOB_CLIENT_ID and MYOB_CLIENT_SECRET must be set in environment variables or passed to constructor.")

    def get_authorization_url(self):
        params = {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'response_type': 'code',
            'scope': 'CompanyFile'
        }
        url = f"{self.token_url}?{urllib.parse.urlencode(params)}"
        return url

    def exchange_code_for_token(self, code):
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'redirect_uri': self.redirect_uri,
            'grant_type': 'authorization_code',
            'code': code
        }
        
        # Note: MYOB token endpoint is actually https://secure.myob.com/oauth2/v1/authorize/ 
        # but for POST it is standard to use the same base or specific token endpoint.
        # Checking docs: POST https://secure.myob.com/oauth2/v1/authorize/ is for getting the token.
        
        response = requests.post(self.access_token_url, data=data, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to retrieve token: {response.text}")

    def refresh_token(self, refresh_token):
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token
        }
        response = requests.post(self.access_token_url, data=data, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to refresh token: {response.text}")
