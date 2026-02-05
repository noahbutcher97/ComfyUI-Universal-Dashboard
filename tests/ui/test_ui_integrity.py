import unittest
import customtkinter as ctk
import os
import sys
import json
import inspect
from datetime import datetime

# Add src to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tests.ui.ui_test_utils import UIMockFactory, UICrawler, ViewDiscoverer, DataGenerator
from tests.ui.deprecation_scanner import DeprecationScanner

class TestUIIntegrity(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        # 1. Setup Headless Root
        try:
            cls.root = ctk.CTk()
            cls.root.withdraw()
        except Exception:
            cls.root = None
            
        # 2. Apply Mocks
        cls.patchers = UIMockFactory.apply_patches()
        
        # 3. Discover Views
        cls.view_classes = ViewDiscoverer.get_all_view_classes()
        print(f"Discovered {len(cls.view_classes)} UI View classes.")

    @classmethod
    def tearDownClass(cls):
        if cls.root:
            cls.root.destroy()
        for p in cls.patchers:
            p.stop()

    def test_a_static_deprecation_scan(self):
        """Scan source code for deprecated modules and symbols."""
        scanner = DeprecationScanner()
        report = scanner.scan_directory("src")
        
        print("\n=== DEPRECATION REPORT ===")
        total_issues = 0
        for file, issues in report.items():
            print(f"\n📄 {file}:")
            for issue in issues:
                print(f"  - [{issue['type']}] Line {issue['line']}: {issue['detail']}")
                total_issues += 1

    def test_b_view_instantiation_and_widget_health(self):
        """Instantiate every view and verify widget bindings."""
        if not self.root:
            self.skipTest("No display available")

        results = []

        for ViewClass in self.view_classes:
            view_name = ViewClass.__name__
            print(f"\n🔍 Testing View: {view_name}")
            
            try:
                # Introspect Constructor
                sig = inspect.signature(ViewClass.__init__)
                kwargs = {}
                
                # Iterate parameters (skip self)
                for name, param in sig.parameters.items():
                    if name in ['self', 'master']:
                        continue
                    
                    # Generate Mock Data
                    kwargs[name] = DataGenerator.get_mock_arg(name, param.annotation)
                
                # Instantiate
                view = ViewClass(self.root, **kwargs)
                
                # Crawl
                interactive = UICrawler.find_interactive_elements(view)
                
                results.append({
                    "view": view_name,
                    "status": "PASS",
                    "widget_count": len(interactive),
                    "interactive_count": len([i for i in interactive if i["category"] == "interactive"])
                })
                
                view.destroy()
                
            except Exception as e:
                print(f"❌ FAILED to instantiate {view_name}: {e}")
                import traceback
                traceback.print_exc()
                results.append({
                    "view": view_name,
                    "status": "FAIL",
                    "error": str(e)
                })

        # Save Report
        self._save_audit_report(results)
        
        # Fail run if any view crashed
        failures = [r for r in results if r["status"] == "FAIL"]
        self.assertEqual(len(failures), 0, f"Failed to instantiate {len(failures)} views: {[f['view'] for f in failures]}")

    def _save_audit_report(self, results):
        report_dir = "docs/audits"
        os.makedirs(report_dir, exist_ok=True)
        path = f"{report_dir}/ui_audit_report_{datetime.now().strftime('%Y%m%d')}.json"
        with open(path, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\n✅ Audit Report Saved: {path}")

if __name__ == '__main__':
    unittest.main()