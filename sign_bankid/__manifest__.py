# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Sign Sale Order with BankID",
    "summary": """
        Sign Sale Order with BankID
    """,
    "version": "18.0.1.0.0",
    "license": "AGPL-3",
    "website": "https://github.com/vertel/odoo-sign",
    "depends": ['sign_sale_order_template', 'sign_report', 'sign_oca', 'web'],
    "data": [
        # 'views/sale_order_template_view.xml',
        # 'views/sale_portal_templates.xml',
        # 'views/sale_order_view.xml',
        'views/sign_oca_request_view.xml',
        # 'views/ir_actions_report_templates.xml',
        # 'views/sign_oca_request_view.xml',
        # 'views/report_templates.xml',
    ],
    'assets': {
        # 'web.assets_frontend': [
        #     'https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js',
        #     'sign_bankid/static/src/js/main.js',
        # ],
        "oca_sign.assets_frontend_sign": [
            'https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js',
            'sign_bankid/static/src/core/signature/oca_signature.esm.js',
            'sign_bankid/static/src/core/signature/signature_dialog.xml',
            'sign_bankid/static/src/core/signature/signature_dialog.js',
            'sign_bankid/static/src/core/signature/bankid_signature.js',
        ],

    }

}