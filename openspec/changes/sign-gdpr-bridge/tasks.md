## 1. Modulstomme

- [ ] 1.1 Skapa `sign_gdpr` med beroenden `sign_oca`, `sign_vrtl`, `gdpr_inventory`
- [ ] 1.2 Sätt `'auto_install': False`

## 2. Konsentens state

- [ ] 2.1 Utöka `gdpr.consent.state` med `pending_signature` via inherit
- [ ] 2.2 Uppdatera `gdpr.consent`-vyn med det nya värdet
- [ ] 2.3 Verifiera att `_get_restrict_objects()` inte påverkas
      (den filtrerar på `withdrawn`)

## 3. requires_signature

- [ ] 3.1 Lägg `requires_signature` (Boolean) på `gdpr.inventory`
- [ ] 3.2 Lägg `requires_signature` (Boolean) på `gdpr.consent`
- [ ] 3.3 Låt konsenten ärva inventeringens värde vid skapande

## 4. Signeringsflödet

- [ ] 4.1 Skapa `vrtl.sign.request` med `record_ref = 'gdpr.consent,<id>'`
      när en konsent som kräver signatur skapas
- [ ] 4.2 Sätt konsentens state till `pending_signature`
- [ ] 4.3 Callback: när `signed` är True → sätt `given` + `signature_date`
- [ ] 4.4 Callback: när signeringen misslyckas → lämna state oförändrat, logga
- [ ] 4.5 Bifoga `signed_doc` på konsentens bilaga
- [ ] 4.6 Lagra provider + tidsstämpel på konsenten

## 5. PUB

- [ ] 5.1 Koppla ett signerat `agreement` till inventeringen (via `agreement_gdpr`
      om den finns, annars via `record_ref`)
- [ ] 5.2 Visa signeringsdatum och undertecknare på inventeringen
- [ ] 5.3 Varna när inventeringen refererar ett PUB utan avslutad signering

## 6. Återkallande

- [ ] 6.1 Verifiera att `action_withdraw()` aldrig kräver signatur
- [ ] 6.2 Test: återkalla en signerad konsent → `withdrawn` direkt

## 7. Provider

- [ ] 7.1 Verifiera att bryggan fungerar utan `sign_bankid`
- [ ] 7.2 Verifiera att `sign_bankid` kan väljas när den finns
- [ ] 7.3 Besvara open question 2 (default-provider)

## 8. Avslut

- [ ] 8.1 Kör `openspec validate sign-gdpr-bridge`
