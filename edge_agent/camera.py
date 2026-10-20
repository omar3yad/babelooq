import asyncio
import httpx


class CameraError(Exception):
    pass


class SnapshotCamera:
    """Fetches JPEG snapshots from IP cameras over the LAN.

    One pooled client keeps connections alive (and httpx reuses the digest
    challenge), so a capture is a single round-trip instead of TCP + 401 + retry.
    """

    def __init__(
        self,
        urls: dict[int, str],
        auth_mode: str,
        username: str | None,
        password: str | None,
        timeout_s: float,
    ) -> None:
        self._urls = urls
        self._timeout_s = timeout_s
        auth: httpx.Auth | None = None
        if auth_mode == "basic" and username:
            auth = httpx.BasicAuth(username, password or "")
        elif auth_mode == "digest" and username:
            auth = httpx.DigestAuth(username, password or "")

        self._client = httpx.AsyncClient(
            auth=auth,
            timeout=httpx.Timeout(timeout_s, connect=min(0.5, timeout_s)),
            limits=httpx.Limits(max_keepalive_connections=8, keepalive_expiry=30),
            headers={"Cache-Control": "no-cache"},
            verify=False,
        )

    @property
    def gates(self) -> list[int]:
        return sorted(self._urls)

    async def snapshot(self, gate_id: int, timeout_s: float | None = None) -> bytes:
        url = self._urls.get(gate_id)
        if url is None:
            raise CameraError(f"no camera configured for gate {gate_id}")
        budget = min(timeout_s or self._timeout_s, self._timeout_s)
        try:
            response = await asyncio.wait_for(self._client.get(url), budget)
            response.raise_for_status()
        except asyncio.TimeoutError as exc:
            raise CameraError(f"snapshot timed out after {budget:.2f}s") from exc
        except httpx.HTTPStatusError as exc:
            raise CameraError(f"camera returned HTTP {exc.response.status_code}") from exc
        except httpx.HTTPError as exc:
            raise CameraError(f"camera unreachable: {exc.__class__.__name__}") from exc

        if not response.headers.get("content-type", "").startswith("image/"):
            raise CameraError("camera did not return an image")
        return response.content

    async def aclose(self) -> None:
        await self._client.aclose()
