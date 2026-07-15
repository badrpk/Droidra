package com.badrpk.shared.core

import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import java.util.concurrent.TimeUnit

class ApiClient(
    private val baseUrl: String,
    private val gcpApiKey: String = BuildConfig.GCP_API_KEY,
) {
    private val jsonType = "application/json; charset=utf-8".toMediaType()
    private val http = OkHttpClient.Builder()
        .connectTimeout(20, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .build()

    var authToken: String? = null

    fun get(path: String): JSONObject {
        val req = Request.Builder().url(baseUrl.trimEnd('/') + path).apply {
            authToken?.let { header("Authorization", "Bearer $it") }
            if (gcpApiKey.isNotBlank()) header("X-Goog-Api-Key", gcpApiKey)
            header("X-GCP-API-Key", gcpApiKey)
        }.get().build()
        http.newCall(req).execute().use { resp ->
            val body = resp.body?.string().orEmpty().ifBlank { "{}" }
            return JSONObject(body)
        }
    }

    fun post(path: String, payload: JSONObject): JSONObject {
        val req = Request.Builder().url(baseUrl.trimEnd('/') + path).apply {
            authToken?.let { header("Authorization", "Bearer $it") }
            if (gcpApiKey.isNotBlank()) header("X-Goog-Api-Key", gcpApiKey)
            header("X-GCP-API-Key", gcpApiKey)
        }.post(payload.toString().toRequestBody(jsonType)).build()
        http.newCall(req).execute().use { resp ->
            val body = resp.body?.string().orEmpty().ifBlank { "{}" }
            return JSONObject(body)
        }
    }
}

data class AuthSession(
    val token: String,
    val email: String,
    val name: String,
    val otpRequired: Boolean = false,
    val demoOtp: String? = null,
)

class AuthRepository(private val api: ApiClient) {
    fun signup(email: String, password: String, name: String = ""): AuthSession {
        val r = api.post("/auth/signup", JSONObject()
            .put("email", email).put("password", password).put("name", name))
        if (!r.optBoolean("ok")) error(r.optString("error", "signup_failed"))
        val otp = r.optJSONObject("otp")
        return AuthSession(
            token = r.optString("token", ""),
            email = email,
            name = name,
            otpRequired = r.optBoolean("otp_required", true),
            demoOtp = otp?.optString("demo_code")?.ifBlank { null },
        )
    }

    fun login(email: String, password: String): AuthSession {
        val r = api.post("/auth/login", JSONObject().put("email", email).put("password", password))
        if (!r.optBoolean("ok")) error(r.optString("error", "login_failed"))
        val token = r.optString("token", "")
        if (token.isNotBlank()) api.authToken = token
        val otp = r.optJSONObject("otp")
        return AuthSession(
            token = token,
            email = email,
            name = r.optJSONObject("user")?.optString("name").orEmpty(),
            otpRequired = r.optBoolean("otp_required", false),
            demoOtp = otp?.optString("demo_code")?.ifBlank { null },
        )
    }

    fun verifyOtp(email: String, code: String): AuthSession {
        val r = api.post("/auth/otp/verify", JSONObject().put("email", email).put("code", code))
        if (!r.optBoolean("ok")) error(r.optString("error", "otp_failed"))
        val token = r.optString("token")
        api.authToken = token
        return AuthSession(token, email, r.optJSONObject("user")?.optString("name").orEmpty(), false)
    }

    fun oauthGoogle(email: String, name: String, id: String = email): AuthSession {
        val profile = JSONObject().put("email", email).put("name", name).put("id", id)
        val r = api.post("/auth/oauth/google", JSONObject().put("profile", profile))
        if (!r.optBoolean("ok")) error(r.optString("error", "oauth_failed"))
        val token = r.optString("token")
        api.authToken = token
        return AuthSession(token, email, name, false)
    }

    fun oauthFacebook(email: String, name: String, id: String = email): AuthSession {
        val profile = JSONObject().put("email", email).put("name", name).put("id", id)
        val r = api.post("/auth/oauth/facebook", JSONObject().put("profile", profile))
        if (!r.optBoolean("ok")) error(r.optString("error", "oauth_failed"))
        val token = r.optString("token")
        api.authToken = token
        return AuthSession(token, email, name, false)
    }

    fun capabilities(): JSONObject = try {
        api.get("/auth/capabilities")
    } catch (_: Exception) {
        api.get("/capabilities")
    }
}
