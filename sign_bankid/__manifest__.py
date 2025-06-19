# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Sign with BankID",
    "summary": """
        Sign with BankID
    """,
    "version": "18.0.1.0.0",
    "license": "AGPL-3",
    "website": "https://github.com/vertel/odoo-sign",
    "depends": ['web', 'sign_vrtl'],
    "data": [
        'data/sign_provider_data.xml',
        'views/sign_provider_views.xml',
        'views/sign_request_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js',
            'sign_bankid/static/src/js/bankid_x_backend.js',
            'sign_bankid/static/src/xml/bankid_modal.xml',
            'sign_bankid/static/src/scss/bankid_modal.scss',
        ],
        # Add frontend assets for portal
        'web.assets_frontend': [
            'https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js',
            'sign_bankid/static/src/js/bankid_x_frontend.js',
            # 'sign_bankid/static/src/scss/portal_bankid.scss',
        ],
    }

}