# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Sign Base Tier Validation with BankID",
    "summary": """
        Sign Sale Order with BankID
    """,
    "version": "18.0.1.0.0",
    "license": "AGPL-3",
    "website": "https://github.com/vertel/odoo-base",
    "depends": ['sign_bankid', 'base_tier_validation', 'account'],
    "data": [
        'views/tier_review_view.xml',
        'views/account_view.xml',
    ],
    'assets': {
        'web.assets_backend': [
            "sign_bankid_base_tier_validation/static/src/components/tier_review_widget/tier_review_widget.xml",
            "sign_bankid_base_tier_validation/static/src/components/tier_review_widget/tier_review_widget.js",
        ],
    }

}