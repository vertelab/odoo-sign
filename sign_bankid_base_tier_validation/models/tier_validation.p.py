import json
import base64
import httpx
import requests
from datetime import datetime
from odoo.exceptions import ValidationError
from odoo import models, fields, api, _


class TierValidation(models.AbstractModel):
    _name = "tier.validation"
    _inherit = ["res.bankid", "tier.validation"]


    def validate_tier(self):
        if not self._has_user_signed_rec():
            return {
                'type': 'ir.actions.client',
                'tag': 'bankid_sign_modal',
                'target': 'new',
                'context': {
                    'default_record_id': self.id,
                    'default_record_model': self._name,
                    'callback_method': 'validate_tier',
                }
            }
        else:
            return super().validate_tier()

    def _reset_bank_id_fields(self):
        res_bankid_fields = self.env['ir.model'].search([('model', '=', 'res.bankid')]).mapped('field_id')
        field_names = res_bankid_fields.mapped('name')
        values_to_write = {field_name: False for field_name in field_names if field_name in self._fields}
        self.write(values_to_write)

    def restart_validation(self):
        self._reset_bank_id_fields()
        return super().restart_validation()

    def request_validation(self):
        self._reset_bank_id_fields()
        return super().request_validation()

    def _get_bankid_fields_to_skip(self):
        """Get BankID fields plus the specific fields that caused validation errors"""
        # Get BankID fields from the res.bankid model
        res_bankid_fields = self.env['ir.model'].search([('model', '=', 'res.bankid')]).mapped('field_id')
        bankid_field_names = res_bankid_fields.mapped('name')

        # Add the exact fields that we know cause problems during BankID operations
        # These are based on your actual error messages
        additional_fields = [
            'needed_terms_dirty',  # From your error "Needed Terms Dirty"
            'is_manually_modified',  # From your error "Is Manually Modified"
            'state'
        ]

        return bankid_field_names + additional_fields

    @api.model
    def _get_under_validation_exceptions(self):
        """Allow BankID fields to be written during validation"""
        res = super()._get_under_validation_exceptions()
        return res + self._get_bankid_fields_to_skip()

    @api.model
    def _get_validation_exceptions(self, extra_domain=None, add_base_exceptions=True):
        """Override the BASE method to include BankID fields everywhere"""
        res = super()._get_validation_exceptions(extra_domain, add_base_exceptions)
        return res + self._get_bankid_fields_to_skip()


    def _validate_tier(self, tiers=False):
        self.ensure_one()
        tier_reviews = tiers or self.review_ids
        waiting_reviews = tier_reviews.filtered(
            lambda r: r.status == "waiting"
                      or r.approve_sequence_bypass
                      and self.env.user in r.reviewer_ids
        )
        if waiting_reviews:
            waiting_reviews.write(
                {
                    "status": "pending",
                }
            )

        user_reviews = tier_reviews.filtered(
            lambda r: r.status == "pending" and (self.env.user in r.reviewer_ids)
        )
        user_reviews.write(
            {
                "status": "approved",
                "done_by": self.env.user.id,
                "reviewed_date": fields.Datetime.now(),
                **self._update_reviewer_sign_status()
            }
        )
        reviews_to_notify = user_reviews.filtered(
            lambda r: r.definition_id.notify_on_accepted
        )
        if reviews_to_notify:
            subscribe = "message_subscribe"
            if hasattr(self, subscribe):
                getattr(self, subscribe)(
                    partner_ids=reviews_to_notify.mapped("reviewer_ids")
                    .mapped("partner_id")
                    .ids
                )
            for review in reviews_to_notify:
                rec = self.env[review.model].browse(review.res_id)
                rec._notify_accepted_reviews()

    def _update_reviewer_sign_status(self):
        fields_to_update = [
            'bankid_order_ref', 'bankid_status', 'signed_user_id', 'signed_partner_id', 'bankid_signed_name',
            'bankid_signed_personal_number', 'bankid_signed_given_name', 'bankid_signed_surname', 'bankid_device_ip',
            'bankid_issue_date', 'bankid_signature','bankid_ocsp_response','signed_date',
        ]
        field_vals = {field_name: self[field_name] for field_name in fields_to_update if field_name}
        return field_vals