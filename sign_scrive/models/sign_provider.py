import requests
import json
from base64 import b64decode, b64encode
from urllib.parse import quote
from odoo import models, fields, api
from odoo.addons.sign_scrive.controllers.main import ScriveController
from werkzeug.urls import url_encode, url_join, url_parse
from odoo.exceptions import ValidationError


class SignProvider(models.Model):
    _inherit = "sign.provider"

    code = fields.Selection(
        selection_add=[('scrive', "Scrive")], ondelete={'scrive': 'set default'})

    scrive_api_url = fields.Char(string="Scrive API URL")
    scrive_username = fields.Char(string="Scrive Username")
    scrive_password = fields.Char(string="Scrive Password")

    scrive_api_token = fields.Char(string="Scrive API Token")
    scrive_api_secret = fields.Char(string="Scrive API Secret")
    scrive_access_token = fields.Char(string="Scrive Access Token")
    scrive_access_secret = fields.Char(string="Scrive Access Secret")

    def action_scrive_auth(self):
        url = f"{self.scrive_api_url}/api/v2/getpersonaltoken"

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
        else:
            print(f"Error: {response.status_code}")
            print(response.text)

    def _api_request_validation(self):
        if not all([
            self.scrive_api_token,
            self.scrive_access_token,
            self.scrive_api_secret,
            self.scrive_access_secret
        ]):
            return False
        return True

    def _build_request_headers(self):
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

    def prepare_scrive_request(self, sign_request):
        """Prepare Scrive-specific data for signing"""
        return {
            'document_name': f"{sign_request.name}.pdf",
        }

    def initiate_scrive_signature(self, sign_request, provider_data):
        """Start the Scrive signing process"""
        # Create document in Scrive
        document_response = self._create_scrive_document(sign_request, provider_data)

        # Save the document ID directly to the sign_request
        sign_request.write({
            'scrive_document_id': document_response['id'],
            'scrive_document_name': provider_data['document_name']
        })

        # Update document with parties and callback URL (this is where they get set)
        update_response = self._update_scrive_document(document_response['id'], sign_request)

        # Save signatory IDs from the update response
        if update_response and 'parties' in update_response:
            for i, party in enumerate(update_response['parties']):
                if i < len(sign_request.signer_ids) and party.get('id'):
                    # You could save the signatory ID to a field on the signer
                    # For now, let's save the first signatory ID to the main request
                    if i == 0:
                        sign_request.write({'scrive_signatory_id': party['id']})

        # Start signing process
        self._start_scrive_signature(document_response['id'])

        return {
            'scrive_document_id': document_response['id'],
            'status': 'initiated'
        }

    def process_scrive_callback(self, sign_request, callback_data):
        """Handle Scrive webhook callbacks"""
        import json

        # Get document_id from callback
        document_id = callback_data.get('document_id')

        # Parse the document_json to get detailed status
        document_json_str = callback_data.get('document_json')
        document_details = None

        if document_json_str:
            try:
                document_details = json.loads(document_json_str)
            except json.JSONDecodeError as e:
                print(f"Error parsing document_json: {e}")
                return

        print("document_id", document_id)
        print("document_signed_and_sealed", callback_data.get('document_signed_and_sealed'))

        # Update sign request with callback info
        sign_request.write({
            'scrive_last_updated': fields.Datetime.now(),
        })

        # Always get document details to check signatory status
        if document_details and 'parties' in document_details:
            try:
                # Update overall document status
                document_status = document_details.get('status')
                if document_status:
                    sign_request.write({'scrive_status': document_status})

                # Update individual signers based on their status
                for party in document_details['parties']:
                    # Find the corresponding signer in our system
                    signer = self._find_signer_by_email(sign_request, party)
                    if signer:
                        # Update signer status and delivery info
                        signer_data = {
                            'scrive_status': party.get('experimental', {}).get('signatory_status'),
                            'email_delivery_status': party.get('email_delivery_status', 'unknown'),
                        }

                        # If they rejected, store the reason
                        if party.get('rejection_reason'):
                            signer_data['rejection_reason'] = party.get('rejection_reason')

                        # If they signed, update signature info
                        if party.get('sign_time'):
                            signer_data.update({
                                'signed_on': fields.Datetime.now(),
                                'signature_hash': party.get('id'),  # Use party ID as signature reference
                            })

                        signer.write(signer_data)

                # Check if document is fully signed and sealed
                document_signed_and_sealed = callback_data.get('document_signed_and_sealed') == 'true'

                if document_signed_and_sealed or document_status == 'signed':
                    sign_request.write({
                        'scrive_is_document_signed': True,
                        'scrive_signed_date': fields.Datetime.now(),
                        'state': 'signed'
                    })

                # Trigger the sign_request to download its own document data
                if hasattr(sign_request, 'download_scrive_document'):
                    sign_request.download_scrive_document()

            except Exception as e:
                print(f"Error processing callback: {e}")

    def _get_document_details(self, document_id):
        """Get full document details from Scrive"""
        url = f"{self.scrive_api_url}/api/v2/documents/{document_id}/get"
        headers = self._build_request_headers()

        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Failed to get document details: {response.status_code}")
            return None

    def _find_signer_by_email(self, sign_request, party):
        """Find the signer record that matches the party email"""
        party_email = None
        for field in party.get('fields', []):
            if field.get('type') == 'email':
                party_email = field.get('value')
                break

        if party_email:
            for signer in sign_request.signer_ids:
                if signer.partner_id.email == party_email:
                    return signer
        return None

    def _create_scrive_document(self, sign_request, provider_data):
        """Create document in Scrive"""
        url = f"{self.scrive_api_url}/api/v2/documents/new"
        headers = self._build_request_headers()

        # Decode base64 data to binary PDF
        pdf_binary = b64decode(sign_request.data)

        # Get PDF data from sign_request
        files = {
            'file': (provider_data['document_name'], pdf_binary, 'application/pdf')
        }
        data = {'saved': "true"}

        response = requests.post(url, headers=headers, data=data, files=files)
        print(response.text)
        response.raise_for_status()
        return response.json()

    def _update_scrive_document(self, document_id, sign_request):
        """Update document with parties and callback URL"""
        url = f"{self.scrive_api_url}/api/v2/documents/{document_id}/update"
        headers = self._build_request_headers()

        # Prepare parties and callback URL at update time
        document_metadata = {
            'api_callback_url': self._get_scrive_callback_url(),
            'parties': self._prepare_scrive_parties(sign_request)
        }

        data = {
            'document': json.dumps(document_metadata)
        }

        response = requests.post(url, headers=headers, data=data)

        print("Update response:", response.text)

        if response.status_code == 200:
            print("Document updated successfully")
            return response.json()
        elif response.status_code == 409:
            error_data = response.json()
            print(f"Document state error: {error_data.get('error_message', 'Unknown error')}")
            if 'error_details' in error_data and 'explanations' in error_data['error_details']:
                print("Explanations:")
                for explanation in error_data['error_details']['explanations']:
                    print(f"  - {explanation}")
            raise ValidationError(f"Scrive document update failed: {error_data.get('error_message')}")
        else:
            print(f"Update failed with status {response.status_code}: {response.text}")
            response.raise_for_status()

    def _start_scrive_signature(self, document_id):
        """Start the signing process"""
        url = f"{self.scrive_api_url}/api/v2/documents/{document_id}/start"
        headers = self._build_request_headers()

        data = {
            'document_id': str(document_id),
        }

        response = requests.post(url, headers=headers, data=data)

        if response.status_code == 200:
            print("Signing process started successfully")
            return response.json()
        elif response.status_code == 409:
            error_data = response.json()
            print(f"Document state error: {error_data.get('error_message', 'Unknown error')}")
            raise ValidationError(f"Scrive signature start failed: {error_data.get('error_message')}")
        else:
            response.raise_for_status()

    def _prepare_scrive_parties(self, sign_request):
        """Prepare signing parties for Scrive"""
        parties = []

        for index, signer in enumerate(sign_request.signer_ids):
            party = {
                "is_signatory": True,
                "signatory_role": "signing_party",
                "fields": [
                    {
                        "type": "name",
                        "order": 1,
                        "value": signer.partner_id.name,
                        "is_obligatory": True,
                        "should_be_filled_by_sender": False,
                        "placements": []
                    },
                    {
                        "type": "email",
                        "value": signer.partner_id.email or '',
                        "is_obligatory": False,
                        "should_be_filled_by_sender": False,
                        "placements": []
                    }
                ],
                "sign_order": index + 1,
            }

            # Add company field if partner has a company
            company_name = signer.partner_id.commercial_partner_id.name if signer.partner_id.commercial_partner_id != signer.partner_id else None

            if company_name:
                party["fields"].append({
                    "type": "company",
                    "value": company_name,
                    "is_obligatory": True,
                    "should_be_filled_by_sender": False,
                })

            parties.append(party)

        print("parties", parties)
        return parties

    def _download_signed_document(self, document_id):
        """Download the signed document from Scrive"""
        url = f"{self.scrive_api_url}/api/v2/documents/{document_id}/files/main"
        headers = self._build_request_headers()

        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            # Return base64 encoded content
            return b64encode(response.content).decode('utf-8')
        else:
            response.raise_for_status()

    def _get_scrive_callback_url(self):
        """Get Scrive callback URL"""
        base_url = self.get_base_url()
        return url_join(base_url, ScriveController._callback_url)