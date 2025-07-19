# TestPilot Mock Testing Integration Plan (Simplified)

## 🎯 Goal
Add `--execution-mode mock` support to TestPilot for fast, local testing using mock servers instead of remote systems.

## 🏗 Current vs Mock Architecture

### Current TestPilot Flow
```
Excel → Parser → TestFlows → SSH Remote Execution → Remote Server → Response Validation
```

### Proposed Mock Flow
```
Excel → Parser → TestFlows → Local Mock Server → Mock Response → Response Validation
```

## 🔄 Single Integration Approach

### CLI Interface
```bash
# Production mode (default - current behavior)
python test_pilot.py -i tests.xlsx -m otp

# Mock mode (new - simplified)
python test_pilot.py -i tests.xlsx -m otp --execution-mode mock
```

### Implementation Strategy
1. Add `--execution-mode mock` CLI parameter
2. Create simple execution router
3. Route to mock testing framework when `--execution-mode mock`
4. Keep existing production flow unchanged

## 🤔 **Key Design Question: Data Simulation Strategy**

When integrating mock mode into TestPilot, we need to decide **how to simulate server responses** that would normally come from remote systems.

### **Current Production Flow Data:**
```
TestPilot → SSH → Remote Server → Real API Response → Validation
```

### **Mock Flow Data Options:**

#### **Smart Mock with Real-like Data** - Lets start with this one.
```
TestPilot → Smart Mock Server → Generated Response → Validation
```
- Mock server generates realistic responses dynamically
- **Pros**: More realistic testing
- **Cons**: Complex to implement


## 🎯 **Critical Questions to Resolve:**

### **1. Response Data Source**
- Should mock responses come from Excel test data? No excel files as data source.
- Should we generate realistic responses dynamically? not required
- Should we capture real responses and replay them? I have a real responses data from server in a JSON format, will share that.

### **2. State Management**
- How do we handle stateful operations (CREATE → READ → UPDATE → DELETE)? It shall act like a real server
- Should mock server maintain in-memory state between requests? yes
- How do we reset state between test runs? Do we really have to do? if mandatory reset the state before next test run otherwise ignore for now.

### **3. API Compatibility**
- Which APIs need to be mocked (NRF, OTP, others)? There are many NFs, we are starting with NRF specific mock tests. This has to be expanded to other NFs later, I'm looking for more generic because URLs will keep changing but the actual server GET, PUT, POST, DELETE remains same.
- Should we create API-specific mock servers or a generic one? generic
- How do we handle different API versions/schemas? Lets start with basic version, then we can start improving as progress is made.

### **4. Test Data Management**
- Where do we store mock response templates? may be save them in a .json format, which can inspected later if any issues with the outcome.
- How do we handle test-specific vs shared mock data? it should be test specific
- Should mock data be version controlled with tests? I don't think so

### **5. Integration Points**
- Should we replace SSH execution entirely in mock mode? yes
- How do we handle TestPilot's existing validation logic? we use as it is except the SSH response comes from mock server, except that nothing should be changed.
- Should we reuse existing `test_pilot_core.py` logic or bypass it? we use as it except mocking SSH response and ignore mapping requests they can be used from config/resources_map.json

## 📋 **Implementation Plan Based on Your Requirements**

### **Your Key Decisions:**
✅ **Generic Mock Server** - Not NRF-specific, handle any API
✅ **Real Response Data** - Use your JSON response data from real server
✅ **State Management** - Act like real server with in-memory state
✅ **Replace SSH entirely** - Mock server response instead of SSH
✅ **Reuse existing validation** - Same logic, different data source
✅ **Test-specific data** - Store responses in JSON format per test

### **Implementation Strategy:**

#### **Step 1: Generic Mock Server**
```python
# Create a generic HTTP mock server that can handle any API
class GenericMockServer:
    def __init__(self, response_data_file):
        self.app = Flask(__name__)
        self.state = {}  # In-memory state like real server
        self.response_data = self.load_real_responses(response_data_file)
        self.setup_generic_routes()

    def setup_generic_routes(self):
        @self.app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
        def handle_any_request(path):
            return self.simulate_real_server_behavior(path, request)
```

#### **Step 2: CLI Integration with SSH Replacement**
```python
# In test_pilot.py - add execution mode
parser.add_argument('--execution-mode', choices=['production', 'mock'], default='production')

# In execute_flows() - intercept SSH execution
if args.execution_mode == 'mock':
    # Replace SSH execution with HTTP request to mock server
    mock_response = send_http_request_to_mock_server(command_data)
    # Feed mock response to existing validation logic
    validate_and_create_result(step, flow, step_data, mock_response, ...)
else:
    # Use existing SSH/kubectl execution
    execute_command(command, host, connector)
```

#### **Step 3: Response Data Integration**
```python
# Load your real server responses and use them for mock behavior
class RealResponseLoader:
    def load_responses_from_json(self, json_file):
        # Load your real response data
        with open(json_file) as f:
            return json.load(f)

    def simulate_server_state(self, method, path, payload):
        # Simulate real server behavior based on your response data
        if method == 'PUT':
            # Create/Update resource, return appropriate response
        elif method == 'GET':
            # Return stored resource data
        # etc.
```

#### **Step 4: Keep Existing Validation Logic**
```python
# No changes to response_parser.py, validation_engine.py
# Just feed mock responses to existing validation:

# Current: SSH response → parse_curl_output() → validate_test_result()
# Mock:    HTTP response → parse_curl_output() → validate_test_result()
```

## 💭 **Discussion Points:**

1. **Which APIs are you primarily testing?** (This affects mock server design)
2. **How important is stateful testing?** (CRUD operations, session management)
3. **Do you want realistic data generation or Excel-driven responses?**
4. **Should mock mode completely bypass SSH or just redirect requests?**
5. **How do you currently handle test data in production mode?**

Let's discuss these design decisions before implementing anything!
