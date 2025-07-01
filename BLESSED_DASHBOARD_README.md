# TestPilot Blessed Dashboard

## Overview

The TestPilot blessed dashboard provides a modern, flicker-free terminal interface for displaying live test results. It replaces the previous Rich and live table implementations with the `blessed` library for better terminal control and cross-platform compatibility.

## Features

- **Flicker-free updates**: Uses proper terminal cursor positioning
- **Real-time progress**: Live counters and statistics
- **Color-coded results**: Visual status indicators (✓ PASS, ✗ FAIL, ◦ DRY-RUN)
- **Responsive layout**: Adapts to terminal size
- **Fallback support**: Works even without blessed library

## Display Modes

### 1. Full Dashboard (`--display-mode blessed`)
**Recommended for most use cases**

Features:
- Live updating table with test results
- Real-time progress bar and statistics  
- Color-coded status indicators
- Scrollable results window
- Bottom status line with counters

```
================================================================================
                        TestPilot - Live Test Results                          
================================================================================
Elapsed: 45.2s | Rate: 3.2/sec | Total: 145

Host         Sheet      Test Name                 Method Status   Duration
----------------------------------------------------------------------------
server-1     API_Tests  User_Authentication       POST   ✓ PASS     0.45s
server-2     API_Tests  Profile_Update            PUT    ✗ FAIL     1.23s
api-gateway  K8s_Tests  Health_Check              GET    ✓ PASS     0.12s
server-3     API_Tests  Order_Processing          POST   ◦ DRY      0.33s

Results: 120 PASS | 20 FAIL | 5 DRY-RUN | Total: 145
```

### 2. Progress Only (`--display-mode progress`)
**Best for fast tests and CI/CD**

Features:
- Single-line progress updates
- Real-time statistics
- Minimal screen usage
- Detailed final summary

```
TestPilot - Progress Only Mode
==================================================
[  45.2s] Tests: 145 | ✓ 120 | ✗  20 | ◦   5 | Rate:  3.2/sec
```

### 3. Simple Fallback (`--display-mode simple`)
**For environments without blessed support**

Features:
- Line-by-line output
- Basic status display
- No special terminal features required

```
[  1] PASS    User_Authentication     on server-1   (0.45s)
[  2] FAIL    Profile_Update          on server-2   (1.23s)
[  3] PASS    Health_Check            on api-gw     (0.12s)
```

## Installation

### With blessed (recommended):
```bash
pip install blessed
```

### Without blessed:
The system automatically falls back to simple mode if blessed is not available.

## Usage

```bash
# Full dashboard (default)
python test_pilot.py --file tests.xlsx --display-mode blessed

# Progress only mode
python test_pilot.py --file tests.xlsx --display-mode progress

# Simple fallback mode
python test_pilot.py --file tests.xlsx --display-mode simple

# With dry-run
python test_pilot.py --file tests.xlsx --dry-run --display-mode blessed
```

## Technical Features

### Terminal Control
- **Cursor positioning**: Uses blessed's precise cursor control
- **Screen clearing**: Selective updates without full screen refresh
- **Color support**: Automatic detection and graceful degradation
- **Responsive**: Adapts to terminal resizing

### Performance
- **Minimal flickering**: Updates only changed areas
- **Low CPU usage**: Efficient rendering
- **Thread-safe**: Proper locking for concurrent updates
- **Memory efficient**: Sliding window for large test suites

### Cross-platform
- **Unix/Linux**: Full feature support
- **macOS**: Full feature support  
- **Windows**: Full support with modern terminals
- **CI/CD**: Works in headless environments

## Configuration

### Visible Rows
The full dashboard mode shows a configurable number of recent test results:

```python
# In blessed_dashboard.py
dashboard = BlessedDashboard(max_visible_rows=25)  # Default: 20
```

### Colors
Colors are automatically detected and can be disabled:

```bash
# Disable colors
NO_COLOR=1 python test_pilot.py --file tests.xlsx --display-mode blessed
```

## Comparison with Previous Implementation

| Feature | Old (Rich/Live) | New (Blessed) |
|---------|----------------|---------------|
| Flickering | High | None |
| CPU Usage | High | Low |
| Terminal Support | Limited | Excellent |
| Fallback | Poor | Graceful |
| Performance | Slow | Fast |
| Customization | Complex | Simple |

## Demo

Run the interactive demo to see all modes:

```bash
python demo_blessed.py
```

## Troubleshooting

### Terminal Issues
- **Cursor stuck**: Press Ctrl+C to restore
- **Garbled output**: Terminal may not support blessed features
- **No colors**: Set `TERM=xterm-256color` or use `--display-mode simple`

### Performance Issues
- **Slow updates**: Reduce `max_visible_rows`
- **High CPU**: Use `--display-mode progress`
- **Memory usage**: Blessed automatically manages memory

### Compatibility
- **Old terminals**: Use `--display-mode simple`
- **SSH sessions**: May need `TERM` environment variable
- **CI/CD**: Progress mode recommended

## API Reference

### BlessedDashboard
```python
dashboard = BlessedDashboard(max_visible_rows=20)
dashboard.start()                    # Initialize display
dashboard.add_result(test_result)    # Add test result
dashboard.stop()                     # Clean up
dashboard.print_final_summary()      # Show final results
```

### BlessedProgressOnly
```python
dashboard = BlessedProgressOnly()
dashboard.start()                    # Start progress display
dashboard.add_result(test_result)    # Update progress
dashboard.print_final_summary()      # Show final summary
```

## Migration from Old Implementation

The blessed dashboard is a drop-in replacement:

```python
# Old way
from rich_dashboard import RichDashboard
dashboard = RichDashboard(total_steps)

# New way  
from blessed_dashboard import create_blessed_dashboard
dashboard = create_blessed_dashboard(mode="full")
```

All existing code that calls `dashboard.add_result()` and `dashboard.print_final_summary()` continues to work unchanged.