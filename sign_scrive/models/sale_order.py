import json
import base64
import requests
from pathlib import Path
from werkzeug import urls
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.addons.sign_scrive.controllers.main import ScriveController


class SaleOrderTemplate(models.Model):
    _inherit = "sale.order.template"

    sign_provider_id = fields.Many2one('sign.provider', string="Signature Provider")



class SaleOrder(models.Model):
    _inherit = "sale.order"

    sign_provider_id = fields.Many2one('sign.provider', string="Signature Provider")

    scrive_document_id = fields.Char(string="Document ID", readonly=False)
    scrive_signatory_id = fields.Char(string="Signatory ID", readonly=False)
    scrive_is_document_signed = fields.Boolean(string="Signed and Sealed?", default=False)
    scrive_document_name = fields.Char(string="Document Name")
    scrive_document_data = fields.Binary(string="Datas")
    scrive_signed_date = fields.Datetime(string="Signed Date")

    def action_callback(self):
        scrive_url = self.env.company.scrive_url
        url = f"{scrive_url}/api/v2/documents/{self.scrive_document_id}/callback"

        headers = self.env.company._scrive_api_access_header()
        response = requests.post(url, headers=headers)
        print(response.text)

    def action_confirm(self):
        print("I see you")
        auth_header = self.env.company._scrive_api_access_header()
        scrive_url = self.env.company.scrive_url

        url = f"{scrive_url}/api/v2/documents/new"

        data = {'saved': "true"}

        pdf_file_path = "/home/ayomir/Downloads/Quotation - S00040.pdf"

        try:
            if pdf_file_path and Path(pdf_file_path).exists():
                with open(pdf_file_path, 'rb') as pdf_file:
                    files = {
                        'file': (Path(pdf_file_path).name, pdf_file, 'application/pdf')
                    }
                    response = requests.post(url, headers=auth_header, data=data, files=files)
                    print(response.text)
                    json_response = response.json()
                    self.write({'scrive_document_id': json_response.get('id')})
                    self.action_update_document(document_metadata=json_response)

            else:
                response = requests.post(url, headers=auth_header, data=data)

            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            return None
        except FileNotFoundError:
            print(f"Error: PDF file not found at {pdf_file_path}")
            return None

    def _get_signing_parties(self):
        parties = []

        if self.user_id:
            parties.append({
                "is_signatory": True,
                "signatory_role": "signing_party",
                "experimental": {
                    "signatory_status": "invitation_sent"
                },
                "fields": [
                    {
                        "type": "name",
                        "order": 1,
                        "value": self.user_id.partner_id.name,
                        "is_obligatory": True,
                        "should_be_filled_by_sender": False,
                        "placements": []
                    },
                    {
                        "type": "email",
                        "value": self.user_id.partner_id.email,
                        "is_obligatory": False,
                        "should_be_filled_by_sender": False,
                        "placements": []
                    },
                    {
                        "type": "company",
                        "value": self.user_id.partner_id.commercial_partner_id.name,
                        "is_obligatory": True,
                        "should_be_filled_by_sender": False,
                    }
                ],
                "sign_order": 1,
            })

        if self.partner_id:
            parties.append({
                "is_signatory": True,
                "signatory_role": "signing_party",
                "experimental": {
                    "signatory_status": "invitation_sent"
                },
                "fields": [
                    {
                        "type": "name",
                        "order": 1,
                        "value": self.partner_id.name,
                        "is_obligatory": True,
                        "should_be_filled_by_sender": False,
                        "placements": []
                    },
                    {
                        "type": "email",
                        "value": self.partner_id.email,
                        "is_obligatory": False,
                        "should_be_filled_by_sender": False,
                        "placements": []
                    },
                    {
                        "type": "company",
                        "value": self.partner_id.commercial_partner_id.name,
                        "is_obligatory": True,
                        "should_be_filled_by_sender": False,
                    }
                ],
                "sign_order": 2,
            })
        print(parties)
        return parties


    def action_update_document(self, document_metadata):
        scrive_url = self.env.company.scrive_url
        url = f"{scrive_url}/api/v2/documents/{document_metadata.get('id')}/update"

        headers = self.env.company._scrive_api_access_header()

        signing_party = []
        # Prepare form data
        document_metadata['api_callback_url'] = 'https://bat-factual-mistakenly.ngrok-free.app/scrive/callback'
        document_metadata['parties'] = self._get_signing_parties()

        data = {
            'document_id': str(self.document_id),
            # 'strict_validations': str(strict_validations).lower()
            'document': json.dumps(document_metadata)
        }

        try:
            response = requests.post(url, headers=headers, data=data)

            # Handle different response codes
            if response.status_code == 200:
                print("updated response", response.json())
                return response.json()
            elif response.status_code == 409:
                # Document state error or version conflict
                error_data = response.json()
                print(f"Document state error: {error_data.get('error_message', 'Unknown error')}")
                if 'error_details' in error_data and 'explanations' in error_data['error_details']:
                    print("Explanations:")
                    for explanation in error_data['error_details']['explanations']:
                        print(f"  - {explanation}")
                return error_data
            else:
                response.raise_for_status()

        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            return None

    def action_start_signature(self):
        scrive_url = self.env.company.scrive_url
        url = f"{scrive_url}/api/v2/documents/{self.scrive_document_id}/start"

        headers = self.env.company._scrive_api_access_header()

        # Prepare form data
        data = {
            'document_id': str(self.document_id),
        }

        try:
            response = requests.post(url, headers=headers, data=data)

            # Handle different response codes
            if response.status_code == 200:
                print(response.json())
                return response.json()
            elif response.status_code == 409:
                # Document state error or version conflict
                error_data = response.json()
                print(f"Document state error: {error_data.get('error_message', 'Unknown error')}")
                if 'error_details' in error_data and 'explanations' in error_data['error_details']:
                    print("Explanations:")
                    for explanation in error_data['error_details']['explanations']:
                        print(f"  - {explanation}")
                return error_data
            else:
                response.raise_for_status()

        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            return None

    def action_getqr_code(self):
        scrive_url = self.env.company.scrive_url
        url = f"{scrive_url}/api/v2/documents/{self.scrive_document_id}/{self.signatory_id}/getqrcode"

        headers = self.env.company._scrive_api_access_header()

        try:
            response = requests.get(url, headers=headers)

            # Handle different response codes
            if response.status_code == 200:
                print(response.json())
                return response.json()
            elif response.status_code == 409:
                # Document state error or version conflict
                error_data = response.json()
                print(f"Document state error: {error_data.get('error_message', 'Unknown error')}")
                return error_data
            else:
                response.raise_for_status()

        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            return None

    def action_scrive_signing_data(self):
        scrive_url = self.env.company.scrive_url
        url = f"{scrive_url}/api/v2/documents/{self.scrive_document_id}/{self.signatory_id}/signingdata"

        headers = self.env.company._scrive_api_access_header()

        try:
            response = requests.get(url, headers=headers)

            # Handle different response codes
            if response.status_code == 200:
                print(response.json())
                return response.json()
            elif response.status_code == 409:
                # Document state error or version conflict
                error_data = response.json()
                print(f"Document state error: {error_data.get('error_message', 'Unknown error')}")
                return error_data
            else:
                response.raise_for_status()

        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            return None


    # def action_get_scrive_document(self):
    #     scrive_url = self.env.company.scrive_url
    #     url = f"{scrive_url}/api/v2/documents/{self.scrive_document_id}/get"
    #
    #     headers = self.env.company._scrive_api_access_header()
    #
    #     try:
    #         response = requests.get(url, headers=headers)
    #
    #         # Handle different response codes
    #         if response.status_code == 200:
    #             print(response.json())
    #             return response.json()
    #         elif response.status_code == 409:
    #             # Document state error or version conflict
    #             error_data = response.json()
    #             print(f"Document state error: {error_data.get('error_message', 'Unknown error')}")
    #             return error_data
    #         else:
    #             response.raise_for_status()
    #
    #     except requests.exceptions.RequestException as e:
    #         print(f"Request failed: {e}")
    #         return None

    def action_get_scrive_document(self):
        scrive_url = self.env.company.scrive_url
        filename = f'{self.name}.pdf'  # Use dynamic filename
        url = f"{scrive_url}/api/v2/documents/{self.scrive_document_id}/files/main/{filename}"

        headers = self.env.company._scrive_api_access_header()

        try:
            response = requests.get(url, headers=headers)

            if response.status_code == 200:
                pdf_content = response.content
                pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')

                # Create attachment
                # attachment = self.env['ir.attachment'].create({
                #     'name': filename,
                #     'type': 'binary',
                #     'datas': pdf_base64,
                #     'res_model': self._name,
                #     'res_id': self.id,
                #     'mimetype': 'application/pdf',
                #     'description': f'Scrive signed document {self.scrive_document_id}'
                # })

                # Update the record with attachment reference
                self.write({
                    'scrive_document_name': filename,
                    'scrive_document_data': pdf_base64
                })

                # Show success message to user
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Success',
                        'message': f'Signed document "{filename}" downloaded successfully',
                        'type': 'success',
                        'sticky': False,
                    }
                }

            else:
                error_msg = f"Failed to download document. Status: {response.status_code}"
                raise ValidationError(error_msg)

        except requests.exceptions.RequestException as e:
            error_msg = f"Network error downloading document: {str(e)}"
            raise ValidationError(error_msg)
        except Exception as e:
            error_msg = f"Error processing document: {str(e)}"
            raise ValidationError(error_msg)