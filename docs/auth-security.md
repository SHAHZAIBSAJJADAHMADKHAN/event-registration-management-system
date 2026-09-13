# Authentication and Authorization Security

## JWT verification

FastAPI accepts only Bearer access tokens issued by the configured Supabase project. The backend verifier:

- Obtains public signing keys from SUPABASE_JWKS_URL and caches them.
- Verifies the JWT signature using the key selected by its key ID.
- Enforces SUPABASE_JWT_ISSUER.
- Requires a subject and expiration claim; expired, malformed, and invalid-signature tokens receive HTTP 401.
- Allows a bounded 30-second clock-skew tolerance for issuer/client timestamp differences while still enforcing expiration.
- Does not use role claims from the token as authorization data.

The backend-only GET /auth/me endpoint resolves the current identity and returns the profile-backed role. It is not a login, signup, or token-issuance endpoint.

## Profile and role resolution

After a token is verified, FastAPI loads the matching public.profiles row using backend credentials. The database profile is the authoritative source for full name and role.

The existing auth.users after-insert trigger creates a profile with the attendee role. A missing profile causes authentication to fail safely. No additional migration is required for Phase 3.

## Role and ownership guards

Reusable dependencies are available for:

- require_authenticated_user
- require_admin
- require_attendee
- require_attendee_owned_resource

The ownership helper is intended for future attendee-private routes containing an attendee_id path parameter. It requires both the attendee role and identity equality; it does not grant access merely because a frontend hides another user's controls.

## Admin provisioning

Self-service sign-up always creates attendee profiles. Public profile updates cannot change role because the database trigger rejects non-server role changes.

Admin promotion remains a trusted operational action through the existing server-only provision_admin(profile_id) RPC, callable only with Supabase backend secret-key credentials. A future administrative workflow must authenticate and authorize an existing administrator before calling that server-side capability. No public admin-registration path exists.

## Testing

Unit tests generate local RSA keys to test valid, malformed, invalid-signature, expired, and wrong-issuer tokens without credentials. The opt-in live Supabase test creates isolated users, sends a real Supabase JWT to FastAPI, tests profile-backed role resolution and self-promotion rejection, then cleans up its test data.
