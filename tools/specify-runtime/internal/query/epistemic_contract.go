package query

const epistemicContractVersion = 1

// EpistemicContract defines what an agent may infer from a project cognition
// navigation packet. Project cognition narrows live repository reads; it does
// not certify current behavior or completion claims.
type EpistemicContract struct {
	ContractVersion          int    `json:"contract_version"`
	GraphRole                string `json:"graph_role"`
	FactSourceOfTruth        string `json:"fact_source_of_truth"`
	LiveVerificationRequired bool   `json:"live_verification_required"`
	GraphOnlyClaimsAllowed   bool   `json:"graph_only_claims_allowed"`
	UnverifiedClaimAction    string `json:"unverified_claim_action"`
}

// NewEpistemicContract returns the machine-readable boundary shared by every
// project cognition navigation payload.
func NewEpistemicContract() EpistemicContract {
	return EpistemicContract{
		ContractVersion:          epistemicContractVersion,
		GraphRole:                "route_candidate_only",
		FactSourceOfTruth:        "live_repository",
		LiveVerificationRequired: true,
		GraphOnlyClaimsAllowed:   false,
		UnverifiedClaimAction:    "withhold",
	}
}
