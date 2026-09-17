package com.rork.eduspark.core.session

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json

interface SecureTokenStore {
    suspend fun read(): StoredSession?
    suspend fun write(session: StoredSession)
    suspend fun clear()
}

@Serializable
data class StoredSession(
    val accessToken: String,
    val refreshToken: String,
    val sessionId: Int,
    val userId: String,
)

class EncryptedTokenStore(context: Context) : SecureTokenStore {
    private val delegate = EncryptedSessionStore(
        DataStoreSessionBlobStore(context.applicationContext),
        AndroidKeyStoreSessionCipher(),
    )

    override suspend fun read(): StoredSession? = delegate.read()
    override suspend fun write(session: StoredSession) = delegate.write(session)
    override suspend fun clear() = delegate.clear()
}

internal interface SessionBlobStore {
    suspend fun read(): ByteArray?
    suspend fun write(value: ByteArray)
    suspend fun clear()
}

internal interface SessionCipher {
    fun encrypt(plainText: ByteArray): ByteArray
    fun decrypt(cipherText: ByteArray): ByteArray
}

internal class EncryptedSessionStore(
    private val blobStore: SessionBlobStore,
    private val cipher: SessionCipher,
    private val json: Json = Json,
) : SecureTokenStore {
    private val mutex = Mutex()

    override suspend fun read(): StoredSession? = mutex.withLock {
        val encrypted = blobStore.read() ?: return@withLock null
        runCatching {
            json.decodeFromString<StoredSession>(cipher.decrypt(encrypted).decodeToString())
        }.getOrElse {
            blobStore.clear()
            null
        }
    }

    override suspend fun write(session: StoredSession) = mutex.withLock {
        val bytes = json.encodeToString(StoredSession.serializer(), session).encodeToByteArray()
        blobStore.write(cipher.encrypt(bytes))
    }

    override suspend fun clear() = mutex.withLock { blobStore.clear() }
}

private val Context.authSessionDataStore: DataStore<Preferences> by
    preferencesDataStore(name = "eduspark_auth_session")

private class DataStoreSessionBlobStore(context: Context) : SessionBlobStore {
    private val store = context.authSessionDataStore

    override suspend fun read(): ByteArray? {
        val encoded = store.data.first()[SESSION_BLOB] ?: return null
        return runCatching { Base64.decode(encoded, Base64.NO_WRAP) }.getOrNull()
    }

    override suspend fun write(value: ByteArray) {
        val encoded = Base64.encodeToString(value, Base64.NO_WRAP)
        store.edit { it[SESSION_BLOB] = encoded }
    }

    override suspend fun clear() {
        store.edit { it.remove(SESSION_BLOB) }
    }

    private companion object {
        val SESSION_BLOB = stringPreferencesKey("encrypted_session_v1")
    }
}

private class AndroidKeyStoreSessionCipher : SessionCipher {
    override fun encrypt(plainText: ByteArray): ByteArray {
        val cipher = Cipher.getInstance(TRANSFORMATION)
        cipher.init(Cipher.ENCRYPT_MODE, secretKey())
        val encrypted = cipher.doFinal(plainText)
        return byteArrayOf(FORMAT_VERSION, cipher.iv.size.toByte()) + cipher.iv + encrypted
    }

    override fun decrypt(cipherText: ByteArray): ByteArray {
        require(cipherText.size > HEADER_SIZE)
        require(cipherText[0] == FORMAT_VERSION)
        val ivSize = cipherText[1].toInt() and 0xff
        require(ivSize in 12..16)
        require(cipherText.size > HEADER_SIZE + ivSize)
        val iv = cipherText.copyOfRange(HEADER_SIZE, HEADER_SIZE + ivSize)
        val encrypted = cipherText.copyOfRange(HEADER_SIZE + ivSize, cipherText.size)
        val cipher = Cipher.getInstance(TRANSFORMATION)
        cipher.init(Cipher.DECRYPT_MODE, secretKey(), GCMParameterSpec(GCM_TAG_BITS, iv))
        return cipher.doFinal(encrypted)
    }

    private fun secretKey(): SecretKey = synchronized(KEY_LOCK) {
        val keyStore = KeyStore.getInstance(KEYSTORE_PROVIDER).apply { load(null) }
        (keyStore.getKey(KEY_ALIAS, null) as? SecretKey) ?: generateKey()
    }

    private fun generateKey(): SecretKey {
        val generator = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, KEYSTORE_PROVIDER)
        generator.init(
            KeyGenParameterSpec.Builder(
                KEY_ALIAS,
                KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT,
            )
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .setRandomizedEncryptionRequired(true)
                .build()
        )
        return generator.generateKey()
    }

    private companion object {
        const val KEYSTORE_PROVIDER = "AndroidKeyStore"
        const val KEY_ALIAS = "edumind.auth.session.v1"
        const val TRANSFORMATION = "AES/GCM/NoPadding"
        const val GCM_TAG_BITS = 128
        const val HEADER_SIZE = 2
        const val FORMAT_VERSION: Byte = 1
        val KEY_LOCK = Any()
    }
}

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
