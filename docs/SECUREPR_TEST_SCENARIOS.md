# SecurePR Pull Request Test Scenarios

Use these as descriptions for separate pull requests against this repository.
They are review scenarios, not instructions to add exploitable behavior. Keep
the default branch safe and passing, and use placeholders for sensitive
configuration examples.

## Low risk

- Fix a typo or clarify setup instructions in `README.md`.
- Add a pure formatting or display helper in `app/services/notification_service.py`
  with a focused unit test.
- Expand a test in `tests/` to cover an existing validation edge case.
- Correct a non-security-related response message while preserving status codes.

Expected review focus: small scope, no changes to authorization or persisted
data, and existing tests continue to pass.

## Medium risk

- Add a nullable profile field with a forward-compatible change to
  `migrations/initial_schema.sql`, then update the model, repository, schema,
  service, and tests.
- Change password or session behavior in `app/core/security.py` and
  `app/api/auth.py`; review compatibility, expiration, and error handling.
- Change a default in `app/core/config.py`; verify local setup, CI, and
  deployment assumptions.
- Update order persistence in both `app/repositories/order_repository.py` and
  `app/services/order_service.py`; verify transaction boundaries and state
  transitions.
- Modify multiple service/repository layers without adding corresponding tests.

Expected review focus: behavior across layers, migration compatibility,
authorization boundaries, and missing test coverage.

## High risk (safe, hypothetical review prompts)

Do not merge unsafe examples into the default branch. A dedicated test PR may
describe or stage a proposed change for SecurePR to review, then be closed or
reverted without deploying it.

- **Destructive migration pattern:** propose dropping or rewriting existing
  account/order tables in a migration. Review data loss, rollback strategy,
  backup requirements, and whether a reversible migration is possible. Keep
  this as a review diff only; do not run it against data that matters.
- **Authorization boundary change:** propose removing the ownership check for
  `GET /orders/{order_id}` or making a customer-facing router depend on the
  admin role instead of the current-user check. Review for cross-account data
  access and unintended privilege changes; do not merge that behavior.
- **Sensitive configuration surface:** propose printing an authentication
  token or a value named `PAYMENT_PROVIDER_SECRET` to logs, or adding a
  placeholder such as `PAYMENT_PROVIDER_SECRET=<example-only>`. The review
  should flag secret-handling and log exposure. Never use a real value.
- **Deployment/infrastructure surface:** propose broadening a workflow
  permission from read-only to write-all, or removing a deployment approval
  gate in a hypothetical deployment file. Review privilege scope and release
  controls; do not add credentials or deploy the sample service.
- **Authentication weakening:** propose accepting a fixed token or skipping
  password verification in `app/core/security.py`. Review the account takeover
  impact and retain the secure implementation in the default branch.

Expected review focus: high-impact data loss, privilege escalation, exposure
of credentials or personal data, and changes to the deployment trust boundary.
All examples use fictional data and placeholders; this repository contains no
real credentials, keys, or intentionally exploitable defaults.
