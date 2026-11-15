# odoo-sign — gren 19.0

> **Denna gren är avsiktligt tom.** Modulerna är INTE portade till Odoo 19.
> Grenen finns så att dev-miljöer (`hansolo19`) kan klona den utan att falla,
> men den påstår ingenting om att koden är portad.

## Baseline

| | |
|---|---|
| Källa | `20.0` |
| Moduler | **9** |
| Grenar i repot | `14.0`, `15.0`, `16.0`, `17.0`, `18.0`, `20.0`, `fix/bankid-credentials`, `main` |

## Moduler

- `sign_bankid`
- `sign_bankid_base_tier_validation`
- `sign_criipto`
- `sign_onboarding`
- `sign_project_task`
- `sign_report`
- `sign_sale_order_template`
- `sign_scrive`
- `sign_vrtl`

## Blockerare

**2 externa beroenden saknas** i Odoo 19-kärnan och OCA 19.0:

| Beroende | Behövs av |
|---|---|
| `base_tier_validation` | `sign_bankid_base_tier_validation` |
| `sign_oca` | `sign_project_task`, `sign_report` |

### Prioritering

Ett beroende som blockerar många moduler ger mest nytta att lösa först:

- `sign_oca` — frisläpper **2** modul(er)
- `base_tier_validation` — frisläpper **1** modul(er)

## Nästa steg

Portering sker på `*-pfile`-maskin med versionsagnostisk kod
(`.p.py` / `.p.xml`). Se `/skill:odoo-pfiles`.
