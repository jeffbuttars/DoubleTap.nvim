local defaults = {
	threshold = 0.4, -- In seconds
	jump_out = {
		{ key = ")" },
		{ key = "}" },
		{ key = "]" },
	},
	jump_in = {
		{ key = "(", lhs = "( ", rhs = " )" },
		{ key = "{", lhs = "{ ", rhs = " }" },
		{ key = "[", lhs = "[", rhs = "]" },
	},
	jump_in_or_out = {
		{ key = "'", lhs = "'", rhs = "'", out_condition = { "string", "string.documentation" } },
		{ key = '"', lhs = '"', rhs = '"', out_condition = { "string", "string.documentation" } },
		{ key = "`", lhs = "`", rhs = "`", out_condition = { "string", "string.documentation" } },
	},

	-- Enclosing/Surrounding character mappings, visually select then double tap the
	-- character to enclose the selections
	-- Add the `enable = false` key to disable a mapping
	visual_surrounds = {
		{ keys = "((", map = "<ESC>`>a)<ESC>`<i(<ESC>" },
		{ keys = "))", map = "<ESC>`<i(<ESC>`><right>a)<ESC>" },
		{ keys = "{{", map = "<ESC>`>a}<ESC>`<i{<ESC>" },
		{ keys = "}}", map = "<ESC>`<i{<ESC>`><right>a}<ESC>" },
		{ keys = "[[", map = "<ESC>`>a]<ESC>`<i[<ESC>" },
		{ keys = "]]", map = "<ESC>`<i[<ESC>`><right>a]<ESC>" },
		{ keys = '""', map = '<ESC>`>a"<ESC>`<i"<ESC>' },
		{ keys = "''", map = "<ESC>`>a'<ESC>`<i'<ESC>" },
		{ keys = "``", map = "<ESC>`>a`<ESC>`<i`<ESC>" },
	},
}

return defaults
