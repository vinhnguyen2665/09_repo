import pytest
import httpx
from sqlalchemy import update
from app.main import app, init_db_and_seed
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.repository import Repository

BASE_URL = "http://testserver"

@pytest.mark.asyncio
async def test_repository_offline_and_group_behavior():
    await init_db_and_seed()

    # Reset all repositories to online
    async with AsyncSessionLocal() as db:
        await db.execute(update(Repository).values(is_online=True))
        await db.commit()

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url=BASE_URL) as client:
        # 1. Login as Admin
        login_resp = await client.post("/api/auth/login", json={
            "username": settings.ADMIN_USERNAME,
            "password": settings.ADMIN_PASSWORD
        })
        assert login_resp.status_code == 200
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Upload a private artifact to maven-private
        jar_data = b"PK\x03\x04private-jar-test-2.0.0"
        put_resp = await client.put(
            "/repository/maven-private/com/zero9/test/2.0.0/test-2.0.0.jar",
            content=jar_data,
            headers=headers
        )
        assert put_resp.status_code == 201

        # Verify it can be downloaded when ONLINE
        get_on = await client.get("/repository/maven-private/com/zero9/test/2.0.0/test-2.0.0.jar")
        assert get_on.status_code == 200
        assert get_on.content == jar_data

        # ================= TEST 1: Direct Access when OFFLINE =================
        print("\n--- TEST 1: Direct Access when OFFLINE ---")
        # Turn maven-private OFFLINE
        edit_resp = await client.put(
            "/api/repositories/maven-private",
            json={"is_online": False, "description": "Offline for security audit"},
            headers=headers
        )
        assert edit_resp.status_code == 200
        assert edit_resp.json()["is_online"] is False
        assert edit_resp.json()["description"] == "Offline for security audit"

        # Direct GET must return 503
        get_off = await client.get("/repository/maven-private/com/zero9/test/2.0.0/test-2.0.0.jar")
        assert get_off.status_code == 503
        assert "is currently offline" in get_off.json()["detail"]
        print("  [PASS] Direct GET on offline maven-private blocked with HTTP 503")

        # Direct HEAD must return 503
        head_off = await client.head("/repository/maven-private/com/zero9/test/2.0.0/test-2.0.0.jar")
        assert head_off.status_code == 503
        print("  [PASS] Direct HEAD on offline maven-private blocked with HTTP 503")

        # Direct PUT must return 503
        put_off = await client.put(
            "/repository/maven-private/com/zero9/test/2.0.0/test2-2.0.0.jar",
            content=b"some-bytes",
            headers=headers
        )
        assert put_off.status_code == 503
        print("  [PASS] Direct PUT upload on offline maven-private blocked with HTTP 503")

        # ================= TEST 2: Docker Registry when OFFLINE =================
        print("\n--- TEST 2: Docker Registry when OFFLINE ---")
        # Turn docker-private OFFLINE
        await client.put("/api/repositories/docker-private", json={"is_online": False}, headers=headers)
        
        docker_ping = await client.get("/v2/", headers=headers)
        assert docker_ping.status_code == 503
        assert "is currently offline" in docker_ping.json()["detail"]
        print("  [PASS] Docker /v2/ ping blocked with HTTP 503 when docker-private is OFFLINE")

        # Turn docker-private back ONLINE
        await client.put("/api/repositories/docker-private", json={"is_online": True}, headers=headers)
        docker_ping_on = await client.get("/v2/", headers=headers)
        assert docker_ping_on.status_code == 200
        print("  [PASS] Docker /v2/ ping succeeded with HTTP 200 when back ONLINE")

        # ================= TEST 3: Group Repo Fallover & Skip OFFLINE Members =================
        print("\n--- TEST 3: Group Repo Fallover & Skip OFFLINE Members ---")
        # Currently: maven-private is OFFLINE, maven-proxy is ONLINE, maven-group is ONLINE
        
        # When querying maven-group for private-only artifact:
        # It skips maven-private (because it is OFFLINE), tries maven-proxy (misses on central), returns 404
        group_private_get = await client.get("/repository/maven-group/com/zero9/test/2.0.0/test-2.0.0.jar")
        assert group_private_get.status_code == 404
        print("  [PASS] maven-group correctly skipped offline maven-private (returned 404)")

        # Turn maven-private back ONLINE
        await client.put("/api/repositories/maven-private", json={"is_online": True}, headers=headers)
        
        # Now querying maven-group for private artifact succeeds!
        group_private_get_on = await client.get("/repository/maven-group/com/zero9/test/2.0.0/test-2.0.0.jar")
        assert group_private_get_on.status_code == 200
        assert group_private_get_on.content == jar_data
        print("  [PASS] maven-group served private artifact when maven-private is back ONLINE")

        # ================= TEST 4: Group Repo Itself OFFLINE =================
        print("\n--- TEST 4: Group Repo Itself OFFLINE ---")
        # Turn maven-group OFFLINE
        await client.put("/api/repositories/maven-group", json={"is_online": False}, headers=headers)
        group_off = await client.get("/repository/maven-group/com/zero9/test/2.0.0/test-2.0.0.jar")
        assert group_off.status_code == 503
        assert "is currently offline" in group_off.json()["detail"]
        print("  [PASS] maven-group blocked all requests with HTTP 503 when group itself is OFFLINE")

        # Restore maven-group to ONLINE
        await client.put("/api/repositories/maven-group", json={"is_online": True}, headers=headers)
        group_restored = await client.get("/repository/maven-group/com/zero9/test/2.0.0/test-2.0.0.jar")
        assert group_restored.status_code == 200
        print("  [PASS] maven-group restored to normal HTTP 200 operation")

        print("\n=== ALL OFFLINE & EDIT REPOSITORY TESTS PASSED 100% ===")
