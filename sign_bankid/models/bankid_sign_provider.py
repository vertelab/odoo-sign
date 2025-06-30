import requests
import json
import logging
from base64 import b64decode, b64encode
from urllib.parse import quote
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from bankid import BankIDClient

_logger = logging.getLogger(__name__)


class BankIDSignProvider(models.Model):
    _inherit = "sign.provider"

    code = fields.Selection(
        selection_add=[('bankid', "Bank ID")],
        ondelete={'bankid': 'set default'}
    )

    bankid_cert_file = fields.Binary(string="BankID Certificate")
    bankid_key_file = fields.Binary(string="BankID Private Key")

    def bank_id_client(self):
        """Get BankID client instance"""
        bankid_cert_file = "/home/ayomir/Downloads/pybankid/bankid/certs/FPTestcert5_20240610_cert.pem"
        bankid_key_file = "/home/ayomir/Downloads/pybankid/bankid/certs/FPTestcert5_20240610_key.pem"

        if self.state == 'enabled':
            client = BankIDClient(certificates=(self.bankid_cert_file, self.bankid_key_file))
        else:
            client = BankIDClient(certificates=(bankid_cert_file, bankid_key_file), test_server=True)
        return client

    def prepare_bankid_request(self, sign_request):
        """Prepare BankID request data"""
        return {
            'document_name': sign_request.name,
            'user_visible_data': f"Sign {sign_request.name}",
            'end_user_ip': self._get_user_ip()
        }

    def initiate_bankid_signature(self, sign_request, provider_data):
        """Start BankID signing process"""
        try:
            _logger.info(f"Starting BankID signature for request ID: {sign_request.id}")

            # Get BankID client
            client = self.bank_id_client()

            # Make sign request to BankID
            response = client.sign(
                end_user_ip=provider_data.get('end_user_ip', '0.0.0.0'),
                user_visible_data=provider_data.get('user_visible_data', f"Sign {sign_request.name}")
            )

            _logger.info(f"BankID response: {response}")

            # Find signer for current user
            signer = sign_request.signer_id  # Current user's signer record
            if not signer:
                # If no signer found, get the first signer for current user
                user = self.env.user
                signer = sign_request.signer_ids.filtered(
                    lambda s: s.partner_id == user.partner_id
                )
                if signer:
                    signer = signer[0]
                else:
                    # Just take the first signer if no match found
                    signer = sign_request.signer_ids[0] if sign_request.signer_ids else None

            if not signer:
                raise UserError(_("No signer found in sign request"))

            _logger.info(f"Found signer: {signer.id} for partner: {signer.partner_id.name}")

            # Update signer with BankID session data
            bankid_data = {
                'bankid_order_ref': response.get("orderRef"),
                'bankid_auto_start_token': response.get("autoStartToken"),
                'bankid_qr_start_token': response.get("qrStartToken"),
                'bankid_qr_start_secret': response.get("qrStartSecret"),
                'bankid_start_time': fields.Datetime.now(),
                'bankid_status': 'pending'
            }

            _logger.info(f"Writing BankID data to signer {signer.id}: {bankid_data}")
            signer.write(bankid_data)
            _logger.info(f"Successfully updated signer {signer.id}")

            # Generate initial QR code and auto-start URL
            qr_content = self._generate_bankid_qr_code(signer)
            auto_start_url = self._generate_bankid_auto_start_url(response.get("autoStartToken"))

            _logger.info(f"BankID initiated successfully - Order ref: {response.get('orderRef')}")

            return {
                'success': True,
                'orderRef': response.get("orderRef"),
                'qrCode': qr_content,
                'autoStartUrl': auto_start_url,
                'signer_id': signer.id
            }

        except Exception as e:
            _logger.error(f"Error initiating BankID: {str(e)}", exc_info=True)
            raise UserError(_("BankID initiation failed: %s") % str(e))

    def check_bankid_status(self, signer):
        """Check the status of BankID signing"""
        if not signer.bankid_order_ref:
            return {'status': 'failed', 'message': 'No active BankID session'}

        try:
            client = self.bank_id_client()
            collect_response = client.collect(signer.bankid_order_ref)

            status = collect_response.get('status')
            _logger.info(f"BankID status check - Order: {signer.bankid_order_ref}, Status: {status}")

            if status == 'complete':
                self._process_bankid_completion(signer, collect_response)
                return {'status': 'complete'}
            elif status == 'failed':
                signer.write({'bankid_status': 'failed'})
                hint_code = collect_response.get('hintCode', '')
                return {'status': 'failed', 'message': f'BankID signing failed: {hint_code}'}
            else:
                # Still pending - return the full response for hint codes
                return collect_response

        except Exception as e:
            _logger.error(f"Error checking BankID status: {str(e)}", exc_info=True)
            return {'status': 'failed', 'message': str(e)}

    def _generate_bankid_qr_code(self, signer):
        """Generate QR code content for BankID scanning"""
        if not all([signer.bankid_qr_start_token, signer.bankid_qr_start_secret, signer.bankid_start_time]):
            _logger.warning(f"Missing QR data for signer {signer.id}")
            return ""

        try:
            client = self.bank_id_client()
            start_timestamp = int(signer.bankid_start_time.timestamp())

            qr_content = client.generate_qr_code_content(
                signer.bankid_qr_start_token,
                start_timestamp,
                signer.bankid_qr_start_secret,
            )
            return qr_content

        except Exception as e:
            _logger.error(f"Error generating QR code: {str(e)}", exc_info=True)
            return ""

    def _generate_bankid_auto_start_url(self, auto_start_token):
        """Generate URL to launch BankID app on devices with the app installed"""
        if not auto_start_token:
            return ""
        return f"bankid:///?autostarttoken={auto_start_token}&redirect=null"

    def _process_bankid_completion(self, signer, collect_response):
        """Process BankID completion"""
        completion_data = collect_response.get("completionData", {})
        user_info = completion_data.get("user", {})
        device_info = completion_data.get("device", {})

        # Update signer with signature data
        bankid_data = {
            'bankid_signed_name': user_info.get('name'),
            'bankid_signed_personal_number': user_info.get('personalNumber'),
            'bankid_signed_given_name': user_info.get('givenName'),
            'bankid_signed_surname': user_info.get('surname'),
            'bankid_device_ip': device_info.get('ipAddress'),
            'bankid_issue_date': completion_data.get('bankIdIssueDate'),
            'bankid_signature': completion_data.get('signature'),
            'bankid_ocsp_response': completion_data.get('ocspResponse'),
            'signed_date': fields.Datetime.now(),
            'bankid_status': 'complete',
            'signed_on': fields.Datetime.now()  # Mark as signed
        }

        signer.write(bankid_data)

        # Check if all signers have signed
        signer.request_id._check_signed()

        _logger.info(f"BankID signing completed for signer ID {signer.id} by {user_info.get('name')}")

    def _get_user_ip(self):
        """Get user IP address"""
        try:
            from odoo.http import request
            if request and hasattr(request, 'httprequest'):
                return request.httprequest.environ.get('REMOTE_ADDR', '0.0.0.0')
        except:
            pass
        return '0.0.0.0'

    def cancel_bankid_sign(self, signer):
        """Cancel an ongoing BankID signing process"""
        if not signer.bankid_order_ref or signer.bankid_status != 'pending':
            return False

        try:
            client = self.bank_id_client()
            result = client.cancel(signer.bankid_order_ref)

            if result:
                signer.write({
                    'bankid_status': 'failed',
                    'bankid_order_ref': False
                })

            return result

        except Exception as e:
            _logger.error(f"Error cancelling BankID signing: {str(e)}", exc_info=True)
            return False