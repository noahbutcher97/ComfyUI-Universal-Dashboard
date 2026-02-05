import unittest
import time
from src.services.dev_service import DevService

class TestDiscoveryPerformance(unittest.TestCase):
    """
    Performance Benchmark for Tool Discovery.
    Ensures that scanning for installed tools is efficient enough for UI interactions.
    """

    def test_provider_scan_speed(self):
        """
        Benchmark the full AI Provider scan loop.
        Target: < 200ms for typical toolset (cached or uncached).
        """
        # 1. Warm-up (populate lru_cache)
        DevService.get_all_providers()
        
        start_time = time.time()
        
        # 2. Real Scan
        providers = DevService.get_all_providers()
        statuses = {name: DevService.is_installed(name) for name in providers}
        
        duration = (time.time() - start_time) * 1000 # ms
        
        print(f"\n[Perf] AI Tool Scan ({len(providers)} tools): {duration:.2f} ms")
        
        # Assertion: Should be fast (e.g. < 500ms even on slow systems)
        self.assertLess(duration, 500, "Tool scanning took too long (>500ms)")

    def test_system_tool_check_speed(self):
        """
        Benchmark single system tool check (shutil.which wrapper).
        """
        # Pick a common tool likely to exist or fail fast
        target = "python"
        
        start_time = time.time()
        for _ in range(100): # Check 100 times to amplify cost
            DevService.check_system_tool(target)
            
        duration = (time.time() - start_time) * 1000
        avg_duration = duration / 100
        
        print(f"\n[Perf] System Tool Check (Avg): {avg_duration:.4f} ms")
        self.assertLess(avg_duration, 5.0, "Individual tool checks must be instant (<5ms)")

if __name__ == "__main__":
    unittest.main()
