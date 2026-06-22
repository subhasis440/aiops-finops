import json
import subprocess
from typing import Any

from .base import CLINotInstalledError, CloudScanner, NotLoggedInError, ScopeNotFoundError


class AzureScannerError(Exception):
    """Base class for Azure scanner errors."""


class AzureCLINotInstalledError(CLINotInstalledError):
    pass


class AzureCLINotLoggedInError(NotLoggedInError):
    pass


class ResourceGroupNotFoundError(ScopeNotFoundError):
    pass


class AzureCLICommandError(AzureScannerError):
    pass


def _normalize_tags(tags: Any) -> dict[str, str]:
    if isinstance(tags, dict):
        return {str(k): str(v) for k, v in tags.items()}
    return {}


class AzureScanner(CloudScanner):
    def _run_az(self, args: list[str], expect_json: bool = True) -> Any:
        try:
            result = subprocess.run(
                ["az", *args],
                capture_output=True,
                text=True,
                check=False,
            )
        except FileNotFoundError as exc:
            raise AzureCLINotInstalledError(
                "Azure CLI is not installed. Install it and retry."
            ) from exc

        stderr = (result.stderr or "").strip()
        stdout = (result.stdout or "").strip()
        if result.returncode != 0:
            lowered = stderr.lower()
            if "az login" in lowered or "please run 'az login'" in lowered:
                raise AzureCLINotLoggedInError(
                    "Azure CLI is not authenticated. Run 'az login' first."
                )
            raise AzureCLICommandError(stderr or stdout or "Azure CLI command failed.")

        if not expect_json:
            return stdout
        if not stdout:
            return []
        try:
            return json.loads(stdout)
        except json.JSONDecodeError as exc:
            raise AzureCLICommandError("Azure CLI returned invalid JSON.") from exc

    def _resource_group_exists(self, name: str) -> bool:
        output = self._run_az(
            ["group", "exists", "--name", name, "-o", "tsv"],
            expect_json=False,
        )
        return str(output).strip().lower() == "true"

    def list_scopes(self) -> list[dict[str, Any]]:
        groups = self._run_az(["group", "list", "-o", "json"])
        scopes: list[dict[str, Any]] = []
        for group in groups:
            scopes.append(
                {
                    "id": group.get("id"),
                    "name": group.get("name"),
                    "location": group.get("location"),
                    "tags": _normalize_tags(group.get("tags")),
                }
            )
        return scopes

    def list_resources(self, scope: str) -> list[dict[str, Any]]:
        if not self._resource_group_exists(scope):
            raise ResourceGroupNotFoundError(f"Resource group '{scope}' was not found.")

        raw_resources = self._run_az(
            ["resource", "list", "--resource-group", scope, "-o", "json"]
        )
        resources: list[dict[str, Any]] = []
        for item in raw_resources:
            raw_sku = item.get("sku")
            sku: str | None = None
            if isinstance(raw_sku, dict):
                sku = raw_sku.get("name") or raw_sku.get("tier")
            elif isinstance(raw_sku, str):
                sku = raw_sku

            resources.append(
                {
                    "id": item.get("id"),
                    "name": item.get("name"),
                    "type": item.get("type"),
                    "location": item.get("location"),
                    "sku": sku,
                    "kind": item.get("kind"),
                    "tags": _normalize_tags(item.get("tags")),
                }
            )
        return resources
