# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Sign with Criipto",
    "summary": """
        Sign with Criipto
    """,
    "version": "18.0.1.0.0",
    "license": "AGPL-3",
    "website": "https://github.com/vertel/odoo-sign",
    "depends": ['base', 'sale', 'sign_sale_order_template'],
    "data": [
        'views/res_company_view.xml',
        'views/sale_order_view.xml',
        'views/sale_portal_templates.xml',
        'views/sign_oca_request_view.xml',
    ],
    'assets': {
        # 'web.assets_frontend': [
        #     'sign_bankid/static/src/js/main.js',
        # ]
    }

}