package main

import (
	"fmt"
	"regexp"
	"strings"
)

func allChecks() []check {
	return []check{
		{name: "scout-summary", tiers: []string{"light", "standard", "deep"}, severity: statusFail, run: checkScoutSummary},
		{name: "capability-triage", tiers: []string{"light", "standard", "deep"}, severity: statusFail, run: checkCapabilityTriage},
		{name: "execution-mode", tiers: []string{"light", "standard", "deep"}, severity: statusFail, run: checkExecutionMode},
		{name: "change-propagation", tiers: []string{"standard", "deep"}, severity: statusFail, run: checkChangePropagation},
		{name: "non-functional", tiers: []string{"standard", "deep"}, severity: statusWarn, run: checkNonFunctional},
		{name: "error-contract", tiers: []string{"standard", "deep"}, severity: statusWarn, run: checkErrorContract},
		{name: "config-effective-when", tiers: []string{"standard", "deep"}, severity: statusWarn, run: checkConfigEffectiveWhen},
		{name: "test-strategy", tiers: []string{"standard", "deep"}, severity: statusWarn, run: checkTestStrategy},
	}
}

// ---- check 1: scout-summary ----
// context.md must cover at least 3 of 6 scout topics.

var scoutTopicGroups = [][]string{
	// ownership / module attribution
	{"owning module", "owned by", "module ownership", "归属", "所属模块", "所属"},
	// reusable assets
	{"reusable", "reuse", "existing component", "existing service", "复用", "可复用"},
	// change-propagation hotspots
	{"change-propagation", "change propagation", "consumer surface", "affected module", "传播", "冲击", "受影响"},
	// integration boundaries
	{"integration boundary", "integration point", "interface boundary", "集成边界", "集成点", "边界"},
	// verification entry points
	{"verification entry", "test entry", "验证入口", "测试入口", "回归"},
	// known unknowns
	{"known unknown", "stale evidence", "gap", "隐忧", "未知", "风险"},
}

func checkScoutSummary(a artifactSet) checkResult {
	if a.context == "" {
		return fileMissing("context.md")
	}

	covered := countKeywordGroups(a.context, scoutTopicGroups)

	if covered >= 4 {
		return checkResult{status: statusPass}
	}
	if covered >= 3 {
		return checkResult{
			status:  statusPass,
			message: fmt.Sprintf("covers %d/6 scout topics (minimum 3)", covered),
		}
	}
	return checkResult{
		status:  statusFail,
		message: fmt.Sprintf("only %d/6 scout topics covered in context.md (need >= 3): ownership, reusable, change-propagation, integration, verification, known-unknowns", covered),
	}
}

// ---- check 2: capability-triage ----
// Each capability in spec.md must have a state label: confirmed/已证明, inferred/可推断, or unresolved/未验证.

var capabilityStateLabels = []string{
	"confirmed", "已证明",
	"inferred", "可推断",
	"unresolved", "未验证",
}

func checkCapabilityTriage(a artifactSet) checkResult {
	if a.spec == "" {
		return fileMissing("spec.md")
	}

	// find capability-definition sections (exclude test-strategy / configuration sections)
	excludeInHeading := []string{"test", "测试", "config", "配置"}
	var capSections []section
	for _, s := range findSectionsWithHeadings(a.spec, "capability") {
		if hasKeyword(s.heading, excludeInHeading) {
			continue
		}
		capSections = append(capSections, s)
	}
	for _, s := range findSectionsWithHeadings(a.spec, "能力") {
		if hasKeyword(s.heading, excludeInHeading) {
			continue
		}
		capSections = append(capSections, s)
	}

	if len(capSections) == 0 {
		return checkResult{
			status:  statusWarn,
			message: "no capability sections found; cannot verify triage labels",
		}
	}

	// extract capability entries: both table rows and list items (deduplicate)
	seen := map[string]bool{}
	var capabilities []string
	capListRe := regexp.MustCompile(`(?mi)^[\s]*[-*]\s*\*?\*?(CAP|Cap|cap|\d+\.)`)
	capTablePrefixRe := regexp.MustCompile(`(?mi)^\s*\|\s*(CAP|Cap|cap|\d+)`)

	for _, sec := range capSections {
		lines := strings.Split(sec.body, "\n")
		for _, line := range lines {
			trimmed := strings.TrimSpace(line)
			if seen[trimmed] {
				continue
			}
			if capListRe.MatchString(line) || capTablePrefixRe.MatchString(line) {
				seen[trimmed] = true
				capabilities = append(capabilities, line)
			}
		}
	}

	if len(capabilities) == 0 {
		return checkResult{
			status:  statusWarn,
			message: "no capability list detected; cannot verify triage labels",
		}
	}

	// filter out table header rows (contain header words but no state label)
	headerWords := []string{"purpose", "description", "capability", "能力", "描述", "purpose"}
	var filtered []string
	for _, cap := range capabilities {
		trimmed := strings.TrimSpace(cap)
		if strings.HasPrefix(trimmed, "|") && hasKeyword(cap, headerWords) && !hasKeyword(cap, capabilityStateLabels) {
			continue
		}
		filtered = append(filtered, cap)
	}

	if len(filtered) == 0 {
		return checkResult{
			status:  statusWarn,
			message: "no capability data rows detected (only headers found)",
		}
	}

	labeled := 0
	for _, cap := range filtered {
		if hasKeyword(cap, capabilityStateLabels) {
			labeled++
		}
	}

	ratio := float64(labeled) / float64(len(filtered))
	if ratio >= 0.8 {
		return checkResult{
			status:  statusPass,
			message: fmt.Sprintf("%d/%d capabilities labeled", labeled, len(filtered)),
		}
	}
	return checkResult{
		status:  statusFail,
		message: fmt.Sprintf("%d/%d capabilities have state labels (need >= 80%%): confirmed/已证明, inferred/可推断, unresolved/未验证", labeled, len(filtered)),
	}
}

// ---- check 3: execution-mode ----
// workflow-state.md or alignment.md must record execution_model.

func checkExecutionMode(a artifactSet) checkResult {
	combined := a.workflowState + "\n" + a.alignment
	if combined == "\n" {
		return checkResult{
			status:  statusFail,
			message: "workflow-state.md and alignment.md both missing — cannot verify execution model",
		}
	}

	execRe := regexp.MustCompile(`(?i)execution[ _-]m(?:ode|odel)\s*[:\-=]\s*(\S+)`)
	match := execRe.FindStringSubmatch(combined)
	if match != nil {
		mode := match[1]
		return checkResult{
			status:  statusPass,
			message: fmt.Sprintf("execution_model: %s", strings.TrimRight(mode, ",;")),
		}
	}
	return checkResult{
		status:  statusFail,
		message: "execution_model not recorded in workflow-state.md or alignment.md",
	}
}

// ---- check 4: change-propagation ----
// context.md must have a change-propagation matrix (table).

var changePropHeadings = []string{
	"change-propagation", "change propagation", "impact", "变更传播", "冲击", "影响面", "影响矩阵",
}

func checkChangePropagation(a artifactSet) checkResult {
	if a.context == "" {
		return fileMissing("context.md")
	}

	// find relevant sections
	var sections []string
	for _, h := range changePropHeadings {
		sections = append(sections, findSections(a.context, h)...)
	}

	if len(sections) == 0 {
		return checkResult{
			status:  statusFail,
			message: "no change-propagation / impact section found in context.md",
		}
	}

	// check for a table within those sections
	for _, sec := range sections {
		rows := countTableDataRows(sec)
		if rows >= 1 {
			return checkResult{
				status:  statusPass,
				message: fmt.Sprintf("change-propagation matrix found (%d data rows)", rows),
			}
		}
	}

	return checkResult{
		status:  statusFail,
		message: "change-propagation section found but no data table present",
	}
}

// ---- check 5: non-functional ----
// spec.md should cover NFR dimensions: performance, security, reliability, observability.

var nfrGroups = [][]string{
	{"performance", "latency", "throughput", "startup", "性能", "延迟", "吞吐", "启动时间"},
	{"security", "auth", "permission", "injection", "安全", "权限", "认证"},
	{"reliability", "availability", "fault", "recovery", "可靠性", "可用性", "容错"},
	{"observability", "logging", "metrics", "tracing", "monitoring", "可观测", "日志", "指标", "监控"},
}

func checkNonFunctional(a artifactSet) checkResult {
	if a.spec == "" {
		return fileMissing("spec.md")
	}

	covered := 0
	missing := []string{}
	for _, g := range nfrGroups {
		if hasKeyword(a.spec, g) {
			covered++
		} else {
			missing = append(missing, g[0])
		}
	}

	if covered >= 3 {
		return checkResult{status: statusPass}
	}
	if covered >= 2 {
		return checkResult{
			status:  statusWarn,
			message: fmt.Sprintf("only %d/4 NFR dimensions covered; consider adding: %s", covered, strings.Join(missing, ", ")),
		}
	}
	return checkResult{
		status:  statusFail,
		message: fmt.Sprintf("only %d/4 NFR dimensions covered (need >= 2): performance, security, reliability, observability", covered),
	}
}

// ---- check 6: error-contract ----
// Error/failure paths should describe user-visible behavior.

var errorKeywords = []string{
	"error", "failure", "exception", "timeout", "错误", "失败", "异常", "超时", "断线", "断开",
}

var userVisibleKeywords = []string{
	"user visible", "user-visible", "display", "show", "notification", "toast",
	"用户可见", "显示", "通知", "横幅", "提示", "reconnecting", "重连",
}

func checkErrorContract(a artifactSet) checkResult {
	if a.spec == "" {
		return fileMissing("spec.md")
	}

	// find sections about errors/failures
	var errorSections []string
	for _, kw := range []string{"error", "failure", "exception", "edge case", "错误", "失败", "异常", "边界"} {
		errorSections = append(errorSections, findSections(a.spec, kw)...)
	}

	if len(errorSections) == 0 {
		// no explicit error sections; try to find error mentions in the body
		if !hasKeyword(a.spec, errorKeywords) {
			return checkResult{
				status:  statusWarn,
				message: "no error/failure paths detected in spec",
			}
		}
		errorSections = []string{a.spec}
	}

	// for each error section, check if user-visible behavior is described
	described := 0
	total := 0
	for _, sec := range errorSections {
		if hasKeyword(sec, errorKeywords) {
			total++
			if hasKeyword(sec, userVisibleKeywords) {
				described++
			}
		}
	}

	if total == 0 {
		return checkResult{status: statusWarn, message: "no error paths detected"}
	}
	if described >= total || total <= 2 {
		return checkResult{status: statusPass}
	}

	return checkResult{
		status:  statusWarn,
		message: fmt.Sprintf("%d/%d error paths mention user-visible behavior; consider adding 'user visible' / '用户可见' descriptions", described, total),
	}
}

// ---- check 7: config-effective-when ----
// Config items should declare when changes take effect.

var configKeywords = []string{
	"config", "configuration", "setting", "option", "配置", "设置",
}

var effectiveWhenKeywords = []string{
	"effective when", "effective immediately", "生效时机", "即时生效", "下次", "next session",
	"after restart", "动态", "runtime",
}

func checkConfigEffectiveWhen(a artifactSet) checkResult {
	combined := a.spec + "\n" + a.context
	if strings.TrimSpace(combined) == "" {
		return checkResult{status: statusWarn, message: "no spec or context to check config declarations"}
	}

	if !hasKeyword(combined, configKeywords) {
		return checkResult{status: statusWarn, message: "no configuration items detected in spec/context"}
	}

	// check the full combined content for effective-when language (not just section bodies)
	if hasKeyword(combined, effectiveWhenKeywords) {
		return checkResult{status: statusPass}
	}

	return checkResult{
		status:  statusWarn,
		message: "config items found but no effective-when / 生效时机 declarations",
	}
}

// ---- check 8: test-strategy ----
// Capabilities should have test strategy notes.

var testStrategyKeywords = []string{
	"test strategy", "test note", "测试策略", "测试注记", "platform test",
	"integration test", "unit test", "e2e test", "平台测试",
}

func checkTestStrategy(a artifactSet) checkResult {
	if a.spec == "" {
		return fileMissing("spec.md")
	}

	// find capability sections
	capSections := findSections(a.spec, "capability")
	capSections = append(capSections, findSections(a.spec, "能力")...)

	if len(capSections) == 0 {
		return checkResult{
			status:  statusWarn,
			message: "no capability sections found; cannot verify test strategy notes",
		}
	}

	// check if any capability section mentions test strategy
	mentioned := 0
	for _, sec := range capSections {
		if hasKeyword(sec, testStrategyKeywords) {
			mentioned++
		}
	}

	if mentioned > 0 {
		return checkResult{
			status:  statusPass,
			message: fmt.Sprintf("test strategy mentioned in %d/%d capability sections", mentioned, len(capSections)),
		}
	}

	// also check globally in spec for test strategy
	if hasKeyword(a.spec, testStrategyKeywords) {
		return checkResult{status: statusPass, message: "test strategy mentioned in spec"}
	}

	return checkResult{
		status:  statusWarn,
		message: "capabilities defined but no test strategy notes found per capability",
	}
}
