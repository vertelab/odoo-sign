import secrets
import base64
import logging
import urllib.parse
import requests
import werkzeug
from odoo import models, fields, api, _
from odoo.http import request
from odoo.exceptions import UserError
from bankid import BankIDClient

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = 'res.company'

    def _bankid_credentials(self):
        appapi_test = "/home/ayomir/Downloads/pybankid/bankid/certs/appapi2.test.bankid.com.pem"
        cert_file = "/home/ayomir/Downloads/pybankid/bankid/certs/FPTestcert5_20240610_cert.pem"
        key_file = "/home/ayomir/Downloads/pybankid/bankid/certs/FPTestcert5_20240610_key.pem"
        return cert_file, key_file, appapi_test

    def bank_id_client(self):
        cert_file, key_file, appapi_test = self._bankid_credentials()
        client = BankIDClient(certificates=(
            cert_file,
            key_file
        ), test_server=True)
        return client
