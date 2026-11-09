# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Sign: Sign Providers",
    "summary": """
        Sign Providers
    """,
    "version": "18.0.1.0.2",
    "license": "AGPL-3",
    "website": "https://vertel.se/apps/odoo-sign/sign_vrtl",
    "depends": ['web', 'base', 'mail', 'sale', 'portal', 'sign_oca'],
    "data": [
        'data/sign_provider_data.xml',

        'views/menu.xml',

        'views/sign_provider_views.xml',
        'views/sign_definition_views.xml',
        'views/sign_request_views.xml',
        # 'views/sale_order_view.xml',


        'security/ir.model.access.csv',
    ],
    # 'assets': { }

}