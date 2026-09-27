# Implementation Plan: User authentication

**Branch**: `001-user-auth` | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/001-user-auth/spec.md`

## Technical Context

**Language**: Python 3.12 · **Storage**: PostgreSQL · **Testing**: pytest

## Phases

1. Session table and store.
2. Sign-in endpoint with the lockout rule.
