# CrediAI — Android WebView app

This folder contains a minimal Android app that opens your **CrediAI Streamlit app** in a full-screen WebView. Build it into an APK and install on devices or publish to the Play Store.

---

## Prerequisites

1. **Deploy your Streamlit app** and get a public URL (e.g. [Streamlit Community Cloud](https://share.streamlit.io) or [Hugging Face Spaces](https://huggingface.co/spaces)).
2. **Install Android Studio** (with Android SDK and build tools): [developer.android.com/studio](https://developer.android.com/studio).
3. **JDK 17** (Android Studio usually bundles this).

---

## 1. Set your app URL

Before building, set your live CrediAI URL:

- Open **`app/src/main/res/values/strings.xml`**.
- Replace the placeholder with your Streamlit URL:

```xml
<string name="credi_app_url">https://your-actual-app-name.streamlit.app</string>
```

Example: if your app is at `https://credi-ai-fake-news.streamlit.app`, use that exact URL.

### Faster load

The app **wakes the server** in the background before loading the WebView (with a short delay), so the first request often hits an already-warming server and the page can load sooner. For **consistently fast** load (no cold start), point `credi_app_url` to a host that doesn’t sleep, e.g. **Streamlit Community Cloud** or **Hugging Face Spaces**, or use a paid Render plan.

---

## 2. Open the project in Android Studio

1. Launch **Android Studio**.
2. **File → Open** and select the **`android-app`** folder (this folder).
3. Wait for Gradle sync to finish (first time may download dependencies).

---

## 3. Build the APK

### Debug APK (for testing)

1. **Build → Build Bundle(s) / APK(s) → Build APK(s)**.
2. When the build finishes, click **Locate** in the notification.
3. The APK is at:  
   `android-app/app/build/outputs/apk/debug/app-debug.apk`

Install this on a device or emulator (enable “Install from unknown sources” if needed).

### Release APK (for distribution)

1. **Build → Generate Signed Bundle / APK**.
2. Choose **APK** → **Next**.
3. Create or select a keystore:
   - **Create new** (first time): set path, password, alias, key password, validity (e.g. 25 years).
   - **Use existing**: browse to your `.jks` or `.keystore` file and enter passwords.
4. Select **release** build type → **Next** → **Finish**.
5. Release APK path:  
   `android-app/app/build/outputs/apk/release/app-release.apk`

---

## 4. Deploy / distribute the APK

- **Direct install**: Copy `app-debug.apk` or `app-release.apk` to a phone and open it to install.
- **Google Play**: Use the **release** APK (or an AAB from **Build → Generate Signed Bundle / APK → Android App Bundle**) and upload in [Google Play Console](https://play.google.com/console).
- **Other stores / website**: Upload the release APK for users to download and install.

---

## Summary

| Step | Action |
|------|--------|
| 1 | Deploy Streamlit app and copy its URL |
| 2 | Put that URL in `app/src/main/res/values/strings.xml` → `credi_app_url` |
| 3 | Open `android-app` in Android Studio and build APK (debug or release) |
| 4 | Install the APK or publish the release APK/AAB |

The app is a single full-screen WebView; all CrediAI logic runs on your deployed Streamlit server.
