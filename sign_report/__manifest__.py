# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Sign Report",
    "summary": """
        Sign docs based on qweb report
    """,
    "version": "14.0.1.0.0",
    "license": "AGPL-3",
    "website": "https://github.com/vertel/odoo-sign",
    "depends": ["sign_oca",],
    "data": [
        "views/sign_oca_template_view.xml",
    ],
    "demo": [
        "demo/sale_order_sign_role.xml",
        "demo/sign_oca_template.xml",
    ],
}