import hashlib
import json
import logging
from base64 import b64decode, b64encode
from hashlib import sha256
from io import BytesIO

from PyPDF2 import PdfFileReader, PdfFileWriter
from reportlab.graphics.shapes import Drawing, Line, Rect
from reportlab.lib.colors import black, transparent
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfgen import canvas
from reportlab.platypus import Image, Paragraph

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.http import request
from odoo.tools import float_repr

_logger = logging.getLogger(__name__)

class SignOcaRequest(models.Model):
    _inherit = "sign.oca.request"

    signing_option = fields.Selection(related='template_id.signing_option')

    def _initiate_sign(self):
        """Generic signing initiator"""
        if not self.signing_option:
            raise UserError("Please select a signature method")

        method_name = f'_initiate_{self.signing_option}_sign'

        if hasattr(self, method_name):
            method = getattr(self, method_name)
            return method()
        else:
            return None


class SignOcaRequestSigner(models.Model):
    _inherit = "sign.oca.request.signer"

    signing_option = fields.Selection(related='request_id.signing_option')

    signature = fields.Binary(string="Signature")

    def _get_pdf_page_signature(self, item, box):
        import base64
        packet = BytesIO()
        can = canvas.Canvas(packet, pagesize=(box.getWidth(), box.getHeight()))
        if not item["value"]:
            return False
        try:
            base64_str = item["value"]
            if len(base64_str) % 4:
                base64_str += "=" * (4 - len(base64_str) % 4)
            if "," in base64_str:
                base64_str = item["value"].split(",")[1]
            image_data = b64decode(base64_str)
            self.signature = base64_str

            par = Image(
                BytesIO(image_data),
                width=item["width"] / 100 * float(box.getWidth()),
                height=item["height"] / 100 * float(box.getHeight()),
            )
            par.drawOn(
                can,
                item["position_x"] / 100 * float(box.getWidth()),
                (100 - item["position_y"] - item["height"])
                / 100
                * float(box.getHeight()),
            )
        except Exception as e:
            _logger.info(f"Error decoding Base64 string: {e}")
            return False
        can.save()
        packet.seek(0)
        new_pdf = PdfFileReader(packet)
        return new_pdf.getPage(0)
