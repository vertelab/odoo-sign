import time
from datetime import datetime

from odoo import fields, http, _, SUPERUSER_ID
from odoo.exceptions import AccessError, MissingError, ValidationError
from odoo.http import request
from odoo.tools import consteq

import logging

_logger = logging.getLogger(__name__)


class BankIDController(http.Controller):

    def _check_res_document_access(self, model_name, document_id, access_token=None):
        """Check if current user is allowed to access the specified record.

        :param str model_name: model of the requested record
        :param int document_id: id of the requested record
        :param str access_token: record token to check if user isn't allowed to read requested record
        :return: expected record, SUDOED, with SUPERUSER context
        :raise MissingError: record not found in database, might have been deleted
        :raise AccessError: current user isn't allowed to read requested document (and no valid token was given)
        """
        document = request.env[model_name].browse([document_id])
        document_sudo = document.with_user(SUPERUSER_ID).exists()
        if not document_sudo:
            raise MissingError(_("This document does not exist."))
        try:
            document.check_access('read')
        except AccessError:
            if not access_token or not document_sudo.access_token or not consteq(document_sudo.access_token,
                                                                                 access_token):
                raise
        return document_sudo

    @http.route(['/bankid/initialize'], type='json', auth="public", website=True)
    def bankid_initialize(self, res_id, res_model, ssn, access_token=None, **kw):
        """Initialize a BankID signing process"""
        try:
            _logger.info(f"BankID Initialize called: res_id={res_id}, res_model={res_model}")

            try:
                rec_sudo = self._check_res_document_access(res_model, res_id, access_token=access_token)
            except (AccessError, MissingError):
                return {'error': 'Access denied or document not found'}

            # Verify the model inherits from res.bankid
            if not hasattr(rec_sudo, 'bankid_order_ref'):
                return {'error': 'Model does not support BankID signing'}

            # Use the existing method from res.bankid abstract model
            result = rec_sudo.initiate_bankid_client()

            if result.get('success'):
                return {
                    'order_ref': result.get('orderRef'),
                    'auto_start_token': result.get(
                        'autoStartUrl', ''
                    ).replace('bankid:///?autostarttoken=', '').replace('&redirect=null', ''),
                    'qr_content': result.get('qrCode'),
                }
            else:
                return {'error': result.get('error', 'Failed to initialize BankID')}

        except Exception as e:
            _logger.error(f"Error in bankid_initialize: {e}", exc_info=True)
            return {'error': str(e)}

    @http.route(['/bankid/get_qr'], type='json', auth="public", website=True)
    def bankid_get_qr(self, res_id, res_model, ssn, access_token=None, **kw):
        """Get updated QR code content"""
        try:
            _logger.info(f"Getting QR code for: res_id={res_id}, res_model={res_model}")

            try:
                rec_sudo = self._check_res_document_access(res_model, res_id, access_token=access_token)
            except (AccessError, MissingError):
                return {'error': 'Access denied or document not found'}

            # Verify the model inherits from res.bankid
            if not hasattr(rec_sudo, 'get_updated_qr_code'):
                return {'error': 'Model does not support BankID signing'}

            # Use the existing method from res.bankid abstract model
            result = rec_sudo.get_updated_qr_code()

            if result.get('success'):
                return {'qr_content': result.get('qrCode')}
            else:
                return {'error': result.get('error', 'Failed to get QR code')}

        except Exception as e:
            _logger.error(f"Error in bankid_get_qr: {e}", exc_info=True)
            return {'error': str(e)}

    @http.route(['/bankid/collect'], type='json', auth="public", website=True)
    def bankid_collect(self, res_id, res_model, access_token=None, **kw):
        """Check the status of a BankID signing process"""
        try:
            _logger.info(f"Collecting BankID status for: res_id={res_id}, res_model={res_model}")

            try:
                rec_sudo = self._check_res_document_access(res_model, res_id, access_token=access_token)
            except (AccessError, MissingError):
                return {'status': 'error', 'message': 'Access denied or document not found'}

            # Verify the model inherits from res.bankid
            if not hasattr(rec_sudo, 'check_bankid_status'):
                return {'status': 'error', 'message': 'Model does not support BankID signing'}

            # Use the existing method from res.bankid abstract model
            return rec_sudo.check_bankid_status()

        except Exception as e:
            _logger.error(f"Error in bankid_collect: {e}", exc_info=True)
            return {'status': 'error', 'message': str(e)}

    @http.route('/bankid/cancel', type='json', auth='public')
    def bankid_cancel(self, order_ref, access_token=None, **kwargs):
        """Cancel the BankID signing process"""
        try:
            _logger.info(f"Cancelling BankID order: {order_ref}")

            # Find any record with this order ref that inherits from res.bankid
            # We'll search across common models that might inherit res.bankid
            models_to_search = ['sale.order', 'purchase.order', 'account.move']  # Add your models here

            rec_sudo = None
            for model in models_to_search:
                if request.env[model]._abstract or not hasattr(request.env[model], 'bankid_order_ref'):
                    continue

                rec_sudo = request.env[model].sudo().search([
                    ('bankid_order_ref', '=', order_ref)
                ], limit=1)

                if rec_sudo:
                    break

            if not rec_sudo:
                return {'error': 'Invalid order reference'}

            # Verify the model inherits from res.bankid
            if not hasattr(rec_sudo, 'cancel_bankid_sign'):
                return {'error': 'Model does not support BankID signing'}

            # Use the existing method from res.bankid abstract model
            result = rec_sudo.cancel_bankid_sign()
            return {'success': result}

        except Exception as e:
            _logger.error(f"Error in bankid_cancel: {e}", exc_info=True)
            return {'error': str(e)}