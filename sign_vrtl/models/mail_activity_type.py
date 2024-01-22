# -*- coding: utf-8 -*-

from odoo import models, fields


class MailActivityType(models.Model):
    _inherit = "mail.activity.type"

    category = fields.Selection(selection_add=[('sign_request', 'Request Signature'),], ondelete={'sign_request': 'set default'})
