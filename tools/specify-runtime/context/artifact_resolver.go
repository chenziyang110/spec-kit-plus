package context

// ArtifactResolver preserves explicit candidates, not arbitrary repository scans.
type ArtifactResolver struct{}

type ArtifactInput struct {
	Path, Reason, Digest string
}

func (ArtifactResolver) Resolve(inputs []ArtifactInput) []Artifact {
	result := make([]Artifact, 0, len(inputs))
	for _, item := range inputs {
		result = append(result, Artifact{Path: item.Path, Reason: item.Reason, Digest: item.Digest})
	}
	return result
}
