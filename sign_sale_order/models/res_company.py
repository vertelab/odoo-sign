from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    sale_order_sign_template_id = fields.Many2one(
        comodel_name="sign.oca.template",
        domain="[('model_id.model', '=', 'sale.order')]",
        string="Sale Order Sign Template",
    )