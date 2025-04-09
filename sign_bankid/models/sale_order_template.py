from odoo import models, fields, api, _


class SignOcaTemplate(models.Model):
    _inherit = "sign.oca.template"

    signing_option = fields.Selection(selection_add=[('bankid', 'Bank ID')], ondelete={'bankid': 'cascade'})
