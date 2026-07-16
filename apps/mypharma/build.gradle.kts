plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}
android {
    namespace = "com.badrpk.mypharma"
    compileSdk = 34
    defaultConfig {
        applicationId = "com.badrpk.mypharma"
        minSdk = 26
        targetSdk = 34
        versionCode = 1
        versionName = "1.0.0"
        val propsFile = rootProject.file("local.properties")
        fun prop(key: String, default: String = ""): String {
            if (!propsFile.exists()) return default
            val prefix = key + "="
            return propsFile.readLines()
                .map { it.trim() }
                .firstOrNull { it.startsWith(prefix) }
                ?.removePrefix(prefix)
                ?.trim()
                ?: default
        }
        val host = prop("API_HOST", "10.0.2.2")
        val base = "http://" + host + ":8765"
        val gcp = prop("GCP_API_KEY", prop("GOOGLE_API_KEY", ""))
        buildConfigField("String", "API_BASE", "\"" + base + "\"")
        buildConfigField("String", "APP_NAME", "\"MyPharma\"")
        buildConfigField("String", "GCP_API_KEY", "\"" + gcp.replace("\"", "") + "\"")
        resValue("string", "app_name", "MyPharma")
    }
    signingConfigs {
        create("release") {
            val ks = rootProject.file("secrets/release.keystore")
            if (ks.exists()) {
                storeFile = ks
                storePassword = System.getenv("KEYSTORE_PASSWORD") ?: "android"
                keyAlias = System.getenv("KEY_ALIAS") ?: "badrpk"
                keyPassword = System.getenv("KEY_PASSWORD") ?: "android"
            }
        }
    }
    buildTypes {
        release {
            isMinifyEnabled = false
            signingConfig = signingConfigs.findByName("release")
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
        }
        debug { applicationIdSuffix = ".debug" }
    }
    buildFeatures { compose = true; buildConfig = true }
    composeOptions { kotlinCompilerExtensionVersion = "1.5.8" }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions { jvmTarget = "17" }
    packaging { resources.excludes += "/META-INF/{AL2.0,LGPL2.1}" }
}
dependencies {
    implementation(project(":shared:core"))
    implementation(platform("androidx.compose:compose-bom:2024.02.00"))
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.ui:ui-tooling-preview")
    implementation("androidx.activity:activity-compose:1.8.2")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.7.0")
    implementation("androidx.navigation:navigation-compose:2.7.7")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.7.3")
}
