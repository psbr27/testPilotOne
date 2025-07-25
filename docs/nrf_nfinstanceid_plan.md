# NRF nfInstanceId Management Plan

## Problem Statement

NRF testing presents unique challenges due to nfInstanceId tracking across sequential operations:

1. **PUT** requests create new nfInstanceId from payload → NRF returns response with nfInstanceId
2. **GET** requests need the same nfInstanceId to retrieve the registration
3. **DELETE** requests need the same nfInstanceId to remove the registration
4. **Current Issue**: No persistence mechanism between sequential test operations

### Complex Sequence Example
```
PUT → GET → PUT → GET → DELETE → PUT → GET → PATCH → GET → DELETE → PUT
```

This sequence shows:
- Multiple nfInstanceId lifecycles (3 separate PUT operations)
- Mixed operations within same test session
- State dependencies between operations
- Potential for stack pollution if DELETE operations are missing

## Current Implementation Analysis

### From `curl_builder.py:108-125`
✅ **Working:**
- Extracts nfInstanceId from PUT payloads
- Appends to URL for NRF variants (`{"ocnrf", "nrf"}`)

❌ **Missing:**
- No persistence mechanism between sequential test operations
- No traceability of which test step created which instance
- No cleanup for orphaned instances
- No handling of complex multi-PUT sequences

### From `enhanced_pattern_matches.json` Analysis
- Contains 20 NRF test patterns across 3 categories
- Shows consistent nfInstanceId usage: `"6faf1bbc-6e4a-4454-a507-a14ef8e1bc5a"`
- Demonstrates PUT/GET/DELETE operation sequences
- Includes error scenarios (400, 413 status codes)

## Solution Architecture

### 1. Enhanced NRF Sequence Manager

```python
class EnhancedNRFSequenceManager:
    def __init__(self):
        self.instance_registry = {}  # Complete registry of all instances
        self.test_step_context = {}  # Track test step hierarchy
        self.active_stack = []       # Current active instances (LIFO)
        self.cleanup_rules = {}      # Auto-cleanup rules

    def handle_operation(self, method, test_context, payload=None):
        """
        test_context = {
            'test_name': 'test_5_1_6_SMF_Registration',
            'test_step': 'step_1_PUT_create_profile',
            'test_suite': 'NRFRegistration',
            'row_number': 21
        }
        """
```

### 2. Stack-Based nfInstanceId Management

#### Operation Flow:
- **PUT operations** → Push new nfInstanceId to stack
- **GET/PATCH operations** → Use top of stack (current active instance)
- **DELETE operations** → Pop from stack (removes current instance)

#### Sequence Execution Example:
```
Stack State After Each Operation:
PUT₁    → [nfId₁]                    # Create first instance
GET₁    → [nfId₁]                    # Read first instance
PUT₂    → [nfId₁, nfId₂]             # Create second instance (stack)
GET₂    → [nfId₁, nfId₂]             # Read second instance (top of stack)
DELETE₂ → [nfId₁]                    # Delete second, pop stack
PUT₃    → [nfId₁, nfId₃]             # Create third instance
GET₃    → [nfId₁, nfId₃]             # Read third instance
PATCH₃  → [nfId₁, nfId₃]             # Update third instance
GET₃    → [nfId₁, nfId₃]             # Read updated third
DELETE₃ → [nfId₁]                    # Delete third, pop stack
PUT₄    → [nfId₁, nfId₄]             # Create fourth instance
```

### 3. Full Traceability System

```python
def _create_instance(self, test_context, payload):
    nf_id = self._extract_or_generate_nf_id(payload)
    timestamp = datetime.now()

    # Full traceability record
    instance_record = {
        'nfInstanceId': nf_id,
        'created_by': {
            'test_name': test_context['test_name'],
            'test_step': test_context['test_step'],
            'row_number': test_context.get('row_number'),
            'timestamp': timestamp
        },
        'operations_history': [
            {'method': 'PUT', 'timestamp': timestamp, 'step': test_context['test_step']}
        ],
        'status': 'active',
        'cleanup_policy': self._determine_cleanup_policy(test_context)
    }
```

### 4. Automatic Cleanup Strategies

#### Cleanup Policies:
```python
class CleanupPolicy:
    TEST_END_CLEANUP = "test_end"      # Clean when test completes
    SUITE_END_CLEANUP = "suite_end"    # Clean when test suite completes
    SESSION_END_CLEANUP = "session_end" # Clean when session ends
    MANUAL_ONLY = "manual"             # Only DELETE operations clean
```

#### Pattern-Based Policy Assignment:
```python
def _determine_cleanup_policy(self, test_context):
    test_name = test_context['test_name']

    if "registration" in test_name.lower():
        return CleanupPolicy.TEST_END_CLEANUP
    elif "discovery" in test_name.lower():
        return CleanupPolicy.SUITE_END_CLEANUP
    else:
        return CleanupPolicy.SESSION_END_CLEANUP
```

### 5. Smart Instance Selection

```python
def _use_active_instance(self, test_context, method):
    """Smart selection of which instance to use for GET/PATCH operations"""

    # Strategy 1: Use most recent instance from same test
    for nf_id in reversed(self.active_stack):
        record = self.instance_registry[nf_id]
        if record['created_by']['test_name'] == test_context['test_name']:
            return nf_id

    # Strategy 2: Use most recent instance from stack (top)
    if self.active_stack:
        return self.active_stack[-1]

    # Strategy 3: No active instances - return None (will cause test failure)
    return None
```

### 6. Test Step Context Tracking

```python
def track_test_progression(self, current_test_context):
    """Track test progression and detect transitions"""
    prev_context = self.test_step_context.get('current')

    # Detect test transitions
    if prev_context:
        if prev_context['test_name'] != current_test_context['test_name']:
            # New test started - cleanup previous test instances
            self.auto_cleanup(CleanupPolicy.TEST_END_CLEANUP, prev_context)
        elif prev_context['test_suite'] != current_test_context['test_suite']:
            # New test suite - cleanup suite instances
            self.auto_cleanup(CleanupPolicy.SUITE_END_CLEANUP, prev_context)
```

## Implementation Plan

### Phase 1: Core Infrastructure
1. **Create EnhancedNRFSequenceManager class**
   - Implement stack-based instance management
   - Add full traceability system
   - Build test context tracking

2. **Integrate with curl_builder.py**
   - Modify existing nfInstanceId handling
   - Add sequence manager integration
   - Maintain backward compatibility

### Phase 2: Cleanup & Monitoring
3. **Implement Automatic Cleanup**
   - Add cleanup policies and triggers
   - Build orphan detection system
   - Create cleanup execution engine

4. **Add Diagnostic Tools**
   - Stack health monitoring
   - Instance lifecycle reports
   - Performance metrics

### Phase 3: Testing & Validation
5. **Create Test Cases**
   - Unit tests for sequence manager
   - Integration tests with existing pipeline
   - Complex sequence validation

6. **Performance Testing**
   - Memory usage optimization
   - Cleanup efficiency validation
   - Concurrent test session handling

## Integration Points

### Enhanced curl_builder.py
```python
# In build_curl_command()
if nf_name.lower() in nrf_variants:
    sequence_manager = get_or_create_sequence_manager(test_session)

    if method == "PUT":
        nf_instance_id = sequence_manager.handle_operation(
            "PUT", test_name, resolved_payload, None
        )
    else:  # GET, DELETE, PATCH
        nf_instance_id = sequence_manager.handle_operation(
            method, test_name
        )

    if nf_instance_id:
        url = f"{url}{nf_instance_id}"
```

### Test Execution Pipeline
```python
# Before each test step
sequence_manager.track_test_progression(test_context)

# During curl_builder call
nf_instance_id = sequence_manager.handle_operation(method, test_context, payload)

# After test completion
sequence_manager.auto_cleanup(CleanupPolicy.TEST_END_CLEANUP, test_context)

# Generate reports
diagnostic_report = sequence_manager.get_diagnostic_report()
```

## Advanced Features

### 1. Response-Based nfInstanceId Extraction
```python
def update_from_response(self, method, response_data):
    """Update stack with actual nfInstanceId from server response"""
    if method == "PUT" and self.instance_stack:
        actual_id = extract_nf_id_from_response(response_data)
        if actual_id:
            self.instance_stack[-1]['nfInstanceId'] = actual_id
```

### 2. Session Isolation
```python
# Each test file/session gets its own sequence manager
session_managers = {}  # {session_id: NRFSequenceManager}
```

### 3. Error Recovery
```python
def handle_failed_operation(self, method, error):
    """Handle failed operations and maintain stack consistency"""
    if method == "DELETE" and not error.is_not_found():
        # Don't pop stack if DELETE failed for other reasons
        pass
```

### 4. Diagnostic & Monitoring
```python
def get_diagnostic_report(self):
    return {
        'active_instances': len(self.active_stack),
        'total_instances_created': len(self.instance_registry),
        'instances_by_test': self._group_by_test(),
        'orphaned_instances': self._find_orphaned_instances(),
        'stack_health': self._assess_stack_health(),
        'cleanup_recommendations': self._suggest_cleanups()
    }
```

## Benefits

### Immediate Benefits
1. **Solves nfInstanceId Tracking**: PUT→GET→DELETE sequences work seamlessly
2. **Handles Complex Sequences**: Multi-PUT scenarios with nested lifecycles
3. **Prevents Stack Pollution**: Automatic cleanup prevents resource leaks
4. **Full Traceability**: Know exactly which test step created each instance

### Long-term Benefits
1. **Test Isolation**: Prevents cross-test contamination
2. **Error Resilience**: Failed operations don't corrupt state
3. **Performance Monitoring**: Track resource usage and cleanup efficiency
4. **Scalability**: Supports concurrent test sessions with independent state

### Compatibility
1. **Backward Compatible**: Existing non-NRF tests unchanged
2. **Progressive Enhancement**: Can be enabled per test suite
3. **Configurable Policies**: Different cleanup strategies for different patterns
4. **Diagnostic Tools**: Monitor and debug instance management

## Risk Mitigation

### Technical Risks
- **Memory Usage**: Mitigated by automatic cleanup policies
- **Performance Impact**: Minimal overhead with efficient data structures
- **Complexity**: Modular design allows incremental implementation

### Operational Risks
- **False Positives**: Smart instance selection reduces wrong ID usage
- **Test Dependencies**: Session isolation prevents cross-test issues
- **Debug Difficulty**: Comprehensive diagnostic tools for troubleshooting

## Success Metrics

1. **Functional Success**:
   - 100% success rate for NRF PUT→GET→DELETE sequences
   - Zero orphaned nfInstanceId instances after test completion
   - Correct nfInstanceId usage in complex multi-PUT scenarios

2. **Performance Success**:
   - < 10ms overhead per operation
   - < 1MB memory usage per test session
   - 100% cleanup efficiency for completed tests

3. **Reliability Success**:
   - Zero cross-test nfInstanceId contamination
   - 99.9% uptime for sequence manager
   - Complete audit trails for all instance operations

This comprehensive solution addresses the NRF nfInstanceId tracking challenges while providing robust error handling, performance optimization, and full operational visibility.
