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

    @http.route([_callback_url], type='http', auth="public", website=True, csrf=False)
    def scrive_callback(self, **kw):
        """Handle Scrive callback webhook"""
        try:
            _logger.info(f"Scrive callback received: {kw}")

            document_id = kw.get('document_id')
            if not document_id:
                _logger.error("No document_id in callback")
                return self._callback_response({'error': 'Missing document_id'}, status=400)

            # Find the sign request by document_id
            sign_request = self._find_sign_request_by_document_id(document_id)
            if not sign_request:
                _logger.error(f"No sign request found for document_id: {document_id}")
                return self._callback_response({'error': 'Sign request not found'}, status=404)

            # Process the callback using the provider
            try:
                result = sign_request.sign_provider_id.process_scrive_callback(sign_request, kw)
                _logger.info(f"Callback processed successfully for document {document_id}")
                return self._callback_response({'status': 'success', 'result': result})

            except Exception as e:
                _logger.error(f"Error processing callback for document {document_id}: {e}", exc_info=True)
                return self._callback_response({'error': f'Processing failed: {str(e)}'}, status=500)

        except Exception as e:
            _logger.error(f"Error in scrive_callback: {e}", exc_info=True)
            return self._callback_response({'error': str(e)}, status=500)

    def _find_sign_request_by_document_id(self, document_id):
        """Find sign request by Scrive document ID"""
        try:
            # Search using the scrive_document_id field you added to the model
            sign_request = request.env['vrtl.sign.request'].sudo().search([
                ('scrive_document_id', '=', document_id)
            ], limit=1)

            if sign_request:
                return sign_request

            return None

        except (AccessError, MissingError) as e:
            _logger.error(f"Access error finding sign request: {e}")
            return None

    def _callback_response(self, data, status=200):
        """Return a properly formatted response"""
        response = request.make_response(
            data if isinstance(data, str) else str(data),
            headers=[('Content-Type', 'application/json')]
        )
        response.status_code = status
        return response