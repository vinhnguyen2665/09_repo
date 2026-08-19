import pytest
import asyncio
import io
import base64
import json
import httpx
from app.main import app, init_db_and_seed
from app.core.config import settings

BASE_URL = "http://testserver"

@pytest.mark.asyncio
async def test_full_zero9repo_suite():
    # Initialize DB schema and default repos/admin
    await init_db_and_seed()

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url=BASE_URL) as client:
        # 1. Health check
        resp = await client.get("/api/stats/health")
        assert resp.status_code == 200
        assert resp.json()["service"] == "Zero9Repo"

        # 2. Login as Admin
        resp = await client.post("/api/auth/login", json={
            "username": settings.ADMIN_USERNAME,
            "password": settings.ADMIN_PASSWORD
        })
        assert resp.status_code == 200, resp.text
        login_data = resp.json()
        token = login_data["access_token"]
        auth_headers = {"Authorization": f"Bearer {token}"}

        # 3. Get /api/auth/me
        resp = await client.get("/api/auth/me", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["username"] == "admin"
        assert resp.json()["role"] == "admin"

        # 4. Generate API Token
        resp = await client.post("/api/auth/tokens", json={"name": "ci-cd-token"}, headers=auth_headers)
        assert resp.status_code == 200
        api_token_data = resp.json()
        raw_token = api_token_data["raw_token"]
        assert raw_token.startswith("z9r_")

        # 5. Verify API Token in Authorization header
        resp = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {raw_token}"})
        assert resp.status_code == 200
        assert resp.json()["username"] == "admin"

        # 6. List Repositories
        resp = await client.get("/api/repositories", headers=auth_headers)
        assert resp.status_code == 200
        repos = resp.json()
        repo_names = [r["name"] for r in repos]
        assert "maven-private" in repo_names
        assert "npm-private" in repo_names
        assert "docker-private" in repo_names
        assert "pypi-private" in repo_names

        # 7. Test MAVEN Engine (Deploy artifact via HTTP PUT)
        jar_content = b"PK\x03\x04fake-jar-binary-content-1.0.0"
        maven_path = "/repository/maven-private/com/zero9/demo/1.0.0/demo-1.0.0.jar"
        resp = await client.put(maven_path, content=jar_content, headers=auth_headers)
        assert resp.status_code == 201
        
        # Put metadata
        metadata_xml = b"""<metadata>
  <groupId>com.zero9</groupId>
  <artifactId>demo</artifactId>
  <versioning>
    <latest>1.0.0</latest>
    <release>1.0.0</release>
    <versions>
      <version>1.0.0</version>
    </versions>
    <lastUpdated>20260814120000</lastUpdated>
  </versioning>
</metadata>"""
        meta_path = "/repository/maven-private/com/zero9/demo/maven-metadata.xml"
        resp = await client.put(meta_path, content=metadata_xml, headers=auth_headers)
        assert resp.status_code == 201

        # Get Maven Artifact via GET
        resp = await client.get(maven_path)
        assert resp.status_code == 200
        assert resp.content == jar_content

        # Get companion SHA1 hash
        resp = await client.get(f"{maven_path}.sha1")
        assert resp.status_code == 200
        assert len(resp.text) == 40

        # Get Group Metadata merge
        resp = await client.get("/repository/maven-group/com/zero9/demo/maven-metadata.xml")
        assert resp.status_code == 200
        assert b"<version>1.0.0</version>" in resp.content

        # 8. Test NPM Engine (npm publish simulation)
        npm_pkg_data = {
            "name": "zero9-logger",
            "description": "Zero9 High Speed Logger",
            "dist-tags": {"latest": "1.0.0"},
            "versions": {
                "1.0.0": {
                    "name": "zero9-logger",
                    "version": "1.0.0",
                    "description": "Zero9 High Speed Logger",
                    "dist": {
                        "tarball": "http://dummy/zero9-logger/-/zero9-logger-1.0.0.tgz"
                    }
                }
            },
            "_attachments": {
                "zero9-logger-1.0.0.tgz": {
                    "content_type": "application/gzip",
                    "data": base64.b64encode(b"fake-npm-tarball-data").decode("utf-8")
                }
            }
        }
        resp = await client.put(
            "/repository/npm-private/zero9-logger",
            json=npm_pkg_data,
            headers=auth_headers
        )
        assert resp.status_code == 201

        # Get NPM metadata
        resp = await client.get("/repository/npm-private/zero9-logger")
        assert resp.status_code == 200
        npm_meta = resp.json()
        assert npm_meta["name"] == "zero9-logger"

        # Download NPM tarball
        resp = await client.get("/repository/npm-private/zero9-logger/-/zero9-logger-1.0.0.tgz")
        assert resp.status_code == 200
        assert resp.content == b"fake-npm-tarball-data"

        # 9. Test Docker / OCI Engine
        # Ping
        resp = await client.get("/v2/", headers=auth_headers)
        assert resp.status_code == 200
        assert "Docker-Distribution-API-Version" in resp.headers

        # Upload Blob
        blob_content = b"fake-docker-layer-blob-data-2026"
        resp = await client.post("/v2/zero9-app/blobs/uploads/", headers=auth_headers)
        assert resp.status_code == 202
        upload_uuid = resp.headers["Docker-Upload-UUID"]

        # Complete blob upload
        import hashlib
        blob_digest = f"sha256:{hashlib.sha256(blob_content).hexdigest()}"
        resp = await client.put(
            f"/v2/zero9-app/blobs/uploads/{upload_uuid}?digest={blob_digest}",
            content=blob_content,
            headers=auth_headers
        )
        assert resp.status_code == 201

        # Check Blob HEAD & GET
        resp = await client.head(f"/v2/zero9-app/blobs/{blob_digest}")
        assert resp.status_code == 200
        resp = await client.get(f"/v2/zero9-app/blobs/{blob_digest}")
        assert resp.status_code == 200
        assert resp.content == blob_content

        # Put Manifest
        manifest_json = json.dumps({
            "schemaVersion": 2,
            "mediaType": "application/vnd.docker.distribution.manifest.v2+json",
            "config": {"mediaType": "application/vnd.docker.container.image.v1+json", "size": len(blob_content), "digest": blob_digest},
            "layers": [{"mediaType": "application/vnd.docker.image.rootfs.diff.tar.gzip", "size": len(blob_content), "digest": blob_digest}]
        }).encode("utf-8")

        resp = await client.put(
            "/v2/zero9-app/manifests/v1.0.0",
            content=manifest_json,
            headers={"Content-Type": "application/vnd.docker.distribution.manifest.v2+json", **auth_headers}
        )
        assert resp.status_code == 201

        # Get Manifest
        resp = await client.get("/v2/zero9-app/manifests/v1.0.0")
        assert resp.status_code == 200
        assert b"schemaVersion" in resp.content

        # List Tags
        resp = await client.get("/v2/zero9-app/tags/list")
        assert resp.status_code == 200
        assert "v1.0.0" in resp.json()["tags"]

        # 10. Test PyPI Engine (Twine upload simulation)
        wheel_content = b"fake-wheel-binary-package"
        files = {
            "content": ("zero9_sdk-1.0.0-py3-none-any.whl", io.BytesIO(wheel_content), "application/octet-stream")
        }
        data = {
            ":action": "file_upload",
            "name": "zero9_sdk",
            "version": "1.0.0"
        }
        resp = await client.post(
            "/repository/pypi-private/",
            data=data,
            files=files,
            headers=auth_headers
        )
        assert resp.status_code == 200

        # PyPI Simple Index
        resp = await client.get("/repository/pypi-private/simple/")
        assert resp.status_code == 200
        assert "zero9-sdk" in resp.text

        # PyPI Package Page
        resp = await client.get("/repository/pypi-private/simple/zero9-sdk/")
        assert resp.status_code == 200
        assert "zero9_sdk-1.0.0-py3-none-any.whl" in resp.text

        # PyPI Package Download
        resp = await client.get("/repository/pypi-private/packages/zero9_sdk-1.0.0-py3-none-any.whl")
        assert resp.status_code == 200
        assert resp.content == wheel_content

        # 11. Test Storage Explorer API & Stats Overview
        resp = await client.get("/api/storage/tree?repo_name=maven-private", headers=auth_headers)
        assert resp.status_code == 200
        tree = resp.json()
        assert len(tree) > 0

        resp = await client.get(
            "/api/storage/preview?repo_name=maven-private&path=com/zero9/demo/maven-metadata.xml",
            headers=auth_headers
        )
        assert resp.status_code == 200
        assert resp.json()["is_text"] is True

        resp = await client.get("/api/stats/overview", headers=auth_headers)
        assert resp.status_code == 200
        stats = resp.json()
        assert stats["storage"]["total_artifacts"] > 0
        assert stats["storage"]["total_repositories"] >= 10

        # Test Group Repository Tree Merging
        resp = await client.get("/api/storage/tree?repo_name=maven-group", headers=auth_headers)
        assert resp.status_code == 200
        group_tree = resp.json()
        assert len(group_tree) > 0
        node_names = [n["name"] for n in group_tree]
        assert "com" in node_names or "org" in node_names

        # Test inspecting an artifact inside a Group repository
        resp = await client.get(
            "/api/storage/inspect?repo_name=maven-group&path=com/zero9/demo/maven-metadata.xml",
            headers=auth_headers
        )
        assert resp.status_code == 200
        assert resp.json()["repo_name"] == "maven-private"

        # Test previewing an artifact inside a Group repository
        resp = await client.get(
            "/api/storage/preview?repo_name=maven-group&path=com/zero9/demo/maven-metadata.xml",
            headers=auth_headers
        )
        assert resp.status_code == 200
        assert resp.json()["is_text"] is True

        print("\n=== ALL Zero9Repo BACKEND TESTS PASSED 100% ===")
