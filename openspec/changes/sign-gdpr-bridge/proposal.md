## Why

Article 7.1 requires the controller to be able to *demonstrate* that the data
subject consented. A checkbox in a database demonstrates that someone clicked a
checkbox. A signed document demonstrates that the person did.

`gdpr_inventory` already has a consent register (`gdpr.consent`) with state and
chatter history. What it cannot do is require a signature, or attach the signed
document to the consent. `sign_oca` and `sign_vrtl` solve both, including
BankID for strong electronic identification (Art. 32).

Split out of `odoo-gdpr` change `gdpr-18-repair-and-extend` (group 9C). The
bridge belongs here because signing is not a GDPR concern — it is a signing
concern that GDPR happens to need.

## What Changes

- New module `sign_gdpr` with `sign_oca`, `sign_vrtl` and `gdpr_inventory` as
  dependencies.
- `requires_signature` on `gdpr.inventory` and `gdpr.consent`.
- A consent that requires a signature is not marked `given` until the signature
  completes.
- The signed document is attached to the consent record, with provider and
  timestamp.
- A signed processing agreement is linked back to the inventory it governs.
- BankID is available as a provider without the bridge depending on it.

## Capabilities

### New Capabilities
- `sign-gdpr-bridge`: the `sign_gdpr` module — signed consent, signed
  agreements, and the state transition that waits for the signature.

### Modified Capabilities
Inga.

## Impact

**Kod:** ny modul `sign_gdpr` i `odoo-sign`.

**Beroende:** `sign_oca` (OCA 18.0), `sign_vrtl` (Vertel 18.0),
`gdpr_inventory` (change `gdpr-18-repair-and-extend`).

**Juridik:** Art. 7.1 (bevisa samtycke), Art. 7.3 (återkallande), Art. 28.3
(biträdesavtal ska vara skriftligt), Art. 32 (stark autentisering).

**Risk:** medel. En konsent som väntar på signering är inte `given` — och
`gdpr.inventory` gallrar samtyckesbaserad data baserat på `state`. Om bryggan
lämnar konsenten i ett tredje tillstånd måste gallringslogiken veta vad det
betyder.

## Open Questions — måste besvaras innan implementation

1. **Vad händer med en konsent som väntar på signering?** Ska den ha ett eget
   state (`pending_signature`), eller vara `given` med en
   `signature_pending`-flagga? Det påverkar `_get_restrict_objects()` i
   `gdpr_inventory`, som filtrerar på `state = 'withdrawn'`.
2. **Ska ett PUB som väntar på signering vara `expiring` eller `missing`?** Se
   `agreement_gdpr`.
3. **Vilken provider är default** — `sign_vrtl` (intern) eller BankID?
