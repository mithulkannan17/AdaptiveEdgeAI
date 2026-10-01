# 🌲 AuraForest Sentinel — Production Deployment Guide

This guide covers all methods to deploy the **AuraForest Sentinel Tactical Edge Platform**, including the **FastAPI Backend Server** (Port `8000`) and the **Streamlit Command Dashboard** (Port `8501`).

---

## 🚀 Option 1: 1-Click Local / Server Deployment (Recommended for Local/Windows/Linux)

The easiest way to run both the FastAPI Backend and Streamlit Dashboard concurrently:

### Windows:
Double-click `start_auraforest.bat` or run in PowerShell:
```powershell
.\.venv\Scripts\python.exe run_system.py
```

### Linux / macOS:
```bash
python3 run_system.py
```

**Services Launched:**
- 🌐 **Sentinel Gateway (Dashboard):** [http://localhost:8501](http://localhost:8501)
- 📡 **FastAPI Backend REST API & Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
- 👑 **Chief Ranger Master Login:** Username: `chief` | Password: `auraadmin123`

---

## 🌐 Option 2: 100% Free Cloud Deployment (Render.com)

Render provides free hosting with automatic HTTPS, continuous deployment from GitHub, and free subdomains (`https://your-app.onrender.com`).

### Step-by-Step Render Deployment:
1. **Push your code to GitHub**:
   ```bash
   git add .
   git commit -m "feat: production cloud deployment ready"
   git push origin main
   ```
2. **Go to [Render Dashboard](https://dashboard.render.com/)**:
   - Sign up / Log in with GitHub.
   - Click **"New +"** -> **"Web Service"**.
   - Connect your **AuraForest** GitHub repository.
3. **Configure the Web Service**:
   - **Name**: `auraforest-sentinel`
   - **Environment**: `Python`
   - **Build Command**: `pip install --upgrade pip && pip install -r requirements.txt`
   - **Start Command**: `python run_system.py`
   - **Instance Type**: `Free`
4. **Add Environment Variables (Secrets)**:
   Under **Environment Variables**, add:
   - `SMTP_HOST` = `smtp.gmail.com`
   - `SMTP_PORT` = `587`
   - `SMTP_SSL` = `false`
   - `SMTP_USER` = `your-gmail@gmail.com`
   - `SMTP_PASS` = `your-16-char-app-password`
   - `SMTP_FROM` = `your-gmail@gmail.com`
5. **Click "Deploy Web Service"**:
   - Render will build dependencies and launch both FastAPI and the Streamlit dashboard on your free `https://auraforest-sentinel.onrender.com` URL!

---

## 🤗 Option 3: 100% Free Permanent Cloud Deployment (Hugging Face Spaces)

Hugging Face Spaces provides 16GB RAM and permanent free cloud hosting with HTTPS.

### Step-by-Step Hugging Face Space Deployment:
1. **Create Space**:
   - Go to [Hugging Face Spaces](https://huggingface.co/spaces) and click **"Create new Space"**.
   - **Space Name**: `auraforest-sentinel`
   - **SDK**: Select **Streamlit** (or **Docker**).
   - **Hardware**: Free (CPU basic - 2 vCPU, 16GB RAM).
2. **Push / Upload Project Files**:
   - Clone the space repo and copy all project files into it, or connect your GitHub repository.
3. **Set Secrets**:
   - In your Space **Settings** -> **Variables and secrets**, add:
     - `SMTP_USER`: `your-gmail@gmail.com`
     - `SMTP_PASS`: `your-16-char-app-password`
     - `SMTP_FROM`: `your-gmail@gmail.com`
     - `SMTP_HOST`: `smtp.gmail.com`
     - `SMTP_PORT`: `587`
     - `SMTP_SSL`: `false`
4. Hugging Face will automatically build and launch the platform at `https://huggingface.co/spaces/<your-username>/auraforest-sentinel`.

---

## 🐳 Option 4: Docker & Docker Compose (Containerized Production)

### 1. Build and Launch:
```bash
docker compose up --build -d
```

### 2. Check Service Logs:
```bash
docker compose logs -f
```

### 3. Stop Services:
```bash
docker compose down
```

---

## ☁️ Option 3: Cloud VPS Deployment (Ubuntu / Debian / AWS EC2 / DigitalOcean)

### Step 1: Install System Dependencies & Python
```bash
sudo apt update && sudo apt install -y python3-pip python3-venv git libsndfile1 ffmpeg nginx
git clone <YOUR_REPO_URL> /opt/auraforest
cd /opt/auraforest
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Step 2: Configure Environment Variables
```bash
cp .env.example .env
nano .env  # Enter your Gmail SMTP credentials
```

### Step 3: Create Systemd Background Service
Create `/etc/systemd/system/auraforest.service`:
```ini
[Unit]
Description=AuraForest Sentinel Tactical Platform
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/auraforest
ExecStart=/opt/auraforest/.venv/bin/python run_system.py
Restart=always
RestartSec=5
Environment=PYTHONPATH=/opt/auraforest

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable auraforest
sudo systemctl start auraforest
sudo systemctl status auraforest
```

### Step 4: Configure Nginx Reverse Proxy with SSL (Port 80/443 -> Port 8501)
Create `/etc/nginx/sites-available/auraforest`:
```nginx
server {
    listen 80;
    server_name sentinel.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```
Enable site and obtain free SSL:
```bash
sudo ln -s /etc/nginx/sites-available/auraforest /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
sudo certbot --nginx -d sentinel.yourdomain.com
```

---

## 🔒 Security & Master Credentials

| Account | Default Username | Default Password | Role |
| :--- | :--- | :--- | :--- |
| **Chief Ranger** | `chief` | `auraadmin123` | Master Administrator (Level 5) |
| **Field Ranger** | Issued by Chief | Generated by System | Field Incident Responder |
| **Public Citizen** | Self Sign-Up | Self Chosen | Eco-Observer & Tip Reporter |

*(Passwords can be changed at any time under **👥 Ranger & User Management** -> **Directory & Edit**)*.
