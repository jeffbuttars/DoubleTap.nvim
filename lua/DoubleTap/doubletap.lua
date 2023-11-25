-- Where the work happens
local dtConfig = require("DoubleTap.config")
local utils = require("DoubleTap.utils")

-- Public Object/Interface
local M = {}

-- context/state
local CTX = {
	config = dtConfig.defaults,
	ft_configs = {},
	ts_node = nil,
	ts_end_char = nil,
	last_key_ts = 0,
	last_key = "",
	ts_captures = nil,
	next_char_matches = false,
	clean_line = "",
	cur_pos_row = 0,
	cur_pos_col = 0,
}

function CTX:reset()
	self.ts_node = nil
	self.ts_end_char = nil
	self.last_key_ts = 0
	self.last_key = ""
	self.ts_captures = nil
	self.next_char_matches = false
	self.clean_line = ""
	self.cur_pos_row = 0
	self.cur_pos_col = 0
end

function CTX:isInCapture(key, capture)
	-- The capture must match and the ts_start_char must match the key,
	-- then we consider the cursor to be in a string that is bound by the
	-- current key
	-- vim.print("isInCapture " .. key .. " : " .. tostring(capture))

	if not CTX.ts_node then
		return false
	end

	local start_row, start_col = CTX.ts_node:start()
	local start_line = vim.fn.getline(start_row + 1)
	local ts_start_char = string.sub(start_line, start_col, start_col)

	if not ((key == ts_start_char) and self.ts_captures) then
		-- vim.print("isInCapture false: does not match start char:" .. key .. " != " .. ts_start_char)
		-- vim.print("isInCapture: or no capture:")
		-- vim.print(CTX.ts_captures)
		return false
	end

	for _, v in ipairs(self.ts_captures) do
		if utils.hasEntry(capture, v) then
			-- vim.print("isInCapture matched capture:" .. v)
			return true
		end
	end

	return false
end

function CTX:isDoubleTap(spec)
	-- vim.print("isDoubleTap: ", spec)
	local key = spec.key
	local now = vim.fn.reltimefloat(vim.fn.reltime())
	local call_is_good = false

	CTX.cur_pos_row, CTX.cur_pos_col = unpack(vim.api.nvim_win_get_cursor(0))

	if key ~= self.last_key then
		-- Not a DoubleTap (yet)
		-- Store what's happened into the CTX so we can know if a DoubleTap occurs
		-- on the next stroke

		-- access the Treesitter information before the line is changed,
		-- we need to look at the line as it is now, before anything is inserted.
		self.last_key_ts = now

		-- If there is an out condition, we'll need more information about
		-- where the cursor is at for that condition to be tested later
		-- if spec.out_condition then

		-- Use Treesitter to find the fist character of the string,
		-- which should be the first string delimiter character
		call_is_good, CTX.ts_node = pcall(vim.treesitter.get_node)
		if not call_is_good then
			CTX.ts_node = nil
		end

		CTX.clean_line = vim.fn.getline(".")
		CTX.cur_pos_row, CTX.cur_pos_col = unpack(vim.api.nvim_win_get_cursor(0))
		local cur_row = CTX.cur_pos_row
		local cur_col = CTX.cur_pos_col

		local next_char = string.sub(CTX.clean_line, cur_col + 1, cur_col + 1)

		-- vim.print("Next CHAR: " .. cur_col)
		-- vim.print("Next CHAR: " .. cur_col .. " : " .. next_char)

		if CTX.ts_node then
			local start_row, _ = CTX.ts_node:start()
			local end_row, end_col = CTX.ts_node:end_()
			local end_line = vim.fn.getline(end_row + 1)
			-- vim.print("End line: " .. end_line)

			-- capture the end_char now on the 'clean' line
			if end_row == start_row then
				CTX.ts_end_char = string.sub(end_line, end_col + 1, end_col + 1)
			else
				CTX.ts_end_char = string.sub(end_line, end_col, end_col)
			end
			-- vim.print("ts_end_char: " .. CTX.ts_end_char)

			if (cur_row - 1) == end_row then
				-- Save this to help determine a walkout later
				CTX.next_char_matches = next_char == key
				-- vim.print("next_char_matches: '" .. next_char .. "':'" .. key .. "'")
			end

			self.ts_captures = vim.treesitter.get_captures_at_cursor(0)
			-- vim.print("Start row: " .. start_row .. ", col: " .. start_col)
			-- vim.print("End row: " .. end_row .. ", col: " .. end_col)
			-- vim.print("Next char: " .. (CTX.next_char_matches and key or ""))
			-- vim.print("Node End char: " .. CTX.ts_end_char)
		else
			-- if there is no TS node found, use other methods to determine our context
			-- Save this to help determine a walkout later
			CTX.next_char_matches = next_char == key
			-- vim.print("next_char_matches: '" .. next_char .. "':'" .. key .. "'")
			-- stifu
		end

		return false
	end

	local delta = now - self.last_key_ts
	self.last_key_ts = now
	if delta > self.config.threshold then
		-- To slow
		return false
	end

	-- vim.print("DoubleTap valid match: " .. CTX.last_key .. key .. delta)
	-- vim.print("isInCapture: " .. tostring(isInCapture(key)))
	return true
end

local finishLine = function(spec)
	local finish_char = spec.rhs
	local cur_row = CTX.cur_pos_row

	-- Trim white space from the end of the line
	local updated_line = CTX.clean_line:match("^(.-)%s*$")

	-- A finish_char, 'rhs' is not required
	-- If there is a finish char, and it's not already there, add it.
	if finish_char then
		if updated_line:sub(-1) ~= finish_char then
			-- vim.print("finishLine:", updated_line:sub(-1), finish_char)
			updated_line = updated_line .. finish_char
		end
	end

	if spec.cursor_to_end then
    -- Set the cursor to the end of the line
		vim.fn.cursor({ cur_row, string.len(updated_line) + 1 })
	end

	vim.api.nvim_buf_set_lines(0, cur_row - 1, cur_row, false, { updated_line })
end

local jumpIn = function(key_spec)
	-- Splice the current line, removing the existing key from the previous input
	-- and splice in the lhs and rhs values for this key spec and then position the
	-- cursor into the middle of the splice point

	local cur_row, cur_col = CTX.cur_pos_row, CTX.cur_pos_col
	local cur_line = vim.api.nvim_buf_get_lines(0, cur_row - 1, cur_row, false)[1]

	local updated_line = string.sub(cur_line, 0, cur_col - 1)
		.. key_spec.lhs
		.. key_spec.rhs
		.. string.sub(cur_line, cur_col + 1, -1)
	vim.api.nvim_buf_set_lines(0, cur_row - 1, cur_row, false, { updated_line })

	vim.fn.cursor({ cur_row, cur_col + string.len(key_spec.lhs) })
end

local walkOut = function()
	-- vim.print("jumpOut WALKING")
	local row, col = CTX.cur_pos_row, CTX.cur_pos_col
	local jump_to_row, jump_to_col = row, col

	-- Walkout is simple, only one key has been fed.
	-- Just move the cursor and don't feed the key
	-- no need to clean lines in this scenario
	vim.fn.cursor({ jump_to_row, jump_to_col + 2 })
end

local jumpOut = function(key_spec)
	-- * Need to determine where to put the cursor
	--    * Treesitter node end character takes precedence if it matches the trigger key
	--    * If there is no node character information:
	--      * Search for the next occurrence of the key
	-- * clean up the current line, remove the extra characters we don't want there
	-- * move the cursor to the new location
	local key = key_spec.key
	local row, col = CTX.cur_pos_row, CTX.cur_pos_col
	local jump_to_row, jump_to_col = row, col

	local dirty_lines = vim.api.nvim_buf_get_lines(0, row - 1, row, false)

	if CTX.ts_node and (CTX.ts_end_char == key) then
		-- Use treesitter node to pick the jump position
		jump_to_row, jump_to_col = CTX.ts_node:end_()
		jump_to_row = jump_to_row + 1
		jump_to_col = jump_to_col + 1
		-- vim.print("jumpOut, end from node: " .. CTX.ts_end_char .. ", " .. jump_to_row .. ":" .. jump_to_col)
	elseif string.sub(dirty_lines[1], col + 1, col + 1) == key then
		-- If the jump to char is at the cursor, just move over one, otherwise search
		-- vim.print("jumpOut, Under cursor:" .. string.sub(dirty_lines[1], col + 1, col + 1))
		jump_to_col = jump_to_col + 1
	else
		-- Use searchpos to pick the naive jump position
		-- vim.print("jumpOut, no node end info, searchpos")
		jump_to_row, jump_to_col = unpack(vim.fn.searchpos(key, "nWz"))
		if jump_to_row == 0 and jump_to_col == 0 then
			-- vim.print("jumpOut, Jump to pos not found, need to searchpos: " .. jump_to_row .. " " .. jump_to_col)
			vim.api.nvim_feedkeys(key, "n", false)
			return
		end

		if jump_to_row ~= row then
			jump_to_col = jump_to_col + 1
		end
	end

	-- Put the cleaned line back into the buffer
	vim.api.nvim_buf_set_lines(0, row - 1, row, false, { CTX.clean_line })

	-- Now we jump
	--
	vim.fn.cursor({ jump_to_row, jump_to_col })
end

local jumpInOrOut = function(key_spec)
	local key = key_spec.key
	local capture = key_spec.out_condition

	if CTX:isInCapture(key, capture) then
		jumpOut(key_spec)
	else
		jumpIn(key_spec)
	end
end

local dispatch_key = function(key)
	-- Use a cheesy method to filter down to keys we care about.
	-- Track keys to look for doubles in the auto commands
	if vim.fn.strlen(key) == 1 then
		CTX.last_key = key
	end

	return key
end

local process_auto_cmd = function(spec, action_func)
	-- vim.print("process_auto_cmd dt", spec.key)
	if CTX:isDoubleTap(spec) then
		-- vim.print("process_auto_cmd dt", spec.key)
		action_func(spec)
		-- Reset the state after taking action
		CTX:reset()
	elseif CTX.next_char_matches and CTX.config.walkout and action_func ~= jumpIn then
		-- See if we can should 'walkout'
		-- vim.print("WALKOUT!")
		walkOut()
		CTX:reset()
	else
		vim.api.nvim_feedkeys(spec.key, "n", false)
	end
end

local setup_insert_keymaps = function(opts)
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

	vim.print("setup_insert_keymaps finishLine")
	vim.print(opts.finish_line)
	for _, spec in ipairs(opts.finish_line) do
		vim.print("Finishline for key ", spec.key)
		vim.keymap.set("i", spec.key, function()
			process_auto_cmd(spec, finishLine)
		end, { nowait = true, noremap = true })
	end
end

local setup_visual_keymaps = function(opts)
	-- Enclosing/Surrounding character mappings, visually select then double tap the
	-- character to enclose the selections
	for _, spec in ipairs(opts.visual_surrounds) do
		if (spec.enabled == nil) or spec.enabled then
			vim.api.nvim_set_keymap("v", spec.keys, spec.map, { noremap = true })
		end
	end
end

local set_current_config = function(ctx)
	-- look for filetype overrides
	local buf_nr = vim.api.nvim_get_current_buf()
	local filetype = vim.bo[buf_nr].filetype

	local current_config = ctx.config

	-- vim.print("DoubleTap set_current_config BNR", buf_nr)
	-- vim.print("DoubleTap set_current_config FT", filetype)
	--
	-- if ctx.config.filetypes[filetype] then
	-- 	vim.print("FT Cconfig:", ctx.config.filetypes[filetype])
	--
	-- 	if not ctx.ft_configs[filetype] then
	-- 		local ft_config = vim.tbl_deep_extend("force", ctx.config, ctx.config.filetypes[filetype])
	-- 		ctx.ft_configs[filetype] = ft_config
	-- 	end
	--
	-- 	current_config = ctx.ft_configs[filetype]
	--
	-- 	vim.print("DoubleTap set_current_config FT", current_config)
	-- end

	setup_visual_keymaps(current_config)
	setup_insert_keymaps(current_config)
end

local setup_auto_cmds = function(ctx)
	-- vim.print("DoubleTap setup_auto_cmds...")
	vim.api.nvim_create_augroup("DoubleTapAugroup", {
		clear = true,
	})

	vim.api.nvim_create_autocmd("BufEnter", {
		desc = "DoubleTap FT specific checks and config setup",
		group = "DoubleTapAugroup",
		callback = function(opts)
			set_current_config(ctx)
		end,
	})
end

M.setup = function(opts)
	CTX.config = dtConfig.setup_config(opts)
	setup_auto_cmds(CTX)
end

return M
