# Copyright 2023-2024 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class SignOcaTemplateGenerateMulti(models.TransientModel):
    _inherit = "sign.oca.template.generate.multi"

    def generate(self):
        requests = self._generate()
        for request in requests:
            request._initiate_sign()
            request.action_send(message=self.message)
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "sign_oca.sign_oca_request_act_window"
        )
        action["domain"] = [("id", "in", requests.ids)]
        return action