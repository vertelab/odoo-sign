## Context

`sign_vrtl` (Vertel 18.0) har:

```
vrtl.sign.request:  name, sign_definition_id, sign_provider_id, data (Binary),
                    signed_doc (Binary), record_ref (Reference), signed (Boolean),
                    signer_ids, state, current_hash, signatory_data
sign.provider:      code, prepare_{code}_request, initiate_{code}_signature,
                    process_{code}_callback
```

`record_ref` är en generisk `Reference` mot alla icke-transienta modeller. Det
betyder att en signeringsförfrågan kan peka på en `gdpr.consent` utan att
`sign_vrtl` vet vad en konsent är.

`gdpr.consent` har `state` (`given`/`withdrawn`/`missing`) och
`gdpr.inventory._get_restrict_objects()` filtrerar på `state = 'withdrawn'` när
rättslig grund är samtycke.

## Goals / Non-Goals

**Goals:**
- En konsent som kräver underskrift blir inte `given` förrän den är signerad.
- Det signerade dokumentet hamnar på konsenten.
- Ett signerat PUB kopplas till inventeringen.

**Non-Goals:**
- Ingen egen signeringsmotor. `sign_vrtl` äger den.
- Ingen egen provider. `sign_bankid`/`sign_criipto`/`sign_scrive` äger dem.
- Ingen dokumentförvaring. Det är `dms_gdpr`.

## Decisions

### D1. Eget state, inte en flagga

**Varför:** `_get_restrict_objects()` filtrerar på `state = 'withdrawn'`. En
konsent som väntar på signering är inte `withdrawn` — men den är inte heller
`given`. Om vi använder en `signature_pending`-flagga på en konsent som redan är
`given` så **ljuger vi**: vi har inte beviset än.

**Hur:** `gdpr.consent.state` får ett fjärde värde: `pending_signature`.
Gallringslogiken påverkas inte — en konsent som väntar på signering är inte
`withdrawn`, alltså gallras den inte. Det är korrekt: vi har ingen grund att
behandla, men vi har inte heller fått ett återkallande.

⚠ **Fälla:** att lägga till ett värde i en `Selection` kräver ingen migrering,
men befintliga poster som är `given` utan signatur påverkas inte. Det är
avsiktligt.

**Alternativ:** `signature_pending`-flagga. Förkastat — se ovan.

### D2. `record_ref` används, inte ett nytt fält

**Varför:** `sign_vrtl` har redan en generisk referens. Att lägga ett
`gdpr_consent_id`-fält på `vrtl.sign.request` hade gjort signeringsmodulen
GDPR-medveten.

**Hur:** bryggan skapar `vrtl.sign.request` med
`record_ref = 'gdpr.consent,%d'` och läser tillbaka via samma referens.

### D3. BankID är en provider, inte ett beroende

**Varför:** `sign_bankid` beror på `sign_vrtl`. Om `sign_gdpr` berodde på
`sign_bankid` skulle en kund som använder Criipto tvingas installera BankID.

**Hur:** `sign_gdpr` beror bara på `sign_oca` + `sign_vrtl`. BankID väljs som
`sign_provider_id` när det finns. Specen har ett scenario för att det ska
fungera utan.

### D4. Återkallande kräver aldrig signatur

**Varför:** Art. 7.3 säger att återkallande ska vara **lika enkelt** som att ge
samtycke. Att kräva en signatur för att återkalla ett signerat samtycke gör
det svårare — och bryter mot artikeln.

**Hur:** `action_withdraw()` sätter `state = 'withdrawn'` direkt, oavsett om
konsenten var signerad.

## Risks / Trade-offs

| Risk | Mitigering |
|---|---|
| **Konsent i `pending_signature` behandlas som given** | Inget i `gdpr_inventory` behandlar `pending_signature` som `given`; gallringen filtrerar på `withdrawn` |
| **Signerat dokument försvinner** | Det ligger på `vrtl.sign.request.signed_doc`; bryggan kopierar till konsentens bilaga |
| **Provider avbryts mitt i** | `sign_vrtl` har `state`; bryggan läser den, gissar inte |
| **`sign_oca` krävs men används inte** | `sign_vrtl` beror på den; bryggan ärver beroendet |

## Migration Plan

1. Skapa `sign_gdpr` med beroenden
2. Utöka `gdpr.consent.state` med `pending_signature`
3. `requires_signature` på `gdpr.inventory` och `gdpr.consent`
4. Skapa signeringsförfrågan vid `add()` när signatur krävs
5. Callback: sätt `given` + bifoga dokument
6. Koppla signerat PUB till inventeringen
7. Test: signering klar → `given`; avbruten → oförändrad

**Rollback:** avinstallation lämnar `pending_signature`-poster som de är. De är
inte `given` och gallras därför inte — vilket är rätt.

## Open Questions

1. **`pending_signature` som eget state — bekräfta.** Det påverkar
   `gdpr_inventory`-specen (`gdpr-retention-automation`), som säger att
   samtyckesbaserad data gallras när samtycket är `withdrawn`. En konsent i
   `pending_signature` är inte `withdrawn` och gallras inte. Det är korrekt men
   bör skrivas in i den specen.
2. **Vilken provider är default?** `sign_vrtl` (intern) eller BankID?
3. **Ska PUB-signering kräva BankID?** Art. 28.3 säger "skriftligt", inte
   "stark autentisering". BankID är starkare än nödvändigt.
