package com.emrsresult.monitor

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import com.example.monitor.ui.theme.EMRSResultMonitorTheme
import com.google.firebase.messaging.FirebaseMessaging

class MainActivity : ComponentActivity() {

    private val notificationPermissionLauncher =
        registerForActivityResult(
            ActivityResultContracts.RequestPermission()
        ) { granted ->
            if (granted) {
                subscribeToNotifications()
            } else {
                Toast.makeText(
                    this,
                    "Notification permission is required",
                    Toast.LENGTH_LONG
                ).show()
            }
        }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        handleNotificationIntent(intent)

        requestNotificationPermission()

        setContent {
            EMRSResultMonitorTheme {
                Scaffold(
                    modifier = Modifier.fillMaxSize()
                ) { innerPadding ->
                    Column(
                        modifier = Modifier
                            .fillMaxSize()
                            .padding(innerPadding),
                        horizontalAlignment = Alignment.CenterHorizontally,
                        verticalArrangement = Arrangement.Center
                    ) {
                        Text(text = "EMRS Result Monitor")
                    }
                }
            }
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        handleNotificationIntent(intent)
    }

    private fun handleNotificationIntent(intent: Intent?) {
        val url = intent?.getStringExtra("url")

        if (!url.isNullOrBlank()) {
            try {
                val browserIntent = Intent(
                    Intent.ACTION_VIEW,
                    Uri.parse(url)
                )
                startActivity(browserIntent)
            } catch (e: Exception) {
                Toast.makeText(
                    this,
                    "Unable to open PDF URL",
                    Toast.LENGTH_LONG
                ).show()
            }
        }
    }

    private fun requestNotificationPermission() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            if (
                ContextCompat.checkSelfPermission(
                    this,
                    Manifest.permission.POST_NOTIFICATIONS
                ) != PackageManager.PERMISSION_GRANTED
            ) {
                notificationPermissionLauncher.launch(
                    Manifest.permission.POST_NOTIFICATIONS
                )
            } else {
                subscribeToNotifications()
            }
        } else {
            subscribeToNotifications()
        }
    }

    private fun subscribeToNotifications() {
        FirebaseMessaging.getInstance()
            .subscribeToTopic("emrs_results")
            .addOnCompleteListener { task ->

                if (task.isSuccessful) {
                    Toast.makeText(
                        this,
                        "Notifications enabled",
                        Toast.LENGTH_SHORT
                    ).show()

                    println("FCM: subscribed to emrs_results")
                } else {
                    Toast.makeText(
                        this,
                        "Failed to enable notifications",
                        Toast.LENGTH_LONG
                    ).show()

                    println("FCM: topic subscription failed")
                }
            }
    }
}