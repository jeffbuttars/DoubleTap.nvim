-- Declare configuration defaults
return {
	threshold = 0.35, -- In seconds

	-- Enable stepping over a rhs if the cursor is in front of it and a single rhs is typed
	walkout = true,
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
