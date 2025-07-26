import jenkins.model.*
import hudson.security.*
import hudson.security.csrf.*

def instance = Jenkins.getInstance()

// Disable Jenkins CLI over remoting for security
instance.getDescriptor("jenkins.CLI").get().setEnabled(false)

// Enable CSRF protection
def csrf = new DefaultCrumbIssuer(true)
instance.setCrumbIssuer(csrf)

// Create admin user if environment variables are set
def adminUsername = System.getenv("JENKINS_ADMIN_USER") ?: "admin"
def adminPassword = System.getenv("JENKINS_ADMIN_PASSWORD") ?: "admin"

def hudsonRealm = new HudsonPrivateSecurityRealm(false)
hudsonRealm.createAccount(adminUsername, adminPassword)
instance.setSecurityRealm(hudsonRealm)

// Enable matrix-based security
def strategy = new GlobalMatrixAuthorizationStrategy()

// Grant admin permissions
strategy.add(Jenkins.ADMINISTER, adminUsername)
strategy.add(Jenkins.READ, "authenticated")
strategy.add(hudson.model.View.READ, "authenticated")
strategy.add(hudson.model.Item.READ, "authenticated")
strategy.add(hudson.model.Item.BUILD, "authenticated")

instance.setAuthorizationStrategy(strategy)

// Save configuration
instance.save()

println "Basic security configuration completed"
