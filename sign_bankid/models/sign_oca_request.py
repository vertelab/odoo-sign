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

    bankid_order_ref = fields.Char("BankID Reference", copy=False, readonly=True)
    bankid_auto_start_token = fields.Char("BankID Auto Start Token", copy=False, readonly=True)
    bankid_qr_start_token = fields.Char("BankID QR Start Token", copy=False, readonly=True)
    bankid_qr_start_secret = fields.Char("BankID QR Start Secret", copy=False, readonly=True)
    bankid_qr_code_content = fields.Char("BankID QR Code Content", copy=False, readonly=True)
    bankid_start_time = fields.Datetime("BankID Start Time", copy=False, readonly=True)
    bankid_status = fields.Selection([
        ('pending', 'Pending'),
        ('complete', 'Complete'),
        ('failed', 'Failed')
    ], string="BankID Status", copy=False, default='pending', readonly=True)


    def _initiate_bankid_sign(self):
        for signer in self.signer_ids:
            signer._bankid_client_sign()


class SignOcaRequestSigner(models.Model):
    _inherit = "sign.oca.request.signer"

    bankid_order_ref = fields.Char("BankID Reference", copy=False, readonly=True)
    bankid_auto_start_token = fields.Char("BankID Auto Start Token", copy=False, readonly=True)
    bankid_qr_start_token = fields.Char("BankID QR Start Token", copy=False, readonly=True)
    bankid_qr_start_secret = fields.Char("BankID QR Start Secret", copy=False, readonly=True)
    bankid_qr_code_content = fields.Char("BankID QR Code Content", copy=False, readonly=True)
    bankid_start_time = fields.Datetime("BankID Start Time", copy=False, readonly=True)
    bankid_status = fields.Selection([
        ('pending', 'Pending'),
        ('complete', 'Complete'),
        ('failed', 'Failed')
    ], string="BankID Status", copy=False, default='pending', readonly=True)

    # metadata
    bankid_signed_name = fields.Char("Signed Name from BankID")
    bankid_signed_personal_number = fields.Char("Signed Personal Number")
    bankid_signed_given_name = fields.Char("Signed Given Name")
    bankid_signed_surname = fields.Char("Signed Surname")
    bankid_device_ip = fields.Char("Device IP Address")
    bankid_issue_date = fields.Date("BankID Issue Date")
    bankid_signature = fields.Binary("BankID Signature (Base64)")
    bankid_ocsp_response = fields.Binary("OCSP Response (Base64)")
    signed_date = fields.Datetime("Date Signed")

    bankid_final_pdf = fields.Binary("Final PDF")

    def get_info(self, access_token=False):
        self.ensure_one()
        self._set_action_log("view", access_token=access_token)
        return {
            "role_id": self.role_id.id if not self.signed_on else False,
            "name": self.request_id.template_id.name,
            "items": self.request_id.signatory_data,
            "to_sign": self.request_id.to_sign,
            "ask_location": self.request_id.ask_location,
            "partner": {
                "id": self.partner_id.id,
                "name": self.partner_id.name,
                "email": self.partner_id.email,
                "phone": self.partner_id.phone,
            },
            "signing_option": self.request_id.signing_option,
            "res_model": self.model,
            "res_id": self.res_id,
            "access_token": self.access_token,
            "document_id": self.id
        }

    def _bankid_client_sign(self):
        client = self.env.company.bank_id_client()

        response = client.sign(
            end_user_ip='0.0.0.0',
            user_visible_data="The information to sign."
        )

        self.bankid_order_ref = response.get("orderRef")
        self.bankid_auto_start_token = response.get("autoStartToken")
        self.bankid_qr_start_token = response.get("qrStartToken")
        self.bankid_qr_start_secret = response.get("qrStartSecret")

    def _process_bankid_completion(self, collect_response):
        completion_data = collect_response.get("completionData", {})
        user_info = completion_data.get("user", {})
        device_info = completion_data.get("device", {})

        bankid_response = {
            'bankid_signed_name': user_info.get('name'),
            'bankid_signed_personal_number': user_info.get('personalNumber'),
            'bankid_signed_given_name': user_info.get('givenName'),
            'bankid_signed_surname': user_info.get('surname'),
            'bankid_device_ip': device_info.get('ipAddress'),
            'bankid_issue_date': completion_data.get('bankIdIssueDate'),
            'bankid_signature': completion_data.get('signature'),
            'bankid_ocsp_response': completion_data.get('ocspResponse'),
            'signed_date': fields.Datetime.now(),
        }
        self.write(bankid_response)

        self.write({'bankid_status': 'complete'})

        # self.save_signature_image()

        self.signature = self.generate_signature_block_image()

    def generate_signature_block_image(self):
        """Generate a signature block image for this signer"""
        from PIL import Image, ImageDraw, ImageFont
        import io
        import base64

        # Image dimensions (signature block size)
        width, height = 400, 150

        # Create white background
        image = Image.new('RGB', (width, height), color='white')
        draw = ImageDraw.Draw(image)

        # Try to load fonts (fallback to default)
        try:
            title_font = ImageFont.truetype("arial.ttf", 14)
            text_font = ImageFont.truetype("arial.ttf", 11)
        except:
            title_font = ImageFont.load_default()
            text_font = ImageFont.load_default()

        # Colors
        blue = '#1e3a8a'
        black = '#000000'
        gray = '#666666'

        # Draw border
        draw.rectangle([(0, 0), (width - 1, height - 1)], outline=blue, width=2)

        # Title
        y_pos = 10
        draw.text((10, y_pos), "Signerad av", fill=blue, font=title_font)

        # Signature details
        y_pos += 25
        signature_details = [
            f"Roll: {self.partner_id.function or 'Undertecknare'}",
            f"Kontonamn: {self.bankid_signed_name or 'N/A'}",
            f"Datum och tid: {self.signed_date.strftime('%Y-%m-%d %H:%M:%S UTC') if self.signed_date else 'N/A'}",
            f"Transaktions-ID: {self.bankid_order_ref[:32] if self.bankid_order_ref else 'N/A'}..."
        ]

        for detail in signature_details:
            draw.text((10, y_pos), detail, fill=black, font=text_font)
            y_pos += 18

        # Convert to base64
        buffer = io.BytesIO()
        image.save(buffer, format='PNG')
        image_data = base64.b64encode(buffer.getvalue())

        return image_data


    # def append_signature_page_to_pdf(self, original_pdf_data):
    #     """Append signature page to existing PDF"""
    #     from reportlab.pdfgen import canvas
    #     from reportlab.lib.pagesizes import A4
    #     from reportlab.lib.colors import HexColor
    #     from PyPDF2 import PdfWriter, PdfReader
    #     import io
    #     import base64
    #
    #     # Create signature page as PDF
    #     buffer = io.BytesIO()
    #     p = canvas.Canvas(buffer, pagesize=A4)
    #     width, height = A4
    #
    #     # Title
    #     p.setFont("Helvetica-Bold", 20)
    #     p.setFillColor(HexColor('#1e3a8a'))
    #
    #     # Calculate center position for text
    #     title_text = "DIGITAL SIGNATURE CERTIFICATE"
    #     text_width = p.stringWidth(title_text, "Helvetica-Bold", 20)
    #     p.drawString((width - text_width) / 2, height - 100, title_text)
    #
    #     # Draw line
    #     p.setStrokeColor(HexColor('#1e3a8a'))
    #     p.setLineWidth(2)
    #     p.line(50, height - 130, width - 50, height - 130)
    #
    #     # Signature details
    #     y_pos = height - 200
    #     p.setFont("Helvetica-Bold", 12)
    #     p.setFillColor(HexColor('#6b7280'))
    #
    #     # Add each field
    #     fields = [
    #         ("SIGNED BY:", self.bankid_signed_name or "N/A"),
    #         ("PERSONAL NUMBER:", self.bankid_signed_personal_number or "N/A"),
    #         ("SIGNATURE DATE:", self.signed_date.strftime('%Y-%m-%d %H:%M:%S') if self.signed_date else "N/A"),
    #         ("SIGNATURE METHOD:", "BankID Digital Signature"),
    #         ("DEVICE IP ADDRESS:", self.bankid_device_ip or "N/A"),
    #         ("BANKID ISSUE DATE:", self.bankid_issue_date or "N/A"),
    #         ("VERIFICATION REFERENCE:", self.bankid_order_ref or "N/A")
    #     ]
    #
    #     for label, value in fields:
    #         p.drawString(70, y_pos, label)
    #         p.setFont("Helvetica", 12)
    #         p.setFillColor(HexColor('#000000'))
    #         p.drawString(90, y_pos - 20, str(value))
    #         p.setFont("Helvetica-Bold", 12)
    #         p.setFillColor(HexColor('#6b7280'))
    #         y_pos -= 60
    #
    #     # Bottom text (centered)
    #     p.setFont("Helvetica-Bold", 14)
    #     p.setFillColor(HexColor('#059669'))
    #
    #     bottom_text = "This document has been digitally signed using BankID"
    #     text_width = p.stringWidth(bottom_text, "Helvetica-Bold", 14)
    #     p.drawString((width - text_width) / 2, 150, bottom_text)
    #
    #     p.setFont("Helvetica", 10)
    #     p.setFillColor(HexColor('#6b7280'))
    #
    #     subtitle_text = "The signature is cryptographically verified and legally binding"
    #     text_width = p.stringWidth(subtitle_text, "Helvetica", 10)
    #     p.drawString((width - text_width) / 2, 130, subtitle_text)
    #
    #     p.showPage()
    #     p.save()
    #
    #     # Get the signature page PDF
    #     signature_pdf = buffer.getvalue()
    #     buffer.close()
    #
    #     # Merge with original PDF
    #     original_pdf = io.BytesIO(base64.b64decode(original_pdf_data))
    #
    #     writer = PdfWriter()
    #
    #     # Add all pages from original PDF
    #     reader = PdfReader(original_pdf)
    #     for page in reader.pages:
    #         writer.add_page(page)
    #
    #     # Add signature page
    #     signature_reader = PdfReader(io.BytesIO(signature_pdf))
    #     writer.add_page(signature_reader.pages[0])
    #
    #     # Output final PDF
    #     final_buffer = io.BytesIO()
    #     writer.write(final_buffer)
    #     final_pdf_data = base64.b64encode(final_buffer.getvalue())
    #     final_buffer.close()
    #
    #     return final_pdf_data

    # Store as Binary field
    # signature_page_image = fields.Binary("Signature Page Image")