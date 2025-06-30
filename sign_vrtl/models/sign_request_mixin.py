from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class SignRequestMixin(models.AbstractModel):
    _name = 'sign.request.mixin'
    _description = "Sign Request Mixin"

    sign_definition_id = fields.Many2one("vrtl.sign.definition")
    sign_provider_id = fields.Many2one(related="sign_definition_id.sign_provider_id", string="Sign Provider")
    sign_provider_code = fields.Selection(related="sign_provider_id.code", string="Sign Provider Code")
    sign_request_id = fields.Many2one('vrtl.sign.request', string="Sign Request")

    def create_sign_request(self):
        """Create sign request using definition - override this in each model"""
        raise NotImplementedError("Each model should implement create_sign_request")

    def initiate_signing(self):
        """Create sign request if needed and start signing"""
        self.ensure_one()

        if not self.sign_request_id:
            self.create_sign_request()

        if self.sign_request_id:
            return self.sign_request_id.sign()
        return None