import hashlib
import json
import logging
from base64 import b64decode, b64encode
from hashlib import sha256
from io import BytesIO

from PyPDF2 import PdfFileReader, PdfFileWriter
from reportlab.graphics.shapes import Drawing, Line, Rect
from reportlab.lib.colors import black, transparent
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfgen import canvas
from reportlab.platypus import Image, Paragraph

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.http import request
from odoo.tools import float_repr

_logger = logging.getLogger(__name__)


class VrtlSignRequest(models.Model):
    _name = "vrtl.sign.request"
    _inherit = ["mail.thread", "mail.activity.mixin", "sign.request.mixin"]
    _description = "Sign Request"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    sign_definition_id = fields.Many2one("vrtl.sign.definition")
    sign_provider_id = fields.Many2one(related="sign_definition_id.sign_provider_id", string="Sign Provider")
    data = fields.Binary(required=True)
    signed_doc = fields.Binary(string="Signed Document")
    filename = fields.Char()
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Responsible",
        default=lambda self: self.env.user,
        required=True,
    )
    record_ref = fields.Reference(
        lambda self: [
            (m.model, m.name)
            for m in self.env["ir.model"]
            .sudo()
            .search([("transient", "=", False), ("model", "not like", "sign.oca")])
        ],
        string="Object",
    )
    signed = fields.Boolean(copy=False)
    signer_ids = fields.One2many(
        "vrtl.sign.request.signer",
        inverse_name="request_id",
        auto_join=True,
        copy=True,
        string="Signers",
    )
    signer_id = fields.Many2one(
        comodel_name="vrtl.sign.request.signer",
        compute="_compute_signer_id",
        help="The signer related to the active user.",
        string="Signer",
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("sent", "Sent"),
            ("signed", "Signed"),
            ("cancel", "Cancelled"),
        ],
        default="draft",
        required=True,
        copy=False,
        tracking=True,
    )
    signed_count = fields.Integer(compute="_compute_signed_count")
    signer_count = fields.Integer(compute="_compute_signer_count")
    to_sign = fields.Boolean(compute="_compute_to_sign")
    signatory_data = fields.Serialized(
        default=lambda r: {},
        copy=False,
    )
    current_hash = fields.Char(copy=False)
    company_id = fields.Many2one(
        "res.company",
        default=lambda r: r.env.company.id,
        required=True,
    )
    next_item_id = fields.Integer(compute="_compute_next_item_id")


    @api.depends("signer_ids")
    @api.depends_context("uid")
    def _compute_signer_id(self):
        user = self.env.user
        for record in self:
            user_diff_roles = record.signer_ids.filtered(
                lambda x: x.partner_id == user.partner_id.commercial_partner_id
            )
            record.signer_id = (
                fields.first(user_diff_roles.filtered(lambda x: x.is_allow_signature))
                if user_diff_roles.filtered(lambda x: x.is_allow_signature)
                else fields.first(user_diff_roles)
            )

    @api.depends(
        "signer_ids",
        "signer_ids.is_allow_signature",
    )
    @api.depends_context("uid")
    def _compute_to_sign(self):
        for record in self:
            record.to_sign = (
                record.signer_id.is_allow_signature if record.signer_id else False
            )



    def get_info(self):
        self.ensure_one()
        return {
            "name": self.name,
            "items": self.signatory_data,
            "roles": [
                {"id": signer.role_id.id, "name": signer.role_id.name}
                for signer in self.signer_ids
            ],
            "fields": [
                {"id": field.id, "name": field.name}
                for field in self.env["sign.oca.field"].search([])
            ],
        }

    def _ensure_draft(self):
        self.ensure_one()
        if not self.signer_ids:
            raise ValidationError(
                self.env._(
                    "There are no signers, please fill them before configuring it"
                )
            )
        if not self.state == "draft":
            raise ValidationError(
                self.env._("You can only configure requests in draft state")
            )

    def sign(self):
        self.ensure_one()
        try:
            if self.sign_provider_id:
                # Call provider methods, not definition methods
                provider_data = self.sign_provider_id.prepare_signing_request(self)
                provider_sign_data = self.sign_provider_id.initiate_signature(self, provider_data)
                self.sign_data(provider_sign_data)
        except Exception as e:
            raise UserError(_(f"{e}"))

    def sign_data(self, provider_sign_data):
        print(provider_sign_data)



    def send(self):
        pass


    def cancel(self):
        self.write({"state": "cancel"})
        self._set_action_log("cancel")

    @api.depends("signer_ids")
    def _compute_signer_count(self):
        for record in self:
            record.signer_count = len(record.signer_ids)

    @api.depends("signer_ids", "signer_ids.signed_on")
    def _compute_signed_count(self):
        for record in self:
            record.signed_count = len(record.signer_ids.filtered(lambda r: r.signed_on))

    def open_template(self):
        return self.template_id.configure()

    def action_send(self, sign_now=False, message=""):
        self.ensure_one()
        if self.state != "draft":
            return
        self._set_action_log("validate")
        self.state = "sent"
        for signer in self.signer_ids:
            signer._portal_ensure_token()
            if sign_now and signer.partner_id == self.env.user.partner_id:
                continue
            render_result = self.env["ir.qweb"]._render(
                "sign_oca.sign_oca_template_mail",
                {"record": signer, "body": message, "link": signer.access_url},
                engine="ir.qweb",
                minimal_qcontext=True,
            )
            self.env["mail.thread"].message_notify(
                body=render_result,
                partner_ids=signer.partner_id.ids,
                subject=self.env._("New document to sign"),
                subtype_id=self.env.ref("mail.mt_comment").id,
                mail_auto_delete=False,
                email_layout_xmlid="mail.mail_notification_light",
            )

    def action_send_signed_request(self):
        self.ensure_one()
        if (
            self.state != "signed"
            or not self.env.company.sign_oca_send_sign_request_copy
        ):
            return
        for signer in self.signer_ids:
            attachments = (
                self.env["ir.attachment"]
                .sudo()
                .search(
                    [
                        ("res_model", "=", "vrtl.sign.request"),
                        ("res_id", "=", self.id),
                        ("res_field", "=", "data"),
                    ]
                )
            )
            # The message will not be linked to the record because we do not want
            # it happen.
            self.env["mail.thread"].message_notify(
                body=self.env._(
                    "%(name)s (%(email)s) has sent the signed document.",
                    name=self.create_uid.name,
                    email=self.create_uid.email,
                ),
                partner_ids=signer.partner_id.ids,
                subject=self.env._("Signed document"),
                subtype_id=self.env.ref("mail.mt_comment").id,
                mail_auto_delete=False,
                attachment_ids=attachments.ids,
            )

    def _check_signed(self):
        self.ensure_one()
        if self.state != "sent":
            return
        if all(self.mapped("signer_ids.signed_on")):
            self.state = "signed"

    def _set_action_log_vals(self, action, **kwargs):
        vals = kwargs.copy()
        vals.update(
            {"action": action, "request_id": self.id, "ip": self._get_action_log_ip()}
        )
        return vals

    def _get_action_log_ip(self):
        if not request or not hasattr(request, "httprequest"):
            # This comes from a server call. Set as localhost
            return "0.0.0.0"
        return request.httprequest.access_route[-1]

    def _set_action_log(self, action, **kwargs):
        self.ensure_one()
        return (
            self.env["vrtl.sign.request.log"]
            .sudo()
            .create(self._set_action_log_vals(action, **kwargs))
        )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            record._set_action_log("create")
        return records


class VrtlSignRequestSigner(models.Model):
    _name = "vrtl.sign.request.signer"
    _description = "Sign Request Value"

    data = fields.Binary(related="request_id.data")
    request_id = fields.Many2one("vrtl.sign.request", required=True, ondelete="cascade")
    partner_name = fields.Char(related="partner_id.name")
    partner_id = fields.Many2one("res.partner", required=True, ondelete="restrict")
    role = fields.Char(required=True, ondelete="restrict")
    signed_on = fields.Datetime()
    signature_hash = fields.Char()
    model = fields.Char(compute="_compute_model", store=True)
    res_id = fields.Integer(compute="_compute_res_id", store=True)
    is_allow_signature = fields.Boolean(compute="_compute_is_allow_signature")
    secure_sequence_number = fields.Integer(
        string="Inalteralbility No Gap Sequence #",
        readonly=True,
        copy=False,
        index=True,
    )
    inalterable_hash = fields.Char(
        string="Inalterability Hash", readonly=True, copy=False
    )
    sequence = fields.Integer(copy=False)
    altered_hash = fields.Boolean()
    latitude = fields.Float()
    longitude = fields.Float()

    @api.depends("request_id.record_ref")
    def _compute_model(self):
        for item in self.filtered(lambda x: x.request_id.record_ref):
            item.model = item.request_id.record_ref._name

    @api.depends("request_id.record_ref")
    def _compute_res_id(self):
        for item in self.filtered(lambda x: x.request_id.record_ref):
            item.res_id = item.request_id.record_ref.id

    @api.depends("signed_on", "partner_id")
    @api.depends_context("uid")
    def _compute_is_allow_signature(self):
        user = self.env.user
        for item in self:
            item.is_allow_signature = bool(
                not item.signed_on and item.partner_id == user.partner_id
            )


    @api.onchange("role_id")
    def _onchange_role_id(self):
        for item in self:
            item.partner_id = item.role_id._get_partner_from_record(
                item.request_id.record_ref
            )

    def get_info(self, access_token=False):
        self.ensure_one()
        self._set_action_log("view", access_token=access_token)
        return {
            "role_id": self.role_id.id if not self.signed_on else False,
            "name": self.request_id.template_id.name,
            "items": self.request_id.signatory_data,
            "to_sign": self.request_id.to_sign,
            "ask_location": self.request_id.ask_location,
            "partner": {
                "id": self.partner_id.id,
                "name": self.partner_id.name,
                "email": self.partner_id.email,
                "phone": self.partner_id.phone,
            },
        }

    def sign(self):
        self.ensure_one()
        try:
            if self.sign_provider_id:
                # Call the provider's prepare method first
                provider_data = self.sign_provider_id.prepare_signing_request(self)

                # Then initiate signature on the PROVIDER, not definition
                provider_sign_data = self.sign_provider_id.initiate_signature(self, provider_data)

                self.sign_data(provider_sign_data)
        except Exception as e:
            raise UserError(_(f"{e}"))

    def action_sign(self, items, access_token=False, latitude=False, longitude=False):
        self.ensure_one()
        if self.signed_on:
            raise ValidationError(
                self.env._("Users %s has already signed the document")
                % self.partner_id.name
            )
        if self.request_id.state != "sent":
            raise ValidationError(self.env._("Request cannot be signed"))
        self.signed_on = fields.Datetime.now()
        # current_hash = self.request_id.current_hash
        signatory_data = self.request_id.signatory_data

        input_data = BytesIO(b64decode(self.request_id.data))
        reader = PdfFileReader(input_data)
        output = PdfFileWriter()
        pages = {}
        for page_number in range(1, reader.numPages + 1):
            pages[page_number] = reader.getPage(page_number - 1)

        for key in signatory_data:
            if signatory_data[key]["role_id"] == self.role_id.id:
                signatory_data[key] = items[key]
                self._check_signable(items[key])
                item = items[key]
                page = pages[item["page"]]
                new_page = self._get_pdf_page(item, page.mediaBox)
                if new_page:
                    page.mergePage(new_page)
                pages[item["page"]] = page
        for page_number in pages:
            output.addPage(pages[page_number])
        output_stream = BytesIO()
        output.write(output_stream)
        output_stream.seek(0)
        signed_pdf = output_stream.read()
        final_hash = hashlib.sha1(signed_pdf).hexdigest()
        # TODO: Review that the hash has not been changed...
        self.request_id.write(
            {
                "signatory_data": signatory_data,
                "data": b64encode(signed_pdf),
                "current_hash": final_hash,
            }
        )
        self.signature_hash = final_hash
        self.latitude = latitude
        self.longitude = longitude
        self.request_id._check_signed()
        self._set_action_log("sign", access_token=access_token)
        if self.sequence_id:
            self.flush_recordset()
            new_number = self.sequence_id.next_by_id()
            self.write(
                {
                    "secure_sequence_number": new_number,
                    "inalterable_hash": self._get_new_hash(new_number),
                }
            )
        self.request_id.action_send_signed_request()
        return {
            "type": "ir.actions.act_url",
            "url": self.access_url,
        }


    def _get_integrity_hash_fields(self):
        return ["partner_id", "role_id", "signed_on", "signature_hash"]


class SignRequestLog(models.Model):
    _name = "vrtl.sign.request.log"
    _description = "Sign Request Log"
    _log_access = False

    uid = fields.Many2one(
        "res.users",
        required=True,
        ondelete="cascade",
        default=lambda r: r.env.user.id,
    )
    date = fields.Datetime(required=True, default=lambda r: fields.Datetime.now())
    partner_id = fields.Many2one(
        "res.partner", required=True, default=lambda r: r.env.user.partner_id.id
    )
    request_id = fields.Many2one("vrtl.sign.request", required=True, ondelete="cascade")
    signer_id = fields.Many2one("vrtl.sign.request.signer")
    action = fields.Selection(
        [
            ("create", "Create"),
            ("validate", "Validate"),
            ("view", "View Document"),
            ("sign", "Sign"),
            ("add_field", "Add field"),
            ("edit_field", "Edit field"),
            ("delete_field", "Delete field"),
            ("cancel", "Cancel"),
            ("configure", "Configure"),
        ],
        required=True,
    )
    access_token = fields.Char()
    ip = fields.Char()
