package changes

import "strings"

// effectiveChangeStatus projects a supported porcelain status onto the live
// worktree operation. In MD and AD the index changed, but the worktree file was
// subsequently deleted: refreshing/adopting that absent file would be wrong.
// Keep the original XY code in Change.GitStatus for provenance. Rename/conflict
// handling remains with the existing intake and typed-update contracts.
func effectiveChangeStatus(status string) string {
	status = strings.TrimSpace(status)
	if status == "MD" || status == "AD" {
		return "D"
	}
	return status
}
