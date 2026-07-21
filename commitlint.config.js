export default {
	extends: ["@commitlint/config-conventional"],
	rules: {
		"type-enum": [2, "always", ["feat", "fix", "docs", "refactor", "chore"]],
		"scope-empty": [2, "never"],
		"scope-enum": [2, "always", ["harvey", "mcp", "prime", "csp", "amint", "ui"]],
	},
};
