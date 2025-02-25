# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Sign Sale Order Template",
    "summary": """
        Sign Sale Order Template
    """,
    "version": "18.0.1.0.0",
    "license": "AGPL-3",
    "website": "https://github.com/vertel/odoo-sign",
    "depends": ['sign_report', 'sale_management'],
    "data": [
        'views/sale_order_template_view.xml',
        'views/sale_portal_templates.xml',
        'views/ir_actions_report_templates.xml',
        'views/sign_oca_request_view.xml',
        'views/report_templates.xml',
    ],

}