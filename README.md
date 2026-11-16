# odoo-sign

## Porteringsstatus

18.0 är baseline. 19.0/20.0 visar om p-filen har ett villkor för utgåvan
— inte om grenen finns. Blockerare är `depends` som saknas i 20.0
(kärna + alla 20.0-grenar).

| Modul | Beskrivning | Manifest | p-fil | 19.0 | 20.0 | Blockerare |
|---|---|---|---|---|---|---|
| sign_bankid | Sign with BankID | 1.0.0 | 0 | — | — | — |
| sign_bankid_base_tier_validation | Sign Sale Order with BankID | 1.0.0 | 0 | — | — | `base_tier_validation` |
| sign_criipto | Sign with Criipto | 1.0.0 | 0 | — | — | — |
| sign_onboarding | Onboardingskurs: elektronisk signering med BankID | 1.0.0 | 0 | — | — | — |
| sign_project_task | Project Task Sign | 1.0.0 | 0 | — | — | `sign_oca` |
| sign_report | Sign docs based on qweb report | 1.0.0 | 0 | — | — | `sign_oca` |
| sign_sale_order_template | Sign Sale Order Template | 1.0.0 | 0 | — | — | — |
| sign_scrive | Sign with Scrive | 1.0.0 | 0 | — | — | — |
| sign_vrtl | Sign Providers | 1.0.0 | 1 | — | ✓ | — |
