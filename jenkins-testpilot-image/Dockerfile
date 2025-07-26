# TestPilot Jenkins Pod Image
# Based on Jenkins LTS with Kubernetes support
FROM jenkins/jenkins:lts-jdk17

# Switch to root to install dependencies
USER root

# Install required system packages
RUN apt-get update && apt-get install -y \
    curl \
    git \
    python3 \
    python3-pip \
    jq \
    zip \
    unzip \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install kubectl for Kubernetes interaction
RUN curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" && \
    install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl && \
    rm kubectl

# Create directories for testPilot
RUN mkdir -p /opt/testpilot/bin \
             /opt/testpilot/config \
             /opt/testpilot/_internal \
             /var/jenkins_home/workspace

# Copy testPilot binary and assets
COPY testpilot-assets/testPilot /opt/testpilot/bin/testPilot
COPY testpilot-assets/_internal /opt/testpilot/_internal/
COPY testpilot-assets/config /opt/testpilot/config/

# Ensure testPilot binary is executable
RUN chmod +x /opt/testpilot/bin/testPilot

# Create a pod-mode specific hosts.json template
RUN cat > /opt/testpilot/config/hosts.json.pod_template << 'EOF'
{
    "use_ssh": false,
    "pod_mode": true,
    "nf_name": "${NF_NAME}",
    "connect_to": "pod",
    "html_generator": {
        "use_nf_style": true
    },
    "system_under_test": {
        "nf_type": "${NF_TYPE}",
        "version": "${NF_VERSION}",
        "environment": "Kubernetes Pod",
        "deployment": "${DEPLOYMENT_NAME}",
        "description": "TestPilot execution in Jenkins pod mode"
    },
    "ssh_settings": {
        "auto_add_hosts": false
    },
    "hosts": []
}
EOF

# Switch back to jenkins user
USER jenkins

# Skip the initial setup wizard
ENV JAVA_OPTS="-Djenkins.install.runSetupWizard=false"

# Define Jenkins plugins to install
COPY jenkins-config/plugins.txt /usr/share/jenkins/ref/plugins.txt
RUN jenkins-plugin-cli --plugin-file /usr/share/jenkins/ref/plugins.txt

# Copy pre-configured jobs
COPY --chown=jenkins:jenkins jenkins-config/jobs /usr/share/jenkins/ref/jobs

# Copy Jenkins configuration scripts
COPY --chown=jenkins:jenkins jenkins-config/init.groovy.d /usr/share/jenkins/ref/init.groovy.d

# Set environment variables for testPilot
ENV TESTPILOT_HOME=/opt/testpilot
ENV PATH="${TESTPILOT_HOME}/bin:${PATH}"

# Add wrapper script for testPilot that handles pod mode configuration
USER root
RUN cat > /opt/testpilot/bin/testpilot-wrapper.sh << 'EOF'
#!/bin/bash
# TestPilot wrapper script for pod mode execution

# Check if we're in pod mode (Jenkins environment)
if [ -n "$JENKINS_HOME" ] && [ -n "$BUILD_NUMBER" ]; then
    echo "🏗️  Detected Jenkins pod environment"

    # Set pod mode environment
    export POD_MODE=true

    # Get namespace from Jenkins parameter or environment
    if [ -n "$TARGET_NAMESPACE" ]; then
        export TESTPILOT_NAMESPACE="$TARGET_NAMESPACE"
    elif [ -n "$NAMESPACE" ]; then
        export TESTPILOT_NAMESPACE="$NAMESPACE"
    else
        echo "⚠️  Warning: No namespace specified. Using 'default'"
        export TESTPILOT_NAMESPACE="default"
    fi

    # Update hosts.json from template
    if [ -f "/opt/testpilot/config/hosts.json.pod_template" ]; then
        envsubst < /opt/testpilot/config/hosts.json.pod_template > /opt/testpilot/config/hosts.json
    fi

    # Ensure resources_map.json exists
    if [ ! -f "/opt/testpilot/config/resources_map.json" ]; then
        echo "⚠️  Warning: resources_map.json not found. Creating default..."
        cat > /opt/testpilot/config/resources_map.json << 'RMAP'
{
    "namespace": "${TESTPILOT_NAMESPACE}",
    "jenkins_build": "${BUILD_NUMBER}",
    "jenkins_job": "${JOB_NAME}"
}
RMAP
    fi
fi

# Execute testPilot with all arguments
exec /opt/testpilot/bin/testPilot "$@"
EOF

RUN chmod +x /opt/testpilot/bin/testpilot-wrapper.sh && \
    ln -sf /opt/testpilot/bin/testpilot-wrapper.sh /usr/local/bin/testpilot

# Create workspace directory with proper permissions
RUN chown -R jenkins:jenkins /opt/testpilot /var/jenkins_home

USER jenkins

# Set working directory
WORKDIR /var/jenkins_home

# Expose Jenkins port
EXPOSE 8080 50000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=2m --retries=5 \
    CMD curl -f http://localhost:8080/login || exit 1
