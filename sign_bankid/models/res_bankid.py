# models/res_bankid.py
import time
import logging
from datetime import datetime
from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)


class BankIDResource(models.AbstractModel):
    _name = 'res.bankid'
    _description = "BankID Resources and Metadata"

    # Tracking fields (optional - only needed if you want to track which record this relates to)
    res_model = fields.Char('Related Document Model', index=True, store=True, readonly=True)
    res_id = fields.Many2oneReference(string='Related Document ID', index=True, model_field='res_model')

    # User tracking - IMPORTANT for security and audit
    signed_user_id = fields.Many2one(
        "res.users", string="Signing User", readonly=True, default=lambda self: self.env.user
    )
    signed_partner_id = fields.Many2one(
        "res.partner",
        string="Signing Partner",
        related='signed_user_id.partner_id',
        store=True, readonly=True)

    # BankID session data
    bankid_order_ref = fields.Char("BankID Reference", copy=False, readonly=True)
    bankid_auto_start_token = fields.Char("BankID Auto Start Token", copy=False, readonly=True)
    bankid_qr_start_token = fields.Char("BankID QR Start Token", copy=False, readonly=True)
    bankid_qr_start_secret = fields.Char("BankID QR Start Secret", copy=False, readonly=True)
    bankid_start_time = fields.Datetime("BankID Start Time", copy=False, readonly=True)
    bankid_status = fields.Selection([
        ('pending', 'Pending'),
        ('complete', 'Complete'),
        ('failed', 'Failed')
    ], string="BankID Status", copy=False, default='pending', readonly=True)

    # Signature metadata (populated after successful signing)
    bankid_signed_name = fields.Char("Signed Name from BankID", readonly=True)
    bankid_signed_personal_number = fields.Char("Signed Personal Number", readonly=True)
    bankid_signed_given_name = fields.Char("Signed Given Name", readonly=True)
    bankid_signed_surname = fields.Char("Signed Surname", readonly=True)
    bankid_device_ip = fields.Char("Device IP Address", readonly=True)
    bankid_issue_date = fields.Date("BankID Issue Date", readonly=True)
    bankid_signature = fields.Binary("BankID Signature (Base64)", readonly=True)
    bankid_ocsp_response = fields.Binary("OCSP Response (Base64)", readonly=True)
    signed_date = fields.Datetime("Date Signed", readonly=True)

    def initiate_bankid_client(self):
        """Start BankID signing process"""
        try:
            _logger.info(f"Starting BankID for {self._name} record ID: {self.id}")

            if not self.id:
                return {'success': False, 'error': 'No record ID available'}

            # Get BankID client
            client = self.env.company.bank_id_client()

            # Get end user IP from request context
            end_user_ip = '0.0.0.0'  # Default fallback
            if hasattr(self.env, 'context') and 'request' in self.env.context:
                end_user_ip = self.env.context.get('request', {}).get('httprequest', {}).get('remote_addr', '0.0.0.0')

            # Make sign request to BankID
            response = client.sign(
                end_user_ip=end_user_ip,
                user_visible_data=f"Sign {self._name} {self.id}"
            )

            # Store BankID session data
            start_time = fields.Datetime.now()
            self.write({
                'res_model': self._name,
                'res_id': self.id,
                'bankid_order_ref': response.get("orderRef"),
                'bankid_auto_start_token': response.get("autoStartToken"),
                'bankid_qr_start_token': response.get("qrStartToken"),
                'bankid_qr_start_secret': response.get("qrStartSecret"),
                'bankid_start_time': start_time,
                'bankid_status': 'pending'
            })

            # Generate initial QR code and auto-start URL
            qr_content = self.generate_bankid_qr_code()
            auto_start_url = self._generate_bankid_auto_start_url(response.get("autoStartToken"))

            _logger.info(f"BankID initiated successfully - Order ref: {response.get('orderRef')}")

            return {
                'success': True,
                'orderRef': response.get("orderRef"),
                'qrCode': qr_content,
                'autoStartUrl': auto_start_url,
            }

        except Exception as e:
            _logger.error(f"Error initiating BankID: {str(e)}", exc_info=True)
            return {'success': False, 'error': str(e)}

    def check_bankid_status(self):
        """Check the status of BankID signing"""
        if not self.bankid_order_ref:
            return {'status': 'failed', 'message': 'No active BankID session'}

        try:
            client = self.env.company.bank_id_client()
            collect_response = client.collect(self.bankid_order_ref)

            status = collect_response.get('status')
            _logger.info(f"BankID status check - Order: {self.bankid_order_ref}, Status: {status}")

            if status == 'complete':
                self._process_bankid_completion(collect_response)
                return {'status': 'complete'}
            elif status == 'failed':
                self.write({'bankid_status': 'failed'})
                hint_code = collect_response.get('hintCode', '')
                return {'status': 'failed', 'message': f'BankID signing failed: {hint_code}'}
            else:
                # Still pending - return the full response for hint codes
                return collect_response

        except Exception as e:
            _logger.error(f"Error checking BankID status: {str(e)}", exc_info=True)
            return {'status': 'failed', 'message': str(e)}

    def get_updated_qr_code(self):
        """Get updated QR code content for BankID (time-based)"""
        if not all([self.bankid_qr_start_token, self.bankid_qr_start_secret, self.bankid_start_time]):
            return {'success': False, 'error': 'Missing QR parameters'}

        try:
            qr_content = self.generate_bankid_qr_code()
            return {'success': True, 'qrCode': qr_content}
        except Exception as e:
            _logger.error(f"Error generating QR code: {str(e)}", exc_info=True)
            return {'success': False, 'error': str(e)}

    def generate_bankid_qr_code(self):
        """Generate QR code content for BankID scanning"""
        if not all([self.bankid_qr_start_token, self.bankid_qr_start_secret, self.bankid_start_time]):
            return ""

        try:
            client = self.env.company.bank_id_client()

            # Convert start_time to timestamp
            start_timestamp = int(self.bankid_start_time.timestamp())

            # Generate QR code content - BankID library handles the time-based updates internally
            qr_content = client.generate_qr_code_content(
                self.bankid_qr_start_token,
                start_timestamp,
                self.bankid_qr_start_secret,
            )

            return qr_content

        except Exception as e:
            _logger.error(f"Error generating QR code: {str(e)}", exc_info=True)
            return ""

    def cancel_bankid_sign(self):
        """Cancel an ongoing BankID signing process"""
        if not self.bankid_order_ref or self.bankid_status != 'pending':
            return False

        try:
            client = self.env.company.bank_id_client()
            result = client.cancel(self.bankid_order_ref)

            if result:
                self.write({
                    'bankid_status': 'failed',
                    'bankid_order_ref': False  # Clear the order ref
                })

                # Log the cancellation if message_post is available
                if hasattr(self, 'message_post'):
                    self.message_post(
                        body=_("BankID signing was cancelled"),
                        subtype_xmlid="mail.mt_note"
                    )

            return result

        except Exception as e:
            _logger.error(f"Error cancelling BankID signing: {str(e)}", exc_info=True)
            if hasattr(self, 'message_post'):
                self.message_post(
                    body=_(f"Error cancelling BankID signing: {str(e)}"),
                    subtype_xmlid="mail.mt_note"
                )
            return False

    def _generate_bankid_auto_start_url(self, auto_start_token):
        """Generate URL to launch BankID app on devices with the app installed"""
        if not auto_start_token:
            return ""
        return f"bankid:///?autostarttoken={auto_start_token}&redirect=null"

    def _process_bankid_completion(self, collect_response):
        """Process BankID completion - can be overridden by specific models"""
        completion_data = collect_response.get("completionData", {})
        user_info = completion_data.get("user", {})
        device_info = completion_data.get("device", {})

        # Update with signature data
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
            'signed_user_id': self.env.user.id
        }

        self.write(bankid_data)

        _logger.info(f"BankID signing completed for {self._name} ID {self.id} by {user_info.get('name')}")

        # Call model-specific completion handler if it exists
        if hasattr(self, '_on_bankid_complete'):
            self._on_bankid_complete(collect_response)

    # Helper method to check if document needs to be signed
    def _has_to_be_signed(self):
        """Override this method in your specific model to define when signing is required"""
        return self.bankid_status != 'complete'


    def _has_user_signed_rec(self):
        """Check if current user has signed this record with BankID"""
        return (
                self.bankid_status == 'complete' and
                self.bankid_signature and
                self.signed_user_id == self.env.user  # or however you track who signed
        )