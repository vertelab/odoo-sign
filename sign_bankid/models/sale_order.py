import json
import base64
import httpx
import requests
from datetime import datetime
from odoo import models, fields, api, _



class SaleOrder(models.Model):
    _inherit = "sale.order"


    def initiate_bankid_sign(self):
        client = self.bank_id_client()
        response = client.sign(
            end_user_ip='0.0.0.0',
            user_visible_data="The information to sign."
        )
        print(response)

        self.bankid_order_ref = response.get("orderRef")
        self.bankid_auto_start_token = response.get("autoStartToken")
        self.bankid_qr_start_token = response.get("qrStartToken")
        self.bankid_qr_start_secret = response.get("qrStartSecret")

        # auto_start_url = self._generate_bankid_auto_start_url(response.get("autoStartToken"))
        self.bankid_qr_code_content = client.generate_qr_code_content(
            response.get("qrStartToken"),
            datetime.now(),
            response.get("qrStartSecret")
        )


    def _generate_bankid_auto_start_url(self, auto_start_token):
        """Generate URL to launch BankID app on devices with the app installed"""
        return f"bankid:///?autostarttoken={auto_start_token}&redirect=null"

    def generate_bankid_qr_code(self):
        """Generate QR code content for BankID scanning"""
        if not all([self.bankid_qr_start_token, self.bankid_qr_start_secret, self.bankid_start_time]):
            return ""

        client = self.bank_id_client()

        # Convert start_time to timestamp
        if isinstance(self.bankid_start_time, datetime):
            start_timestamp = self.bankid_start_time.timestamp()
        else:
            # If not datetime, assume it's a timestamp already
            start_timestamp = float(self.bankid_start_time)

        # Generate QR code content
        return client.generate_qr_code_content(
            self.bankid_qr_start_token,
            start_timestamp,
            self.bankid_qr_start_secret
        )

    def cancel_bankid_sign(self):
        """Cancel an ongoing BankID signing process"""
        if not self.bankid_order_ref or self.bankid_status != 'pending':
            return False

        client = self.bank_id_client()

        try:
            # Cancel the order
            result = client.cancel(self.bankid_order_ref)
            if result:
                self.bankid_status = 'failed'
                self.message_post(
                    body=_("BankID signing was cancelled"),
                    subtype_xmlid="mail.mt_note"
                )
            return result
        except Exception as e:
            self.message_post(
                body=_(f"Error cancelling BankID signing: {str(e)}"),
                subtype_xmlid="mail.mt_note"
            )
            return False