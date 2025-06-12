# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Sign: Sign Providers",
    "summary": """
        Sign Providers
    """,
    "version": "18.0.1.0.0",
    "license": "AGPL-3",
    "website": "https://github.com/vertel/odoo-sign",
    "depends": ['web', 'base'],
    "data": [
        'data/sign_provider_data.xml',

        'views/sign_provider_views.xml',
        'security/ir.model.access.csv',
    ],
    # 'assets': { }

}