# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Sale Order Sign",
    "summary": """
        Sale Order Sign
    """,
    "version": "14.0.1.0.0",
    "license": "AGPL-3",
    "website": "https://github.com/vertel/odoo-sign",
    "depends": ["sign_oca", "sale_management"],
    "data": [
        "views/sale_order.xml",
        "views/res_config_settings.xml",
        "views/sign_oca_request.xml",
    ],
    "demo": [
        "demo/sale_order_sign_role.xml",
        "demo/sign_oca_template.xml",
    ],
}