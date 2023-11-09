local M = {}

M.defaults = {
	threshold = 0.4, -- In seconds
	jump_out = {
		{ key = ")", },
		{ key = "}" },
		{ key = "]" },
		-- { key = "'", capture = { "string", "string.documentation" } },
		-- { key = '"', capture = { "string", "string.documentation" } },
		-- { key = '`', capture = { "string", "string.documentation" } },
	},
	jump_in = {
		{ key = "(", lhs = "( ", rhs = " )"},
		{ key = "{", lhs = "{ ", rhs = " }" },
		{ key = "[", lhs = "[", rhs = "]" },
		{ key = "'", lhs = "'", rhs = "'", capture = { "string", "string.documentation" } },
		{ key = '"', lhs = '"', rhs = '"', capture = { "string", "string.documentation" } },
		{ key = "`", lhs = "`", rhs = "`", capture = { "string", "string.documentation" } },
	},
	finish_line = {
		[";"] = { ";", trim = true },
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
