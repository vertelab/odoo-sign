from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    sale_order_sign_template_id = fields.Many2one(
        comodel_name="sign.oca.template",
        related="company_id.sale_order_sign_template_id",
        string="Sale Order Sign Template",
        readonly=False,
    )