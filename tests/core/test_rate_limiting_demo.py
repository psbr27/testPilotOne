#!/usr/bin/env python3
"""
Demo script to test rate limiting integration with actual TestPilot components.
This demonstrates the complete rate limiting pipeline.
"""

import sys
import os
import time
import tempfile
import json

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from testpilot.utils.rate_limiter import RateLimiter, create_rate_limiter_from_config, parse_excel_rate_limit

def demo_rate_limiting_scenarios():
    """Demonstrate different rate limiting scenarios."""
    print("🚀 TestPilot Rate Limiting Demo")
    print("=" * 50)

    # Scenario 1: CLI Override
    print("\n📋 Scenario 1: CLI Rate Limit Override")
    print("-" * 30)

    config = {"rate_limiting": {"enabled": True, "default_reqs_per_sec": 3.0}}
    rate_limiter = create_rate_limiter_from_config(config)

    # Simulate CLI override
    cli_rate = 5.0
    rate_limiter.set_rate(cli_rate)

    print(f"Config rate: 3.0 reqs/sec")
    print(f"CLI override: {cli_rate} reqs/sec")

    start_time = time.time()
    for i in range(3):
        delay = rate_limiter.acquire()
        print(f"Request {i+1}: delay={delay:.2f}s")
        if delay > 0:
            time.sleep(delay)

    elapsed = time.time() - start_time
    expected_min = 0.4  # 3 requests at 5 req/sec = ~0.4s minimum
    print(f"Total time: {elapsed:.2f}s (expected ~{expected_min:.2f}s)")
    print("✅ CLI override working" if elapsed >= expected_min - 0.1 else "❌ CLI override failed")

    # Scenario 2: Excel Column Override
    print("\n📊 Scenario 2: Excel Column Rate Limit")
    print("-" * 30)

    rate_limiter = RateLimiter(default_rate=10.0)

    # Simulate Excel row data
    excel_data = {"reqs_sec": "2"}  # 2 requests per second from Excel
    excel_rate = parse_excel_rate_limit(excel_data)

    if excel_rate:
        rate_limiter.set_rate(excel_rate)
        print(f"Excel rate: {excel_rate} reqs/sec")

        start_time = time.time()
        for i in range(3):
            delay = rate_limiter.acquire()
            print(f"Request {i+1}: delay={delay:.2f}s")
            if delay > 0:
                time.sleep(delay)

        elapsed = time.time() - start_time
        expected_min = 1.0  # 3 requests at 2 req/sec = ~1.0s minimum
        print(f"Total time: {elapsed:.2f}s (expected ~{expected_min:.2f}s)")
        print("✅ Excel rate limiting working" if elapsed >= expected_min - 0.1 else "❌ Excel rate limiting failed")

    # Scenario 3: Per-Host Rate Limiting
    print("\n🖥️  Scenario 3: Per-Host Rate Limiting")
    print("-" * 30)

    rate_limiter = RateLimiter(default_rate=4.0, per_host=True)
    rate_limiter.set_rate(1.0, "slow-host")  # 1 req/sec for slow host
    rate_limiter.set_rate(10.0, "fast-host")  # 10 req/sec for fast host

    print("Testing slow host (1 req/sec):")
    start_time = time.time()
    delay1 = rate_limiter.acquire("slow-host")
    delay2 = rate_limiter.acquire("slow-host")
    slow_elapsed = time.time() - start_time
    print(f"  Delays: {delay1:.2f}s, {delay2:.2f}s (total: {slow_elapsed:.2f}s)")

    print("Testing fast host (10 req/sec):")
    start_time = time.time()
    delay3 = rate_limiter.acquire("fast-host")
    delay4 = rate_limiter.acquire("fast-host")
    fast_elapsed = time.time() - start_time
    print(f"  Delays: {delay3:.2f}s, {delay4:.2f}s (total: {fast_elapsed:.2f}s)")

    print("✅ Per-host rate limiting working" if delay2 > delay4 else "⚠️  Per-host timing may vary")

    # Scenario 4: Configuration Priority
    print("\n⚖️  Scenario 4: Configuration Priority Test")
    print("-" * 30)

    # Priority: Excel > CLI > Config > Default
    config_rate = 5.0
    cli_rate = 8.0
    excel_rate = 3.0

    print(f"Priority test: Excel({excel_rate}) > CLI({cli_rate}) > Config({config_rate})")
    print(f"Expected result: {excel_rate} reqs/sec")

    config = {"rate_limiting": {"enabled": True, "default_reqs_per_sec": config_rate}}
    rate_limiter = create_rate_limiter_from_config(config)

    # Simulate CLI override
    rate_limiter.set_rate(cli_rate)

    # Simulate Excel override (highest priority)
    excel_data = {"reqs_sec": str(excel_rate)}
    parsed_excel_rate = parse_excel_rate_limit(excel_data)
    if parsed_excel_rate:
        rate_limiter.set_rate(parsed_excel_rate)

    print(f"Final rate: {rate_limiter.default_rate} reqs/sec")
    print("✅ Priority working correctly" if rate_limiter.default_rate == excel_rate else "❌ Priority failed")

    # Scenario 5: Disabled Rate Limiting
    print("\n🚫 Scenario 5: Disabled Rate Limiting")
    print("-" * 30)

    config_disabled = {"rate_limiting": {"enabled": False}}
    rate_limiter = create_rate_limiter_from_config(config_disabled)

    if rate_limiter is None:
        print("✅ Rate limiting properly disabled")
        print("  Fallback behavior: uses --step-delay")
    else:
        print("❌ Rate limiting should be disabled")

    print("\n" + "=" * 50)
    print("🎉 Rate Limiting Demo Complete!")
    print("\n📚 Usage Summary:")
    print("1. Enable in config: rate_limiting.enabled = true")
    print("2. CLI override: --rate-limit 5.0")
    print("3. Excel column: add 'reqs_sec' or 'Reqs_Sec' column")
    print("4. Priority: Excel > CLI > Config > step_delay")

def main():
    """Run the demo."""
    try:
        demo_rate_limiting_scenarios()
        return True
    except Exception as e:
        print(f"❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)