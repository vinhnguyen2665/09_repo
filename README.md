# ⚡ Zero9Repo (Universal Enterprise Package Repository Manager)

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python: 3.12+](https://img.shields.io/badge/Python-3.12%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688.svg)](https://fastapi.tiangolo.com)
[![React: 18](https://img.shields.io/badge/React-18-61dafb.svg)](https://reactjs.org/)
[![TailwindCSS](https://img.shields.io/badge/Tailwind-3.4-38bdf8.svg)](https://tailwindcss.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ed.svg)](https://www.docker.com/)

[**Tiếng Việt (Vietnamese Documentation)**](./README.vi.md)

**Zero9Repo** is a lightweight, high-performance, async Universal Package Repository Manager. It is built with **Python 3.12+ FastAPI**, **SQLAlchemy 2.0 Async ORM**, **Aiofiles**, and a sleek **React + TypeScript + Tailwind CSS + Ant Design** Web Dashboard.

---

## 🌟 Key Architectural Features

### 1. Multi-Format Package Engines
- **☕ Maven / Gradle Engine** (`/repository/maven-private/`, `/repository/maven-proxy/`, `/repository/maven-group/`):
  - Supports HTTP `GET`, `PUT`, and `HEAD` methods.
  - Handles artifacts (`.jar`, `.war`, `.aar`, `.pom`), companion checksums (`.sha1`, `.md5`, `.sha256`).
  - **Dynamic `maven-metadata.xml` Merge Service**: Merges versions across local and proxy upstream repositories dynamically on Group repos to ensure accurate `LATEST` and `RELEASE` resolution.
  - Native support for `mvn deploy` and Gradle `publish` tasks with HTTP Basic Auth and API tokens.
- **📦 NPM Registry Engine** (`/repository/npm-private/`, `/repository/npm-proxy/`, `/repository/npm-group/`):
  - CouchDB-compatible user authentication (`/-/user/org.couchdb.user:*`).
  - Native `npm publish` support (base64 tarball extraction, indexing, and metadata generation).
  - Proxy fallback with automatic local caching from `https://registry.npmjs.org/`.
- **🐳 Docker / OCI Container Registry Engine** (`/v2/`):
  - Compliant with Docker Registry HTTP API V2 & OCI Image Specification v1.0.
  - Supports image manifests (`/v2/<name>/manifests/<tag_or_digest>`) and layer blobs (`/v2/<name>/blobs/<digest>`).
  - Chunked and monolithic blob uploads (`/v2/<name>/blobs/uploads/`).
  - Full compatibility with `docker login`, `docker tag`, `docker push`, and `docker pull`.
- **🐍 Python PyPI Engine** (`/repository/pypi-private/`, `/repository/pypi-proxy/`, `/repository/pypi-group/`):
  - PEP 503 Simple Repository API for `pip install`.
  - Multipart upload handler for `twine upload`.
  - Lazy proxy caching for wheel (`.whl`) and source tarballs from PyPI.org.

### 2. Repository Types & Smart Proxy Caching
For every package ecosystem, Zero9Repo supports 3 distinct repository types:
1. **Hosted (Private)**: Direct deployment and persistent internal storage on local disk.
2. **Proxy**: Lazy-fetches packages from remote upstream registries (Maven Central, npmjs.org, PyPI.org) on cache-miss, caching them permanently to local disk with configurable TTL.
3. **Group**: Unified endpoint combining multiple Hosted & Proxy repositories in prioritized order. If a requested package is missing from internal repos, it is automatically fetched from upstream proxies, stored in local cache, and served immediately to the developer.

### 3. High Performance Storage & Streaming Layer
- **Async I/O (`aiofiles`)**: Zero-memory overhead streaming file responses with HTTP `Range: bytes=start-end` support for large artifacts (>1GB).
- **Directory Tree Navigation & Inspector**: File tree exploration, SHA1/MD5/SHA256 checksum verification, built-in XML/JSON/Code preview modal, and recursive deletion cleanup.

### 4. Security & Role-Based Access Control (RBAC)
- **Authentication**: JWT Bearer Tokens, HTTP Basic Auth (for Maven, Gradle, NPM, Pip, Twine, Docker CLI), and Personal API Tokens (`z9r_...`).
- **RBAC Roles**:
  - `Admin`: Full management over repositories, user accounts, and storage cleanup.
  - `Developer`: Can deploy and publish artifacts (`mvn deploy`, `npm publish`, `docker push`, `twine upload`) and download packages.
  - `Reader`: Read-only pull and download access.
- **Password Security**: Bcrypt hashing with salted rounds.
- **Default Admin Account**: Auto-seeded on initial boot (`admin` / `admin123`).

---

## 🚀 Deployment Guide

### Method 1: Docker Compose (Recommended for Production)

1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/Zero9Repo.git
   cd Zero9Repo
   ```

2. Start services with Docker Compose:
   ```bash
   docker-compose up -d --build
   ```

3. Check container logs:
   ```bash
   docker-compose logs -f zero9repo
   ```

4. Access the Web Dashboard:
   - **URL**: `http://localhost:8000`
   - **Default Username**: `admin`
   - **Default Password**: `admin123`

All persistent data (SQLite database, cached packages, and uploaded artifacts) is stored safely inside the `zero9repo_data` volume (or `./data`).

---

### Method 2: Standalone Docker Run

```bash
# Build Docker image
docker build -t zero9repo:latest .

# Run container with volume mount
docker run -d \
  --name zero9repo-app \
  -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  -e SECRET_KEY="your-production-secret-key" \
  -e ADMIN_USERNAME="admin" \
  -e ADMIN_PASSWORD="admin123" \
  zero9repo:latest
```

---

## 💻 Local Development Setup

### Prerequisites
- **Python 3.12+**
- **Node.js 20+** and **npm**

### Step 1: Backend Setup
```bash
cd backend

# Create and activate virtual environment
python -m venv venv

# On Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# On Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run backend server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
API Documentation will be available at: `http://localhost:8000/docs`.

### Step 2: Frontend Setup
```bash
cd frontend

# Install packages
npm install

# Start Vite dev server
npm run dev
```
Frontend development server will be available at: `http://localhost:3000` (proxied to backend at `:8000`).

### Step 3: Run Automated Test Suite
```bash
cd backend
.\venv\Scripts\python.exe -m pytest -v -s tests/test_all_engines.py
```

---

## 📋 Client Connect & Configuration Guide

### 1. Maven Configuration

#### A. Configure credentials in `~/.m2/settings.xml`:
```xml
<settings>
  <servers>
    <server>
      <id>zero9repo</id>
      <username>admin</username>
      <password>admin123</password> <!-- or your z9r_ API Token -->
    </server>
  </servers>
  <mirrors>
    <mirror>
      <id>zero9repo-mirror</id>
      <mirrorOf>*</mirrorOf>
      <url>http://localhost:8000/repository/maven-group/</url>
    </mirror>
  </mirrors>
</settings>
```

#### B. Configure deployment in your project's `pom.xml`:
```xml
<project>
  ...
  <distributionManagement>
    <repository>
      <id>zero9repo</id>
      <name>Zero9Repo Hosted Releases</name>
      <url>http://localhost:8000/repository/maven-private/</url>
    </repository>
  </distributionManagement>
</project>
```
Deploy artifact:
```bash
mvn clean deploy
```

---

### 2. Gradle Configuration

In your `build.gradle` (Groovy DSL):
```groovy
repositories {
    maven {
        url "http://localhost:8000/repository/maven-group/"
        credentials {
            username = "admin"
            password = "admin123"
        }
    }
}

publishing {
    repositories {
        maven {
            url = "http://localhost:8000/repository/maven-private/"
            credentials {
                username = "admin"
                password = "admin123"
            }
        }
    }
}
```
Publish artifact:
```bash
gradle publish
```

---

### 3. NPM Configuration

#### A. Configure project `.npmrc`:
```ini
registry=http://localhost:8000/repository/npm-group/
//localhost:8000/repository/npm-private/:_authToken=z9r_YOUR_API_TOKEN
always-auth=true
```

#### B. Publish a package:
```bash
# Set publish registry to hosted private repo
npm config set registry http://localhost:8000/repository/npm-private/

# Publish
npm publish
```

---

### 4. Docker / OCI Registry Configuration

```bash
# 1. Login to Zero9Repo Registry
docker login localhost:8000
# Username: admin
# Password: admin123 (or your API Token)

# 2. Tag your container image
docker tag my-image:latest localhost:8000/my-image:1.0.0

# 3. Push to Zero9Repo
docker push localhost:8000/my-image:1.0.0

# 4. Pull image
docker pull localhost:8000/my-image:1.0.0
```

---

### 5. Python / Pip & Twine Configuration

#### A. Configure Pip (`~/.pip/pip.conf` on Linux/macOS or `%APPDATA%\pip\pip.ini` on Windows):
```ini
[global]
index-url = http://localhost:8000/repository/pypi-group/simple/
trusted-host = localhost
```
Install packages:
```bash
pip install requests
```

#### B. Upload packages with Twine (`~/.pypirc`):
```ini
[distutils]
index-servers =
    zero9repo

[zero9repo]
repository = http://localhost:8000/repository/pypi-private/
username = __token__
password = z9r_YOUR_API_TOKEN
```
Upload distribution:
```bash
twine upload --repository zero9repo dist/*
```

---

## 📁 Project Directory Structure

```text
├── backend/
│   ├── app/
│   │   ├── api/                  # REST Routers (auth, users, repos, explorer, stats, dispatcher)
│   │   ├── core/                 # Config, Database engine, Security (Bcrypt, JWT), RBAC
│   │   ├── models/               # SQLAlchemy Models (User, ApiToken, Repository, Artifact)
│   │   ├── schemas/              # Pydantic Request/Response Models
│   │   ├── services/             # Storage Engine, Proxy Client, Maven/NPM/Docker/PyPI Engines
│   │   └── main.py               # FastAPI App & Startup Seeding
│   ├── tests/                    # End-to-End Test Suite
│   └── requirements.txt          # Python Dependencies
├── frontend/
│   ├── src/
│   │   ├── api/                  # Axios Client & React Query Hooks
│   │   ├── components/           # Dashboard, Storage Explorer, Repo Manager, Snippets, Users
│   │   ├── context/              # Auth Context
│   │   ├── types/                # TypeScript Interfaces
│   │   ├── App.tsx               # App Root & Navigation
│   │   └── main.tsx              # React DOM Bootstrap
│   ├── package.json              # Frontend Dependencies
│   └── vite.config.ts            # Vite Configuration & Backend Proxy
├── data/                         # Persistent Storage (SQLite DB, Uploaded & Cached Packages)
├── Dockerfile                    # Multi-stage Container Build
├── docker-compose.yml            # Production Compose Stack
├── README.md                     # English Documentation
└── README.vi.md                  # Vietnamese Documentation
```

---

## 🛡️ License

This project is open-source and licensed under the [Apache License 2.0](LICENSE).
