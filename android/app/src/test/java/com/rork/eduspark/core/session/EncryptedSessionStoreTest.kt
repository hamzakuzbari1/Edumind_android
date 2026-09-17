package com.rork.eduspark.core.session

import kotlinx.coroutines.runBlocking
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNull

class EncryptedSessionStoreTest {
    @Test
    fun encryptedSessionSavesReadsAndClears() = runBlocking {
        val blob = MemoryBlobStore()
        val store = EncryptedSessionStore(blob, ReversingCipher())
        val session = StoredSession("access-1", "refresh-1", 7, "42")

        store.write(session)

        assertEquals(session, store.read())
        store.clear()
        assertNull(store.read())
    }

    @Test
    fun rotationAtomicallyReplacesBothTokensAndNeverRestoresOldSession() = runBlocking {
        val blob = MemoryBlobStore()
        val store = EncryptedSessionStore(blob, ReversingCipher())
        val old = StoredSession("access-old", "refresh-old", 1, "42")
        val rotated = StoredSession("access-new", "refresh-new", 1, "42")

        store.write(old)
        store.write(rotated)

        assertEquals(rotated, store.read())
    }

    @Test
    fun corruptCiphertextIsRejectedAndCleared() = runBlocking {
        val blob = MemoryBlobStore().apply { value = byteArrayOf(1, 2, 3) }
        val store = EncryptedSessionStore(blob, ReversingCipher())

        assertNull(store.read())
        assertNull(blob.value)
    }
}

private class MemoryBlobStore : SessionBlobStore {
    var value: ByteArray? = null
    override suspend fun read(): ByteArray? = value
    override suspend fun write(value: ByteArray) { this.value = value.copyOf() }
    override suspend fun clear() { value = null }
}

private class ReversingCipher : SessionCipher {
    override fun encrypt(plainText: ByteArray): ByteArray = plainText.reversedArray()
    override fun decrypt(cipherText: ByteArray): ByteArray = cipherText.reversedArray()
}
