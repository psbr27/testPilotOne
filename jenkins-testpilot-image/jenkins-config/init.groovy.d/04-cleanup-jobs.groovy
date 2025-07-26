import jenkins.model.*
import hudson.model.*

def jenkins = Jenkins.getInstance()

// Remove the simple test job if it exists
def testJobName = "test-pipeline-simple"
def testJob = jenkins.getItem(testJobName)
if (testJob != null) {
    testJob.delete()
    println "Removed test job: ${testJobName}"
}

// Verify testpilot-pipeline exists
def testpilotJobName = "testpilot-pipeline"
def testpilotJob = jenkins.getItem(testpilotJobName)
if (testpilotJob != null) {
    println "TestPilot pipeline job verified: ${testpilotJobName}"
    println "Job description: ${testpilotJob.getDescription()}"
} else {
    println "WARNING: TestPilot pipeline job not found: ${testpilotJobName}"
}

// Save Jenkins configuration
jenkins.save()
