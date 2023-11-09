local M = {}
M.defaults = require("DoubleTap.defaults")

M.setup_config = function(config)
	if not (type(config) == "table") then
		return
	end

	local updated_config = vim.tbl_deep_extend("force", M.defaults, config)

	return updated_config
end

return M
