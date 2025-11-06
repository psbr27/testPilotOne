#!/usr/bin/env python3
"""
Test script for the RateLimiter implementation.
Tests basic functionality without external dependencies.
"""

import time
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from testpilot.utils.rate_limiter import RateLimiter, create_rate_limiter_from_config, parse_excel_rate_limit

    def test_basic_rate_limiting():
        """Test basic rate limiting functionality."""
        print("Testing basic rate limiting...")

        # Create rate limiter: 2 requests per second
        rate_limiter = RateLimiter(default_rate=2.0, per_host=False)

        # Test rapid requests
        start_time = time.time()
        delays = []

        for i in range(5):
            delay = rate_limiter.acquire()
            delays.append(delay)
            if delay > 0:
                print(f"Request {i+1}: Rate limited, sleeping {delay:.2f}s")
                time.sleep(delay)
            else:
                print(f"Request {i+1}: No delay needed")

        total_time = time.time() - start_time
        # More realistic expectation: with 2 req/sec, we should see some delays
        # The first few requests may be allowed due to initial tokens, but delays should accumulate
        total_delays = sum(delays)
        expected_min_delay = 1.0  # At 2 req/sec, we should have some delays

        print(f"Total time: {total_time:.2f}s")
        print(f"Total delays: {total_delays:.2f}s (expected >= {expected_min_delay:.2f}s)")
        print(f"Individual delays: {[f'{d:.2f}s' for d in delays]}")

        # Check if rate limiting is working (some delays should occur)
        if total_delays >= expected_min_delay - 0.1 and max(delays) > 0:
            print("✅ Basic rate limiting test PASSED")
            return True
        else:
            print("❌ Basic rate limiting test FAILED")
            return False

    def test_config_creation():
        """Test rate limiter creation from config."""
        print("\nTesting config-based creation...")

        # Test disabled config
        config_disabled = {"rate_limiting": {"enabled": False}}
        rate_limiter = create_rate_limiter_from_config(config_disabled)

        if rate_limiter is None:
            print("✅ Disabled config test PASSED")
        else:
            print("❌ Disabled config test FAILED")

        # Test enabled config
        config_enabled = {
            "rate_limiting": {
                "enabled": True,
                "default_reqs_per_sec": 5.0,
                "per_host": True
            }
        }
        rate_limiter = create_rate_limiter_from_config(config_enabled)

        if rate_limiter is not None and rate_limiter.default_rate == 5.0 and rate_limiter.per_host == True:
            print("✅ Enabled config test PASSED")
        else:
            print("❌ Enabled config test FAILED")

    def test_excel_parsing():
        """Test Excel rate limit parsing."""
        print("\nTesting Excel rate parsing...")

        # Test various Excel formats
        test_cases = [
            ({"reqs_sec": "3.5"}, 3.5),
            ({"Reqs_Sec": 10}, 10.0),
            ({"reqs_per_sec": "5"}, 5.0),
            ({"invalid_key": "test"}, None),
            ({"reqs_sec": "invalid"}, None),
            ({"reqs_sec": "-1"}, None),  # Negative should be invalid
        ]

        all_passed = True
        for step_data, expected in test_cases:
            result = parse_excel_rate_limit(step_data)
            if result == expected:
                print(f"✅ Excel parse test PASSED: {step_data} -> {result}")
            else:
                print(f"❌ Excel parse test FAILED: {step_data} -> {result} (expected {expected})")
                all_passed = False

        return all_passed

    def test_per_host_rate_limiting():
        """Test per-host rate limiting."""
        print("\nTesting per-host rate limiting...")

        rate_limiter = RateLimiter(default_rate=3.0, per_host=True)

        # Set different rates for different hosts
        rate_limiter.set_rate(1.0, "host1")  # 1 req/sec
        rate_limiter.set_rate(5.0, "host2")  # 5 req/sec

        # Test host1 (should be slower)
        start_time = time.time()
        delay1 = rate_limiter.acquire("host1")
        delay2 = rate_limiter.acquire("host1")  # Should have delay
        host1_time = time.time() - start_time

        # Test host2 (should be faster)
        start_time = time.time()
        delay3 = rate_limiter.acquire("host2")
        delay4 = rate_limiter.acquire("host2")  # Might have less delay
        host2_time = time.time() - start_time

        print(f"Host1 delays: {delay1:.2f}s, {delay2:.2f}s")
        print(f"Host2 delays: {delay3:.2f}s, {delay4:.2f}s")

        # Host1 should generally have higher delays due to lower rate
        if delay2 >= delay4:
            print("✅ Per-host rate limiting test PASSED")
            return True
        else:
            print("❌ Per-host rate limiting test FAILED")
            return False

    def main():
        """Run all tests."""
        print("🧪 Testing TestPilot Rate Limiter Implementation")
        print("=" * 50)

        tests = [
            test_basic_rate_limiting,
            test_config_creation,
            test_excel_parsing,
            test_per_host_rate_limiting,
        ]

        passed = 0
        total = len(tests)

        for test_func in tests:
            try:
                if test_func():
                    passed += 1
            except Exception as e:
                print(f"❌ Test {test_func.__name__} FAILED with exception: {e}")

        print("\n" + "=" * 50)
        print(f"📊 Test Results: {passed}/{total} tests passed")

        if passed == total:
            print("🎉 All tests PASSED! Rate limiter implementation is working correctly.")
        else:
            print("⚠️  Some tests FAILED. Please review the implementation.")

        return passed == total

    if __name__ == "__main__":
        success = main()
        sys.exit(0 if success else 1)

except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure the rate_limiter module is properly implemented.")
    sys.exit(1)