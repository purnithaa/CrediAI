# Add project specific ProGuard rules here.
# By default, the flags in this file are appended to flags specified
# in SDK_HOME/tools/proguard/proguard-android.txt

# Keep WebView related
-keepclassmembers class * {
    @android.webkit.JavascriptInterface <methods>;
}
