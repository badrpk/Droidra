package com.badrpk.khaana

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.badrpk.shared.core.ApiClient
import com.badrpk.shared.core.AuthRepository
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONObject

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val api = ApiClient(BuildConfig.API_BASE, BuildConfig.GCP_API_KEY)
        val auth = AuthRepository(api)
        setContent {
            MaterialTheme(colorScheme = lightColorScheme(primary = Color(0xFFE65100))) {
                Surface(Modifier.fillMaxSize()) {
                    AppRoot(auth, api)
                }
            }
        }
    }
}

@Composable
fun AppRoot(auth: AuthRepository, api: ApiClient) {
    var token by remember { mutableStateOf<String?>(null) }
    var email by remember { mutableStateOf("") }
    if (token == null) {
        AuthScreen(auth, onAuthed = { t, e -> token = t; email = e; api.authToken = t })
    } else {
        HomeScreen(api, email, product = "Khaana", onLogout = { token = null; api.authToken = null })
    }
}

@Composable
fun AuthScreen(auth: AuthRepository, onAuthed: (String, String) -> Unit) {
    val scope = rememberCoroutineScope()
    var mode by remember { mutableStateOf("login") } // login | signup | otp
    var email by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    var name by remember { mutableStateOf("") }
    var otp by remember { mutableStateOf("") }
    var status by remember { mutableStateOf("Sign in to Khaana") }
    var loading by remember { mutableStateOf(false) }
    var pendingEmail by remember { mutableStateOf("") }

    Column(
        Modifier.fillMaxSize().padding(24.dp).verticalScroll(rememberScrollState()),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Box(
            Modifier.size(72.dp).background(Color(0xFFE65100), RoundedCornerShape(18.dp)),
            contentAlignment = Alignment.Center
        ) {
            Text("Khaana"[0].toString(), color = Color.White, fontSize = 32.sp, fontWeight = FontWeight.Bold)
        }
        Spacer(Modifier.height(16.dp))
        Text("Khaana", fontSize = 26.sp, fontWeight = FontWeight.Bold)
        Text(BuildConfig.APP_NAME + " · GCP-enabled Android client", color = Color.Gray, fontSize = 13.sp)
        Spacer(Modifier.height(8.dp))
        Text(status, color = MaterialTheme.colorScheme.primary, fontSize = 14.sp)
        Spacer(Modifier.height(20.dp))

        if (mode != "otp") {
            if (mode == "signup") {
                OutlinedTextField(name, { name = it }, label = { Text("Name") }, modifier = Modifier.fillMaxWidth())
                Spacer(Modifier.height(8.dp))
            }
            OutlinedTextField(email, { email = it }, label = { Text("Email") }, modifier = Modifier.fillMaxWidth())
            Spacer(Modifier.height(8.dp))
            OutlinedTextField(
                password, { password = it }, label = { Text("Password") },
                visualTransformation = PasswordVisualTransformation(),
                modifier = Modifier.fillMaxWidth()
            )
            Spacer(Modifier.height(16.dp))
            Button(
                onClick = {
                    loading = true
                    scope.launch {
                        try {
                            val s = withContext(Dispatchers.IO) {
                                if (mode == "signup") auth.signup(email.trim(), password, name)
                                else auth.login(email.trim(), password)
                            }
                            if (s.otpRequired) {
                                pendingEmail = email.trim()
                                otp = s.demoOtp.orEmpty()
                                mode = "otp"
                                status = "OTP required (first-time). " + (s.demoOtp?.let { "Code: $it" } ?: "Check email")
                            } else if (s.token.isNotBlank()) {
                                onAuthed(s.token, email.trim())
                            } else status = "Unexpected auth response"
                        } catch (e: Exception) {
                            status = e.message ?: "Auth failed"
                        } finally { loading = false }
                    }
                },
                enabled = !loading && email.isNotBlank() && password.length >= 6,
                modifier = Modifier.fillMaxWidth().height(52.dp)
            ) { Text(if (mode == "signup") "Sign up" else "Sign in") }

            TextButton(onClick = { mode = if (mode == "login") "signup" else "login" }) {
                Text(if (mode == "login") "Create account" else "Have an account? Sign in")
            }

            Spacer(Modifier.height(8.dp))
            Text("Existing verified users skip OTP. Social login never needs OTP.", fontSize = 12.sp, color = Color.Gray)
            Spacer(Modifier.height(8.dp))
            OutlinedButton(
                onClick = {
                    loading = true
                    scope.launch {
                        try {
                            val s = withContext(Dispatchers.IO) {
                                auth.oauthGoogle(email.ifBlank { "user@gmail.com" }, name.ifBlank { "Google User" })
                            }
                            onAuthed(s.token, s.email)
                        } catch (e: Exception) { status = e.message ?: "Google login failed" }
                        finally { loading = false }
                    }
                },
                modifier = Modifier.fillMaxWidth()
            ) { Text("Continue with Google / Gmail") }
            OutlinedButton(
                onClick = {
                    loading = true
                    scope.launch {
                        try {
                            val s = withContext(Dispatchers.IO) {
                                auth.oauthFacebook(email.ifBlank { "user@facebook.com" }, name.ifBlank { "Facebook User" })
                            }
                            onAuthed(s.token, s.email)
                        } catch (e: Exception) { status = e.message ?: "Facebook login failed" }
                        finally { loading = false }
                    }
                },
                modifier = Modifier.fillMaxWidth()
            ) { Text("Continue with Facebook") }
        } else {
            Text("Enter OTP for $pendingEmail", fontWeight = FontWeight.SemiBold)
            Spacer(Modifier.height(8.dp))
            OutlinedTextField(otp, { otp = it }, label = { Text("6-digit OTP") }, modifier = Modifier.fillMaxWidth())
            Spacer(Modifier.height(12.dp))
            Button(
                onClick = {
                    loading = true
                    scope.launch {
                        try {
                            val s = withContext(Dispatchers.IO) { auth.verifyOtp(pendingEmail, otp.trim()) }
                            onAuthed(s.token, pendingEmail)
                        } catch (e: Exception) { status = e.message ?: "OTP failed" }
                        finally { loading = false }
                    }
                },
                modifier = Modifier.fillMaxWidth().height(52.dp)
            ) { Text("Verify OTP") }
            TextButton(onClick = { mode = "login" }) { Text("Back") }
        }
        if (loading) {
            Spacer(Modifier.height(16.dp))
            CircularProgressIndicator()
        }
        Spacer(Modifier.height(24.dp))
        Text("API: ${BuildConfig.API_BASE}", fontSize = 11.sp, color = Color.Gray)
        Text("GCP key configured: ${BuildConfig.GCP_API_KEY.isNotBlank()}", fontSize = 11.sp, color = Color.Gray)
    }
}

@Composable
fun HomeScreen(api: ApiClient, email: String, product: String, onLogout: () -> Unit) {
    val scope = rememberCoroutineScope()
    var body by remember { mutableStateOf("Loading capabilities…") }
    var busy by remember { mutableStateOf(false) }
    LaunchedEffect(Unit) {
        busy = true
        body = try {
            withContext(Dispatchers.IO) {
                val cap = try { api.get("/auth/capabilities") } catch (_: Exception) {
                    try { api.get("/capabilities") } catch (_: Exception) { api.get("/health") }
                }
                cap.toString(2)
            }
        } catch (e: Exception) { "Error: ${e.message}\n\nStart the backend API, then pull to refresh." }
        busy = false
    }
    Column(Modifier.fillMaxSize().padding(20.dp)) {
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
            Column {
                Text(product, fontSize = 22.sp, fontWeight = FontWeight.Bold)
                Text(email, color = Color.Gray, fontSize = 13.sp)
            }
            TextButton(onClick = onLogout) { Text("Logout") }
        }
        Spacer(Modifier.height(12.dp))
        Text("Multi-vendor food delivery", color = Color.DarkGray)
        Spacer(Modifier.height(12.dp))
        Row {
            Button(onClick = {
                busy = true
                scope.launch {
                    body = try {
                        withContext(Dispatchers.IO) {
                            try { api.get("/auth/capabilities") } catch (_: Exception) {
                                try { api.get("/capabilities") } catch (_: Exception) { api.get("/health") }
                            }.toString(2)
                        }
                    } catch (e: Exception) { e.message ?: "failed" }
                    busy = false
                }
            }) { Text("Refresh API") }
            Spacer(Modifier.width(8.dp))
            OutlinedButton(onClick = {
                busy = true
                scope.launch {
                    body = try {
                        withContext(Dispatchers.IO) {
                            api.get("/pricing").toString(2)
                        }
                    } catch (e: Exception) { "No /pricing or error: ${e.message}" }
                    busy = false
                }
            }) { Text("Pricing") }
        }
        Spacer(Modifier.height(12.dp))
        if (busy) LinearProgressIndicator(Modifier.fillMaxWidth())
        Card(Modifier.fillMaxSize(), shape = RoundedCornerShape(16.dp)) {
            Text(
                body,
                Modifier.padding(16.dp).verticalScroll(rememberScrollState()),
                fontSize = 12.sp,
                fontFamily = androidx.compose.ui.text.font.FontFamily.Monospace
            )
        }
    }
}
