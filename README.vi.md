# ⚡ Zero9Repo - Hệ Thống Quản Lý Kho Gói Package Đa Nền Tảng

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python: 3.12+](https://img.shields.io/badge/Python-3.12%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688.svg)](https://fastapi.tiangolo.com)
[![React: 18](https://img.shields.io/badge/React-18-61dafb.svg)](https://reactjs.org/)
[![TailwindCSS](https://img.shields.io/badge/Tailwind-3.4-38bdf8.svg)](https://tailwindcss.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ed.svg)](https://www.docker.com/)

[**English Documentation**](./README.md)

**Zero9Repo** là hệ thống Repository Manager. Dự án được phát triển bằng **Python 3.12+ FastAPI**, **SQLAlchemy 2.0 Async ORM**, **Aiofiles**, cùng giao diện Web Dashboard quản trị hiện đại bằng **React + TypeScript + Tailwind CSS + Ant Design**.

---

## 🌟 Tính Năng Nổi Bật & Kiến Trúc

### 1. Hỗ Trợ 4 Hệ Sinh Thái Package Phổ Biến Nhất
- **☕ Maven / Gradle Engine** (`/repository/maven-private/`, `/repository/maven-proxy/`, `/repository/maven-group/`):
  - Hỗ trợ đầy đủ các HTTP method `GET`, `PUT`, `HEAD`.
  - Quản lý các file Artifacts (`.jar`, `.war`, `.aar`, `.pom`) và tự động tính toán mã checksum (`.sha1`, `.md5`, `.sha256`).
  - **Dịch vụ gộp `maven-metadata.xml` động (Dynamic Merge Service)**: Khi người dùng kéo package từ Group Repo, hệ thống tự động gộp metadata giữa repo nội bộ và proxy upstream để client luôn nhìn thấy đúng phiên bản `LATEST` và `RELEASE`.
  - Tương thích trực tiếp với lệnh `mvn deploy` và Gradle task `publish`.
- **📦 NPM Registry Engine** (`/repository/npm-private/`, `/repository/npm-proxy/`, `/repository/npm-group/`):
  - Hỗ trợ xác thực người dùng chuẩn CouchDB (`/-/user/org.couchdb.user:*`).
  - Hỗ trợ lệnh `npm publish` (tự động giải nén tarball base64, lập chỉ mục và tạo metadata phiên bản).
  - Tự động proxy fallback và lưu cache từ `https://registry.npmjs.org/`.
- **🐳 Docker / OCI Container Registry Engine** (`/v2/`):
  - Tuân thủ đặc tả OCI Image Specification v1.0 & Docker Registry HTTP API V2.
  - Hỗ trợ quản lý Image Manifest (`/v2/<name>/manifests/<tag>`) và Layer Blobs (`/v2/<name>/blobs/<digest>`).
  - Hỗ trợ upload blob theo chunk hoặc monolithic (`/v2/<name>/blobs/uploads/`).
  - Tương thích hoàn toàn với các lệnh `docker login`, `docker tag`, `docker push` và `docker pull`.
- **🐍 Python PyPI Engine** (`/repository/pypi-private/`, `/repository/pypi-proxy/`, `/repository/pypi-group/`):
  - Hỗ trợ chuẩn PEP 503 Simple Repository API cho lệnh `pip install`.
  - Hỗ trợ multipart upload chuẩn PEP 508 cho lệnh `twine upload`.
  - Tự động kéo và lưu cache các file wheel (`.whl`) và source (`.tar.gz`) từ PyPI.org.

### 2. Ba Loại Repository & Cơ Chế Cache Thông Minh
Với mỗi định dạng package (Maven, NPM, Docker, PyPI), Zero9Repo hỗ trợ 3 loại repository:
1. **Hosted (Nội bộ / Private)**: Dùng để lưu trữ trực tiếp các package nội bộ do đội ngũ phát triển tải lên ổ cứng local.
2. **Proxy**: Tự động lazy-fetch (tải khi có yêu cầu) các package từ các registry trung tâm (Maven Central, npmjs.org, PyPI.org) khi máy khách yêu cầu, sau đó lưu trữ vĩnh viễn trên ổ cứng với thời gian TTL có thể tùy chỉnh.
3. **Group (Nhóm hợp nhất)**: Điểm truy cập duy nhất kết hợp nhiều repo Hosted và Proxy theo thứ tự ưu tiên. **Đặc biệt: Nếu package chưa có trong repo nội bộ, hệ thống sẽ tự động kéo từ proxy upstream về và lưu trữ lại trên ổ cứng nội bộ**, giúp các lần tải tiếp theo nhanh chóng và không phụ thuộc mạng ngoài.

### 3. Tầng Lưu Trữ Bất Đồng Bộ & Tối Ưu Băng Thông
- **Async I/O (`aiofiles`)**: Sử dụng FastAPI `StreamingResponse` với hỗ trợ header `Range: bytes=start-end`, giúp truyền tải các file dung lượng lớn (>1GB) với mức chiếm dụng RAM xấp xỉ bằng 0.
- **Storage Explorer**: Giao diện cây thư mục trực quan, kiểm tra mã băm SHA1/MD5/SHA256, trình xem trước code/XML/JSON tích hợp sẵn, và xóa artifact đệ quy an toàn.

### 4. Bảo Mật & Phân Quyền Vai Trò (RBAC)
- **Phương thức xác thực**: JWT Bearer Token, HTTP Basic Auth (dành cho Maven, Gradle, NPM, Pip, Twine, Docker CLI) và Personal API Token (`z9r_...`).
- **3 Cấp độ phân quyền**:
  - `Admin`: Toàn quyền quản trị hệ thống, thêm/xóa repo, quản lý người dùng.
  - `Developer`: Quyền deploy/publish package (`mvn deploy`, `npm publish`, `docker push`, `twine upload`) và tải package.
  - `Reader`: Quyền chỉ đọc (download/pull package).
- **Mã hóa mật khẩu**: Sử dụng thuật toán Bcrypt với salt an toàn.
- **Tài khoản mặc định ban đầu**: Tự động khởi tạo khi chạy lần đầu (`admin` / `admin123`).

---

## 🚀 Hướng Dẫn Cài Đặt & Triển Khai (Deploy)

### Cách 1: Triển Khai Bằng Docker Compose (Khuyên dùng cho Production)

1. Clone mã nguồn về máy:
   ```bash
   git clone https://github.com/your-username/Zero9Repo.git
   cd Zero9Repo
   ```

2. Khởi chạy toàn bộ hệ thống bằng Docker Compose:
   ```bash
   docker-compose up -d --build
   ```

3. Xem log hoạt động:
   ```bash
   docker-compose logs -f zero9repo
   ```

4. Truy cập giao diện quản trị Web Dashboard:
   - **Địa chỉ**: `http://localhost:8000`
   - **Tài khoản mặc định**: `admin`
   - **Mật khẩu mặc định**: `admin123`

Toàn bộ dữ liệu (cơ sở dữ liệu SQLite, các artifact tải lên và cache proxy) được lưu trữ an toàn trong volume `zero9repo_data` (hoặc thư mục `./data`).

---

### Cách 2: Chạy Bằng Docker Độc Lập

```bash
# Build image Docker
docker build -t zero9repo:latest .

# Chạy container và gắn volume dữ liệu
docker run -d \
  --name zero9repo-app \
  -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  -e SECRET_KEY="chuoi-khoa-bao-mat-production-2026" \
  -e ADMIN_USERNAME="admin" \
  -e ADMIN_PASSWORD="admin123" \
  zero9repo:latest
```

---

## 💻 Hướng Dẫn Cài Đặt Môi Trường Phát Triển (Local Dev)

### Yêu Cầu Hệ Thống
- **Python 3.12+**
- **Node.js 20+** và **npm**

### Bước 1: Khởi Chạy Backend (FastAPI)
```bash
cd backend

# Tạo và kích hoạt môi trường ảo
python -m venv venv

# Trên Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# Trên Linux/macOS:
source venv/bin/activate

# Cài đặt các thư viện phụ thuộc
pip install -r requirements.txt

# Khởi chạy server FastAPI
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
Swagger UI tài liệu API sẽ có tại: `http://localhost:8000/docs`.

### Bước 2: Khởi Chạy Frontend (React + Vite)
```bash
cd frontend

# Cài đặt dependencies
npm install

# Chạy dev server
npm run dev
```
Giao diện phát triển sẽ có tại: `http://localhost:3000` (được proxy tự động sang backend `:8000`).

### Bước 3: Chạy Bộ Test Tự Động
```bash
cd backend
.\venv\Scripts\python.exe -m pytest -v -s tests/test_all_engines.py
```

---

## 📋 Hướng Dẫn Kết Nối Các Client Lập Trình

### 1. Kết Nối Maven

#### A. Cấu hình chứng thực trong file `~/.m2/settings.xml`:
```xml
<settings>
  <servers>
    <server>
      <id>zero9repo</id>
      <username>admin</username>
      <password>admin123</password> <!-- Hoặc mã API Token z9r_... -->
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

#### B. Cấu hình triển khai (Deploy) trong `pom.xml` của dự án:
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
Lệnh deploy:
```bash
mvn clean deploy
```

---

### 2. Kết Nối Gradle

Trong file `build.gradle` (Groovy DSL):
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
Lệnh publish:
```bash
gradle publish
```

---

### 3. Kết Nối NPM

#### A. Cấu hình file `.npmrc` trong dự án:
```ini
registry=http://localhost:8000/repository/npm-group/
//localhost:8000/repository/npm-private/:_authToken=z9r_API_TOKEN_CUA_BAN
always-auth=true
```

#### B. Publish package lên Zero9Repo:
```bash
# Đặt registry publish về repo hosted
npm config set registry http://localhost:8000/repository/npm-private/

# Đăng gói
npm publish
```

---

### 4. Kết Nối Docker CLI

```bash
# 1. Đăng nhập vào Registry Zero9Repo
docker login localhost:8000
# Tên đăng nhập: admin
# Mật khẩu: admin123 (hoặc API Token)

# 2. Gắn tag cho image
docker tag my-image:latest localhost:8000/my-image:1.0.0

# 3. Đẩy image lên Zero9Repo
docker push localhost:8000/my-image:1.0.0

# 4. Kéo image về máy
docker pull localhost:8000/my-image:1.0.0
```

---

### 5. Kết Nối Python / Pip & Twine

#### A. Cấu hình Pip (`~/.pip/pip.conf` trên Linux/macOS hoặc `%APPDATA%\pip\pip.ini` trên Windows):
```ini
[global]
index-url = http://localhost:8000/repository/pypi-group/simple/
trusted-host = localhost
```
Cài đặt package:
```bash
pip install requests
```

#### B. Upload package bằng Twine (`~/.pypirc`):
```ini
[distutils]
index-servers =
    zero9repo

[zero9repo]
repository = http://localhost:8000/repository/pypi-private/
username = __token__
password = z9r_API_TOKEN_CUA_BAN
```
Lệnh upload file bản dựng:
```bash
twine upload --repository zero9repo dist/*
```

---

## 📁 Cấu Trúc Thư Mục Dự Án

```text
├── backend/
│   ├── app/
│   │   ├── api/                  # Các router REST (auth, users, repos, explorer, stats, dispatcher)
│   │   ├── core/                 # Cấu hình, Database Engine, Bảo mật (Bcrypt, JWT), Phân quyền RBAC
│   │   ├── models/               # Model SQLAlchemy (User, ApiToken, Repository, Artifact)
│   │   ├── schemas/              # Schema Pydantic cho Request & Response
│   │   ├── services/             # Engine lưu trữ, Proxy Client, Xử lý Maven/NPM/Docker/PyPI
│   │   └── main.py               # Ứng dụng chính FastAPI & Cơ chế tự động seed dữ liệu
│   ├── tests/                    # Bộ kiểm thử End-to-End toàn diện
│   └── requirements.txt          # Danh sách thư viện Python
├── frontend/
│   ├── src/
│   │   ├── api/                  # Axios Client & React Query Hooks
│   │   ├── components/           # Dashboard, Storage Explorer, Repo Manager, Snippets, Users
│   │   ├── context/              # Context quản lý phiên đăng nhập (Auth Context)
│   │   ├── types/                # Interface định kiểu dữ liệu TypeScript
│   │   ├── App.tsx               # Component gốc & Điều hướng Tab
│   │   └── main.tsx              # Điểm khởi động ứng dụng React
│   ├── package.json              # Danh sách thư viện NPM Frontend
│   └── vite.config.ts            # Cấu hình Vite & Proxy kết nối Backend
├── data/                         # Thư mục dữ liệu bền vững (SQLite DB, Uploads & Proxy Cache)
├── Dockerfile                    # File build Docker đa tầng (Multi-stage)
├── docker-compose.yml            # File cấu hình triển khai Docker Compose
├── README.md                     # Tài liệu tiếng Anh
└── README.vi.md                  # Tài liệu tiếng Việt
```

---

## 🛡️ Giấy Phép Bản Quyền

Dự án được phát hành mã nguồn mở theo giấy phép [Apache License 2.0](LICENSE).
