from odoo import api, fields, models
from odoo.tools import config
import base64
from odoo.tools.safe_eval import safe_eval


class SignOcaTemplate(models.Model):
    _inherit = "sign.oca.template"

    report_template = fields.Many2one('ir.actions.report', string="Report Template")

    def get_report_data(self, record):
        if self.report_template:
            report_content, report_format = self.env['ir.actions.report']._render_qweb_pdf(
                self.report_template.report_name, res_ids=record.ids
            )
            return base64.b64encode(report_content)
        else:
            return self.data

    def _prepare_sign_oca_request_vals_from_record(self, record):
        roles = self.mapped("item_ids.role_id").filtered(
            lambda role: role.partner_selection_policy != "empty"
        )

        return {
            "name": self.name,
            "template_id": self.id,
            "record_ref": "%s,%s" % (record._name, record.id),
            "signatory_data": self._get_signatory_data(),
            "data":  self.get_report_data(record),
            "signer_ids": [
                (
                    0,
                    0,
                    {
                        "partner_id": role._get_partner_from_record(record),
                        "role_id": role.id,
                    },
                )
                for role in roles
            ],
        }


class SignOcaRole(models.Model):
    _inherit = "sign.oca.role"

    def _get_partner_from_record(self, record):
        partner = self.default_partner_id.id or False
        if self.partner_selection_policy == "expression" and record:
            res = safe_eval(
                self.expression_partner,
                {
                    'object': self.env[record._name].browse(record.ids),
                }
            )
            # res = self.env["mail.render.mixin"]._render_template(
            #     self.expression_partner, record._name, record.ids
            # )[record.id]
            partner = int(res) if res else False
        return partner
