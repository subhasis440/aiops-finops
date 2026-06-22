import json
import subprocess
from typing import Any

from .base import CLINotInstalledError, CloudScanner, NotLoggedInError


class GCloudCLINotInstalledError(CLINotInstalledError):
    pass


class GCloudNotLoggedInError(NotLoggedInError):
    pass


class GCloudCommandError(Exception):
    pass


def _normalize_tags(labels: Any) -> dict[str, str]:
    if isinstance(labels, dict):
        return {str(k): str(v) for k, v in labels.items()}
    return {}


class GCPScanner(CloudScanner):
    def _run_gcloud(self, args: list[str]) -> Any:
        try:
            result = subprocess.run(
                ["gcloud", *args],
                capture_output=True,
                text=True,
                check=False,
            )
        except FileNotFoundError as exc:
            raise GCloudCLINotInstalledError("gcloud CLI is not installed.") from exc

        stderr = (result.stderr or "").strip()
        stdout = (result.stdout or "").strip()
        if result.returncode != 0:
            lowered = stderr.lower()
            if "gcloud auth login" in lowered or "not have an active account" in lowered:
                raise GCloudNotLoggedInError(
                    "gcloud is not authenticated. Run 'gcloud auth login'."
                )
            raise GCloudCommandError(stderr or stdout or "gcloud command failed.")

        if not stdout:
            return []
        try:
            return json.loads(stdout)
        except json.JSONDecodeError as exc:
            raise GCloudCommandError("gcloud returned invalid JSON.") from exc

    def list_scopes(self) -> list[dict[str, Any]]:
        projects = self._run_gcloud(["projects", "list", "--format=json"])
        scopes: list[dict[str, Any]] = []
        for project in projects:
            project_id = project.get("projectId")
            scopes.append(
                {
                    "id": project_id,
                    "name": project.get("name") or project_id,
                    "location": "global",
                    "tags": {},
                }
            )
        return scopes

    def list_resources(self, scope: str) -> list[dict[str, Any]]:
        assets = self._run_gcloud(
            ["asset", "search-all-resources", f"--project={scope}", "--format=json"]
        )
        resources: list[dict[str, Any]] = []
        for item in assets:
            locations = item.get("locations") or []
            resources.append(
                {
                    "id": item.get("name"),
                    "name": (item.get("displayName") or item.get("name", "").split("/")[-1]),
                    "type": item.get("assetType"),
                    "location": locations[0] if locations else "global",
                    "sku": None,
                    "kind": None,
                    "tags": _normalize_tags(item.get("labels")),
                }
            )
        return resources
