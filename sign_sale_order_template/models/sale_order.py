from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _sign_request_domain(self):
        record_ref = f"{self._name},{self.id}"
        return [('record_ref', '=', record_ref)]

    sign_request_id = fields.Many2one(
        'sign.oca.request', string="Sign Request", domain=_sign_request_domain, readonly=True, copy=False)
    signed_doc = fields.Binary(string="Signed", related="sign_request_id.data", copy=False)
    signer_ids = fields.One2many(related="sign_request_id.signer_ids", copy=False)

    @api.depends('signer_ids')
    def compute_sales_person_signer(self):
        for rec in self:
            if rec.signer_ids:
                sale_order_sale_person_signer_id = self.sign_request_id.signer_ids.filtered(
                    lambda signer: signer.partner_id.id == self.user_id.partner_id.id
                )
                if sale_order_sale_person_signer_id.signature:
                    rec.signed_by_sales_person = True
                else:
                    rec.signed_by_sales_person = False
            else:
                rec.signed_by_sales_person = False

    signed_by_sales_person = fields.Boolean(
        string="Signed by Salesperson", compute=compute_sales_person_signer, copy=False)

    def action_quotation_send(self):
        if not self.signed_by_sales_person:
            raise ValidationError(
                "The salesperson is yet to sign this quotation. Kindly sign before sending the quotation"
            )
        return super().action_quotation_send()

    def action_confirm(self):
        signer_signatures = self.signer_ids.mapped('signature')

        if not signer_signatures or not all(signer_signatures):
            raise ValidationError("You cannot confirm this order until all parties have signed")
        return super().action_confirm()

    def _prepare_sign_oca_request_vals(self):
        return self.sale_order_template_id.sign_template_id._prepare_sign_oca_request_vals_from_record(
            record=self
        )

    def action_generate_sign_request(self):
        if not self.sale_order_template_id:
            raise UserError("Select a quotation template before you sign the quotation")
        if self.sign_request_id:
            sign_request_id = self.sign_request_id
        else:
            sign_request_id = self.env["sign.oca.request"].create(
                self._prepare_sign_oca_request_vals()
            )
            sign_request_id.state = "sent"
            self.sign_request_id = sign_request_id.id
        return sign_request_id.sign()

    def action_update_sign_request(self):
        sale_order_partner_signer_id = self.sign_request_id.signer_ids.filtered(
            lambda signer: signer.partner_id.id == self.partner_id.id
        )

        info = self.sign_request_id.get_info()
        info_item = info.get("items")

        for key, value in info_item.items():
            if self.signature:
                if value.get('role_id') == sale_order_partner_signer_id.role_id.id:
                    value['value'] = f"data:image/png;base64,{self.signature.decode('utf-8')}"
            else:
                raise UserError("This document is not signed yet")
        sale_order_partner_signer_id.action_sign(info_item)



