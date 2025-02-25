import binascii

from odoo import fields, http, _
from odoo.exceptions import AccessError, MissingError, ValidationError
from odoo.fields import Command
from odoo.http import request

from odoo.addons.sale.controllers.portal import CustomerPortal


class CustomerPortalExtended(CustomerPortal):

    # @http.route(['/my/orders/<int:order_id>/accept'], type='json', auth="public", website=True)
    def portal_quote_accept(self, order_id, access_token=None, name=None, signature=None):
        # get from query string if not on json param
        access_token = access_token or request.httprequest.args.get('access_token')
        try:
            order_sudo = self._document_check_access('sale.order', order_id, access_token=access_token)
        except (AccessError, MissingError):
            return {'error': _('Invalid order.')}

        if not order_sudo._has_to_be_signed():
            return {'error': _('The order is not in a state requiring customer signature.')}
        if not signature:
            return {'error': _('Signature is missing.')}

        try:
            order_sudo.write({
                'signed_by': name,
                'signed_on': fields.Datetime.now(),
                'signature': signature,
            })
            order_sudo.action_update_sign_request()
            request.env.cr.commit()
        except (TypeError, binascii.Error) as e:
            return {'error': _('Invalid signature data.')}

        if not order_sudo._has_to_be_paid():
            order_sudo._validate_order()

        pdf = request.env['ir.actions.report'].sudo()._render_qweb_pdf('sale.action_report_saleorder', [order_sudo.id])[0]

        order_sudo.message_post(
            attachments=[('%s.pdf' % order_sudo.name, pdf)],
            author_id=(
                order_sudo.partner_id.id
                if request.env.user._is_public()
                else request.env.user.partner_id.id
            ),
            body=_('Order signed by %s', name),
            message_type='comment',
            subtype_xmlid='mail.mt_comment',
        )

        query_string = '&message=sign_ok'
        if order_sudo._has_to_be_paid():
            query_string += '&allow_payment=yes'
        return {
            'force_refresh': True,
            'redirect_url': order_sudo.get_portal_url(query_string=query_string),
        }