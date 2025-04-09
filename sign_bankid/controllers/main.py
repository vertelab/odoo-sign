from odoo import fields, http, _
from odoo.exceptions import AccessError, MissingError, ValidationError
from odoo.addons.sale.controllers.portal import CustomerPortal
from odoo.fields import Command
from odoo.http import request
import logging


class KnowitController(CustomerPortal):

    @http.route(["/knowit/bankid/sign/init"], type="json", auth="user", website=True, methods=["POST"])
    def start_sign(self, order_id=False, access_token=False, partner=False, ssn=False, **kwargs):
        # Debug: Log values to check if they are being received
        logging.info(f"Order ID: {order_id}")
        logging.info(f"SSN: {ssn}")
        logging.info(f"Access Token: {access_token}")
        logging.info(f"Partner: {partner}")

        access_token = access_token or request.httprequest.args.get('access_token')
        try:
            order_sudo = self._document_check_access('sale.order', int(order_id), access_token=access_token)
        except (AccessError, MissingError):
            return {'error': _('Invalid order.')}

        order_sudo.init_knowit_sign()

        return {"success": True, "message": "Sign request received!"}
