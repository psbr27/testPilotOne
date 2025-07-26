import jenkins.model.*
import org.csanchez.jenkins.plugins.kubernetes.*
import org.csanchez.jenkins.plugins.kubernetes.volumes.*

def jenkins = Jenkins.getInstance()

// Configure Kubernetes plugin
def kubernetesCloud = new KubernetesCloud("kubernetes")

// Use in-cluster configuration
kubernetesCloud.setSkipTlsVerify(true)
kubernetesCloud.setNamespace("default")
kubernetesCloud.setJenkinsUrl("")
kubernetesCloud.setJenkinsTunnel("")
kubernetesCloud.setContainerCap(10)
kubernetesCloud.setRetentionTimeout(5)
kubernetesCloud.setConnectTimeout(5)
kubernetesCloud.setReadTimeout(15)
kubernetesCloud.setMaxRequestsPerHost(32)

// Create pod template for TestPilot execution
def podTemplate = new PodTemplate()
podTemplate.setName("testpilot-executor")
podTemplate.setLabel("testpilot")
podTemplate.setNamespace("default")
podTemplate.setNodeUsageMode(PodTemplate.NodeUsageMode.EXCLUSIVE)

// Container template
def containerTemplate = new ContainerTemplate("testpilot", "jenkins/inbound-agent:latest")
containerTemplate.setTtyEnabled(true)
containerTemplate.setPrivileged(false)
containerTemplate.setAlwaysPullImage(false)
containerTemplate.setWorkingDir("/home/jenkins/agent")
containerTemplate.setCommand("sleep")
containerTemplate.setArgs("99999999")

// Add testPilot volume mount
def volumes = []
volumes.add(new EmptyDirVolume("/opt/testpilot-workspace", false))

podTemplate.setVolumes(volumes)
podTemplate.setContainers([containerTemplate])

// Add pod template to cloud
kubernetesCloud.addTemplate(podTemplate)

// Add cloud to Jenkins
jenkins.clouds.removeAll(KubernetesCloud.class)
jenkins.clouds.add(kubernetesCloud)

// Save configuration
jenkins.save()

println "Kubernetes cloud configuration completed"
