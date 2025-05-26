import time
from datetime import datetime

from odoo import fields, http, _
from odoo.exceptions import AccessError, MissingError, ValidationError
from odoo.http import request

from bankid import BankIDClient
from bankid.exceptions import BankIDError
from bankid.certutils import resolve_cert_path

import logging


class BankIDController(http.Controller):

    def _get_and_validate_signer(self, document_id, ssn, access_token):
        """Get the signer directly and validate access"""
        try:
            # Get the signer document directly
            signer = request.env['sign.oca.request.signer'].sudo().browse(document_id)
            print(signer.partner_id.name)

            if not signer.exists():
                return None, _("Invalid signing document.")

            # Validate access token
            if signer.access_token != access_token:
                return None, _("Invalid access token.")

            # Validate SSN matches
            if signer.partner_id.social_sec_nr != ssn:
                return None, _("You are not authorized to sign this document with the provided personal number.")

            # Check if already signed
            if signer.signed_on:
                return None, _("This document has already been signed.")

            return signer, None

        except Exception as e:
            return None, str(e)

    @http.route(['/bankid/initialize'], type='json', auth="public", website=True)
    def bankid_initialize(self, document_id, ssn, access_token=None, **kw):
        """Initialize a BankID signing process"""
        try:
            # Get and validate signer
            signer, error = self._get_and_validate_signer(document_id, ssn, access_token)
            print(signer, error)
            if error:
                return {'error': error}

            client = request.env.company.bank_id_client()

            # Check if already initialized and not expired/failed
            if signer.bankid_order_ref and signer.bankid_status == 'pending':
                try:
                    collect_response = client.collect(signer.bankid_order_ref)
                    if collect_response.get("status") == "pending":
                        # Still valid, return existing info
                        qr_content = client.generate_qr_code_content(
                            signer.bankid_qr_start_token,
                            time.time(),
                            signer.bankid_qr_start_secret
                        )
                        return {
                            'order_ref': signer.bankid_order_ref,
                            'auto_start_token': signer.bankid_auto_start_token,
                            'qr_content': qr_content
                        }
                except:
                    # Error or expired, continue with new initialization
                    pass

            # Get end user IP
            end_user_ip = request.httprequest.remote_addr

            # Create text to be signed - use the related document's info
            record_name = f"{signer.model} #{signer.res_id}"
            if signer.model and signer.res_id:
                try:
                    record = request.env[signer.model].sudo().browse(signer.res_id)
                    if record.exists():
                        record_name = record.display_name
                except:
                    pass

            user_visible_data = f"Sign document: {record_name}"

            try:
                # Make the sign request
                response = client.sign(
                    end_user_ip=end_user_ip,
                    user_visible_data=user_visible_data
                )

                # Store the response data
                signer.write({
                    'bankid_order_ref': response.get("orderRef"),
                    'bankid_auto_start_token': response.get("autoStartToken"),
                    'bankid_qr_start_token': response.get("qrStartToken"),
                    'bankid_qr_start_secret': response.get("qrStartSecret"),
                    'bankid_start_time': fields.Datetime.now(),
                    'bankid_status': 'pending'
                })

                # Generate initial QR code content
                qr_content = client.generate_qr_code_content(
                    response.get("qrStartToken"),
                    time.time(),
                    response.get("qrStartSecret")
                )

                return {
                    'order_ref': response.get("orderRef"),
                    'auto_start_token': response.get("autoStartToken"),
                    'qr_content': qr_content,
                }

            except Exception as e:
                return {'error': str(e)}

        except Exception as e:
            return {'error': str(e)}

    @http.route(['/bankid/get_qr'], type='json', auth="public", website=True)
    def bankid_get_qr(self, order_ref, access_token=None, **kw):
        """Get updated QR code content"""
        signer = request.env['sign.oca.request.signer'].sudo().search([
            ('bankid_order_ref', '=', order_ref)
        ], limit=1)

        if not signer:
            return {'error': 'Invalid order reference'}

        client = request.env.company.bank_id_client()

        # Use the original start time as reference
        if signer.bankid_start_time:
            reference_time = signer.bankid_start_time.timestamp()
        else:
            reference_time = time.time()

        qr_content = client.generate_qr_code_content(
            signer.bankid_qr_start_token,
            reference_time,
            signer.bankid_qr_start_secret
        )

        return {'qr_content': qr_content}

    @http.route(['/bankid/collect'], type='json', auth="public", website=True)
    def bankid_collect(self, order_ref, access_token=None, **kw):
        """Check the status of a BankID signing process"""
        signer = request.env['sign.oca.request.signer'].sudo().search([
            ('bankid_order_ref', '=', order_ref)
        ], limit=1)

        if not signer:
            return {'status': 'error', 'message': 'Invalid order reference'}

        client = request.env.company.bank_id_client()

        try:
            collect_response = client.collect(signer.bankid_order_ref)

            # Update the signer status
            if collect_response.get("status") == "complete":
                collect_response['completionData']['user']['role'] = signer.role_id.name
                print("collect_response", collect_response)
                signer._process_bankid_completion(collect_response)
            elif collect_response.get("status") == "failed":
                signer.write({'bankid_status': 'failed'})

            return collect_response
        except BankIDError as e:
            return {'status': 'error', 'message': str(e)}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    @http.route('/bankid/cancel', type='json', auth='public')
    def bankid_cancel(self, order_ref, access_token=None, **kwargs):
        """Cancel the BankID signing process"""
        signer = request.env['sign.oca.request.signer'].sudo().search([
            ('bankid_order_ref', '=', order_ref)
        ], limit=1)

        if not signer:
            return {'error': 'Invalid order reference'}

        try:
            client = request.env.company.bank_id_client()
            client.cancel(order_ref)

            signer.write({
                'bankid_status': 'cancelled',
                'bankid_order_ref': False
            })

            return {'success': True}
        except Exception as e:
            return {'error': str(e)}