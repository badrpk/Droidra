plugins {
    id("com.android.library")
    id("org.jetbrains.kotlin.android")
}
android {
    namespace = "com.badrpk.shared.core"
    compileSdk = 34
    defaultConfig {
        minSdk = 26
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
        consumerProguardFiles("consumer-rules.pro")
        val props = rootProject.file("local.properties")
        val gcp = if (props.exists()) {
            props.readLines().mapNotNull {
                val t = it.trim()
                if (t.startsWith("GCP_API_KEY=") || t.startsWith("GOOGLE_API_KEY=")) t.substringAfter("=") else null
            }.firstOrNull() ?: ""
        } else ""
        buildConfigField("String", "GCP_API_KEY", ""$gcp"")
    }
    buildFeatures { buildConfig = true }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions { jvmTarget = "17" }
}
dependencies {
    implementation("androidx.core:core-ktx:1.12.0")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.7.3")
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("org.json:json:20231013")
}
