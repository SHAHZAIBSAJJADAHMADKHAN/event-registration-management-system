# Supabase Development Setup

## Local configuration

Copy backend/.env.example to the ignored backend/.env file. Set values only in the local file:

- SUPABASE_URL
- SUPABASE_PUBLISHABLE_KEY
- SUPABASE_SECRET_KEY
- SUPABASE_JWT_ISSUER
- SUPABASE_JWKS_URL
- FRONTEND_ORIGIN
- ENVIRONMENT

The publishable key may later be used by the frontend. The secret key is backend-only and must never be committed, documented with its value, or sent to a browser.

## Migrations

The version-controlled migration is:

- supabase/migrations/20260912000100_event_management_foundation.sql

Apply it exactly once per development database through the approved migration workflow. Before applying it, inspect the database migration state and do not re-run it against a database where it has already been applied.

## Live integration verification

Normal tests do not need Supabase credentials:

    cd backend
    python -m pytest

To run the development-database verification after backend/.env has real values, opt in explicitly:

    cd backend
    $env:RUN_SUPABASE_INTEGRATION_TESTS = 'true'
    python -m pytest

The live test creates uniquely named temporary users and events, verifies schema constraints, RPC behavior, and RLS isolation, then removes its records in reverse dependency order. Run it only against an approved development project.
