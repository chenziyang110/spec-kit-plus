package context

// ArtifactResolver resolves explicitly supplied artifact candidates.
// It does not scan repositories or infer ownership.
type ArtifactResolver struct{}

type ArtifactInput struct {
	Path   string
	Reason string
}

func (ArtifactResolver) Resolve(inputs []ArtifactInput) []Artifact {
	result := make([]Artifact, 0, len(inputs))
	for _, item := range inputs {
		result = append(result, Artifact{
			Path:   item.Path,
			Reason: item.Reason,
		})
	}
	return result
}
