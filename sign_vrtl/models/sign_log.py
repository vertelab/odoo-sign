# -*- coding: utf-8 -*-

from hashlib import sha256
from json import dumps
from datetime import datetime
import logging

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError
from odoo.http import request

_logger = logging.getLogger(__name__)

class SignLog(models.Model):
    _name = 'sign_vrtl.log'
    _order = 'date, id'
    _description = "Sign requests access history"


    date = fields.Datetime(default=fields.Datetime.now, required=True)
    sign_request_id = fields.Many2one('sign_vrtl.request', required=True, ondelete="cascade")
    sign_request_item_id = fields.Many2one('sign_vrtl.request.item')
    user_id = fields.Many2one('res.users', groups="sign_vrtl.group_sign_manager")
    partner_id = fields.Many2one('res.partner')
    latitude = fields.Float(digits=(10, 7), groups="sign_vrtl.group_sign_manager")
    longitude = fields.Float(digits=(10, 7), groups="sign_vrtl.group_sign_manager")
    ip = fields.Char("IP address of the visitor", required=True, groups="sign_vrtl.group_sign_manager")
    log_hash = fields.Char(string="Inalterability Hash", readonly=True, copy=False)
    token = fields.Char(string="User token")

    action = fields.Selection(
        string="Action Performed",
        selection=[
            ('create', 'Creation'),
            ('open', 'View/Download'),
            ('save', 'Save'),
            ('sign', 'Signature'),
            ('refuse', 'Refuse'),
            ('cancel', 'Cancel'),
            ('update_mail', 'Mail Update'),
            ('update', 'Update')
        ], required=True,
    )

    request_state = fields.Selection([
        ("shared", "Shared"),
        ("sent", "Before Signature"),
        ("signed", "After Signature"),
        ("refused", "Refused Signature"),
        ("canceled", "Canceled"),
        ("expired", "Expired"),
    ], required=True, string="State of the request on action log", groups="sign_vrtl.group_sign_manager")

    @api.model_create_multi
    def create(self, vals_list):

        vals_list_request_item = [vals for vals in vals_list if vals.get('sign_request_item_id')]
        sign_request_items = self.env['sign_vrtl.request.item'].browse([vals['sign_request_item_id'] for vals in vals_list_request_item])
        vals_list_request = [vals for vals in vals_list if not vals.get('sign_request_item_id') and vals.get('sign_request_id')]
        sign_requests = self.env['sign_vrtl.request'].browse([vals['sign_request_id'] for vals in vals_list_request])
        for vals, sign_request_item in zip(vals_list_request_item, sign_request_items):
            vals.update(self._prepare_vals_from_item(sign_request_item))
        for vals, sign_request in zip(vals_list_request, sign_requests):
            vals.update(self._prepare_vals_from_request(sign_request))
        user_id = self.env.user.id if not self.env.user._is_public() else None
        ip = request.httprequest.remote_addr if request else '0.0.0.0'
        now = datetime.utcnow()
        for vals in vals_list:
            vals.update({
                'user_id': user_id,
                'ip': ip,
                'date': now,
            })
            vals['log_hash'] = self._get_or_check_hash(vals)
        return super().create(vals_list)

    def _prepare_vals_from_item(self, request_item):
        sign_request = request_item.sign_request_id
        latitude = 0.0
        longitude = 0.0
        if request:
            latitude = (request.geoip.location.latitude or 0.0) if request_item.state != 'sent' else request_item.latitude
            longitude = (request.geoip.location.longitude or 0.0) if request_item.state != 'sent' else request_item.longitude
        return dict(
            sign_request_item_id=request_item.id,
            sign_request_id=sign_request.id,
            request_state=sign_request.state,
            latitude=latitude,
            longitude=longitude,
            partner_id=request_item.partner_id.id,
            token=request_item.access_token,
        )

    def _prepare_vals_from_request(self, sign_request):
        return dict(
            sign_request_id=sign_request.id,
            request_state=sign_request.state,
            latitude=(request.geoip.location.latitude or 0.0) if request else 0.0,
            longitude=(request.geoip.location.longitude or 0.0) if request else 0.0,
            partner_id=self.env.user.partner_id.id if not self.env.user._is_public() else None,
        )
