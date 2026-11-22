import base64
from odoo import api, fields, models


class SignOcaTemplate(models.Model):
    _name = "vrtl.sign.definition"
    _description = "Sign Definitions"  # TODO
    _inherit = ["mail.thread"]

    name = fields.Char(required=True)
    data = fields.Binary(attachment=True, required=True)
    filename = fields.Char()
    item_ids = fields.One2many("vrtl.sign.definition.item", inverse_name="sign_definition_id")
    model_id = fields.Many2one(
        comodel_name="ir.model",
        string="Model",
        domain=[("transient", "=", False), ("model", "not in", ["sign.oca", "vrtl.sign.definition"])],
    )
    model = fields.Char(
        compute="_compute_model", string="Model name", compute_sudo=True, store=True
    )
    active = fields.Boolean(default=True)

    report_template = fields.Many2one('ir.actions.report', string="Report Template")
    sign_provider_id = fields.Many2one('sign.provider', string="Signature Provider")


    def get_report_data(self, record):
        if self.report_template:
            report_content, report_format = self.env['ir.actions.report']._render_qweb_pdf(
                self.report_template.report_name, res_ids=record.ids
            )
            return base64.b64encode(report_content)
        else:
            return self.data

    @api.depends("model_id")
    def _compute_model(self):
        for item in self:
            item.model = item.model_id.model or False

    # def get_report_data(self, record):
    #     if self.report_template:
    #         report_content, report_format = self.env['ir.actions.report']._render_qweb_pdf(
    #             self.report_template.report_name, res_ids=record.ids
    #         )
    #         return base64.b64encode(report_content)
    #     else:
    #         return self.data


    def _prepare_vrtl_sign_request_vals_from_record(self, record):
        return {
            "name": record.name,
            "data": self.get_report_data(record),
            "sign_definition_id": self.id,
            "record_ref": f"{record._name},{record.id}",
            "signer_ids": [
                (
                    0,
                    0,
                    {
                        "partner_id": line._get_partner_from_record(record, line.field_id),
                        "role": line.role,
                    },
                )
                for line in self.item_ids
            ],
        }


class SignOcaTemplateItem(models.Model):
    _name = "vrtl.sign.definition.item"
    _description = "Sign Definition Item"

    sign_definition_id = fields.Many2one(
        "vrtl.sign.definition", required=True, ondelete="cascade"
    )

    role = fields.Char(string="Role")
    required = fields.Boolean()
    placeholder = fields.Char()
    model_id = fields.Many2one(related="sign_definition_id.model_id", string="Model")
    field_id = fields.Many2one("ir.model.fields", domain="[('model_id', '=', model_id)]")
    sign_provider_id = fields.Many2one(related="sign_definition_id.sign_provider_id", string="Signature Provider")

    def get_info(self):
        self.ensure_one()
        return {
            "id": self.id,
            "field_id": self.field_id.id,
            "name": self.field_id.field_description,
            "role": self.role,
            "placeholder": self.placeholder,
            "required": self.required,
        }


    def _get_partner_from_record(self, record, model_field):
        partner = False
        if model_field.relation == "res.users":
            partner = record[model_field.name].partner_id.id
        elif model_field.relation == "res.partner":
            partner = record[model_field.name].id
        return partner