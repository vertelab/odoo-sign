import requests
import base64
import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.http import request

_logger = logging.getLogger(__name__)


class VrtlSignRequest(models.Model):
    _inherit = "vrtl.sign.request"

    def sign_data(self, provider_sign_data):
        """Handle provider-specific sign data"""
        if self.sign_provider_code == 'bankid':
            return self._handle_bankid_sign_data(provider_sign_data)
        else:
            # Handle other providers or default behavior
            print(provider_sign_data)
            return True

    def _handle_bankid_sign_data(self, provider_sign_data):
        """Handle BankID specific sign data"""
        if provider_sign_data.get('success'):
            # Use your existing BankID modal
            return {
                'type': 'ir.actions.client',
                'tag': 'bankid_sign_modal',
                'target': 'new',
                'context': {
                    'default_record_id': self.id,
                    'default_record_model': self._name,
                    'callback_method': '_on_bankid_complete',
                    'order_ref': provider_sign_data.get('orderRef'),
                    'qr_code': provider_sign_data.get('qrCode'),
                    'auto_start_url': provider_sign_data.get('autoStartUrl'),
                    'signer_id': provider_sign_data.get('signer_id'),
                }
            }
        else:
            raise UserError(
                _("Failed to initiate BankID signing: %s") % provider_sign_data.get('error', 'Unknown error'))

    def _on_bankid_complete(self):
        """Callback method when BankID signing is complete"""
        try:
            _logger.info(f"BankID completion callback called for sign request {self.id}")

            # Check if all signers have signed and update state accordingly
            if hasattr(self, '_check_signed'):
                self._check_signed()
                _logger.info(f"Sign request {self.id} checked for completion")
            else:
                _logger.warning(f"_check_signed method not found on {self._name}")

            # Mark this specific request as signed if needed
            if hasattr(self, 'write'):
                # You might want to update a status field here
                # self.write({'state': 'signed'})
                pass

            _logger.info(f"BankID completion callback finished successfully for {self.id}")
            return {'success': True}

        except Exception as e:
            _logger.error(f"Error in _on_bankid_complete for {self.id}: {str(e)}", exc_info=True)
            # Return error details for JS to handle
            return {'success': False, 'error': str(e)}

    def sign(self):
        """Override the original sign method to return the modal action"""
        self.ensure_one()
        try:
            if self.sign_provider_id:
                # Call provider methods, not definition methods
                provider_data = self.sign_provider_id.prepare_signing_request(self)
                provider_sign_data = self.sign_provider_id.initiate_signature(self, provider_data)
                return self.sign_data(provider_sign_data)  # Return the result
        except Exception as e:
            raise UserError(_(f"{e}"))

    # Methods expected by your JavaScript
    def initiate_bankid_client(self):
        """Initialize BankID signing - called by JavaScript"""
        try:
            if self.sign_provider_code != 'bankid':
                return {'success': False, 'error': 'Not configured for BankID signing'}

            # Get current user's signer
            signer = self._get_current_user_signer()
            if not signer:
                return {'success': False, 'error': 'No signer found for current user'}

            # Prepare provider data
            provider_data = self.sign_provider_id.prepare_bankid_request(self)

            # Initiate BankID signature
            provider_sign_data = self.sign_provider_id.initiate_bankid_signature(self, provider_data)

            return provider_sign_data

        except Exception as e:
            _logger.error(f"Error in initiate_bankid_client: {str(e)}", exc_info=True)
            return {'success': False, 'error': str(e)}

    def check_bankid_status(self):
        """Check BankID status - called by JavaScript"""
        try:
            if self.sign_provider_code != 'bankid':
                return {'status': 'error', 'message': 'Not configured for BankID signing'}

            # Get current user's signer
            signer = self._get_current_user_signer()
            if not signer:
                return {'status': 'error', 'message': 'No signer found for current user'}

            return self.sign_provider_id.check_bankid_status(signer)

        except Exception as e:
            _logger.error(f"Error in check_bankid_status: {str(e)}", exc_info=True)
            return {'status': 'error', 'message': str(e)}

    def get_updated_qr_code(self):
        """Get updated QR code - called by JavaScript"""
        try:
            if self.sign_provider_code != 'bankid':
                return {'success': False, 'error': 'Not configured for BankID signing'}

            # Get current user's signer
            signer = self._get_current_user_signer()
            if not signer:
                return {'success': False, 'error': 'No signer found for current user'}

            qr_content = self.sign_provider_id._generate_bankid_qr_code(signer)
            return {'success': True, 'qrCode': qr_content}

        except Exception as e:
            _logger.error(f"Error in get_updated_qr_code: {str(e)}", exc_info=True)
            return {'success': False, 'error': str(e)}

    def cancel_bankid_sign(self):
        """Cancel BankID signing - called by JavaScript"""
        try:
            if self.sign_provider_code != 'bankid':
                return False

            # Get current user's signer
            signer = self._get_current_user_signer()
            if not signer:
                return False

            return self.sign_provider_id.cancel_bankid_sign(signer)

        except Exception as e:
            _logger.error(f"Error in cancel_bankid_sign: {str(e)}", exc_info=True)
            return False

    def _get_current_user_signer(self):
        """Get the signer for the current user"""
        user = self.env.user
        signer = self.signer_ids.filtered(lambda s: s.partner_id == user.partner_id)
        if signer:
            return signer[0]
        elif self.signer_ids:
            # If no match found, just return the first signer
            return self.signer_ids[0]
        return None


class VrtlSignRequestSigner(models.Model):
    _inherit = "vrtl.sign.request.signer"

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

    def write(self, vals):
        """Override write to add debugging"""
        _logger.info(f"Writing to signer {self.id}: {vals}")
        result = super().write(vals)
        _logger.info(f"Write completed for signer {self.id}")
        return result

    def sign_data(self, provider_sign_data):
        """Handle provider-specific signing for signer"""
        if self.sign_provider_code == 'bankid':
            return self._handle_bankid_sign_data(provider_sign_data)
        else:
            # Handle other providers or call parent method
            print(provider_sign_data)

    def _handle_bankid_sign_data(self, provider_sign_data):
        """Handle BankID specific sign data for signer"""
        if provider_sign_data.get('success'):
            # Use your existing BankID modal
            return {
                'type': 'ir.actions.client',
                'tag': 'bankid_sign_modal',
                'target': 'new',
                'context': {
                    'default_record_id': self.id,
                    'default_record_model': self._name,
                    'callback_method': '_on_signer_bankid_complete',
                    'order_ref': provider_sign_data.get('orderRef'),
                    'qr_code': provider_sign_data.get('qrCode'),
                    'auto_start_url': provider_sign_data.get('autoStartUrl'),
                }
            }
        else:
            raise UserError(
                _("Failed to initiate BankID signing: %s") % provider_sign_data.get('error', 'Unknown error'))

    def _on_signer_bankid_complete(self):
        """Callback method when signer completes BankID signing"""
        # This signer is now signed, check if request is fully signed
        self.request_id._check_signed()
        return True

    def check_bankid_status(self):
        """Check BankID status - called from frontend"""
        self.ensure_one()
        if self.sign_provider_code == 'bankid':
            return self.request_id.sign_provider_id.check_bankid_status(self)
        return {'status': 'failed', 'message': 'Not a BankID signer'}

    def cancel_bankid_sign(self):
        """Cancel BankID signing"""
        self.ensure_one()
        if self.sign_provider_code == 'bankid':
            return self.request_id.sign_provider_id.cancel_bankid_sign(self)
        return False

    def get_updated_qr_code(self):
        """Get updated QR code for BankID"""
        self.ensure_one()
        if self.sign_provider_code == 'bankid':
            qr_content = self.request_id.sign_provider_id._generate_bankid_qr_code(self)
            return {'success': True, 'qrCode': qr_content}
        return {'success': False, 'error': 'Not a BankID signer'}