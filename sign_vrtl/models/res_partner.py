# -*- coding: utf-8 -*-

from odoo import fields, models, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    signature_count = fields.Integer(compute='_compute_signature_count', string="# Signatures")
    signature_request = fields.Many2many(comodel_name='sign_vrtl.request',string='Signature Requests') # relation|column1|column2

    def _compute_signature_count(self):
        signature_data = self.env['sign_vrtl.request.item'].sudo()._read_group([('partner_id', 'in', self.ids), ('state', 'in', ['sent', 'completed'])], ['partner_id'], ['__count'])
        signature_data_mapped = {partner.id: count for partner, count in signature_data}
        for partner in self:
            partner.signature_count = signature_data_mapped.get(partner.id, 0)

    def open_signatures(self):  # Smart button
        self.ensure_one()
        request_ids = self.env['sign_vrtl.request.item'].search([('partner_id', '=', self.id)]).mapped('sign_request_id')
        return {
            'type': 'ir.actions.act_window',
            'name': _('Signature(s)'),
            'view_mode': 'kanban,tree,form',
            'res_model': 'sign_vrtl.request',
            'domain': [('id', 'in', request_ids.ids)],
            'context': {
                'search_default_reference': self.name,
                'search_default_signed': 1,
                'search_default_in_progress': 1,
            },
        }
