import requests
import json
from base64 import b64decode, b64encode
from urllib.parse import quote
from odoo import models, fields, api
from odoo.addons.sign_scrive.controllers.main import ScriveController
from werkzeug.urls import url_encode, url_join, url_parse
from odoo.exceptions import ValidationError


class BankIDSignProvider(models.Model):
    _inherit = "sign.provider"

    code = fields.Selection(
        selection_add=[('bankid', "Bank ID")], ondelete={'bankid': 'set default'})

    cert_file = fields.Binary(string="Cert")