local M = {}

M.defaults = {
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
}

M.setup_config = function(config)
	if not (type(config) == "table") then
		return
	end

	local updated_config = vim.tbl_deep_extend("force", M.defaults, config)

	return updated_config
end

return M
