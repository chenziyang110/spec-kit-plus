"""Artifact scaffold writer placeholder."""


class ArtifactScaffoldError(ValueError):
    """Raised when artifact scaffold generation fails."""


def scaffold_artifact(*args, **kwargs):
    raise ArtifactScaffoldError("artifact scaffold writer is not implemented")
