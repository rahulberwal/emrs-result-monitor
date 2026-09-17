package com.emrsresult.monitor

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Intent
import android.net.Uri
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage

class MyFirebaseMessagingService : FirebaseMessagingService() {

    companion object {
        private const val CHANNEL_ID = "nests_results"
        private const val CHANNEL_NAME = "NESTS Results"
        private const val NOTIFICATION_ID = 1001
    }

    override fun onMessageReceived(remoteMessage: RemoteMessage) {

        val title = remoteMessage.data["title"] ?: "🚨 NESTS PDF FOUND"
        val body = remoteMessage.data["body"] ?: "A new NESTS PDF has been detected."
        val url = remoteMessage.data["url"]

        createNotificationChannel()

        val intent = if (!url.isNullOrBlank()) {
            Intent(Intent.ACTION_VIEW, Uri.parse(url))
        } else {
            Intent(this, MainActivity::class.java)
        }

        intent.flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP

        val pendingIntent = PendingIntent.getActivity(
            this,
            NOTIFICATION_ID,
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        val notification = NotificationCompat.Builder(this, CHANNEL_ID)
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setContentTitle(title)
            .setContentText(body)
            .setStyle(NotificationCompat.BigTextStyle().bigText(body))
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setAutoCancel(true)
            .setContentIntent(pendingIntent)
            .build()

        NotificationManagerCompat.from(this)
            .notify(NOTIFICATION_ID, notification)
    }

    private fun createNotificationChannel() {

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {

            val channel = NotificationChannel(
                CHANNEL_ID,
                CHANNEL_NAME,
                NotificationManager.IMPORTANCE_HIGH
            ).apply {
                description = "Notifications when a new NESTS PDF is detected"
            }

            val manager = getSystemService(NotificationManager::class.java)

            manager.createNotificationChannel(channel)
        }
    }
}