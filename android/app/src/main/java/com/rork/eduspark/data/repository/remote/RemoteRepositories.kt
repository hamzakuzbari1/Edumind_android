package com.rork.eduspark.data.repository.remote

/**
 * ══════════════════════════════════════════════════════════════════════════
 * REMOTE IMPLEMENTATIONS — intentionally empty.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * This package is the reserved home for the FastAPI-backed repositories. It contains no
 * code yet, and that is deliberate:
 *
 *  • The backend is the source of truth and is NOT connected in this phase.
 *  • Writing speculative Ktor calls now would mean inventing routes, field names and
 *    response envelopes — the single most expensive mistake available to us, because the
 *    fiction would be copied into every screen built on top of it.
 *
 * When integration begins, the sequence is:
 *   1. Export `openapi.json` from the FastAPI service.
 *   2. Generate the typed client + models into a `data/api/generated` package.
 *   3. Add `RemoteAuthRepository` / `RemoteLearningRepository` here, implementing the
 *      SAME interfaces in `data/repository`, plus DTO → domain mappers.
 *   4. Flip `DATA_SOURCE_MODE` in `build.gradle.kts` from MOCK to REMOTE.
 *
 * Nothing in `ui/` changes at any point in that sequence. Two backend realities must be
 * honoured by whoever writes these classes:
 *   • There is no refresh endpoint — map 401 to `AppError.SessionExpired` and sign out.
 *   • Media URLs come back relative (`/uploads/...`) and must be prefixed with the API host.
 */
