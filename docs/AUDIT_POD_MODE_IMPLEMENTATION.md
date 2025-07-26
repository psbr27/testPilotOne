# Audit Module Pod Mode Implementation

## Overview

The TestPilot Audit Module has been extended with "Pod Mode" support, enabling testPilot to run directly within Jenkins pods. This implementation provides specialized logic for execution context detection, command processing, and resource management in containerized environments.

## Key Features

### 1. Pod Mode Detection
The audit module automatically detects when testPilot is running inside a Jenkins pod by checking multiple indicators:

- **Kubernetes Environment Variables**: `KUBERNETES_SERVICE_HOST`, `KUBERNETES_SERVICE_PORT`, `KUBE_POD_NAME`, `POD_NAME`, `POD_NAMESPACE`
- **Jenkins Environment Variables**: `JENKINS_URL`, `BUILD_NUMBER`, `JOB_NAME`, `WORKSPACE`
- **Container Indicators**: Presence of `/.dockerenv` file, cgroup information
- **Pod-Specific Files**: Kubernetes secret mounts at `/var/run/secrets/kubernetes.io`

### 2. Resource Map Configuration
In pod mode, testPilot requires a `resources_map.json` file in the `config/` directory for placeholder pattern resolution:

```json
{
  "service_endpoints": {
    "user_service": "http://user-service:8080",
    "auth_service": "http://auth-service:8081"
  },
  "kubernetes_services": {
    "egressgateway": "provgw-prov-egressgateway",
    "ingressgateway-prov": "ocslf-ingressgateway-prov"
  },
  "common_placeholders": {
    "base_url": "http://api.test.com",
    "api_version": "v1",
    "tenant_id": "test-tenant"
  }
}
```

### 3. Simplified Command Execution
Pod mode uses direct curl command execution instead of complex kubectl exec wrappers:

- Validates curl commands from Excel sheets
- Resolves placeholders using `resources_map.json`
- Executes commands directly within the pod environment
- Captures stdout/stderr for audit validation

### 4. Log Management
Pod mode eliminates local log file creation:
- All logs go to stdout/stderr for Jenkins pipeline capture
- No `logs/` folder creation in ephemeral pod storage
- Compatible with external log aggregation solutions

### 5. Output Management
Audit reports are generated in pod-aware output directories:
- Uses `WORKSPACE` environment variable when available
- Creates Excel and HTML reports in accessible locations
- Maintains full audit functionality

## Architecture Components

### PodModeManager
Central component that handles:
- Pod mode detection logic
- Resource map loading and validation
- Placeholder resolution
- Command execution and validation
- Output directory management

### Enhanced Audit Processor
Extended with `process_single_step_audit_pod_mode()` function:
- Detects pod mode and switches execution strategy
- Performs direct curl command execution
- Maintains full audit validation
- Updates dashboards and test results

### Audit Engine Integration
Seamless integration with existing audit validation:
- 100% pattern matching validation
- HTTP method and status code validation
- Comprehensive audit trail generation
- Pod mode metadata in audit results

## Usage

### Automatic Mode Switching
The audit module automatically detects pod mode and switches execution strategies:

```python
from src.testpilot.audit import process_single_step_audit_pod_mode

# Automatically detects and handles pod vs non-pod mode
process_single_step_audit_pod_mode(
    step, flow, target_hosts, svc_maps, placeholder_pattern,
    connector, host_cli_map, test_results, audit_engine,
    show_table, dashboard, args, step_delay
)
```

### Manual Pod Mode Manager Usage
Direct usage of pod mode functionality:

```python
from src.testpilot.audit import pod_mode_manager

# Check execution environment
if pod_mode_manager.is_pod_mode():
    print("Running in Jenkins pod")

    # Load resource mappings
    resources = pod_mode_manager.load_resources_map()

    # Resolve placeholders
    command = "curl {{api_url}}/users"
    resolved = pod_mode_manager.resolve_placeholders(command)

    # Execute command
    stdout, stderr, code = pod_mode_manager.execute_curl_command(resolved)
```

## Configuration Requirements

### For Pod Mode Execution
1. **Mandatory**: `config/resources_map.json` file with placeholder mappings
2. **Environment**: Kubernetes/Jenkins environment variables
3. **Commands**: Valid curl commands in Excel test sheets

### For Non-Pod Mode
- No additional configuration required
- Falls back to standard OTP execution logic
- Compatible with existing SSH and local execution modes

## Error Handling

### Pod Mode Validation
- **Missing Resources Map**: Immediate error with clear message
- **Invalid JSON**: Descriptive error with line information
- **Empty Configuration**: Error requiring user configuration
- **Invalid Commands**: Warning with command validation details

### Graceful Fallbacks
- Non-pod mode detection triggers standard audit processing
- Command validation failures skip execution with clear logging
- Exception handling prevents audit result corruption

## Testing

### Comprehensive Test Suite
The implementation includes extensive unit tests covering:

- Pod mode detection scenarios
- Resource map loading and validation
- Placeholder resolution patterns
- Command execution simulation
- Audit integration workflows
- Error handling edge cases

### Test Execution
```bash
# Run all pod mode tests
python -m pytest tests/audit/test_pod_mode.py -v

# Run specific test categories
python -m pytest tests/audit/test_pod_mode.py::TestPodModeManager -v
python -m pytest tests/audit/test_pod_mode.py::TestPodModeAuditIntegration -v
```

## Integration Points

### Existing Audit Features
Pod mode maintains full compatibility with:
- ✅ AuditEngine 100% pattern matching
- ✅ AuditExporter Excel/HTML report generation
- ✅ Dashboard integration and updates
- ✅ Comprehensive audit trail generation
- ✅ Error detection and reporting

### Jenkins Pipeline Integration
Pod mode enhances Jenkins pipeline execution:
- Direct command execution within pod context
- Environment variable-based configuration
- Workspace-aware output generation
- Log aggregation compatibility

## Performance Considerations

### Pod Mode Advantages
- **Simplified Execution**: Direct commands without kubectl overhead
- **Reduced Latency**: No remote command execution delays
- **Native Environment**: Commands run in actual service context
- **Resource Efficiency**: No external SSH connections required

### Memory and Storage
- **Ephemeral Storage**: No persistent local files in pods
- **Memory Usage**: Maintains existing audit engine memory footprint
- **Output Generation**: Efficient report generation in workspace

## Migration Guide

### From Standard to Pod Mode
1. Create `config/resources_map.json` with appropriate mappings
2. Update Excel test sheets to use curl commands
3. Configure Jenkins pipeline with pod execution
4. Verify environment variable availability

### Maintaining Compatibility
- Existing non-pod deployments continue working unchanged
- Pod mode detection is automatic and non-intrusive
- Standard audit features remain fully functional

## Monitoring and Debugging

### Log Messages
Pod mode provides clear logging for debugging:
```
🏗️  Pod mode detected - Running inside Jenkins pod environment
✅ Loaded resources_map.json with 5 resource mappings
🚀 Executing curl command: curl -X GET http://user-service:8080/api/v1/users
✅ [AUDIT PASS - POD MODE] test_user_list: 100% validation successful
```

### Context Information
Execution context details available via:
```python
context = pod_mode_manager.get_execution_context()
# Returns comprehensive environment and configuration status
```

## Security Considerations

### Resource Map Security
- Store sensitive URLs/endpoints in Kubernetes secrets
- Use environment variable substitution for credentials
- Avoid hardcoding sensitive information in resource maps

### Command Execution
- Only curl commands are executed directly
- Command validation prevents injection attacks
- Subprocess execution with proper error handling

## Future Enhancements

### Planned Features
- Support for additional command types beyond curl
- Dynamic resource map loading from ConfigMaps
- Enhanced placeholder pattern matching
- Integration with Kubernetes service discovery

### Compatibility
- Backward compatibility with existing audit workflows
- Progressive enhancement of pod mode capabilities
- Seamless integration with future testPilot features
