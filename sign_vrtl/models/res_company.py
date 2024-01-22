# -*- coding: utf-8 -*-

from odoo import fields, models


class Company(models.Model):
    _inherit = 'res.company'

    sign_terms_type = fields.Selection([('plain', 'Terms in Email'), ('html', 'Terms as Web Page')],
        default='plain', string='Sign Terms & Conditions format', help="""Terms in Email - The text will be displayed at the bottom of every signature request email.""")
    sign_terms = fields.Html(string='Sign Default Terms and Conditions', translate=True,
        default="""<h1 style="text-align: center; ">Terms &amp; Conditions</h1>
        <p>Your conditions...</p>""")
    sign_terms_html = fields.Html(string='Sign Default Terms and Conditions as a Web page', translate=True,
        default="""<h1 style="text-align: center; ">Terms &amp; Conditions</h1>
        <p>Your conditions special terms and ...</p>""", sanitize_attributes=False)
