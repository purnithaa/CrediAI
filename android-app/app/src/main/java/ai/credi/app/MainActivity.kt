package ai.credi.app

import android.annotation.SuppressLint
import android.os.Bundle
import android.webkit.WebChromeClient
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import android.view.View
import androidx.activity.OnBackPressedCallback
import androidx.appcompat.app.AppCompatActivity
import androidx.core.view.isVisible
import java.net.HttpURLConnection
import java.net.URL

class MainActivity : AppCompatActivity() {

    private lateinit var webView: WebView
    private lateinit var loadingOverlay: View

    /** Wake the server in the background so the WebView load may hit an already-warming instance. */
    private fun wakeServer(url: String) {
        Thread {
            try {
                val conn = URL(url).openConnection() as HttpURLConnection
                conn.requestMethod = "GET"
                conn.connectTimeout = 15_000
                conn.readTimeout = 10_000
                conn.instanceFollowRedirects = true
                conn.connect()
                conn.responseCode
                conn.disconnect()
            } catch (_: Exception) { /* ignore */ }
        }.start()
    }

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        webView = findViewById(R.id.webview)
        loadingOverlay = findViewById(R.id.loadingOverlay)

        webView.apply {
            settings.apply {
                javaScriptEnabled = true
                domStorageEnabled = true
                cacheMode = WebSettings.LOAD_DEFAULT
                mixedContentMode = WebSettings.MIXED_CONTENT_COMPATIBILITY_MODE
                userAgentString = settings.userAgentString
            }
            webViewClient = object : WebViewClient() {
                override fun onPageFinished(view: WebView?, url: String?) {
                    loadingOverlay.isVisible = false
                }
            }
            webChromeClient = WebChromeClient()
        }

        val appUrl = getString(R.string.credi_app_url).trim()
        if (appUrl.isNotEmpty()) {
            wakeServer(appUrl)
            webView.postDelayed({ webView.loadUrl(appUrl) }, 1200L)
        } else {
            loadingOverlay.isVisible = false
            webView.loadUrl("about:blank")
        }

        onBackPressedDispatcher.addCallback(this, object : OnBackPressedCallback(true) {
            override fun handleOnBackPressed() {
                if (webView.canGoBack()) webView.goBack() else finish()
            }
        })
    }
}
