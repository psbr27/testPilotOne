import jenkins.model.*
import hudson.tools.*

def instance = Jenkins.getInstance()

// Configure global tools location
def testpilotHome = "/opt/testpilot"

// Set environment variables
def globalNodeProperties = instance.getGlobalNodeProperties()
def envVarsNodePropertyList = globalNodeProperties.getAll(hudson.slaves.EnvironmentVariablesNodeProperty.class)

def envVars = null

if (envVarsNodePropertyList.size() == 0) {
    def envVarsNodeProperty = new hudson.slaves.EnvironmentVariablesNodeProperty()
    globalNodeProperties.add(envVarsNodeProperty)
    envVars = envVarsNodeProperty.getEnvVars()
} else {
    envVars = envVarsNodePropertyList.get(0).getEnvVars()
}

// Add TestPilot environment variables
envVars.put("TESTPILOT_HOME", testpilotHome)
envVars.put("PATH+TESTPILOT", "${testpilotHome}/bin")

// Save configuration
instance.save()

println "Global tools configuration completed"
