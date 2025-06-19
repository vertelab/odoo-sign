import requests
import json
import logging
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class SignProviderMixin(models.AbstractModel):
    _name = "sign.provider.mixin"
    _description = 'Sign Providers Mixin'

    name = fields.Char(string="Name", required=True, translate=True)

    state = fields.Selection(
        string="State",
        selection=[('disabled', "Disabled"), ('enabled', "Enabled"), ('test', "Test Mode")],
        default='disabled', required=False, copy=False)

    company_id = fields.Many2one(  # Indexed to speed-up ORM searches (from ir_rule or others)
        string="Company", comodel_name='res.company', default=lambda self: self.env.company.id,
        required=True, index=True)
    sequence = fields.Integer(string="Sequence")
    code = fields.Selection(
        string="Code",
        help="The technical code of this payment provider.",
        selection=[('internal', "Internal")],
        default='internal',
        required=True,
    )

    # Kanban view fields
    image_128 = fields.Image(string="Image", max_width=128, max_height=128)
    color = fields.Integer(
        string="Color", help="The color of the card in kanban view", compute='_compute_color',
        store=True)

    # Module-related fields
    module_id = fields.Many2one(string="Corresponding Module", comodel_name='ir.module.module')
    module_state = fields.Selection(string="Installation State", related='module_id.state')

    def base_url(self):
        return self.env['ir.config_parameter'].sudo().get_param('web.base.url')

    def _build_request_headers(self):
        return {}


    def _api_requests(self, url, endpoint_param=None, payload=None, method='POST', headers=None):
        # headers = self._build_request_headers()
        try:
            response = requests.request(method, url, json=payload, headers=headers, timeout=60)
            try:
                response.raise_for_status()
            except requests.exceptions.HTTPError:
                _logger.exception(
                    "invalid API request at %s with data %s: %s", url, payload, response.text
                )
                msg = response.json().get('message', '')
                raise ValidationError(
                    f"{self.code}: " + _("The communication with the API failed. Details: %s", msg)
                )
        except requests.exceptions.ConnectionError:
            _logger.exception("unable to reach endpoint at %s", url)
            raise ValidationError("Adyen: " + _("Could not establish the connection to the API."))
        return response.json()