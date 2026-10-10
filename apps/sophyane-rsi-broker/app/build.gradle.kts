plugins {
    id("com.android.application")
}

android {
    namespace = "com.sophyane.rsi.broker"
    compileSdk = 36

    defaultConfig {
        applicationId = "com.sophyane.rsi.broker"
        minSdk = 26
        targetSdk = 36
        versionCode = 1
        versionName = "0.1.0"
    }

    buildTypes {
        getByName("release") {
            // Remove generated classes unused by this code-free broker.
            // The compiled APK must still pass the strict no-DEX verifier.
            isMinifyEnabled = true
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}
