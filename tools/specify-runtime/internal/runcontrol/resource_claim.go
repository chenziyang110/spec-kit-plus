package runcontrol

// ResourceType and ResourceClaimMode describe shared execution intent. They do
// not require a supervised process or a legacy resource_claims row.
type ResourceType string

const (
	ResourceFilesystem     ResourceType = "filesystem"
	ResourceTCPPort        ResourceType = "tcp-port"
	ResourceDatabase       ResourceType = "database"
	ResourceSchema         ResourceType = "schema"
	ResourceService        ResourceType = "service"
	ResourceComposeProject ResourceType = "compose-project"
	ResourceTemp           ResourceType = "temp"
	ResourceCache          ResourceType = "cache"
	ResourceExternalEffect ResourceType = "external-effect"
	ResourceCapability     ResourceType = "capability"
	ResourceFeature        ResourceType = "feature"
	ResourceAPI            ResourceType = "api"
	ResourceUISurface      ResourceType = "ui-surface"
	ResourceConfig         ResourceType = "config"
)

type ResourceClaimMode string

const (
	ResourceClaimShared    ResourceClaimMode = "shared"
	ResourceClaimExclusive ResourceClaimMode = "exclusive"
	ResourceShared         ResourceClaimMode = ResourceClaimShared
	ResourceExclusive      ResourceClaimMode = ResourceClaimExclusive
)
