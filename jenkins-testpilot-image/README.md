# TestPilot Jenkins Pod Image

This directory contains all the components needed to build a self-contained Jenkins Docker image with TestPilot for customer distribution.

## Directory Structure

```
jenkins-testpilot-image/
├── Dockerfile                    # Main Docker image definition
├── Jenkinsfile                  # Pre-configured TestPilot pipeline
├── build-jenkins-image.sh       # Build script to create the deployment package
├── CUSTOMER_DEPLOYMENT_GUIDE.md # Comprehensive deployment documentation
├── jenkins-config/              # Jenkins configuration files
│   ├── plugins.txt             # Required Jenkins plugins list
│   ├── init.groovy.d/          # Jenkins initialization scripts
│   │   ├── 01-basic-security.groovy
│   │   ├── 02-kubernetes-config.groovy
│   │   ├── 03-global-tools.groovy
│   │   └── 04-create-test-job.groovy
│   └── jobs/                   # Pre-configured Jenkins jobs
│       └── testpilot-pipeline/
│           └── config.xml
└── testpilot-assets/           # TestPilot binary and config (created during build)
```

## Building the Image

### Prerequisites

1. TestPilot must be built first:
   ```bash
   cd ..
   bash build_with_spec.sh
   ```

2. Docker must be installed and running

### Build Process

Run the build script:
```bash
./build-jenkins-image.sh
```

This will:
1. Validate prerequisites
2. Copy TestPilot binary and assets
3. Build the Docker image
4. Export it as a tar file
5. Create a complete deployment package

### Output

The build process creates:
- `output/testpilot-jenkins-deploy-1.0.0.tar.gz` - Complete deployment package for customers

## Key Features

### Pod Mode Support
- TestPilot runs directly inside Jenkins pods
- No SSH connections required
- Simplified namespace configuration via Jenkins variables
- Direct curl command execution

### Pre-configured Jenkins
- All required plugins pre-installed
- Kubernetes cloud configuration
- Security settings configured
- TestPilot pipeline ready to use
- Pipeline script embedded in job configuration (no external Jenkinsfile needed)

### Namespace Configuration
The namespace for TestPilot execution is determined from (in priority order):
1. `TESTPILOT_NAMESPACE` environment variable
2. `TARGET_NAMESPACE` Jenkins parameter
3. `NAMESPACE` environment variable
4. `POD_NAMESPACE` environment variable
5. `namespace` in resources_map.json
6. Default: 'default'

### Resource Mapping
- Uses `resources_map.json` for placeholder resolution
- Supports service endpoints and common placeholders
- Dynamically resolves variables in curl commands

## Customer Deployment

Customers receive the deployment package containing:
1. Docker image (tar.gz)
2. Deployment scripts
3. Documentation
4. Sample configurations

See `CUSTOMER_DEPLOYMENT_GUIDE.md` for detailed deployment instructions.

## Pipeline Configuration

The TestPilot pipeline is pre-configured with:
- Embedded pipeline script (no external Jenkinsfile required)
- Parameterized execution for flexibility
- Automatic artifact archiving
- HTML report publishing

### Job Configuration
The pipeline job (`testpilot-pipeline`) includes:
- Target namespace parameter
- Excel file path parameter
- Sheet selection option
- Network Function metadata
- Audit enable/disable option

## Customization

### Adding Plugins
Edit `jenkins-config/plugins.txt` to add more Jenkins plugins.

### Modifying Pipeline
Edit the pipeline script in `jenkins-config/jobs/testpilot-pipeline/config.xml` to customize execution.

### Updating TestPilot
1. Rebuild TestPilot with latest changes
2. Run `build-jenkins-image.sh` again
3. Distribute new package to customers

## Security Notes

- Default admin credentials are configurable via environment variables
- RBAC is configured for Kubernetes access
- Secrets are generated during deployment
- No hardcoded credentials in the image

## Troubleshooting

If the pipeline shows "Jenkinsfile not found" error:
1. The job is configured with inline pipeline script
2. Ensure the Docker image was built with the latest job configuration
3. Check that the init.groovy.d scripts ran successfully during Jenkins startup
