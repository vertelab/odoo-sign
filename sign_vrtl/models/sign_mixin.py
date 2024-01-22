# -*- coding: utf-8 -*-


from odoo import api, fields, models, Command, _
from odoo.exceptions import UserError, AccessError, ValidationError

class SignMixin(models.AbstractModel):
    """
        Makes a model signable, adds sign parties to the model
        
        Add a page to notebook tree-view "Sign Parties":
            partner_id role sign_status sign_hash sign_request
        
    """
    _name = "sign_vrtl.mixin"
    _description = "Sign Mixin"


    sign_item_ids = fields.One2many('sign_vrtl.item', 'template_id', string="Signature Items", copy=True)
    responsible_count = fields.Integer(compute='_compute_responsible_count', string="Responsible Count")

    active = fields.Boolean(default=True, string="Active")
    favorited_ids = fields.Many2many('res.users', string="Favorited Users", relation="sign_template_favorited_users_rel", default=_default_favorited_ids)
    user_id = fields.Many2one('res.users', string="Responsible", default=lambda self: self.env.user)

    sign_request_ids = fields.One2many('sign.request', 'template_id', string="Signature Requests")

    color = fields.Integer()
    redirect_url = fields.Char(string="Redirect Link", default="",
        help="Optional link for redirection after signature")
    redirect_url_text = fields.Char(string="Link Label", default="Open Link", translate=True,
        help="Optional text to display on the button link")
    signed_count = fields.Integer(compute='_compute_signed_in_progress_template')


    def open_logs(self):  # Smart button
        self.ensure_one()
        return {
            "name": _("Activity Logs"),
            "type": "ir.actions.act_window",
            "res_model": "sign_vrtl.log",
            'view_mode': 'tree,form',
            'domain': [('sign_request_id', '=', self.id)],
        }



    def open_requests(self): # Smart button
        return {
            "type": "ir.actions.act_window",
            "name": _("Sign requests"),
            "res_model": "sign_vrtl.request",
            "res_id": self.id,
            "domain": [["object_id", "in", self.ids]],
            "views": [[False, 'kanban'], [False, "form"]],
            "context": {'search_default_signed': True}
        }

  