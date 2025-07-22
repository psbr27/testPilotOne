# NRF nfInstanceId Implementation Plan

## Overview

This implementation plan ensures the NRF nfInstanceId tracking feature is added without disturbing the existing logic for other NF types (SLF, SMF, UDM, etc.). The implementation uses the `nf_name` from `config/hosts.json` to isolate NRF-specific behavior.

## Current State Analysis

### Existing Flow
1. **nf_name Detection**: `curl_builder.py` reads `nf_name` from `config/hosts.json` (lines 76-106)
2. **NRF Handling**: When `nf_name.lower() in {"ocnrf", "nrf"}`, it extracts nfInstanceId from payload and appends to URL (lines 111-125)
3. **Test Context**: Currently not passed to `build_curl_command()` but available at all call sites

### Key Constraint
- Must maintain backward compatibility for all non-NRF NF types
- Only activate enhanced tracking when `nf_name` is NRF variant

## Implementation Architecture

### 1. New Module Structure
```
src/testpilot/
├── utils/
│   ├── curl_builder.py          # Minimal changes - add test_context parameter
│   └── nrf/                     # New NRF-specific module
│       ├── __init__.py
│       ├── sequence_manager.py  # NRF sequence management
│       └── instance_tracker.py  # nfInstanceId tracking logic
```

### 2. Minimal Changes to Existing Code

#### curl_builder.py Modifications
```python
def build_curl_command(
    url: str,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    payload: Optional[Union[str, Dict, List]] = None,
    payloads_folder: str = "payloads",
    extra_curl_args: Optional[List[str]] = None,
    direct_json_allowed: bool = True,
    test_context: Optional[Dict[str, Any]] = None,  # NEW PARAMETER
) -> Tuple[str, Optional[str]]:
    """
    Added test_context parameter for NRF tracking.
    Backward compatible - defaults to None.
    """
    # ... existing code remains unchanged until line 107 ...

    # Modified NRF handling section (lines 108-125)
    nrf_variants = {"ocnrf", "nrf"}
    if nf_name.lower() in nrf_variants:
        # Import NRF handler only when needed (lazy import)
        from testpilot.utils.nrf.sequence_manager import handle_nrf_operation

        # Delegate to NRF-specific handler
        modified_url = handle_nrf_operation(
            url=url,
            method=method,
            payload=resolved_payload,
            test_context=test_context,
            nf_name=nf_name
        )
        if modified_url:
            url = modified_url

    # ... rest of existing code unchanged ...
```

### 3. NRF Sequence Manager Implementation

#### src/testpilot/utils/nrf/sequence_manager.py
```python
import json
import logging
from datetime import datetime
from typing import Dict, Optional, Any
from .instance_tracker import NRFInstanceTracker

logger = logging.getLogger("NRFSequenceManager")

# Global session managers per test session
_session_managers: Dict[str, NRFInstanceTracker] = {}

def get_or_create_session_manager(session_id: str) -> NRFInstanceTracker:
    """Get or create a session-specific NRF instance tracker"""
    if session_id not in _session_managers:
        _session_managers[session_id] = NRFInstanceTracker()
    return _session_managers[session_id]

def handle_nrf_operation(
    url: str,
    method: str,
    payload: Optional[str],
    test_context: Optional[Dict[str, Any]],
    nf_name: str
) -> Optional[str]:
    """
    Handle NRF-specific operations with nfInstanceId tracking.
    Returns modified URL if needed, None otherwise.
    """
    # If no test context, fall back to legacy behavior
    if not test_context:
        return _legacy_nrf_handling(url, method, payload)

    # Extract session identifier
    session_id = test_context.get('session_id', 'default')
    tracker = get_or_create_session_manager(session_id)

    # Track test progression
    tracker.track_test_progression(test_context)

    # Handle operation based on method
    if method == "PUT":
        nf_instance_id = _extract_nf_instance_id(payload)
        if nf_instance_id:
            tracker.handle_put_operation(test_context, nf_instance_id)
            return f"{url}{nf_instance_id}"

    elif method in ["GET", "PATCH"]:
        nf_instance_id = tracker.get_active_instance_id(test_context)
        if nf_instance_id:
            return f"{url}{nf_instance_id}"

    elif method == "DELETE":
        nf_instance_id = tracker.handle_delete_operation(test_context)
        if nf_instance_id:
            return f"{url}{nf_instance_id}"

    return None

def _legacy_nrf_handling(url: str, method: str, payload: Optional[str]) -> Optional[str]:
    """Maintain existing behavior for backward compatibility"""
    if payload and method in ["PUT", "GET", "DELETE", "PATCH"]:
        try:
            parsed = json.loads(payload)
            nf_instance_id = None

            if isinstance(parsed, dict):
                nf_instance_id = parsed.get("nfInstanceId")
            elif isinstance(parsed, list):
                for item in parsed:
                    if isinstance(item, dict) and "nfInstanceId" in item:
                        nf_instance_id = item["nfInstanceId"]
                        break

            if nf_instance_id:
                return f"{url}{nf_instance_id}"
        except (json.JSONDecodeError, TypeError):
            pass

    return None

def _extract_nf_instance_id(payload: Optional[str]) -> Optional[str]:
    """Extract nfInstanceId from payload"""
    if not payload:
        return None

    try:
        parsed = json.loads(payload)
        if isinstance(parsed, dict):
            return parsed.get("nfInstanceId")
        elif isinstance(parsed, list):
            for item in parsed:
                if isinstance(item, dict) and "nfInstanceId" in item:
                    return item["nfInstanceId"]
    except (json.JSONDecodeError, TypeError):
        pass

    return None
```

#### src/testpilot/utils/nrf/instance_tracker.py
```python
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum

class CleanupPolicy(Enum):
    TEST_END = "test_end"
    SUITE_END = "suite_end"
    SESSION_END = "session_end"
    MANUAL_ONLY = "manual"

class NRFInstanceTracker:
    """Tracks nfInstanceId lifecycle for NRF operations"""

    def __init__(self):
        self.instance_registry: Dict[str, Dict[str, Any]] = {}
        self.active_stack: List[str] = []
        self.test_context_history: List[Dict[str, Any]] = []
        self.current_test_context: Optional[Dict[str, Any]] = None

    def track_test_progression(self, test_context: Dict[str, Any]):
        """Track test progression and trigger cleanups"""
        if self.current_test_context:
            # Check for test transition
            if self.current_test_context.get('test_name') != test_context.get('test_name'):
                self._cleanup_test_instances(self.current_test_context)
            elif self.current_test_context.get('sheet') != test_context.get('sheet'):
                self._cleanup_suite_instances(self.current_test_context)

        self.current_test_context = test_context
        self.test_context_history.append(test_context)

    def handle_put_operation(self, test_context: Dict[str, Any], nf_instance_id: str):
        """Handle PUT operation - create new instance"""
        timestamp = datetime.now()

        instance_record = {
            'nfInstanceId': nf_instance_id,
            'created_by': {
                'test_name': test_context.get('test_name'),
                'test_step': test_context.get('row_idx'),
                'sheet': test_context.get('sheet'),
                'timestamp': timestamp
            },
            'operations': [{'method': 'PUT', 'timestamp': timestamp}],
            'status': 'active',
            'cleanup_policy': self._determine_cleanup_policy(test_context)
        }

        self.instance_registry[nf_instance_id] = instance_record
        self.active_stack.append(nf_instance_id)

    def get_active_instance_id(self, test_context: Dict[str, Any]) -> Optional[str]:
        """Get active instance ID for GET/PATCH operations"""
        # Strategy 1: Use most recent from same test
        test_name = test_context.get('test_name')
        for nf_id in reversed(self.active_stack):
            record = self.instance_registry.get(nf_id, {})
            if record.get('created_by', {}).get('test_name') == test_name:
                self._log_operation(nf_id, 'GET/PATCH')
                return nf_id

        # Strategy 2: Use top of stack
        if self.active_stack:
            nf_id = self.active_stack[-1]
            self._log_operation(nf_id, 'GET/PATCH')
            return nf_id

        return None

    def handle_delete_operation(self, test_context: Dict[str, Any]) -> Optional[str]:
        """Handle DELETE operation - remove instance"""
        nf_id = self.get_active_instance_id(test_context)
        if nf_id and nf_id in self.active_stack:
            self.active_stack.remove(nf_id)
            self._mark_deleted(nf_id)
        return nf_id

    def _determine_cleanup_policy(self, test_context: Dict[str, Any]) -> CleanupPolicy:
        """Determine cleanup policy based on test patterns"""
        test_name = test_context.get('test_name', '').lower()

        if 'registration' in test_name:
            return CleanupPolicy.TEST_END
        elif 'discovery' in test_name:
            return CleanupPolicy.SUITE_END
        else:
            return CleanupPolicy.SESSION_END

    def _cleanup_test_instances(self, test_context: Dict[str, Any]):
        """Clean up instances when test ends"""
        test_name = test_context.get('test_name')
        to_cleanup = []

        for nf_id, record in self.instance_registry.items():
            if (record['status'] == 'active' and
                record['cleanup_policy'] == CleanupPolicy.TEST_END and
                record['created_by']['test_name'] == test_name):
                to_cleanup.append(nf_id)

        for nf_id in to_cleanup:
            if nf_id in self.active_stack:
                self.active_stack.remove(nf_id)
            self._mark_deleted(nf_id, reason='auto_cleanup_test_end')

    def _cleanup_suite_instances(self, test_context: Dict[str, Any]):
        """Clean up instances when suite ends"""
        sheet = test_context.get('sheet')
        to_cleanup = []

        for nf_id, record in self.instance_registry.items():
            if (record['status'] == 'active' and
                record['cleanup_policy'] == CleanupPolicy.SUITE_END and
                record['created_by']['sheet'] == sheet):
                to_cleanup.append(nf_id)

        for nf_id in to_cleanup:
            if nf_id in self.active_stack:
                self.active_stack.remove(nf_id)
            self._mark_deleted(nf_id, reason='auto_cleanup_suite_end')

    def _log_operation(self, nf_id: str, method: str):
        """Log operation on instance"""
        if nf_id in self.instance_registry:
            self.instance_registry[nf_id]['operations'].append({
                'method': method,
                'timestamp': datetime.now()
            })

    def _mark_deleted(self, nf_id: str, reason: str = 'DELETE'):
        """Mark instance as deleted"""
        if nf_id in self.instance_registry:
            self.instance_registry[nf_id]['status'] = 'deleted'
            self.instance_registry[nf_id]['deleted_at'] = datetime.now()
            self.instance_registry[nf_id]['deletion_reason'] = reason

    def get_diagnostic_report(self) -> Dict[str, Any]:
        """Generate diagnostic report"""
        active_instances = [nf_id for nf_id, record in self.instance_registry.items()
                          if record['status'] == 'active']

        return {
            'active_instances': len(active_instances),
            'active_stack_size': len(self.active_stack),
            'total_instances_created': len(self.instance_registry),
            'instances_by_test': self._group_by_test(),
            'orphaned_instances': self._find_orphaned_instances()
        }

    def _group_by_test(self) -> Dict[str, int]:
        """Group instances by test name"""
        by_test = {}
        for record in self.instance_registry.values():
            test_name = record['created_by']['test_name']
            by_test[test_name] = by_test.get(test_name, 0) + 1
        return by_test

    def _find_orphaned_instances(self) -> List[Dict[str, Any]]:
        """Find potentially orphaned instances"""
        orphaned = []
        current_test = self.current_test_context.get('test_name') if self.current_test_context else None

        for nf_id, record in self.instance_registry.items():
            if (record['status'] == 'active' and
                record['created_by']['test_name'] != current_test and
                record['cleanup_policy'] == CleanupPolicy.TEST_END):

                orphaned.append({
                    'nfInstanceId': nf_id,
                    'created_by': record['created_by']['test_name'],
                    'age_minutes': (datetime.now() - record['created_by']['timestamp']).seconds / 60
                })

        return orphaned
```

### 4. Integration Points

#### Modify test_pilot_core.py
```python
# In build_command_for_step function, add test context
def build_command_for_step(step: TestStep, flow: TestFlow, config: Config) -> Tuple[str, Optional[str]]:
    """Build command for test step execution"""

    # Create test context for NRF tracking
    test_context = {
        'test_name': flow.test_name,
        'sheet': flow.sheet,
        'row_idx': step.row_idx,
        'session_id': f"{flow.sheet}_{flow.test_name}"  # Unique session ID
    }

    if config.pod_mode:
        return build_pod_mode(
            url=substituted_url,
            method=method,
            headers=substituted_headers,
            payload=substituted_payload,
            payloads_folder="payloads",
            test_context=test_context  # Pass context
        )
    else:
        return build_url_based_command(
            config=config,
            url=substituted_url,
            method=method,
            headers=substituted_headers,
            payload=substituted_payload,
            test_context=test_context  # Pass context
        )
```

#### Update build_url_based_command and build_pod_mode
```python
# Add test_context parameter and pass through to build_curl_command
def build_url_based_command(
    config: Config,
    url: str,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    payload: Optional[Union[str, Dict, List]] = None,
    test_context: Optional[Dict[str, Any]] = None  # NEW
) -> Tuple[str, Optional[str]]:
    # ... existing code ...
    return build_curl_command(
        url=url,
        method=method,
        headers=headers,
        payload=payload,
        payloads_folder="payloads",
        test_context=test_context  # Pass through
    )
```

### 5. Session Cleanup Hook

Add cleanup at test session end:

```python
# In test_pilot.py main function
def run_tests():
    try:
        # ... existing test execution ...
    finally:
        # Cleanup NRF sessions
        from testpilot.utils.nrf.sequence_manager import cleanup_all_sessions
        cleanup_all_sessions()
```

## Implementation Phases

### Phase 1: Core Infrastructure (Week 1)
1. Create NRF module structure
2. Implement NRFInstanceTracker
3. Add test_context parameter to build_curl_command (backward compatible)
4. Basic integration testing

### Phase 2: Integration (Week 2)
1. Update all call sites to pass test_context
2. Integrate with test_pilot_core.py
3. Add session cleanup hooks
4. End-to-end testing with sample NRF tests

### Phase 3: Advanced Features (Week 3)
1. Response-based nfInstanceId updates
2. Diagnostic reporting
3. Performance optimization
4. Documentation and examples

## Testing Strategy

### Unit Tests
```python
# test_nrf_instance_tracker.py
def test_nrf_instance_lifecycle():
    tracker = NRFInstanceTracker()

    # Test PUT operation
    test_context = {'test_name': 'test_1', 'sheet': 'NRF', 'row_idx': 1}
    tracker.handle_put_operation(test_context, 'nf-123')
    assert len(tracker.active_stack) == 1

    # Test GET operation
    nf_id = tracker.get_active_instance_id(test_context)
    assert nf_id == 'nf-123'

    # Test DELETE operation
    deleted_id = tracker.handle_delete_operation(test_context)
    assert deleted_id == 'nf-123'
    assert len(tracker.active_stack) == 0
```

### Integration Tests
1. Test with real NRF test sequences
2. Verify no impact on non-NRF tests
3. Test cleanup policies
4. Performance benchmarks

## Rollback Plan

If issues arise:
1. Set `test_context=None` in all calls to disable NRF tracking
2. NRF handler falls back to legacy behavior automatically
3. Remove NRF module if needed (no impact on core code)

## Monitoring & Diagnostics

### Logging
```python
# Enable detailed NRF tracking logs
logging.getLogger("NRFSequenceManager").setLevel(logging.DEBUG)
```

### Diagnostic Endpoint
```python
# Get current NRF state
from testpilot.utils.nrf.sequence_manager import get_global_diagnostic_report
report = get_global_diagnostic_report()
```

## Success Criteria

1. **Functionality**: NRF tests with PUT→GET→DELETE sequences work correctly
2. **Compatibility**: Zero impact on non-NRF tests
3. **Performance**: < 5ms overhead per operation
4. **Reliability**: 100% cleanup rate for completed tests
5. **Maintainability**: Clear separation of NRF logic from core code
