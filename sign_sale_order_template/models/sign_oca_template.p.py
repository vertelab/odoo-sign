from odoo import api, fields, models


class SignOcaTemplate(models.Model):
    _inherit = "sign.oca.template"

    signing_option = fields.Selection([
        ('internal', 'Internal')], string="Signing Option", default='internal')
    data = fields.Binary(attachment=True, required=False)
