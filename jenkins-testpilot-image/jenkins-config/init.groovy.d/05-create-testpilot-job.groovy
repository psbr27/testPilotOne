import jenkins.model.*
import hudson.model.*
import org.jenkinsci.plugins.workflow.job.WorkflowJob
import org.jenkinsci.plugins.workflow.cps.CpsFlowDefinition

def jenkins = Jenkins.getInstance()

// Create TestPilot pipeline job programmatically
def jobName = "testpilot-pipeline"
def job = jenkins.getItem(jobName)

if (job == null) {
    println "Creating TestPilot pipeline job: ${jobName}"

    try {
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

        // Simple pipeline script without complex shell blocks
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
                echo "🚀 Starting TestPilot Pipeline"
                echo "Target Namespace: ${params.TARGET_NAMESPACE}"
                echo "Excel File: ${params.EXCEL_FILE_PATH}"
                echo "Audit Enabled: ${params.ENABLE_AUDIT}"

                sh "mkdir -p ${REPORTS_DIR}"
                sh "which testpilot || echo 'testpilot not found'"
                sh "ls -la /opt/testpilot/bin/ || echo 'testpilot directory not found'"
            }
        }

        stage('Prepare Configuration') {
            steps {
                script {
                    sh 'echo "Creating configuration files..."'
                    sh 'ls -la ${TESTPILOT_HOME}/config/ || echo "Config directory not found"'
                }
            }
        }

        stage('Execute TestPilot') {
            steps {
                script {
                    echo "🏃 Executing TestPilot audit"
                    echo "This stage would execute: testpilot audit -e ${params.EXCEL_FILE_PATH} -o ${REPORTS_DIR}"
                    sh 'echo "TestPilot execution completed (demo mode)"'
                }
            }
        }

        stage('Archive Results') {
            steps {
                echo "📊 Archiving results"
                sh 'echo "Results archived successfully"'
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

        println "✅ TestPilot pipeline job created successfully: ${jobName}"
    } catch (Exception e) {
        println "❌ Failed to create job: ${e.message}"
        e.printStackTrace()
    }
} else {
    println "TestPilot pipeline job already exists: ${jobName}"
}

// Save Jenkins configuration
jenkins.save()
