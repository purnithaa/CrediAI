# Deploy CrediAI to Render

Use these steps to deploy the CrediAI Streamlit app on [Render](https://render.com) and get a public URL (then use that URL in the Android app).

---

## 1. Push your code to GitHub

If the project isn’t in a Git repo yet:

```bash
cd "c:\Users\L E N O V O\OneDrive\Desktop\credi_ai"
git init
git add .
git commit -m "Initial commit - CrediAI + Render config"
```

Create a new repository on [GitHub](https://github.com/new), then:

```bash
git remote add origin https://github.com/YOUR_USERNAME/credi_ai.git
git branch -M main
git push -u origin main
```

Replace `YOUR_USERNAME/credi_ai` with your actual repo URL.

---

## 2. Create a Web Service on Render

1. Go to **[dashboard.render.com](https://dashboard.render.com)** and sign in (or sign up with GitHub).
2. Click **New +** → **Web Service**.
3. Connect your GitHub account if needed, then select the **credi_ai** repository (or the repo you pushed).
4. Use these settings:

   | Field | Value |
   |-------|--------|
   | **Name** | `credi-ai` (or any name) |
   | **Region** | Choose closest to you |
   | **Branch** | `main` |
   | **Runtime** | `Python 3` |
   | **Build Command** | `pip install -r requirements.txt` |
   | **Start Command** | `streamlit run app.py --server.address 0.0.0.0 --server.port $PORT` |

5. (Optional) Under **Environment**, add:
   - **Key:** `PYTHON_VERSION`  
   - **Value:** `3.11.7`

6. Click **Create Web Service**.

Render will build and deploy. The first build can take several minutes (installing `torch` and `transformers`).

---

## 3. Get your app URL

When the deploy finishes, Render shows a URL like:

**`https://credi-ai-xxxx.onrender.com`**

Use this URL in the Android app:

- Open **`android-app/app/src/main/res/values/strings.xml`**
- Set:  
  `<string name="credi_app_url">https://credi-ai-xxxx.onrender.com</string>`

---

## 4. (Optional) Deploy via Blueprint

If your repo already has **`render.yaml`** (this project does):

1. On Render: **New +** → **Blueprint**.
2. Connect the **credi_ai** repo and select it.
3. Render will read `render.yaml` and create the Web Service with the same build/start commands. Click **Apply**.

---

## Notes

- **Free tier:** The service may spin down after ~15 minutes of no traffic. The first request after that can take 30–60 seconds while it starts again.
- **Secrets:** If you use API keys (e.g. Twitter), add them as **Environment Variables** in the Render dashboard (Environment tab), not in code.
- **Heavy dependencies:** `torch` and `transformers` make the build slow and the service memory-heavy. If you hit memory limits, consider a paid plan or a lighter model setup.

After deployment, your Streamlit app URL is the one you put in the Android app’s `strings.xml`.
