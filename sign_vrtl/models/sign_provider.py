from odoo import models, fields, api


class SignProvider(models.Model):
    _name = "sign.provider"
    _inherit = ['sign.provider.mixin']
    _description = 'Manages Sign Providers'




    def button_immediate_install(self):
        """ Install the module and reload the page.

        Note: `self.ensure_one()`

        :return: The action to reload the page.
        :rtype: dict
        """
        if self.module_id and self.module_state != 'installed':
            self.module_id.button_immediate_install()
            return {
                'type': 'ir.actions.client',
                'tag': 'reload',
            }
        return None

    def _make_request(
            self, endpoint, payload=None, method='POST', offline=False, idempotency_key=None
    ):
        pass