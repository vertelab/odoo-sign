from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestSignBankidTierValidation(TransactionCase):
    """Tier validation gated on a BankID signature.

    The module makes the BankID fields writable while a record is under
    validation — otherwise the signature could never be stored — and resets
    them when validation restarts.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "Reviewer Partner"})
        cls.reviewer = cls.env["res.users"].create(
            {
                "name": "Tier Reviewer",
                "login": "tier_reviewer_bankid",
                "partner_id": cls.partner.id,
                "group_ids": [(6, 0, [cls.env.ref("base.group_user").id])],
            }
        )
        cls.definition = cls.env["tier.definition"].create(
            {
                "model_id": cls.env.ref("sale.model_sale_order").id,
                "review_type": "individual",
                "reviewer_id": cls.reviewer.id,
                "name": "BankID review",
            }
        )
        cls.order = cls.env["sale.order"].create({"partner_id": cls.partner.id})

    def test_bankid_fields_are_exempt_from_the_validation_lock(self):
        """BankID fields are added to the under-validation exceptions."""
        exceptions = self.order._get_under_validation_exceptions()
        self.assertIn("bankid_order_ref", exceptions)
        self.assertIn("bankid_status", exceptions)

    def test_bankid_fields_are_exempt_from_the_validation_check(self):
        """BankID fields are also added to the tracked-field exceptions."""
        exceptions = self.order._get_validation_exceptions()
        self.assertIn("bankid_order_ref", exceptions)
        self.assertIn("bankid_signature", exceptions)

    def test_review_carries_the_signature_metadata(self):
        """A tier review stores who signed and with which BankID reference."""
        review = self.env["tier.review"].create(
            {
                "model": "sale.order",
                "res_id": self.order.id,
                "definition_id": self.definition.id,
                "status": "pending",
                "bankid_order_ref": "order-ref-1",
                "bankid_status": "complete",
                "bankid_signed_name": "Anna Andersson",
                "signed_user_id": self.reviewer.id,
            }
        )
        self.assertEqual(review.bankid_order_ref, "order-ref-1")
        self.assertEqual(review.bankid_status, "complete")
        self.assertEqual(review.signed_partner_id, self.partner)

    def test_reset_clears_the_bankid_fields(self):
        """Restarting validation clears the BankID fields on the record."""
        self.order.write({"bankid_order_ref": "order-ref-2", "bankid_status": "complete"})
        self.order._reset_bank_id_fields()
        self.assertFalse(self.order.bankid_order_ref)
        self.assertEqual(self.order.bankid_status, "pending")
