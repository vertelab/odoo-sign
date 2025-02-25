from odoo import models, fields, api, _


class SaleOrderTemplate(models.Model):
    _inherit = "sale.order.template"

    sign_template_id = fields.Many2one('sign.oca.template', string="Sign Template")
