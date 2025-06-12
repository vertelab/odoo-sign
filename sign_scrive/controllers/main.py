import time
from datetime import datetime

from odoo import fields, http, _, SUPERUSER_ID
from odoo.exceptions import AccessError, MissingError, ValidationError
from odoo.http import request
from odoo.tools import consteq

import logging

_logger = logging.getLogger(__name__)


class ScriveController(http.Controller):

    _callback_url = '/sign/scrive/callback'

    @http.route(['/scrive/callback'], type='http', auth="public", website=True, csrf=False)
    def scrive_callback(self, **kw):
        """Initialize a BankID signing process"""
        try:
            print("callback", request.httprequest.args)
            print("kw", kw)
            # _logger.info(f"BankID Initialize called: res_id={res_id}, res_model={res_model}")
            #
            try:
                rec_sudo = request.env['sale.order'].sudo().search([
                    ('scrive_document_id', '=', kw.get('document_id'))
                ])
            except (AccessError, MissingError):
                return {'error': 'Access denied or document not found'}

            # # Verify the model inherits from res.bankid
            # if not hasattr(rec_sudo, 'bankid_order_ref'):
            #     return {'error': 'Model does not support BankID signing'}
            #
            # # Use the existing method from res.bankid abstract model
            # result = rec_sudo.initiate_bankid_client()
            #
            # if result.get('success'):
            #     return {
            #         'order_ref': result.get('orderRef'),
            #         'auto_start_token': result.get('autoStartUrl', '').replace('bankid:///?autostarttoken=',
            #                                                                    '').replace('&redirect=null', ''),
            #         'qr_content': result.get('qrCode'),
            #     }
            # else:
            #     return {'error': result.get('error', 'Failed to initialize BankID')}

        except Exception as e:
            _logger.error(f"Error in bankid_initialize: {e}", exc_info=True)
            return {'error': str(e)}

