package com.rork.eduspark.core.session

/**
 * Encrypted storage for the JWT access token and the server session id.
 *
 * Source Audit §3 — the platform issues an access token, a refresh token and a session id,
 * but **there is no refresh endpoint**. A 401 therefore ends the session: the client clears
 * this store and routes to A-04 Login. No silent-refresh path is modelled anywhere, because
 * building one would be designing against a backend capability that does not exist.
 *
 * The concrete Keystore-backed implementation lands with the real API layer; the in-memory
 * implementation below keeps the foundation runnable without pretending to be secure.
 */
interface SecureTokenStore {
    suspend fun read(): StoredSession?
    suspend fun write(session: StoredSession)
    suspend fun clear()
}

data class StoredSession(
    val accessToken: String,
    val sessionId: String,
    val userId: String,
)

/**
 * Development-only store. Explicitly NOT secure and never shipped: it exists so the
 * foundation runs before the Keystore implementation is written alongside the API client.
 */
class InMemoryTokenStore : SecureTokenStore {
    private var session: StoredSession? = null

    override suspend fun read(): StoredSession? = session

    override suspend fun write(session: StoredSession) {
        this.session = session
    }

    override suspend fun clear() {
        session = null
    }
}
