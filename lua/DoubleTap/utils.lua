return {
	hasEntry = function(table, value)
		if type(table) ~= "table" then
			return false
		end

		for _, v in ipairs(table) do
			if v == value then
				return true
			end
		end

		return false
	end,
}
