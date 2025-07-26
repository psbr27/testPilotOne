#!/bin/bash
# Verification script to check if TestPilot pipeline is properly configured

echo "🔍 Verifying TestPilot Jenkins Setup..."

# Check if testpilot-pipeline job configuration exists
if [ -f "jenkins-config/jobs/testpilot-pipeline/config.xml" ]; then
    echo "✅ TestPilot pipeline job configuration found"

    # Check if the pipeline script is embedded
    if grep -q "CpsFlowDefinition" jenkins-config/jobs/testpilot-pipeline/config.xml; then
        echo "✅ Pipeline script is embedded (CpsFlowDefinition)"
    else
        echo "❌ Pipeline script is not embedded properly"
    fi

    # Check for required parameters
    required_params=("TARGET_NAMESPACE" "EXCEL_FILE_PATH" "ENABLE_AUDIT")
    for param in "${required_params[@]}"; do
        if grep -q "$param" jenkins-config/jobs/testpilot-pipeline/config.xml; then
            echo "✅ Parameter found: $param"
        else
            echo "❌ Parameter missing: $param"
        fi
    done

else
    echo "❌ TestPilot pipeline job configuration NOT found"
fi

# Check init scripts
echo -e "\n🔧 Checking initialization scripts..."
init_scripts=(
    "01-basic-security.groovy"
    "02-kubernetes-config.groovy"
    "03-global-tools.groovy"
    "04-cleanup-jobs.groovy"
)

for script in "${init_scripts[@]}"; do
    if [ -f "jenkins-config/init.groovy.d/$script" ]; then
        echo "✅ Init script found: $script"
    else
        echo "❌ Init script missing: $script"
    fi
done

# Check plugins
echo -e "\n📦 Checking essential plugins..."
essential_plugins=("workflow-aggregator" "kubernetes" "git" "credentials-binding")
for plugin in "${essential_plugins[@]}"; do
    if grep -q "$plugin" jenkins-config/plugins.txt; then
        echo "✅ Plugin configured: $plugin"
    else
        echo "❌ Plugin missing: $plugin"
    fi
done

# Check Dockerfile
echo -e "\n🐳 Checking Dockerfile..."
if [ -f "Dockerfile" ]; then
    echo "✅ Dockerfile found"

    if grep -q "COPY testpilot-assets/testPilot" Dockerfile; then
        echo "✅ TestPilot binary copy instruction found"
    else
        echo "❌ TestPilot binary copy instruction missing"
    fi

    if grep -q "testpilot-wrapper.sh" Dockerfile; then
        echo "✅ TestPilot wrapper script found"
    else
        echo "❌ TestPilot wrapper script missing"
    fi
else
    echo "❌ Dockerfile not found"
fi

echo -e "\n🏁 Verification complete!"
echo "If all items show ✅, the TestPilot Jenkins setup should work correctly."
