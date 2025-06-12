import requests
from urllib.parse import quote
from odoo import models, fields, api
from odoo.exceptions import ValidationError



class ResCompany(models.Model):
    _inherit = 'res.company'

    scrive_url = fields.Char(string="Scrive URL")
    scrive_username = fields.Char(string="Scrive Username")
    scrive_password = fields.Char(string="Scrive Password")

    scrive_api_token = fields.Char(string="Scrive API Token")
    scrive_api_secret = fields.Char(string="Scrive API Secret")
    scrive_access_token = fields.Char(string="Scrive Access Token")
    scrive_access_secret = fields.Char(string="Scrive Access Secret")

    def action_scrive_auth(self):
        url = f"{self.scrive_url}/api/v2/getpersonaltoken"

        data = {
            'email': self.scrive_username,
            'password': self.scrive_password
        }

        response = requests.post(url, data=data)

        # Check if the request was successful
        if response.status_code == 200:
            json_resp = response.json()
            self.write({
                'scrive_api_token': json_resp.get('apitoken'),
                'scrive_api_secret': json_resp.get('apisecret'),
                'scrive_access_token': json_resp.get('accesstoken'),
                'scrive_access_secret': json_resp.get('accesssecret'),
            })
            print(response.json())  # or response.json() if the response is JSON
        else:
            print(f"Error: {response.status_code}")
            print(response.text)

    def _api_request_validation(self):
        if not all(
                self.scrive_api_token and
                self.scrive_access_token and
                self.scrive_api_secret and
                self.scrive_access_secret
        ):
            return False
        return True



    def _scrive_api_access_header(self):
        if not self._api_request_validation():
            raise ValidationError(
                "There is a problem making request to scrive. Ensure you have api and access token and secret setup"
            )

        # URL encode the values to handle special characters
        auth_header = (
            f'oauth_signature_method="PLAINTEXT",'
            f'oauth_consumer_key="{quote(self.scrive_api_token)}",'
            f'oauth_token="{quote(self.scrive_access_token)}",'
            f'oauth_signature="{quote(self.scrive_api_secret)}&{quote(self.scrive_access_secret)}"'
        )
        headers = {
            'Authorization': auth_header
        }
        return headers


