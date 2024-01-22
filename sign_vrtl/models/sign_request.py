# -*- coding: utf-8 -*-

from werkzeug.urls import url_join, url_quote, url_encode
from dateutil.relativedelta import relativedelta
from datetime import timedelta

from odoo import api, fields, models, http, _, Command
from odoo.tools import config, email_normalize, get_lang, is_html_empty, format_date, formataddr, groupby, consteq
from odoo.exceptions import UserError, ValidationError


class SignRequest(models.Model):
    _name = "sign_vrtl.request"
    _description = "Signature Request"
    _rec_name = 'reference'
    _inherit = ['mail.thread', 'mail.activity.mixin']


    #template_id = fields.Many2one('sign.template', string="Template", required=True)  object_id referense to object
    subject = fields.Char(string="Email Subject")
    reference = fields.Char(required=True, string="Document Name", help="This is how the document will be named in the mail")

    access_token = fields.Char('Security Token', required=True, default=_default_access_token, readonly=True, copy=False)
    share_link = fields.Char(string="Share Link", compute='_compute_share_link')

    request_item_ids = fields.One2many('sign_vrtl.request.item', 'sign_request_id', string="Signers", copy=True)
    state = fields.Selection([
        ("shared", "Shared"),
        ("sent", "Sent"),
        ("signed", "Fully Signed"),
        ("refused", "Refused"),
        ("canceled", "Canceled"),
        ("expired", "Expired"),
    ], default='sent', tracking=True, group_expand='_expand_states', copy=False, index=True)

    completed_document = fields.Binary(readonly=True, string="Completed Document", attachment=True, copy=False)

    nb_wait = fields.Integer(string="Sent Requests", compute="_compute_stats", store=True)
    nb_closed = fields.Integer(string="Completed Signatures", compute="_compute_stats", store=True)
    nb_total = fields.Integer(string="Requested Signatures", compute="_compute_stats", store=True)
    progress = fields.Char(string="Progress", compute="_compute_progress", compute_sudo=True)
    start_sign = fields.Boolean(string="Signature Started", help="At least one signer has signed the document.", compute="_compute_progress", compute_sudo=True)
    integrity = fields.Boolean(string="Integrity of the Sign request", compute='_compute_hashes', compute_sudo=True)

    active = fields.Boolean(default=True, string="Active", copy=False)

    color = fields.Integer()
    last_action_date = fields.Datetime(related="message_ids.create_date", readonly=True, string="Last Action Date")
    completion_date = fields.Date(string="Completion Date", compute="_compute_progress", compute_sudo=True)

    sign_log_ids = fields.One2many('sign_vrtl.log', 'sign_request_id', string="Logs", help="Activity logs linked to this request")
    message = fields.Html(string='sign.message')
   
    validity = fields.Date(string='Valid Until')
    reminder = fields.Integer(string='Reminder', default=0)
    last_reminder = fields.Date(string='Last reminder', default=lambda self: fields.Date.today())

    def open_logs(self):
        self.ensure_one()
        return {
            "name": _("Activity Logs"),
            "type": "ir.actions.act_window",
            "res_model": "sign_vrtl.log",
            'view_mode': 'tree,form',
            'domain': [('sign_request_id', '=', self.id)],
        }



    def _refuse(self, refuser, refusal_reason):
        """ Refuse a SignRequest. It can only be used in SignRequestItem._refuse
        :param res.partner refuser: the refuser who refuse to sign
        :param str refusal_reason: the refusal reason provided by the refuser
        """
      

    @api.model
    def _cron_reminder(self):
        """  Remind and expire
        """


    def _sign(self):
        """ Sign a SignRequest. It can only be used in the SignRequestItem._sign """
        self.ensure_one()
        if self.state != 'sent' or any(sri.state != 'completed' for sri in self.request_item_ids):
            raise UserError(_("This sign request cannot be signed"))
        self.write({'state': 'signed'})
        if not bool(config['test_enable'] or config['test_file']):
            self.env.cr.commit()
        if not self._check_is_encrypted():
            # if the file is encrypted, we must wait that the document is decrypted
            self._send_completed_document()


    def cancel(self):
        for sign_request in self:
            sign_request.write({'access_token': self._default_access_token(), 'state': 'canceled'})
        self.request_item_ids._cancel()

        # cancel activities for signers
        for user in self.request_item_ids.sudo().partner_id.user_ids.filtered(lambda u: u.has_group('sign_vrtl.group_sign_user')):
            self.activity_unlink(['mail.mail_activity_data_todo'], user_id=user.id)

        self.env['sign_vrtl.log'].sudo().create([{'sign_request_id': sign_request.id, 'action': 'cancel'} for sign_request in self])


    def _send_completed_document_mail(self, signers, request_edited, partner, access_token=None, with_message_cc=True, force_send=False):
        self.ensure_one()
        if access_token is None:
            access_token = self.access_token
        partner_lang = get_lang(self.env, lang_code=partner.lang).code
        base_url = self.get_base_url()
        body = self.env['ir.qweb']._render('sign_vrtl.sign_template_mail_completed', {
            'record': self,
            'link': url_join(base_url, 'sign/document/%s/%s' % (self.id, access_token)),
            'subject': '%s signed' % self.reference,
            'body': self.message_cc if with_message_cc and not is_html_empty(self.message_cc) else False,
            'recipient_name': partner.name,
            'recipient_id': partner.id,
            'signers': signers,
            'request_edited': request_edited,
            }, lang=partner_lang, minimal_qcontext=True)

        self.env['sign_vrtl.request']._message_send_mail(
            body, 'mail.mail_notification_light',
            {'record_name': self.reference},
            {'model_description': 'signature', 'company': self.communication_company_id or self.create_uid.company_id},
            {'email_from': self.create_uid.email_formatted,
             'author_id': self.create_uid.partner_id.id,
             'email_to': partner.email_formatted,
             'subject': _('%s has been edited and signed', self.reference) if request_edited else _('%s has been signed', self.reference),
             'attachment_ids': self.attachment_ids.ids + self.completed_document_attachment_ids.ids},
            force_send=force_send,
            lang=partner_lang,
        )



    @api.model
    def _message_send_mail(self, body, email_layout_xmlid, message_values, notif_values, mail_values, force_send=False, **kwargs):
        """ Shortcut to send an email. """
        default_lang = get_lang(self.env, lang_code=kwargs.get('lang')).code
        lang = kwargs.get('lang', default_lang)
        sign_request = self.with_context(lang=lang)

        # the notif layout wrapping expects a mail.message record, but we don't want
        # to actually create the record
        # See @tde-banana-odoo for details
        msg = sign_request.env['mail.message'].sudo().new(dict(body=body, **message_values))
        body_html = self.env['ir.qweb']._render(email_layout_xmlid, dict(message=msg, **notif_values), minimal_qcontext=True)
        body_html = sign_request.env['mail.render.mixin']._replace_local_links(body_html)

        mail_values['reply_to'] = mail_values.get('email_from')
        mail = sign_request.env['mail.mail'].sudo().create(dict(body_html=body_html, **mail_values))
        if force_send:
            mail.send()
        return mail

    def _schedule_activity(self, sign_users):
        for user in sign_users:
            self.with_context(mail_activity_quick_update=True).activity_schedule(
                'mail.mail_activity_data_todo',
                user_id=user.id
            )


class SignRequestItem(models.Model):
    _name = "sign_vrtl.request.item"
    _description = "Signature Request Item"
    _inherit = ['portal.mixin']
    _rec_name = 'partner_id'

    partner_id = fields.Many2one('res.partner', string="Signer", ondelete='restrict')
    sign_request_id = fields.Many2one('sign_vrtl.request', string="Signature Request", ondelete='cascade', required=True, copy=False)

    access_token = fields.Char(required=True, default=_default_access_token, readonly=True, copy=False, groups="base.group_system")
    access_via_link = fields.Boolean('Accessed Through Token', copy=False)
    role_id = fields.Many2one('sign_vrtl.item.role', string="Role", required=True, readonly=True)

    sign_blob = fields.Binary(attachment=True, copy=False)
    signing_date = fields.Date('Signed on', readonly=True, copy=False)
    state = fields.Selection([
        ("sent", "To Sign"),
        ("refused", "Refused"),
        ("completed", "Completed"),
        ("canceled", "Canceled"),
    ], readonly=True, default="sent", copy=False, index=True)

    signer_email = fields.Char(string='Email', compute="_compute_email", store=True)
    is_mail_sent = fields.Boolean(readonly=True, copy=False, help="The signature mail has been sent.")
    change_authorized = fields.Boolean(related='role_id.change_authorized')

    def _cancel(self, no_access=True):
        """ Cancel a SignRequestItem. 
        """

    def _refuse(self, refusal_reason):
        """  Refuse
        """
        self.ensure_one()


    def _send_signature_access_mail(self):
        for signer in self:
            signer_email_normalized = email_normalize(signer.signer_email or '')
            signer_lang = get_lang(self.env, lang_code=signer.partner_id.lang).code
            context = {'lang': signer_lang}
            # We hide the validity information if it is the default (6 month from the create_date)
            has_default_validity = signer.sign_request_id.validity and signer.sign_request_id.validity - relativedelta(months=6) == signer.sign_request_id.create_date.date()
            expiry_link_timestamp = signer._generate_expiry_link_timestamp()
            url_params = url_encode({
                'timestamp': expiry_link_timestamp,
                'exp': signer._generate_expiry_signature(signer.id, expiry_link_timestamp)
            })
            body = self.env['ir.qweb']._render('sign_vrtl.sign_template_mail_request', {
                'record': signer,
                'link': url_join(signer.get_base_url(), "sign/document/mail/%(request_id)s/%(access_token)s?%(url_params)s" % {'request_id': signer.sign_request_id.id, 'access_token': signer.sudo().access_token, 'url_params': url_params}),
                'subject': signer.sign_request_id.subject,
                'body': signer.sign_request_id.message if not is_html_empty(signer.sign_request_id.message) else False,
                'use_sign_terms': self.env['ir.config_parameter'].sudo().get_param('sign_vrtl.use_sign_terms'),
                'user_signature': signer.create_uid.signature,
                'show_validity': signer.sign_request_id.validity and not has_default_validity,
            }, lang=signer_lang, minimal_qcontext=True)

            attachment_ids = signer.sign_request_id.attachment_ids.ids
            self.env['sign_vrtl.request']._message_send_mail(
                body, 'mail.mail_notification_light',
                {'record_name': signer.sign_request_id.reference},
                {'model_description': _('Signature'), 'company': signer.communication_company_id or signer.sign_request_id.create_uid.company_id},
                {'email_from': signer.create_uid.email_formatted,
                 'author_id': signer.create_uid.partner_id.id,
                 'email_to': formataddr((signer.partner_id.name, signer_email_normalized)),
                 'attachment_ids': attachment_ids,
                 'subject': signer.sign_request_id.subject},
                force_send=True,
                lang=signer_lang,
            )
            signer.is_mail_sent = True
            del context


    def _sign(self, signature, **kwargs):
        """ Stores the sign request item values.
        :param signature: dictionary containing signature values and corresponding ids / signature image
        :param validation_required: boolean indicating whether the sign request item will after a further validation process or now
        """
        self.ensure_one()
        


class SaleApproval(models.Model):
    _name = 'sale.approval'
    _rec_name = 'name'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Sale Order Multi Approval'

    name = fields.Char(default='Approval Configuration')
    approve_customer_sale = fields.Boolean(string="Approval on Sale Orders",
                                           help='Enable this field for adding the approvals for the Sale Orders')
    threshold = fields.Integer("Threshold for double signing", default=200000)

    def apply_configuration(self):
        """Function for applying the approval configuration"""
        return True


class ApprovalLine(models.Model):
    _name = 'approval.line'
    _description = 'Approval line in Sale Order'

    sale_order_id = fields.Many2one('sale.order', readonly=0)
    approver_id = fields.Many2one('res.users', string='Approver', readonly=1)
    approval_status = fields.Boolean(string='Status', readonly=1)
    signed_document = fields.Binary(string='Is Document Signed', readonly=1)
    signed_xml_document = fields.Many2one("ir.attachment", "Signed Document", readonly=1)
    signer_ca = fields.Binary(string='Signer Ca', readonly=1)
    assertion = fields.Binary(string='Assertion', readonly=1)
    relay_state = fields.Binary(string='Relay State', readonly=1)
    signed_on = fields.Datetime(string='Signed on')

    def unlink(self):
        if self.signed_document or self.signed_xml_document or self.approval_status or self.signed_on:
            raise UserError(_("You are not allowed to remove this approval line"))
        return super(ApprovalLine, self).unlink()
