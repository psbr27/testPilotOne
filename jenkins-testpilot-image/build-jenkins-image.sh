#!/bin/bash
# Build and package Jenkins TestPilot image for customer distribution

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_step() { echo -e "${BLUE}[STEP]${NC} $1"; }

# Configuration
IMAGE_NAME="testpilot-jenkins"
IMAGE_TAG="1.0.0"
TESTPILOT_DIR="../dist/testPilot"
OUTPUT_DIR="./output"
TEMP_DIR="./testpilot-assets"

# Validate prerequisites
log_step "Validating prerequisites..."

if [ ! -d "$TESTPILOT_DIR" ]; then
    log_error "TestPilot distribution not found at $TESTPILOT_DIR"
    log_info "Please build TestPilot first using: bash build_with_spec.sh"
    exit 1
fi

if ! command -v docker &> /dev/null; then
    log_error "Docker not installed. Please install Docker first."
    exit 1
fi

# Clean previous builds
log_step "Cleaning previous builds..."
rm -rf "$OUTPUT_DIR" "$TEMP_DIR"
mkdir -p "$OUTPUT_DIR" "$TEMP_DIR"

# Prepare TestPilot assets
log_step "Preparing TestPilot assets..."
cp -r "$TESTPILOT_DIR"/* "$TEMP_DIR/"

# Ensure config directory exists
mkdir -p "$TEMP_DIR/config"

# Create a sample resources_map.json if it doesn't exist
if [ ! -f "$TEMP_DIR/config/resources_map.json" ]; then
    log_info "Creating sample resources_map.json..."
    cat > "$TEMP_DIR/config/resources_map.json" << 'EOF'
{
    "comment": "Sample resources_map.json for TestPilot Pod Mode",
    "description": "Update this file with your service endpoints and placeholders",

    "service_endpoints": {
        "example_service": "http://example-service:8080",
        "api_gateway": "http://api-gateway:8082"
    },

    "kubernetes_services": {
        "namespace": "default",
        "cluster_name": "customer-cluster"
    },

    "common_placeholders": {
        "base_url": "http://api.example.com",
        "api_version": "v1"
    }
}
EOF
fi

# Build Docker image
log_step "Building Docker image..."
docker build -t "${IMAGE_NAME}:${IMAGE_TAG}" .

if [ $? -ne 0 ]; then
    log_error "Docker build failed"
    exit 1
fi

# Verify image
log_step "Verifying Docker image..."
docker images | grep "$IMAGE_NAME" | grep "$IMAGE_TAG"

# Export Docker image to tar file
log_step "Exporting Docker image to tar file..."
TAR_FILE="${OUTPUT_DIR}/${IMAGE_NAME}-${IMAGE_TAG}.tar"
docker save -o "$TAR_FILE" "${IMAGE_NAME}:${IMAGE_TAG}"

if [ $? -ne 0 ]; then
    log_error "Failed to export Docker image"
    exit 1
fi

# Compress the tar file
log_step "Compressing image..."
gzip "$TAR_FILE"
FINAL_FILE="${TAR_FILE}.gz"

# Create deployment package
log_step "Creating deployment package..."
DEPLOY_DIR="${OUTPUT_DIR}/testpilot-jenkins-deploy"
mkdir -p "$DEPLOY_DIR"

# Copy deployment files
cp "$FINAL_FILE" "$DEPLOY_DIR/"
cp Jenkinsfile "$DEPLOY_DIR/"

# Create deployment documentation
cat > "$DEPLOY_DIR/README.md" << 'EOF'
# TestPilot Jenkins Deployment Package

## Contents
- `testpilot-jenkins-*.tar.gz`: Docker image containing Jenkins with TestPilot
- `Jenkinsfile`: Pre-configured pipeline for TestPilot execution
- `deploy-to-k8s.sh`: Deployment script for Kubernetes
- `sample-excel/`: Sample TestPilot Excel files

## Quick Start

### 1. Load Docker Image
```bash
# Load the image into your Docker registry
gunzip testpilot-jenkins-*.tar.gz
docker load -i testpilot-jenkins-*.tar

# Tag for your registry
docker tag testpilot-jenkins:1.0.0 your-registry/testpilot-jenkins:1.0.0

# Push to registry
docker push your-registry/testpilot-jenkins:1.0.0
```

### 2. Deploy to Kubernetes
```bash
# Edit the deployment script with your values
./deploy-to-k8s.sh
```

### 3. Access Jenkins
```bash
# Get the Jenkins URL
kubectl get svc jenkins-testpilot -n jenkins

# Get admin password
kubectl get secret jenkins-admin -n jenkins -o jsonpath='{.data.password}' | base64 -d
```

### 4. Run TestPilot Pipeline
1. Access Jenkins UI
2. Navigate to "testpilot-pipeline" job
3. Click "Build with Parameters"
4. Set:
   - TARGET_NAMESPACE: Your Kubernetes namespace
   - EXCEL_FILE_PATH: Path to your test Excel file
   - ENABLE_AUDIT: true (for audit validation)
5. Click "Build"

## Configuration

### Environment Variables
- `JENKINS_ADMIN_USER`: Admin username (default: admin)
- `JENKINS_ADMIN_PASSWORD`: Admin password (default: auto-generated)
- `TESTPILOT_NAMESPACE`: Target namespace for tests

### Customizing resources_map.json
Edit `/opt/testpilot/config/resources_map.json` in the pod:
```json
{
    "service_endpoints": {
        "your_service": "http://your-service:port"
    },
    "namespace": "your-namespace"
}
```

## Troubleshooting
- Check pod logs: `kubectl logs -f <jenkins-pod> -n jenkins`
- Verify TestPilot: `kubectl exec <jenkins-pod> -n jenkins -- testpilot --version`
- View audit reports in Jenkins artifacts after pipeline execution
EOF

# Create deployment script
cat > "$DEPLOY_DIR/deploy-to-k8s.sh" << 'EOF'
#!/bin/bash
# Deploy TestPilot Jenkins to Kubernetes

NAMESPACE="jenkins"
RELEASE_NAME="testpilot-jenkins"
IMAGE_NAME="testpilot-jenkins:1.0.0"

# Create namespace
kubectl create namespace $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -

# Create Jenkins deployment
cat << YAML | kubectl apply -f -
apiVersion: v1
kind: Service
metadata:
  name: jenkins-testpilot
  namespace: $NAMESPACE
spec:
  type: LoadBalancer
  ports:
  - port: 8080
    targetPort: 8080
    name: http
  - port: 50000
    targetPort: 50000
    name: agent
  selector:
    app: jenkins-testpilot
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: jenkins-testpilot
  namespace: $NAMESPACE
spec:
  replicas: 1
  selector:
    matchLabels:
      app: jenkins-testpilot
  template:
    metadata:
      labels:
        app: jenkins-testpilot
    spec:
      serviceAccountName: jenkins
      containers:
      - name: jenkins
        image: $IMAGE_NAME
        imagePullPolicy: IfNotPresent
        ports:
        - containerPort: 8080
          name: http
        - containerPort: 50000
          name: agent
        env:
        - name: JAVA_OPTS
          value: "-Djenkins.install.runSetupWizard=false"
        - name: JENKINS_ADMIN_USER
          value: "admin"
        - name: JENKINS_ADMIN_PASSWORD
          valueFrom:
            secretKeyRef:
              name: jenkins-admin
              key: password
        volumeMounts:
        - name: jenkins-home
          mountPath: /var/jenkins_home
      volumes:
      - name: jenkins-home
        persistentVolumeClaim:
          claimName: jenkins-home
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: jenkins-home
  namespace: $NAMESPACE
spec:
  accessModes:
  - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: jenkins
  namespace: $NAMESPACE
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: jenkins
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: cluster-admin
subjects:
- kind: ServiceAccount
  name: jenkins
  namespace: $NAMESPACE
---
apiVersion: v1
kind: Secret
metadata:
  name: jenkins-admin
  namespace: $NAMESPACE
type: Opaque
data:
  password: $(openssl rand -base64 32 | base64)
YAML

echo "Deployment complete!"
echo "Jenkins URL: http://$(kubectl get svc jenkins-testpilot -n $NAMESPACE -o jsonpath='{.status.loadBalancer.ingress[0].ip}'):8080"
echo "Admin password: $(kubectl get secret jenkins-admin -n $NAMESPACE -o jsonpath='{.data.password}' | base64 -d)"
EOF

chmod +x "$DEPLOY_DIR/deploy-to-k8s.sh"

# Create sample Excel directory
mkdir -p "$DEPLOY_DIR/sample-excel"
cat > "$DEPLOY_DIR/sample-excel/sample-audit-test.xlsx.readme" << 'EOF'
Place your TestPilot Excel test files in this directory.

Expected format:
- Sheet columns: Test_Name, Command, Pattern_Match, Expected_Status, etc.
- Commands should be curl commands for pod mode execution
- Use placeholders like {{service_name}} that will be resolved from resources_map.json
EOF

# Create final archive
log_step "Creating final deployment archive..."
cd "$OUTPUT_DIR"
tar -czf "testpilot-jenkins-deploy-${IMAGE_TAG}.tar.gz" "testpilot-jenkins-deploy"
cd -

# Cleanup temporary files
rm -rf "$TEMP_DIR"

# Summary
log_info "✅ Build completed successfully!"
log_info "📦 Deployment package: ${OUTPUT_DIR}/testpilot-jenkins-deploy-${IMAGE_TAG}.tar.gz"
log_info "📋 Contents:"
log_info "   - Jenkins Docker image with TestPilot"
log_info "   - Pre-configured Jenkinsfile"
log_info "   - Kubernetes deployment scripts"
log_info "   - Documentation"
log_info ""
log_info "🚀 Next steps:"
log_info "   1. Extract: tar -xzf testpilot-jenkins-deploy-${IMAGE_TAG}.tar.gz"
log_info "   2. Follow README.md in the extracted directory"
