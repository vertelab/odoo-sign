## ADDED Requirements

### Requirement: Consent can require a signature

A consent SHALL be able to require a signature, so that the controller can
demonstrate that consent was given (Article 7.1).

#### Scenario: Consent with signature required
- **WHEN** an inventory requires signed consent
- **THEN** giving consent creates a signature request
- **AND** the consent is not marked `given` until the signature is complete

#### Scenario: Signature completes
- **WHEN** the signature request completes
- **THEN** the consent becomes `given`
- **AND** the signature date is stored

#### Scenario: Signature fails or is abandoned
- **WHEN** a signer fails or aborts authentication
- **THEN** the consent remains in its previous state
- **AND** the failure is recorded on the signature request

### Requirement: Signed document is attached to the consent

The signed document SHALL be stored on the consent record, together with the
provider and the timestamp that produced it.

#### Scenario: Document attached
- **WHEN** a signature completes
- **THEN** the signed document is attached to the consent record
- **AND** the signature provider and timestamp are recorded

#### Scenario: Document is retrievable
- **WHEN** a GDPR officer opens a signed consent
- **THEN** the signed document can be downloaded
- **AND** it is the document the signer saw

### Requirement: Strong authentication is available

Signature requests SHALL be able to use a strong electronic identification
provider such as BankID.

#### Scenario: BankID signature
- **WHEN** a signature request is configured to use BankID
- **THEN** the signer authenticates with BankID
- **AND** the resulting record names the provider and the authentication method

#### Scenario: BankID is optional
- **WHEN** `sign_bankid` is not installed
- **THEN** the bridge still works with the providers that are
- **AND** no import error occurs

### Requirement: Signed agreements are linked to inventories

A processing agreement signed through the signature module SHALL be linked back
to the inventory it governs.

#### Scenario: Signed processing agreement
- **WHEN** a processing agreement is signed
- **THEN** the signed document is linked to the inventory
- **AND** the inventory shows the signature date and signatory

#### Scenario: Unsigned agreement is flagged
- **WHEN** an inventory references a processing agreement with no completed
  signature
- **THEN** the inventory shows a warning
- **AND** the warning names the agreement

### Requirement: Withdrawal needs no signature

Withdrawing a consent SHALL be possible without a signature, and SHALL be as
easy as giving it (Article 7.3).

#### Scenario: Withdrawal from the portal
- **WHEN** a data subject withdraws a signed consent
- **THEN** the withdrawal takes effect immediately
- **AND** no signature is requested
