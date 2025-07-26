# TestPilot Jenkins Pod Image - Customer Deployment Guide

## Overview

This guide provides step-by-step instructions for deploying the TestPilot Jenkins pod image in your Kubernetes environment. The image contains a pre-configured Jenkins instance with TestPilot binary, all required plugins, and a ready-to-use pipeline for executing TestPilot audits in pod mode.

## Prerequisites

- Kubernetes cluster (v1.19+)
- `kubectl` CLI configured with cluster access
- Docker registry accessible from your Kubernetes cluster
- Basic understanding of Kubernetes and Jenkins concepts

## Package Contents

The deployment package (`testpilot-jenkins-deploy-*.tar.gz`) contains:

1. **Docker Image** (`testpilot-jenkins-*.tar.gz`): Jenkins with TestPilot pre-installed
2. **Jenkinsfile**: Pre-configured pipeline for TestPilot execution
3. **Deployment Scripts**: Kubernetes manifests and helper scripts
4. **Documentation**: This guide and additional resources

## Deployment Steps

### Step 1: Extract the Package

```bash
tar -xzf testpilot-jenkins-deploy-1.0.0.tar.gz
cd testpilot-jenkins-deploy
```

### Step 2: Load and Push Docker Image

#### 2.1 Load the Docker image locally:

```bash
gunzip testpilot-jenkins-1.0.0.tar.gz
docker load -i testpilot-jenkins-1.0.0.tar
```

#### 2.2 Tag the image for your registry:

```bash
# Replace 'your-registry.com' with your actual registry URL
docker tag testpilot-jenkins:1.0.0 your-registry.com/testpilot-jenkins:1.0.0
```

#### 2.3 Push to your registry:

```bash
docker push your-registry.com/testpilot-jenkins:1.0.0
```

### Step 3: Update Deployment Configuration

Edit the `deploy-to-k8s.sh` script to use your registry:

```bash
# Change this line:
IMAGE_NAME="testpilot-jenkins:1.0.0"

# To:
IMAGE_NAME="your-registry.com/testpilot-jenkins:1.0.0"
```

### Step 4: Deploy to Kubernetes

Execute the deployment script:

```bash
./deploy-to-k8s.sh
```

This script will:
- Create a `jenkins` namespace
- Deploy Jenkins with persistent storage
- Configure RBAC permissions
- Create a LoadBalancer service
- Generate admin credentials

### Step 5: Access Jenkins

#### 5.1 Get the Jenkins URL:

```bash
# For LoadBalancer service:
kubectl get svc jenkins-testpilot -n jenkins

# For NodePort (if LoadBalancer not available):
kubectl patch svc jenkins-testpilot -n jenkins -p '{"spec": {"type": "NodePort"}}'
kubectl get svc jenkins-testpilot -n jenkins
```

#### 5.2 Retrieve admin credentials:

```bash
# Username is 'admin'
# Get password:
kubectl get secret jenkins-admin -n jenkins -o jsonpath='{.data.password}' | base64 -d
```

#### 5.3 Access Jenkins UI:

Open your browser and navigate to `http://<JENKINS_URL>:8080`

## Using TestPilot in Jenkins

### Running the Pre-configured Pipeline

1. **Login to Jenkins** using the admin credentials

2. **Navigate to the TestPilot Pipeline**:
   - Click on "testpilot-pipeline" from the Jenkins dashboard

3. **Configure Build Parameters**:
   - Click "Build with Parameters"
   - Set the following parameters:
     - **TARGET_NAMESPACE**: The Kubernetes namespace to test
     - **EXCEL_FILE_PATH**: Path to your TestPilot Excel file
     - **SHEET_NAME**: Specific sheet to execute (optional)
     - **NF_NAME**: Network Function name
     - **NF_TYPE**: Network Function type (e.g., AMF, SMF)
     - **NF_VERSION**: Version information
     - **ENABLE_AUDIT**: Enable comprehensive audit validation

4. **Upload Test Files**:
   - Place your Excel test files in the Jenkins workspace
   - Or configure a Git repository with your test files

5. **Execute the Pipeline**:
   - Click "Build"
   - Monitor the execution in real-time

### Configuring TestPilot for Your Environment

#### 1. Update resources_map.json

The `resources_map.json` file maps placeholders in your Excel commands to actual service endpoints:

```bash
# Connect to the Jenkins pod
kubectl exec -it <jenkins-pod-name> -n jenkins -- bash

# Edit the resources map
cat > /opt/testpilot/config/resources_map.json << 'EOF'
{
    "service_endpoints": {
        "user_service": "http://user-service.your-namespace.svc.cluster.local:8080",
        "auth_service": "http://auth-service.your-namespace.svc.cluster.local:8081",
        "api_gateway": "http://gateway.your-namespace.svc.cluster.local:8082"
    },
    "kubernetes_services": {
        "namespace": "your-namespace",
        "cluster_name": "production"
    },
    "common_placeholders": {
        "base_url": "http://api.your-domain.com",
        "api_version": "v1",
        "tenant_id": "your-tenant"
    }
}
EOF
```

#### 2. Excel File Format for Pod Mode

Your Excel test files should use curl commands for pod mode execution:

| Test_Name | Command | Pattern_Match | Expected_Status |
|-----------|---------|---------------|-----------------|
| test_user_list | curl -X GET {{user_service}}/api/v1/users | "users".*"id" | 200 |
| test_auth | curl -X POST {{auth_service}}/login -d '{"user":"test"}' | "token" | 200 |

### Creating Custom Pipelines

You can create additional pipelines by copying and modifying the provided Jenkinsfile:

```groovy
// Example: Custom pipeline for specific NF testing
pipeline {
    agent { kubernetes { label 'testpilot' } }

    stages {
        stage('Execute Custom Tests') {
            steps {
                container('testpilot') {
                    sh '''
                        # Set namespace from Jenkins parameter
                        export TESTPILOT_NAMESPACE="${TARGET_NAMESPACE}"

                        # Run testpilot with custom options
                        testpilot audit \
                            -e custom_tests.xlsx \
                            -s "Production Tests" \
                            -o reports/
                    '''
                }
            }
        }
    }
}
```

## Advanced Configuration

### Environment Variables

The following environment variables can be configured:

- `TESTPILOT_NAMESPACE`: Target Kubernetes namespace
- `POD_MODE`: Set to "true" for pod mode execution
- `NF_NAME`, `NF_TYPE`, `NF_VERSION`: Network Function metadata

### Persistent Storage

Jenkins data is stored in a PersistentVolumeClaim. To customize storage:

```yaml
# Edit the PVC in deploy-to-k8s.sh
spec:
  storageClassName: your-storage-class
  resources:
    requests:
      storage: 20Gi  # Increase as needed
```

### Security Considerations

1. **Change Default Credentials**: Update the admin password after first login
2. **Configure RBAC**: The default deployment uses cluster-admin; restrict as needed
3. **Network Policies**: Implement network policies to restrict pod communication
4. **Image Scanning**: Scan the Docker image before deployment

## Troubleshooting

### Common Issues

1. **Jenkins pod not starting**:
   ```bash
   kubectl logs -f deployment/jenkins-testpilot -n jenkins
   kubectl describe pod -l app=jenkins-testpilot -n jenkins
   ```

2. **TestPilot not found**:
   ```bash
   kubectl exec -it <pod-name> -n jenkins -- which testpilot
   kubectl exec -it <pod-name> -n jenkins -- testpilot --version
   ```

3. **Pipeline failures**:
   - Check Jenkins console output
   - Verify Excel file format
   - Ensure resources_map.json is properly configured

### Debug Commands

```bash
# Check pod status
kubectl get pods -n jenkins

# View pod logs
kubectl logs -f <pod-name> -n jenkins

# Execute commands in pod
kubectl exec -it <pod-name> -n jenkins -- bash

# Check TestPilot configuration
kubectl exec <pod-name> -n jenkins -- cat /opt/testpilot/config/hosts.json
kubectl exec <pod-name> -n jenkins -- cat /opt/testpilot/config/resources_map.json
```

## Maintenance

### Updating TestPilot

To update the TestPilot binary:

1. Build a new Docker image with updated TestPilot
2. Push to your registry
3. Update the deployment:
   ```bash
   kubectl set image deployment/jenkins-testpilot \
     jenkins=your-registry.com/testpilot-jenkins:new-version \
     -n jenkins
   ```

### Backup and Restore

Backup Jenkins configuration:

```bash
# Backup
kubectl exec <pod-name> -n jenkins -- tar -czf /tmp/jenkins-backup.tar.gz /var/jenkins_home
kubectl cp jenkins/<pod-name>:/tmp/jenkins-backup.tar.gz ./jenkins-backup.tar.gz

# Restore
kubectl cp ./jenkins-backup.tar.gz jenkins/<pod-name>:/tmp/
kubectl exec <pod-name> -n jenkins -- tar -xzf /tmp/jenkins-backup.tar.gz -C /
```

## Support

For issues or questions:
1. Check the TestPilot logs in pod mode
2. Review the audit reports generated
3. Ensure all placeholders in Excel are defined in resources_map.json
4. Verify network connectivity between Jenkins pod and target services

## Appendix

### Sample Excel Test File

Create `sample-audit-tests.xlsx` with the following structure:

| Test_Name | Command | Pattern_Match | Expected_Status | Method |
|-----------|---------|---------------|-----------------|---------|
| health_check | curl {{api_gateway}}/health | "status".*"healthy" | 200 | GET |
| create_user | curl -X POST {{user_service}}/users -d '{"name":"test"}' | "id" | 201 | POST |
| list_users | curl {{user_service}}/users?limit=10 | "users".*array | 200 | GET |

### Sample resources_map.json

```json
{
    "service_endpoints": {
        "api_gateway": "http://gateway.default.svc.cluster.local:8080",
        "user_service": "http://users.default.svc.cluster.local:8081",
        "auth_service": "http://auth.default.svc.cluster.local:8082"
    },
    "environment": {
        "namespace": "${TESTPILOT_NAMESPACE}",
        "cluster": "production",
        "region": "us-east-1"
    },
    "common_headers": {
        "Content-Type": "application/json",
        "X-Request-ID": "${BUILD_NUMBER}"
    }
}
```
