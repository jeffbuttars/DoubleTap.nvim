local dtConfig = require("DoubleTap.config")

-- Public Object/Interface
local M = {}

-- context/state
local CTX = {
	config = dtConfig.defaults,
	last_key_ts = 0,
	last_key = "",
	ts_captures = nil,
	ts_start_char = nil,
}

function CTX:reset()
	self.last_key_ts = 0
	self.last_key = ""
	self.ts_captures = nil
	self.ts_start_char = nil
end

local hasEntry = function(table, value)
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
end

local isInString = function(key, capture)
	-- The capture must match and the ts_start_char must match the key,
	-- then we consider the cursor to be in a string that is bound by the
	-- current key
	-- vim.print("isInString " .. key .. " : " .. tostring(capture))

	if not ((key == CTX.ts_start_char) and CTX.ts_captures) then
		-- vim.print("isInString false: does not match start char:" .. key .. " != " .. CTX.ts_start_char)
		-- vim.print("isInString: or no capture:")
		-- vim.print(CTX.ts_captures)
		return false
	end
	-- vim.print("isInString: matched start char:" .. key .. " == " .. CTX.ts_start_char)

	local ts_captures = CTX.ts_captures

	-- vim.print(ts_captures)
	for _, v in ipairs(ts_captures) do
		if hasEntry(capture, v) then
			-- vim.print("isInString matched capture:" .. v)
			return true
		end
	end

	return false
end

local isDoubleTap = function(spec)
	local key = spec.key
	local now = vim.fn.reltimefloat(vim.fn.reltime())

	if key ~= CTX.last_key then
		-- Not a DoubleTap (yet)
		-- Store what's happened into the CTX so we can know if a DoubleTap occurs
		-- on the next stroke

		-- vim.print("DoubleTap last key no match: " .. CTX.last_key .. key)
		-- vim.print(CTX.last_key)
		-- vim.print(key)
		-- access the Treesitter information of before the line is changed
		CTX.last_key_ts = now

		-- If there is an out condition, we'll need more information about
		-- where the cursor is at for that condition to be tested later
		if spec.out_condition then
			-- Use Treesitter to find the fist character of the string,
			local ts_node = vim.treesitter.get_node()
			CTX.ts_captures = vim.treesitter.get_captures_at_cursor(0)

			if ts_node then
				local start_row, start_col = ts_node:start()
				local start_line = vim.fn.getline(start_row + 1)
				CTX.ts_start_char = string.sub(start_line, start_col, start_col)
			end
		end

		-- vim.print("Start line: " .. start_line)
		-- vim.print("Start char: " .. CTX.ts_start_char)

		-- vim.print("remember capture and node: ")
		-- vim.print(CTX.ts_captures)
		-- vim.print(ts_node)
		return false
	end

	local delta = now - CTX.last_key_ts
	CTX.last_key_ts = now
	if delta > CTX.config.threshold then
		-- vim.print("DoubleTap to slow " .. key)
		-- To slow
		return false
	end

	-- vim.print("DoubleTap valid match: " .. CTX.last_key .. key .. delta)
	-- vim.print("isInString: " .. tostring(isInString(key)))
	return true
end

local jumpIn = function(key_spec)
	-- Splice the current line, removing the existing key from the previous input
	-- and splice in the lhs and rhs values for this key spec and then position the
	-- cursor into the middle of the splice point

	local cur_row, cur_col = unpack(vim.api.nvim_win_get_cursor(0))
	local cur_line = vim.api.nvim_buf_get_lines(0, cur_row - 1, cur_row, false)[1]

	local updated_line = string.sub(cur_line, 0, cur_col - 1)
		.. key_spec.lhs
		.. key_spec.rhs
		.. string.sub(cur_line, cur_col + 1, -1)
	vim.api.nvim_buf_set_lines(0, cur_row - 1, cur_row, false, { updated_line })

	vim.fn.cursor({ cur_row, cur_col + string.len(key_spec.lhs) })

	CTX:reset()
end

local jumpOut = function(key_spec)
	local key = key_spec.key

	-- If the jump to char is at the cursor, just move over one, otherwise search
	local cur_pos = vim.api.nvim_win_get_cursor(0)
	local row, col = unpack(cur_pos)
	local jump_to_row, jump_to_col = row, col
	local dirty_lines = vim.api.nvim_buf_get_lines(0, row - 1, row, false)

	if string.sub(dirty_lines[1], col + 1, col + 1) == key then
		-- vim.print("Under cursor:" .. string.sub(dirty_lines[1], col + 1, col + 1))
		jump_to_col = jump_to_col + 1
	else
		jump_to_row, jump_to_col = unpack(vim.fn.searchpos(key, "nWz"))
		if jump_to_row == 0 and jump_to_col == 0 then
			-- vim.print("Jump to pos not found: " .. jump_to_row .. " " .. jump_to_col)
			vim.api.nvim_feedkeys(key, "n", false)
			return
		end

		if jump_to_row ~= row then
			jump_to_col = jump_to_col + 1
		end

		-- vim.print("jump to:" .. jump_to_row .. " " .. jump_to_col)
	end

	-- vim.print(cur_pos)
	-- vim.print(dirty_lines[1])
	-- Remove the DoubleTap chars, and if needed, adjust the jump to pos if it's on the same row
	local cleaned_line = dirty_lines[1]:sub(1, col - 1) .. dirty_lines[1]:sub(col + 1)

	-- Put the cleaned line back into the buffer
	vim.api.nvim_buf_set_lines(0, row - 1, row, false, { cleaned_line })

	-- Now we jump
	-- vim.api.nvim_win_set_cursor(0, { jump_to_row, jump_to_col })
	vim.fn.cursor(jump_to_row, jump_to_col)

	CTX:reset()
end

local jumpInOrOut = function(key_spec)
	-- vim.print(CTX.ts_captures)
	local key = key_spec.key
	local capture = key_spec.out_condition

	if isInString(key, capture) then
		-- vim.print("jumpInOrOut: Out " .. key)
		jumpOut(key_spec)
	else
		-- vim.print("jumpInOrOut: In " .. key)
		jumpIn(key_spec)
	end
	-- vim.api.nvim_feedkeys(key, "n", false)
end

local dispatch_key = function(key)
	-- Use a cheesy method to filter down to keys we care about.
	-- Track keys to look for doubles in the auto commands
	if vim.fn.strlen(key) == 1 then
		CTX.last_key = key
	end

	return key
end

local process_auto_cmd = function(spec, func)
	if isDoubleTap(spec) then
		func(spec)
	else
		vim.api.nvim_feedkeys(spec.key, "n", false)
	end
end

local setup_keymaps = function(opts)
	-- Watch every key to help detect the DoubleTap
	vim.on_key(dispatch_key)

	for _, spec in ipairs(opts.jump_out) do
		vim.keymap.set("i", spec.key, function()
			process_auto_cmd(spec, jumpOut)
		end, { nowait = true, noremap = true })
	end

	for _, spec in ipairs(opts.jump_in) do
		vim.keymap.set("i", spec.key, function()
			process_auto_cmd(spec, jumpIn)
		end, { nowait = true, noremap = true })
	end

	for _, spec in ipairs(opts.jump_in_or_out) do
		vim.keymap.set("i", spec.key, function()
			process_auto_cmd(spec, jumpInOrOut)
		end, { nowait = true, noremap = true })
	end

	-- Enclosing/Surrounding character mappings, visually select then double tap the
	-- character to enclose the selections
	for _, spec in ipairs(opts.visual_surrounds) do
		if (spec.enabled == nil) or spec.enabled then
			vim.api.nvim_set_keymap("v", spec.keys, spec.map, { noremap = true })
		end
	end
end

M.setup = function(opts)
	CTX.config = dtConfig.setup_config(opts)

	setup_keymaps(CTX.config)
end

return M
