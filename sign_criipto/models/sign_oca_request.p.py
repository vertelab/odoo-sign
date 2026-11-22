import hashlib
import json
import logging
import base64
import traceback
from base64 import b64decode, b64encode
from hashlib import sha256
from io import BytesIO

from PyPDF2 import PdfFileReader, PdfFileWriter
from reportlab.graphics.shapes import Drawing, Line, Rect
from reportlab.lib.colors import black, transparent
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfgen import canvas
from reportlab.platypus import Image, Paragraph

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.http import request
from odoo.tools import float_repr

_logger = logging.getLogger(__name__)


class SignOcaRequest(models.Model):
    _inherit = "sign.oca.request"

    criipto_signature_order_id = fields.Char(string="Criipto Signature Order ID", readonly=True)

    def _action_initiate_signature(self):
        self.ensure_one()

        if not self.signer_ids:
            raise UserError(_("Please add at least one signatory before requesting signatures."))

        try:
            # Get the client
            client = self.env.company.get_criipto_client()

            pdf_base64 = base64.b64decode(self.data)

            # At this point, self.signed_doc is a valid base64-encoded PDF
            # Create the signature order
            signature_order = client.create_signature_order({
                'title': self.name,
                'documents': [
                    {
                        'pdf': {
                            'title': self.name,
                            'blob': pdf_base64,  # Use directly, it's already base64
                            'storageMode': 'Temporary'
                        }
                    }
                ]
            })

            self.criipto_signature_order_id = signature_order['id']
            self._add_signers_to_signature_order(signature_order=signature_order, client=client)

        except Exception as e:
            _logger.error(f"Failed to create signature request: {str(e)}")
            _logger.error(f"Traceback: {traceback.format_exc()}")
            return None

    def _add_signers_to_signature_order(self, signature_order, client):
        for signer in self.signer_ids:
            signer_data = {
                'name': signer.partner_id.name,
                'role': signer.role_id.name,
            }
            signer_signature = client.add_signatory(signature_order['id'], signer_data)
            signer.write({
                'criipto_signature_id': signer_signature['id'],
                'criipto_signature_url': signer_signature['href'],
            })

    def action_poll_signature_status(self):
        """Poll for signature status updates"""
        self.ensure_one()

        if not self.criipto_signature_order_id:
            return

        try:
            # Get the client
            client = self.env.company.get_criipto_client()

            # Query the signature order
            signature_order = client.query_signature_order(self.criipto_signature_order_id)

            print(signature_order)

            # if not signature_order:
            #     return
            #
            # # Update the status of each signatory
            # api_signatories = {s['id']: s for s in signature_order['signatories']}
            #
            # for signatory in self.signatory_ids:
            #     if signatory.signatory_id in api_signatories:
            #         api_status = api_signatories[signatory.signatory_id]['status']
            #
            #         # Map API status to our status
            #         if api_status == 'SIGNED' and signatory.status != 'signed':
            #             signatory.status = 'signed'
            #         elif api_status == 'REJECTED' and signatory.status != 'rejected':
            #             signatory.status = 'rejected'
            #         elif api_status == 'ERROR' and signatory.status != 'error':
            #             signatory.status = 'error'
            #
            # # Check if all signatories have signed
            # all_signed = all(s.status == 'signed' for s in self.signatory_ids)
            # if all_signed and self.signature_status != 'signed':
            #     # All signatories have signed, trigger appropriate actions
            #     pass

        except Exception as e:
            _logger.error(f"Error polling signature status: {str(e)}")

    def action_view_current_document(self):
        """View the document in its current state (with any signatures applied so far)"""
        self.ensure_one()

        if not self.criipto_signature_order_id:
            raise UserError(_("No signature order found for this sale order."))

        try:
            # Get the client
            client = self.env.company.get_criipto_client()

            # Query the signature order with documents
            signature_order = client.query_signature_order(self.criipto_signature_order_id, include_documents=True)

            if not signature_order:
                raise UserError(_("Signature order not found."))

            # Check if the documents have blobs
            documents_with_blobs = [doc for doc in signature_order.get('documents', []) if doc.get('blob')]

            if not documents_with_blobs:
                raise UserError(_("No document content found in the signature order."))

            # Save the current state of each document as a temporary attachment
            attachment_ids = []
            for i, document in enumerate(documents_with_blobs):
                # Create a name for the attachment
                doc_name = document.get('title') or f"{self.name} - Current State"
                if len(documents_with_blobs) > 1:
                    doc_name += f" ({i + 1})"
                if not doc_name.lower().endswith('.pdf'):
                    doc_name += ".pdf"

                # Add a timestamp to avoid name conflicts
                from datetime import datetime
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                doc_name = f"{doc_name.split('.')[0]}_{timestamp}.pdf"

                # Create a temporary attachment
                attachment = self.env['ir.attachment'].create({
                    'name': doc_name,
                    'datas': document['blob'],  # The API should return this as base64
                    'res_model': self._name,
                    'res_id': self.id,
                    'mimetype': 'application/pdf',
                    # Optional: Mark as temporary if you don't want to keep these previews
                    # 'temporary': True,
                })

                attachment_ids.append(attachment.id)

            # If there's only one document, open it directly
            if len(attachment_ids) == 1:
                return {
                    'type': 'ir.actions.act_url',
                    'url': f'/web/content/{attachment_ids[0]}?download=true',
                    'target': 'new',
                }

            # If there are multiple documents, show a notification with links
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Documents'),
                    'message': _('Current document state retrieved. Click the links below to view them:'),
                    'links': [
                        {
                            'label': _('Document %d', i + 1),
                            'url': f'/web/content/{attachment_id}?download=true'
                        } for i, attachment_id in enumerate(attachment_ids)
                    ],
                    'sticky': True,
                    'type': 'info',
                }
            }

        except Exception as e:
            _logger.error(f"Failed to retrieve current document state: {str(e)}")
            _logger.error(f"Traceback: {traceback.format_exc()}")
            raise UserError(_("Failed to retrieve current document state: %s") % str(e))


class SignOcaRequestSigner(models.Model):
    _inherit = "sign.oca.request.signer"

    criipto_signature_id = fields.Char(string="Criipto Signature ID", readonly=True)
    criipto_signature_url = fields.Char(string="Criipto Signature URL", readonly=True)



