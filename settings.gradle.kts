pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}
dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
    }
}
rootProject.name = "badrpk-android-apps"
include(":shared:core")
include(":apps:sophyane")
include(":apps:khaana")
include(":apps:mypharma")
include(":apps:bijli")
include(":apps:laibabadar")
include(":apps:rangoons")
include(":apps:vps")
include(":apps:shmry")
include(":apps:huobz")
include(":apps:nifdu")
include(":apps:darulsakina")
include(":apps:cast")
include(":apps:xerus")
