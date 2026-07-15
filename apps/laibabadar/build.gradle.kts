plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}
android {
    namespace = "com.badrpk.laibabadar"
    compileSdk = 34
    defaultConfig {
        applicationId = "com.badrpk.laibabadar"
        minSdk = 26
        targetSdk = 34
        versionCode = 1
        versionName = "1.0.0"
        val props = rootProject.file("local.properties")
        fun prop(k: String, d: String = ""): String {
            if (!props.exists()) return d
            return props.readLines().firstOrNull { it.trim().startsWith("$k=") }?.substringAfter("=")?.trim() ?: d
        }
        val host = prop("API_HOST", "10.0.2.2")
        val base = "http://$host:8788"
        buildConfigField("String", "API_BASE", "\"$base\"")
        buildConfigField("String", "APP_NAME", "\"Laiba Badar\"")
        buildConfigField("String", "GCP_API_KEY", "\"${prop("GCP_API_KEY", prop("GOOGLE_API_KEY"))}\"")
        resValue("string", "app_name", "Laiba Badar")
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
