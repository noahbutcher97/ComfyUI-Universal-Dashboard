import unittest
import sys
import os

# Add src to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def run_audit():
    """Run the UI Integrity and Deprecation Audit."""
    print("="*60)
    print("🕵️  AI Universal Suite - UI Integrity & Deprecation Audit")
    print("="*60)
    
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromName("tests.ui.test_ui_integrity")
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    if not result.wasSuccessful():
        sys.exit(1)

if __name__ == "__main__":
    run_audit()
