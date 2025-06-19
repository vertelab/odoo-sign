# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Sign with Scrive",
    "summary": """
        Sign with Scrive
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

}