return {
	hasEntry = function(table, value)
		-- vim.print("hasEntry: " .. type(table))
		-- vim.print(table, value)

		if type(table) ~= "table" then
			-- vim.print("hasEntry: false, no table")
			return false
		end

		for _, v in ipairs(table) do
			if v == value then
				-- vim.print("hasEntry: true")
				return true
			end
		end

		-- vim.print("hasEntry: false, bottom")
		return false
	end,
}
