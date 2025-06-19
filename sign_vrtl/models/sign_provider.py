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

    def _get_callback_url(self):
        """Get the callback URL for provider webhooks - override in provider-specific modules"""
        # Base implementation returns None - each provider should override
        return None

    def _get_callback_url_with_params(self, sign_request):
        """Get callback URL with additional parameters if needed"""
        return self._get_callback_url()

    def prepare_signing_request(self, sign_request):
        """Dispatch to provider-specific request preparation"""
        self.ensure_one()

        method_name = f'prepare_{self.code}_request'

        if hasattr(self, method_name):
            method = getattr(self, method_name)
            return method(sign_request)
        else:
            return {}  # Default empty preparation

    def initiate_signature(self, sign_request, provider_data):
        """Dispatch to provider-specific signature initiation method"""
        self.ensure_one()

        # Dynamic method name based on provider code
        method_name = f'initiate_{self.code}_signature'

        if hasattr(self, method_name):
            method = getattr(self, method_name)
            return method(sign_request, provider_data)
        else:
            raise NotImplementedError(
                f"Provider '{self.code}' does not implement {method_name}"
            )

    def process_callback(self, sign_request, callback_data):
        """Dispatch to provider-specific callback processing"""
        self.ensure_one()

        method_name = f'process_{self.code}_callback'

        if hasattr(self, method_name):
            method = getattr(self, method_name)
            return method(sign_request, callback_data)
        else:
            raise NotImplementedError(
                f"Provider '{self.code}' does not implement {method_name}"
            )


    def get_base_url(self):
        """Get the base URL for this environment"""
        return self.env['ir.config_parameter'].sudo().get_param('web.base.url')