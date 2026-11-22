import logging

import pytz

from odoo import api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class TierReview(models.Model):
    _inherit = "tier.review"

    bankid_order_ref = fields.Char("BankID Reference", copy=False, readonly=True)

    bankid_status = fields.Selection([
        ('pending', 'Pending'),
        ('complete', 'Complete'),
        ('failed', 'Failed')
    ], string="BankID Status", copy=False, default='pending', readonly=True)

    signed_user_id = fields.Many2one(
        "res.users", string="Signing User", readonly=True, default=lambda self: self.env.user
    )
    signed_partner_id = fields.Many2one(
        "res.partner",
        string="Signing Partner",
        related='signed_user_id.partner_id',
        store=True, readonly=True)

    bankid_signed_name = fields.Char("Signed Name from BankID", readonly=True)
    bankid_signed_personal_number = fields.Char("Signed Personal Number", readonly=True)
    bankid_signed_given_name = fields.Char("Signed Given Name", readonly=True)
    bankid_signed_surname = fields.Char("Signed Surname", readonly=True)
    bankid_device_ip = fields.Char("Device IP Address", readonly=True)
    bankid_issue_date = fields.Date("BankID Issue Date", readonly=True)
    bankid_signature = fields.Binary("BankID Signature (Base64)", readonly=True)
    bankid_ocsp_response = fields.Binary("OCSP Response (Base64)", readonly=True)
    signed_date = fields.Datetime("Date Signed", readonly=True)
