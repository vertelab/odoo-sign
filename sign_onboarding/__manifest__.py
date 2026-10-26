# -*- coding: utf-8 -*-
{
    'name': 'Signering i Vertel',
    'version': '18.0.2.0.0',
    'summary': 'Onboardingskurs: elektronisk signering med BankID',
    'description': """
Lär dig skicka dokument för signering, följa status och arkivera det signerade.

Kursen har fem sektioner:
  1. Vad det är och varför
  2. Så kopplar du upp dig
  3. Skicka och följ upp
  4. Signera och arkivera
  5. Manuellt test — verifiera att det fungerar

Allt innehåll ligger i data/ (inte demo/) och skapas därmed även i
produktionsdatabaser som körs med --without-demo=all.
""",
    'author': 'Vertel Sverige AB',
    'website': 'https://vertel.se',
    'license': 'LGPL-3',
    'category': 'Website/eLearning',
    'depends': ['website_slides'],
    'data': [
        'views/slide_channel_data.xml',
        'data/slide_slides_s1.xml',
        'data/slide_slides_s2.xml',
        'data/slide_slides_s3.xml',
        'data/slide_slides_s4.xml',
        'data/slide_slides_s5.xml',
    ],
    'demo': [
        'demo/slide_slide_demo.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
