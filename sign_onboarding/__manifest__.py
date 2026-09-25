# -*- coding: utf-8 -*-
{
    'name': 'Signering i Vertel',
    'version': '18.0.1.0.0',
    'summary': 'Onboardingskurs: elektronisk signering med BankID',
    'description': """
Lär dig skicka dokument för signering, följa status och arkivera det signerade.
""",
    'author': 'Vertel AB',
    'website': 'https://vertel.se',
    'license': 'LGPL-3',
    'category': 'Website/eLearning',
    'depends': ['website_slides'],
    'data': [
        'views/slide_channel_data.xml',
    ],
    'demo': [
        'demo/slide_slide_demo.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
