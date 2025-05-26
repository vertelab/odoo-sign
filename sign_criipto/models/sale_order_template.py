from odoo import models, fields, api, _


class SignOcaTemplate(models.Model):
    _inherit = "sign.oca.template"

    signing_option = fields.Selection(selection_add=[('criipto', 'Criipto')], ondelete={'criipto': 'cascade'})
