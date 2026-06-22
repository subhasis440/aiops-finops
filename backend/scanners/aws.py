import json
import subprocess
from typing import Any

from .base import CLINotInstalledError, CloudScanner, NotLoggedInError


class AWSCLINotInstalledError(CLINotInstalledError):
    pass


class AWSNotLoggedInError(NotLoggedInError):
    pass


class AWSCLICommandError(Exception):
    pass


def _normalize_tags(tag_list: Any) -> dict[str, str]:
    if isinstance(tag_list, list):
        return {
            str(item.get("Key")): str(item.get("Value"))
            for item in tag_list
            if item.get("Key") is not None
        }
    return {}


class AWSScanner(CloudScanner):
    def _run_aws(self, args: list[str]) -> Any:
        try:
            result = subprocess.run(
                ["aws", *args],
                capture_output=True,
                text=True,
                check=False,
            )
        except FileNotFoundError as exc:
            raise AWSCLINotInstalledError("AWS CLI is not installed.") from exc

        stderr = (result.stderr or "").strip()
        stdout = (result.stdout or "").strip()
        if result.returncode != 0:
            lowered = stderr.lower()
            if "unable to locate credentials" in lowered or "expiredtoken" in lowered:
                raise AWSNotLoggedInError(
                    "AWS CLI is not authenticated. Configure credentials first."
                )
            raise AWSCLICommandError(stderr or stdout or "AWS CLI command failed.")

        if not stdout:
            return {}
        try:
            return json.loads(stdout)
        except json.JSONDecodeError as exc:
            raise AWSCLICommandError("AWS CLI returned invalid JSON.") from exc

    def list_scopes(self) -> list[dict[str, Any]]:
        payload = self._run_aws(["ec2", "describe-regions", "--all-regions", "--output", "json"])
        scopes: list[dict[str, Any]] = []
        for region in payload.get("Regions", []):
            region_name = region.get("RegionName")
            scopes.append(
                {
                    "id": region_name,
                    "name": region_name,
                    "location": region_name,
                    "tags": {},
                }
            )
        return scopes

    def list_resources(self, scope: str) -> list[dict[str, Any]]:
        payload = self._run_aws(
            [
                "resourcegroupstaggingapi",
                "get-resources",
                "--region",
                scope,
                "--output",
                "json",
            ]
        )
        resources: list[dict[str, Any]] = []
        for item in payload.get("ResourceTagMappingList", []):
            arn = item.get("ResourceARN", "")
            arn_parts = arn.split(":")
            resource_type = arn_parts[2] if len(arn_parts) > 2 else "unknown"
            name = arn.split("/")[-1] if "/" in arn else arn.rsplit(":", maxsplit=1)[-1]

            resources.append(
                {
                    "id": arn,
                    "name": name,
                    "type": resource_type,
                    "location": scope,
                    "sku": None,
                    "kind": None,
                    "tags": _normalize_tags(item.get("Tags")),
                }
            )
        return resources
