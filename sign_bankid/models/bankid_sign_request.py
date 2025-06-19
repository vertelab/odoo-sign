import requests
import base64
import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.http import request
from odoo.tools import float_repr

_logger = logging.getLogger(__name__)


class BankIDSignRequest(models.Model):
    _inherit = "vrtl.sign.request"

    bankid_order_ref = fields.Char("BankID Reference", copy=False, readonly=True)
    bankid_auto_start_token = fields.Char("BankID Auto Start Token", copy=False, readonly=True)


class BankIDSignRequestSinger(models.Model):
    _inherit = "vrtl.sign.request.signer"

