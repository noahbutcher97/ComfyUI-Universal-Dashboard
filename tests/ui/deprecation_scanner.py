import ast
import os
from typing import List, Dict, Set, Any
from pathlib import Path

class DeprecationScanner:
    """
    Static analysis tool to find usage of deprecated modules/functions.
    """
    
    DEPRECATED_MODULES = [
        "src.services.scoring_service",
        "src.config.resources.json" 
    ]
    
    DEPRECATED_SYMBOLS = [
        "ScoringService",
        "score_model_candidates", # Legacy scoring method
        "generate_recommendations_legacy",
        "_build_expanded_view" # Legacy blocking method in ModelCard (if still present)
    ]

    @staticmethod
    def scan_file(file_path: str) -> List[Dict[str, Any]]:
        findings = []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                tree = ast.parse(content)
                
            for node in ast.walk(tree):
                # Check imports
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    module_name = getattr(node, "module", "")
                    if module_name:
                        for dep in DeprecationScanner.DEPRECATED_MODULES:
                            if dep in module_name:
                                findings.append({
                                    "type": "deprecated_import",
                                    "line": node.lineno,
                                    "detail": f"Importing deprecated module: {module_name}"
                                })

                # Check function calls / attribute access
                if isinstance(node, ast.Name):
                    if node.id in DeprecationScanner.DEPRECATED_SYMBOLS:
                        findings.append({
                            "type": "deprecated_usage",
                            "line": node.lineno,
                            "detail": f"Usage of deprecated symbol: {node.id}"
                        })
                
                # Check for "resources.json" string usage (manual config loading)
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    if "resources.json" in node.value:
                         findings.append({
                            "type": "deprecated_data_source",
                            "line": node.lineno,
                            "detail": "Direct reference to 'resources.json'"
                        })

        except Exception as e:
            # findings.append({"type": "error", "line": 0, "detail": str(e)})
            pass # Ignore parsing errors for non-python files if any
            
        return findings

    @staticmethod
    def scan_directory(root_dir: str) -> Dict[str, List[Dict]]:
        report = {}
        for root, _, files in os.walk(root_dir):
            for file in files:
                if file.endswith(".py"):
                    path = os.path.join(root, file)
                    findings = DeprecationScanner.scan_file(path)
                    if findings:
                        report[path] = findings
        return report
