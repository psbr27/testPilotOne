# TestPilot Rate Limiting Implementation

## Overview

Successfully implemented requests/second rate limiting for the TestPilot framework. Users can now control the rate of HTTP requests using Excel columns, CLI arguments, or configuration files.

## ✅ Implementation Complete

### 1. **RateLimiter Utility Class**
- **File**: `src/testpilot/utils/rate_limiter.py`
- **Algorithm**: Token bucket with configurable rate and burst size
- **Features**:
  - Thread-safe implementation
  - Per-host rate limiting support
  - Global rate limiting option
  - Configuration priority handling

### 2. **Configuration Support**
- **File**: `config/hosts.json.template`
- **New Section**:
```json
"rate_limiting": {
  "enabled": false,
  "default_reqs_per_sec": 10,
  "per_host": false,
  "burst_size": null,
  "mode": "token_bucket"
}
```

### 3. **CLI Integration**
- **New Argument**: `--rate-limit RATE_LIMIT`
- **Description**: "Maximum requests per second (overrides config and Excel settings)"
- **Usage**: `python test_pilot.py -i input.xlsx -m config --rate-limit 5.0`

### 4. **Excel Column Support**
- **Supported Columns**: `reqs_sec`, `Reqs_Sec`, `reqs_per_sec`, `Reqs_Per_Sec`, `rate_limit`
- **Format**: Positive numbers (integer or float)
- **Example**: Excel cell with value `5` = 5 requests per second for that test step

### 5. **Core Integration**
- **File**: `src/testpilot/core/test_pilot_core.py`
- **Integration Points**:
  - Rate limit parsing from Excel columns
  - Rate limiting before `execute_command()`
  - Replacement of static `step_delay` with dynamic rate limiting

## 🎯 Usage Examples

### Enable Rate Limiting via Config
```json
{
  "rate_limiting": {
    "enabled": true,
    "default_reqs_per_sec": 10,
    "per_host": false
  }
}
```

### CLI Override
```bash
python test_pilot.py -i tests.xlsx -m config --rate-limit 5.0
```

### Excel Column
| Test_Name | URL | Method | reqs_sec |
|-----------|-----|--------|----------|
| Login API | /api/login | POST | 3 |
| Get Users | /api/users | GET | 10 |

## ⚡ Configuration Priority

1. **Excel Column** (`reqs_sec`) - Highest priority
2. **CLI Argument** (`--rate-limit`) - Overrides config
3. **Config File** (`rate_limiting.default_reqs_per_sec`) - Default
4. **Step Delay** (`--step-delay`) - Fallback when rate limiting disabled

## 🛠️ Technical Details

### Token Bucket Algorithm
- Initial tokens: 1 (allows first request immediately)
- Token refill rate: Configured requests per second
- Burst size: Configurable (defaults to rate)
- Thread-safe with locks

### Rate Limiting Logic
```python
# Before request execution
if rate_limiter is not None:
    delay = rate_limiter.acquire(host)
    if delay > 0:
        time.sleep(delay)

# Execute command
output, error, duration = execute_command(command, host, connector)
```

### Per-Host Support
```python
# Different rates for different hosts
rate_limiter = RateLimiter(default_rate=5.0, per_host=True)
rate_limiter.set_rate(2.0, "slow-server")
rate_limiter.set_rate(10.0, "fast-server")
```

## 🧪 Testing

### Test Files Created
1. `test_rate_limiter.py` - Unit tests for RateLimiter class
2. `test_rate_limiting_demo.py` - Integration demo with scenarios

### Test Results
- ✅ Configuration creation and priority
- ✅ Excel column parsing
- ✅ Per-host rate limiting
- ✅ Token bucket rate limiting
- ✅ CLI integration

### Run Tests
```bash
# Create virtual environment
python3 -m venv test_env
source test_env/bin/activate

# Install dependencies
pip install pandas tabulate jsondiff blessed jinja2 paramiko scp deepdiff

# Run tests
python test_rate_limiter.py
python test_rate_limiting_demo.py
```

## 📋 Backward Compatibility

- **Default Behavior**: Rate limiting disabled by default
- **Existing Tests**: Continue to work unchanged
- **Step Delay**: Still works when rate limiting is disabled
- **Configuration**: Old configs work without rate_limiting section

## 🔧 Future Enhancements

1. **Dynamic Rate Adjustment**: Adjust rate based on response times
2. **Rate Limit Metrics**: Export rate limiting statistics to reports
3. **Advanced Algorithms**: Implement sliding window or leaky bucket
4. **Queue Management**: Handle request queuing for very low rates

## 📖 Documentation Updates Needed

1. Update main README.md with rate limiting section
2. Update Excel template documentation
3. Add rate limiting examples to documentation
4. Update deployment guide with new config options

---

## 🎉 Implementation Status: COMPLETE

All planned features have been successfully implemented and tested. The rate limiting system is now fully integrated into the TestPilot framework and ready for production use.