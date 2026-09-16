import java.util.Properties

plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.android)
    alias(libs.plugins.kotlin.compose)
    alias(libs.plugins.kotlin.serialization)
}

val localEnv = Properties().apply {
    rootProject.file(".env")
        .takeIf { it.isFile }
        ?.inputStream()
        ?.use(::load)
}

fun envValue(name: String, defaultValue: String): String =
    providers.environmentVariable(name).orNull
        ?.trim()
        ?.takeIf { it.isNotEmpty() }
        ?: localEnv.getProperty(name)?.trim()?.takeIf { it.isNotEmpty() }
        ?: defaultValue

fun buildConfigString(value: String): String =
    "\"${value.replace("\\", "\\\\").replace("\"", "\\\"")}\""

android {
    namespace = "com.rork.eduspark"
    compileSdk = 36

    defaultConfig {
        applicationId = "com.rork.eduspark"
        minSdk = 24
        targetSdk = 36
        versionCode = 1
        versionName = "1.0"

        // Distribution flavour switch (Master Plan §1b / Design System §ST-17).
        // `direct` = sideloaded APK: local payment rails + portal links allowed.
        // `play`   = Google Play build: Play Billing only, no external payment surface.
        // Kept as a BuildConfig constant for now; promoted to real Gradle product
        // flavours at release-engineering time so CI keeps a single release artefact.
        buildConfigField(
            "String",
            "PAYMENT_MODE",
            buildConfigString(envValue("PAYMENT_MODE", "direct"))
        )

        // Feature data stays isolated in memory while auth can be selected independently.
        buildConfigField(
            "String",
            "DATA_SOURCE_MODE",
            buildConfigString(envValue("DATA_SOURCE_MODE", "MOCK"))
        )
        buildConfigField(
            "String",
            "AUTH_DATA_SOURCE_MODE",
            buildConfigString(envValue("AUTH_DATA_SOURCE_MODE", "REMOTE"))
        )
        buildConfigField(
            "String",
            "LEARNING_DATA_SOURCE_MODE",
            buildConfigString(envValue("LEARNING_DATA_SOURCE_MODE", "REMOTE"))
        )
        buildConfigField(
            "String",
            "PROFILE_DATA_SOURCE_MODE",
            buildConfigString(envValue("PROFILE_DATA_SOURCE_MODE", "REMOTE"))
        )
        buildConfigField(
            "String",
            "PLANNER_DATA_SOURCE_MODE",
            buildConfigString(envValue("PLANNER_DATA_SOURCE_MODE", "REMOTE"))
        )
        buildConfigField(
            "String",
            "ROUTINE_DATA_SOURCE_MODE",
            buildConfigString(envValue("ROUTINE_DATA_SOURCE_MODE", "REMOTE"))
        )
        buildConfigField(
            "String",
            "ACHIEVEMENT_DATA_SOURCE_MODE",
            buildConfigString(envValue("ACHIEVEMENT_DATA_SOURCE_MODE", "REMOTE"))
        )
        buildConfigField(
            "String",
            "TEACHER_NOTES_DATA_SOURCE_MODE",
            buildConfigString(envValue("TEACHER_NOTES_DATA_SOURCE_MODE", "REMOTE"))
        )
        buildConfigField(
            "String",
            "QUIZ_DATA_SOURCE_MODE",
            buildConfigString(envValue("QUIZ_DATA_SOURCE_MODE", "REMOTE"))
        )
        buildConfigField(
            "String",
            "API_BASE_URL",
            buildConfigString(envValue("API_BASE_URL", "http://10.0.2.2:8000"))
        )
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            signingConfig = signingConfigs.getByName("debug")
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_11
        targetCompatibility = JavaVersion.VERSION_11
    }

    buildFeatures {
        compose = true
        buildConfig = true
    }
}

kotlin {
    compilerOptions {
        jvmTarget.set(org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_11)
    }
}

dependencies {
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.lifecycle.runtime.ktx)
    implementation(libs.androidx.lifecycle.runtime.compose)
    implementation(libs.androidx.lifecycle.viewmodel.compose)
    implementation(libs.androidx.activity.compose)
    implementation(platform(libs.androidx.compose.bom))
    implementation(libs.androidx.ui)
    implementation(libs.androidx.ui.graphics)
    implementation(libs.androidx.ui.tooling.preview)
    implementation(libs.androidx.material3)
    implementation(libs.androidx.material.icons.extended)
    implementation(libs.androidx.navigation.compose)
    implementation(libs.kotlinx.serialization.json)
    implementation(libs.ktor.client.core)
    implementation(libs.ktor.client.android)
    implementation(libs.ktor.client.content.negotiation)
    implementation(libs.ktor.serialization.json)
    implementation(libs.coil.compose)
    implementation(libs.coil.network.okhttp)
    implementation(libs.koin.androidx.compose)
    implementation(libs.androidx.appcompat)
    implementation(libs.androidx.datastore.preferences)
    implementation(libs.androidx.core.splashscreen)
    testImplementation(kotlin("test-junit"))
    testImplementation(libs.ktor.client.mock)
    debugImplementation(libs.androidx.ui.tooling)
}
