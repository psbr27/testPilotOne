# TestPilot Display Modes

## Problem
When tests complete rapidly (0.3 seconds average), the standard table display causes excessive flickering, making it difficult to follow test progress.

## Solutions

### 1. Progress Only Mode (`--display-mode progress_only`)
**Best for: Very fast tests, CI/CD pipelines**

Shows only a real-time progress counter during execution:
```
[12.3s] Tests: 45 | ✅ 42 | ❌ 3 | Rate: 3.7/sec
```

Benefits:
- No flickering
- Shows overall progress and rate
- Final detailed summary at the end
- Minimal CPU overhead

### 2. Batched Table Mode (`--display-mode batched`)
**Best for: Moderate speed tests, detailed progress tracking**

Updates the table in batches (default: every 5 tests):
```bash
python test_pilot.py --file tests.xlsx --display-mode batched --batch-size 5
```

Benefits:
- Reduces flickering by 80%
- Shows detailed results in groups
- Configurable batch size
- Progress counters between batches

### 3. Static + Live Mode (`--display-mode static_live`)
**Best for: Monitoring recent activity**

Shows static summary + live window of recent tests:
```
Total: 45 | Passed: 42 | Failed: 3 | Rate: 3.7/sec

Recent Results:
✅ PASS Auth_Test        on host-1    (0.45s)
❌ FAIL API_Validation   on host-2    (1.23s)
✅ PASS Health_Check     on host-1    (0.12s)
```

Benefits:
- See overall progress and recent activity
- No table flickering
- Real-time recent results

### 4. Standard Mode (`--display-mode standard`)
**Best for: Slow tests, debugging**

Original line-by-line table updates (default):
- Shows every test immediately
- Full table view
- Can flicker with fast tests

## Usage Examples

```bash
# Progress only (recommended for fast tests)
python test_pilot.py --file tests.xlsx --display-mode progress_only

# Batched updates every 3 tests
python test_pilot.py --file tests.xlsx --display-mode batched --batch-size 3

# Static summary with recent results
python test_pilot.py --file tests.xlsx --display-mode static_live

# Standard mode (default)
python test_pilot.py --file tests.xlsx --display-mode standard
```

## Dry-Run Mode

All display modes work with dry-run:
```bash
python test_pilot.py --file tests.xlsx --dry-run --display-mode progress_only
```

## Performance Comparison

| Mode | CPU Usage | Flickering | Detail Level | Best For |
|------|-----------|------------|--------------|----------|
| progress_only | Lowest | None | Summary | Fast tests, CI/CD |
| batched | Low | Minimal | Medium | Balanced viewing |
| static_live | Medium | None | Recent focus | Monitoring |
| standard | High | High | Full | Slow tests, debug |

## Demo

Run the demo to see all modes in action:
```bash
python demo_display_modes.py
```

## Technical Details

- **Batched**: Collects N results before updating display
- **Progress Only**: Single line updates with real-time counters
- **Static Live**: Fixed summary + sliding window of recent tests
- **Standard**: Line-by-line immediate updates (original behavior)

All modes provide the same final summary with complete results.