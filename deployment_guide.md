# Production Deployment Guide: Vercel (Frontend) & Render (Backend)

This guide outlines the production deployment steps for the SalesOP Operational Intelligence & Data Reliability Platform. We have pre-emptively audited the codebase, patched potential blockers, and structured a seamless deployment checklist.

---

## 1. Backend Deployment (Render)

Render hosts the FastAPI application (`backend/` directory). Follow these steps to set up and configure the web service.

### A. Render Configuration Checklist
1.  **Create Web Service:** Connect your GitHub repository to Render and choose the `backend` directory.
2.  **Environment:** Select `Python` as the runtime.
3.  **Build Command:** 
    ```bash
    pip install -r requirements.txt
    ```
    > [!IMPORTANT]
    > **Dependency Stability:** We patched `requirements.txt` to explicitly pin `bcrypt==3.2.2`. This prevents Render from installing incompatible `bcrypt>=4.0` releases which cause crash-on-login issues with `passlib`.
4.  **Start Command:**
    ```bash
    uvicorn app.main:app --host 0.0.0.0 --port $PORT
    ```

### B. Environment Variables (Render Dashboard)
Add the following variables in the **Environment** tab:

| Variable | Description | Example / Recommended Value |
| :--- | :--- | :--- |
| `DATABASE_URL` | Neon PostgreSQL database connection string | `postgresql://neondb_owner:...` (Use Neon pooler string) |
| `SECRET_KEY` | Strong key for JWT access token signatures | Generate using: `openssl rand -hex 32` |
| `GROQ_API_KEY` | API Key for constrained AI interpretation | `YOUR_GROQ_API_KEY_HERE` |
| `BACKEND_CORS_ORIGINS` | Comma-separated list of authorized Vercel domains | `https://salesop.vercel.app,https://salesop-dev.vercel.app` |

> [!NOTE]
> **Dynamic CORS Origins:** We updated the backend middleware (`backend/app/main.py`) to parse `BACKEND_CORS_ORIGINS` dynamically. This prevents cross-origin resource sharing (CORS) blocks between the Next.js Vercel frontend and the Render API.

### C. Critical: Persistent File Storage (Render Disk)
*   **The Issue:** Render instances use an ephemeral filesystem. If the container restarts (daily or on new deploys), any CSV files stored in `data/uploads` will be lost. This would cause the **Auto-Merge** feature to fail since it reads the merged datasets from disk.
*   **The Solution:** In your Render Web Service dashboard:
    1. Go to the **Disks** tab.
    2. Click **Add Disk**.
    3. Name: `uploads-store` (or choice).
    4. Mount Path: `/app/data/uploads` (This is the workspace folder).
    5. Size: `1 GB` (Plenty for CSV datasets).
    This mounts a persistent volume to preserve all uploaded files across deployments and container restarts!

---

## 2. Frontend Deployment (Vercel)

Vercel hosts the Next.js frontend application (`frontend/` directory). 

### A. Vercel Configuration Checklist
1.  **Import Project:** Import your repository into the Vercel Dashboard.
2.  **Root Directory:** Select `frontend` as the root directory.
3.  **Framework Preset:** Select `Next.js`.
4.  **Build Settings:** Default settings are correct.

### B. Environment Variables (Vercel Dashboard)
Prior to hitting deploy, configure the following environment variable:

| Variable | Description | Example / Value |
| :--- | :--- | :--- |
| `NEXT_PUBLIC_API_URL` | Deployed Render backend base API URL | `https://salesop-backend.onrender.com/api/v1` |

> [!IMPORTANT]
> **File Upload Path Resolved:** We updated the file upload interface component (`UploadInterface.tsx`) to pull from `process.env.NEXT_PUBLIC_API_URL` instead of a hardcoded `localhost:8000` destination. This ensures file processing works flawlessly in production.

---

## 3. Post-Deployment Verification Flow

Once both Vercel and Render builds are active and successful:
1.  Navigate to your deployed Vercel URL (e.g. `https://salesop.vercel.app`).
2.  **Verify First Page Welcome Constraint:** You should see the welcome/landing page first.
3.  **Registration / Login Test:** Register a new Work Email, log in, and verify you are redirected to the `/dashboard`.
4.  **Verify New Session:** Confirm that your session starts fresh (tracked under local storage `session_id`).
5.  **CSV Upload & Auto-Merge:** Upload two CSV datasets (e.g., customer list and billing). Wait until their status becomes `VISUALIZATION_READY`. Head to **Auto-Merge**, click merge, and verify that the backend cleanly merges the files and displays the unified `Data Trust Score™` and analytics charts dynamically.
6.  **AI Explorer:** Ask a natural language question inside **NL Explorer** to confirm LLaMA3 interpretation is connected.
7.  **Inactivity Test:** Stay idle for 9 minutes to confirm the countdown warning toast displays, followed by automatic redirect to the login screen on the 10th minute.
