import yaml
import requests
import logging
import sys
import os
import time
import json
from pathlib import Path
from urllib.parse import urlparse
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

# Add src to path for config_manager
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.config.manager import config_manager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/model_validation.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
log = logging.getLogger(__name__)

class ModelValidator:
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "summary": {"total": 0, "valid": 0, "invalid": 0, "warnings": 0},
            "details": []
        }
        # Try ConfigManager first (App Storage), then Env Var
        self.hf_token = config_manager.get_secure("HF_TOKEN") or os.getenv("HF_TOKEN")
        
        self.headers = {"User-Agent": "AI-Universal-Suite-Validator/1.0"}
        if self.hf_token:
            self.headers["Authorization"] = f"Bearer {self.hf_token}"
            log.info("Authenticated with Hugging Face Token")
        else:
            log.warning("No Hugging Face Token found. Rate limits will be strict.")

    def load_database(self) -> Dict[str, Any]:
        try:
            with open(self.db_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except Exception as e:
            log.error(f"Failed to load database: {e}")
            return {}

    def check_url(self, url: str) -> Tuple[bool, int, str]:
        """
        Verifies URL reachability and returns content size.
        Returns: (is_reachable, size_bytes, message)
        """
        time.sleep(0.2) # Rate limit protection (5 req/s)
        try:
            response = requests.head(url, headers=self.headers, allow_redirects=True, timeout=10)
            if response.status_code == 405: # Method Not Allowed, try GET with stream
                 response = requests.get(url, headers=self.headers, stream=True, timeout=10)
                 response.close()
            
            if response.status_code == 429:
                time.sleep(2) # Backoff
                return self.check_url(url)

            if response.status_code >= 400:
                return False, 0, f"HTTP {response.status_code}"
            
            size = int(response.headers.get("Content-Length", 0))
            return True, size, "OK"
        except Exception as e:
            return False, 0, str(e)

    def validate_hf_metadata(self, url: str, expected_params: str = None) -> Dict[str, Any]:
        """
        Fetches metadata from Hugging Face API if applicable.
        """
        # Parse Repo ID from URL
        # Format: https://huggingface.co/{org}/{repo}/resolve/{branch}/{filename}
        try:
            parsed = urlparse(url)
            if "huggingface.co" not in parsed.netloc:
                return {}
            
            parts = parsed.path.strip("/").split("/")
            if len(parts) < 4:
                return {}
                
            repo_id = f"{parts[0]}/{parts[1]}"
            api_url = f"https://huggingface.co/api/models/{repo_id}"
            
            response = requests.get(api_url, headers=self.headers, timeout=5)
            if response.status_code == 200:
                data = response.json()
                return {
                    "downloads": data.get("downloads", 0),
                    "likes": data.get("likes", 0),
                    "tags": data.get("tags", []),
                    "pipeline_tag": data.get("pipeline_tag"),
                    "card_data": data.get("cardData", {})
                }
        except Exception as e:
            log.warning(f"Failed to fetch HF metadata for {url}: {e}")
        
        return {}

    def validate_model(self, model_id: str, model_data: Dict[str, Any], is_cloud: bool = False):
        """Validates a single model entry."""
        log.info(f"Validating {model_id}...")
        
        # 1. Custom Nodes (Repository Check)
        repo_url = model_data.get("repository")
        if repo_url:
            reachable, _, msg = self.check_url(repo_url)
            status = "pass" if reachable else "fail"
            self._log_result(model_id, "repository", status, msg if not reachable else "Repo accessible")
            return

        # 2. Cloud APIs (Provider Check)
        if is_cloud or model_data.get("provider"):
            # Check for pricing or provider info
            if "pricing" in model_data or "provider" in model_data:
                self._log_result(model_id, "schema", "pass", "Cloud API configuration valid")
            else:
                self._log_result(model_id, "schema", "warning", "Cloud API missing pricing/provider info")
            return

        # 3. Local Models (Variant Check)
        variants = model_data.get("variants", [])
        if not variants:
            self._log_result(model_id, "structure", "fail", "No variants defined")
            return

        for variant in variants:
            url = variant.get("download_url")
            expected_size_gb = variant.get("download_size_gb", 0)
            variant_id = variant.get("id", "unknown")
            
            if not url:
                self._log_result(model_id, variant_id, "fail", "Missing download_url")
                continue

            # Link Check
            reachable, size_bytes, msg = self.check_url(url)
            
            if not reachable:
                self._log_result(model_id, variant_id, "fail", f"Unreachable: {msg}")
                continue

            # Size Validation
            if size_bytes > 0 and expected_size_gb > 0:
                size_gb = size_bytes / (1024**3)
                diff = abs(size_gb - expected_size_gb)
                if diff > 0.5 and diff > (expected_size_gb * 0.1):
                    self._log_result(model_id, variant_id, "warning", 
                        f"Size mismatch: DB={expected_size_gb:.2f}GB, Real={size_gb:.2f}GB")
                else:
                    self._log_result(model_id, variant_id, "pass", 
                        f"URL OK. Size verified ({size_gb:.2f}GB)")
            else:
                self._log_result(model_id, variant_id, "pass", "URL OK (Size check skipped)")

            # HF Metadata Cross-reference
            if "huggingface.co" in url:
                hf_meta = self.validate_hf_metadata(url)
                if hf_meta and hf_meta.get("likes", 0) < 5:
                    self._log_result(model_id, variant_id, "warning", "Low popularity (<5 likes)")

    def _log_result(self, model_id: str, variant_id: str, status: str, message: str):
        self.results["summary"]["total"] += 1
        if status == "pass":
            self.results["summary"]["valid"] += 1
        elif status == "fail":
            self.results["summary"]["invalid"] += 1
        elif status == "warning":
            self.results["summary"]["warnings"] += 1
            self.results["summary"]["valid"] += 1 # Count warnings as valid functionality-wise

        self.results["details"].append({
            "model_id": model_id,
            "variant_id": variant_id,
            "status": status,
            "message": message
        })
        
        log_method = log.error if status == "fail" else (log.warning if status == "warning" else log.info)
        log_method(f"[{status.upper()}] {model_id}/{variant_id}: {message}")

    def run(self):
        data = self.load_database()
        
        # Traverse Two-Tier Structure
        categories = ["local_models", "cloud_apis"]
        
        for root_cat in categories:
            root_data = data.get(root_cat, {})
            if not isinstance(root_data, dict): continue
            
            is_cloud = (root_cat == "cloud_apis")
            
            for subcat, models in root_data.items():
                if not isinstance(models, dict): continue
                
                for model_id, model_data in models.items():
                    if isinstance(model_data, dict):
                        self.validate_model(model_id, model_data, is_cloud=is_cloud)

        self.save_report()

    def save_report(self):
        # JSON Report
        os.makedirs("docs/audits", exist_ok=True)
        with open("docs/audits/model_link_validation.json", "w") as f:
            json.dump(self.results, f, indent=2)
            
        # Markdown Report
        with open("docs/audits/MODEL_LINK_AUDIT.md", "w", encoding="utf-8") as f:
            f.write("# Model Link & Schema Validation Report\n")
            f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
            
            summary = self.results["summary"]
            f.write("## Summary\n")
            f.write(f"- **Total Variants Checked:** {summary['total']}\n")
            f.write(f"- **Valid:** {summary['valid']}\n")
            f.write(f"- **Invalid:** {summary['invalid']}\n")
            f.write(f"- **Warnings:** {summary['warnings']}\n\n")
            
            f.write("## Failures & Warnings\n")
            f.write("| Model | Variant | Status | Message |\n")
            f.write("|-------|---------|--------|---------|\n")
            
            for item in self.results["details"]:
                if item["status"] != "pass":
                    icon = "🔴" if item["status"] == "fail" else "⚠️"
                    f.write(f"| {item['model_id']} | {item['variant_id']} | {icon} {item['status']} | {item['message']} |\n")

        log.info("Validation complete. Report saved to docs/audits/MODEL_LINK_AUDIT.md")

if __name__ == "__main__":
    validator = ModelValidator("data/models_database.yaml")
    validator.run()
