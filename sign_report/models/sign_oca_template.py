from odoo import api, fields, models
from odoo.tools import config
import base64


class SignOcaTemplate(models.Model):
    _inherit = "sign.oca.template"

    report_template = fields.Many2one('ir.actions.report', string="Report Template")

    def get_report_data(self, record):
        if self.report_template:
            report = self.env['ir.actions.report']._get_report_from_name(self.report_template.report_name)
            pdf_content, _ = report._render_qweb_pdf(res_ids=record.ids)
            return base64.b64encode(pdf_content)
        else:
            return self.data

    def _prepare_sign_oca_request_vals_from_record(self, record):
        roles = self.mapped("item_ids.role_id").filtered(
            lambda x: x.partner_type != "empty"
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
