// Run this script in Jenkins Script Console to manually create the TestPilot job
// Go to Manage Jenkins > Script Console and paste this script

import jenkins.model.*
import hudson.model.*
import org.jenkinsci.plugins.workflow.job.WorkflowJob
import org.jenkinsci.plugins.workflow.cps.CpsFlowDefinition

def jenkins = Jenkins.getInstance()

// Create TestPilot pipeline job
def jobName = "testpilot-pipeline"
def job = jenkins.getItem(jobName)

if (job != null) {
    // Remove existing job
    job.delete()
    println "Removed existing job: ${jobName}"
}

println "Creating TestPilot pipeline job: ${jobName}"

job = jenkins.createProject(WorkflowJob.class, jobName)
job.setDescription("TestPilot audit execution pipeline for Kubernetes environments")

// Add parameters
def parameterDefinitions = [
    new hudson.model.StringParameterDefinition("TARGET_NAMESPACE", "default", "Target Kubernetes namespace for TestPilot audit"),
    new hudson.model.StringParameterDefinition("EXCEL_FILE_PATH", "tests/audit_tests.xlsx", "Path to the TestPilot Excel file (relative to workspace)"),
    new hudson.model.StringParameterDefinition("SHEET_NAME", "", "Excel sheet name to execute (leave empty for all sheets)"),
    new hudson.model.StringParameterDefinition("NF_NAME", "TestNF", "Network Function name"),
    new hudson.model.StringParameterDefinition("NF_TYPE", "AMF", "Network Function type (e.g., AMF, SMF, UPF)"),
    new hudson.model.StringParameterDefinition("NF_VERSION", "v23.4.x", "Network Function version"),
    new hudson.model.BooleanParameterDefinition("ENABLE_AUDIT", true, "Enable comprehensive audit validation")
]

def parametersProperty = new hudson.model.ParametersDefinitionProperty(parameterDefinitions)
job.addProperty(parametersProperty)

// Define the pipeline script
def pipelineScript = '''
pipeline {
    agent any

    environment {
        TESTPILOT_NAMESPACE = "${params.TARGET_NAMESPACE}"
        NF_NAME = "${params.NF_NAME}"
        NF_TYPE = "${params.NF_TYPE}"
        NF_VERSION = "${params.NF_VERSION}"
        TESTPILOT_HOME = "/opt/testpilot"
        REPORTS_DIR = "${WORKSPACE}/audit_reports"
    }

    stages {
        stage('Initialize') {
            steps {
                script {
                    echo "🚀 Initializing TestPilot Pipeline"
                    echo "Target Namespace: ${params.TARGET_NAMESPACE}"
                    echo "Excel File: ${params.EXCEL_FILE_PATH}"
                    echo "Audit Enabled: ${params.ENABLE_AUDIT}"

                    sh '''
                        echo "TestPilot Binary Location:"
                        which testpilot || echo "testpilot not in PATH"
                        ls -la /opt/testpilot/bin/ || echo "TestPilot bin directory not found"

                        echo "TestPilot Version:"
                        testpilot --version || echo "Failed to get version"
                    '''

                    sh "mkdir -p ${REPORTS_DIR}"
                }
            }
        }

        stage('Prepare Configuration') {
            steps {
                script {
                    sh '''
                        if [ ! -f "${TESTPILOT_HOME}/config/resources_map.json" ]; then
                            echo "Creating default resources_map.json..."
                            cat > ${TESTPILOT_HOME}/config/resources_map.json << 'EOF'
{
    "namespace": "${TESTPILOT_NAMESPACE}",
    "jenkins_build": "${BUILD_NUMBER}",
    "jenkins_job": "${JOB_NAME}",
    "environment": "jenkins-pod",
    "common_placeholders": {
        "base_url": "http://api.${TESTPILOT_NAMESPACE}.svc.cluster.local",
        "api_version": "v1"
    }
}
EOF
                        fi
                    '''

                    sh '''
                        echo "Current Configuration:"
                        echo "hosts.json:"
                        cat ${TESTPILOT_HOME}/config/hosts.json || echo "hosts.json not found"

                        echo "resources_map.json:"
                        cat ${TESTPILOT_HOME}/config/resources_map.json || echo "resources_map.json not found"
                    '''
                }
            }
        }

        stage('Test TestPilot') {
            steps {
                script {
                    echo "🧪 Testing TestPilot installation..."

                    sh '''
                        # Test basic testpilot functionality
                        echo "Testing testpilot help..."
                        testpilot --help || echo "TestPilot help failed"

                        echo "Testing testpilot version..."
                        testpilot --version || echo "TestPilot version failed"

                        echo "Checking config directory..."
                        ls -la ${TESTPILOT_HOME}/config/ || echo "Config directory not found"
                    '''
                }
            }
        }

        stage('Archive Artifacts') {
            steps {
                script {
                    archiveArtifacts artifacts: 'audit_reports/**/*',
                                   allowEmptyArchive: true,
                                   fingerprint: true
                }
            }
        }
    }

    post {
        always {
            echo "🧹 Pipeline execution completed"
        }
        success {
            echo "✅ TestPilot pipeline completed successfully!"
        }
        failure {
            echo "❌ TestPilot pipeline failed. Check the logs for details."
        }
    }
}
'''

job.setDefinition(new CpsFlowDefinition(pipelineScript, true))
job.save()

println "✅ TestPilot pipeline job created successfully!"
println "You can now find the job at: ${jenkins.getRootUrl()}job/${jobName}/"

return "Job created successfully"
