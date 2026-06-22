from scanners import CloudScanner
from scanners.aws import AWSScanner
from scanners.azure import AzureScanner
from scanners.gcp import GCPScanner


def get_scanner(provider: str) -> CloudScanner:
    normalized = (provider or "").strip().lower()
    if normalized == "azure":
        return AzureScanner()
    if normalized == "aws":
        return AWSScanner()
    if normalized == "gcp":
        return GCPScanner()
    raise ValueError(f"Unknown provider: {provider}")
