require("DoubleTap.globals")
local dtConfig = require("DoubleTap.config")

-- Public Object/Interface
local DoubleTap = {}

-- Local context/state
local CTX = {
	last_key_ts = 0,
	last_key = "",
	clean_lines = { "" },
	config = dtConfig.defaults,
}

local hasEntry = function(table, value)
	vim.print("hasEntry: " .. type(table))
	vim.print(table, value)

	if not (type(table) == "table") then
		vim.print("hasEntry: false, no table")
		return false
	end

	for _, v in ipairs(table) do
		if v == value then
			vim.print("hasEntry: true")
			return true
		end
	end

	vim.print("hasEntry: false, bottom")
	return false
end

local canJumpOut = function(capture, row, col)
	if not capture then
		-- This key doesn't need to be captured to jump,
		-- so it can jump out
		vim.print("canJumpOut true, no capture")
		return true
	end

	if not row then
		row = vim.fn.line(".") - 1
	end

	if not col then
		col = vim.fn.col(".") - 1
	end

	-- local ts_captures = vim.treesitter.get_captures_at_pos(0, row, col)
	vim.treesitter.get_parser(0):parse(true)
	local ts_captures = vim.treesitter.get_captures_at_cursor(0)

	vim.print(row, col)
	vim.print(ts_captures)

	for _, v in ipairs(ts_captures) do
		if hasEntry(capture, v) then
			vim.print("canJumpOut true, has entry:" .. v)
			return true
		end
	end

	vim.print("canJumpOut false")
	return false
end

local jumpOut = function(key, capture)
	local now = vim.fn.reltimefloat(vim.fn.reltime())

	-- The clean_line is the current line that's being edited before any
	-- DoubleTap chars are inserted into it.
	-- If a jumpOot occurs, we need to restore the clean_line into the buffer
	-- local cur_pos = vim.api.nvim_win_get_cursor(0)
	-- local row, col = unpack(cur_pos)
	-- local clean_line = vim.api.nvim_buf_get_lines(0, row - 1, col, false)
	-- CTX.clean_lines = clean_line

	-- If this char does match a previously stored char, we
	-- are at the first state and this current line needs to be preserved
	-- in case we perform a jump out and need to return the line back to it's original state
	if not (key == CTX.last_key) then
		-- Not a DoubleTap (yet)
		-- Store what's happened into the CTX so we can know if a DoubleTap occurs
		-- on the next stroke
		vim.api.nvim_feedkeys(key, "n", false)

		-- CTX.last_key = key
		CTX.last_key_ts = now

		vim.print("DoubleTap last key no match: " .. CTX.last_key .. key)
		-- vim.print(CTX.last_key)
		-- vim.print(key)
		return
	end
	vim.print("DoubleTap, :" .. CTX.last_key .. key .. "got double char")

	-- See if happened fast enough!
	local delta = now - CTX.last_key_ts
	CTX.last_key_ts = now
	if delta > CTX.config.threshold then
		-- it's been to long, effectively reset our state.
		-- CTX.last_key = key
		-- restore the 'dirty' line
		-- vim.api.nvim_buf_set_lines(0, c[1] - 1, c[1], false, orig_line)
		-- CTX.clean_lines = orig_line
		vim.api.nvim_feedkeys(key, "n", false)

		vim.print("DoubleTap to slow " .. key)
		-- To slow
		return
	end

	vim.print("DoubleTap valid match: " .. CTX.last_key .. key .. delta)

	-- * Need to see if we can find a place to jump to
	-- * If a jump is found
	-- * Edit the current line to remove the double chars
	-- * If the jump pos is on the same line, adjust it's column pos
	-- * Move the cursor to the jump pos

	-- If the jump to char is at the cursor, just move over one, otherwise search
	local cur_pos = vim.api.nvim_win_get_cursor(0)
	local row, col = unpack(cur_pos)
	local jump_to_row, jump_to_col = row, col
	local dirty_lines = vim.api.nvim_buf_get_lines(0, row - 1, row, false)

	if string.sub(dirty_lines[1], col + 1, col + 1) == key then
		vim.print("Under cursor:" .. string.sub(dirty_lines[1], col + 1, col + 1))
		jump_to_col = jump_to_col + 1
	else
		jump_to_row, jump_to_col = unpack(vim.fn.searchpos(key, "nWz"))
		if jump_to_row == 0 and jump_to_col == 0 then
			vim.print("Jump to pos not found: " .. jump_to_row .. " " .. jump_to_col)
			vim.api.nvim_feedkeys(key, "n", false)
			return
		end

		if not (jump_to_row == row) then
			jump_to_col = jump_to_col + 1
		end

		vim.print("jump to:" .. jump_to_row .. " " .. jump_to_col)
	end

	-- vim.print(cur_pos)
	vim.print(dirty_lines[1])
	-- Remove the DoubleTap chars, and if needed, adjust the jump to pos if it's on the same row
	local cleaned_line = dirty_lines[1]:sub(1, col - 1) .. dirty_lines[1]:sub(col + 1)

	-- Put the cleaned line back into the buffer
	vim.api.nvim_buf_set_lines(0, row - 1, row, false, { cleaned_line })

	-- Now we jump
	-- vim.api.nvim_win_set_cursor(0, { jump_to_row, jump_to_col })
	vim.fn.cursor(jump_to_row, jump_to_col)

	-- Reset some state?
	-- CTX.last_key = nil

	-- If we're here, it's because we just got the same char, twice in a row
	-- We use time to decide if we consider it a DoubleTap or not.

	-- BAIL NOW
	-- it's
	-- vim.api.nvim_feedkeys(key, "n", false)
	do
		return
	end
	-- BAIL NOW

	-- Store the line, before the key is typed
	local c = vim.api.nvim_win_get_cursor(0)
	local orig_line = vim.api.nvim_buf_get_lines(0, c[1] - 1, c[1], false)

	-- vim.print("capture: ", capture)
	-- vim.print("inString: ", canJumpOut(capture))

	if not (key == CTX.last_key) then
		-- Not a DoubleTap (yet), we don't care about this key
		CTX.last_key = key
		CTX.last_key_ts = now
		-- Before the line is altered, we'll consider this the 'clean' line
		CTX.clean_lines = orig_line

		vim.api.nvim_feedkeys(key, "n", false)

		vim.print("DoubleTap Just a single " .. key)
		return
	end

	-- In order to inspect the text, we have to return it to how it was
	-- before the characters we're typed and we detected a DoubleTap

	vim.print("Resetting to clean lines:")
	P(CTX.clean_lines)
	vim.api.nvim_buf_set_lines(0, c[1] - 1, c[1], false, CTX.clean_lines)
	-- vim.print("Reset? :")
	-- P(vim.api.nvim_buf_get_lines(0, c[1] - 1, c[1], false))

	-- Is this key in a context that allows a jump out?
	if not canJumpOut(capture) then
		-- restore the 'dirty' line
		vim.api.nvim_buf_set_lines(0, c[1] - 1, c[1], false, orig_line)
		CTX.last_key = key
		CTX.clean_lines = orig_line
		vim.api.nvim_feedkeys(key, "n", false)

		vim.print("DoubleTap not in context " .. key)
		return
	end

	-- The DoubleTap must be quick enough
	local delta = now - CTX.last_key_ts
	CTX.last_key_ts = now
	CTX.last_key = key
	vim.print("DoubleTap Catch key '" .. key .. "'delta:" .. delta .. " - " .. CTX.config.threshold)

	if delta > CTX.config.threshold then
		-- we don't care about this key, it's been to long
		CTX.last_key = key
		-- restore the 'dirty' line
		vim.api.nvim_buf_set_lines(0, c[1] - 1, c[1], false, orig_line)
		CTX.clean_lines = orig_line
		vim.api.nvim_feedkeys(key, "n", false)

		vim.print("DoubleTap to slow " .. key)
		-- To slow
		return
	end

	-- Going to take action
	CTX.last_key = ""

	-- local r, c = vim.api.nvim_win_get_cursor(0)
	vim.print("DoubleTap Caught pos :" .. c[1] .. " " .. c[2])

	-- vim.api.nvim_feedkeys(key, 'n', false)

	-- vim.print("DoubleTap Caught pos :" .. c)
	-- P(c)
	vim.print("DoubleTap Caught key :" .. key .. " " .. delta .. " - " .. CTX.config.threshold)
	local n_pos = vim.fn.searchpos(key, "nWz")
	P(n_pos)

	if n_pos[1] == 0 then
		-- Nothing found
		vim.print("DoubleTap no pos found")
		CTX.clean_lines = orig_line
		vim.api.nvim_buf_set_lines(0, c[1] - 1, c[1], false, orig_line)
		vim.api.nvim_feedkeys(key, "n", false)
		return
	end

	vim.print("Line to fix:" .. c[1] - 1 .. "," .. c[1])

	-- local updated_line = orig_line[1]:sub(1, c[2] - 1) .. orig_line[1]:sub(c[2] + 1)

	P(orig_line)
	P(CTX.clean_lines)

	-- Restore the 'clean' line
	vim.api.nvim_buf_set_lines(0, c[1] - 1, c[1], false, CTX.clean_lines)

	vim.print("DoubleTap set cursor")
	vim.print("DoubleTap get buf:" .. vim.api.nvim_win_get_buf(0))
	P(vim.api.nvim_win_get_buf(0))
	vim.api.nvim_win_set_cursor(0, { n_pos[1], n_pos[2] })

	-- vim.api.nvim_feedkeys(key, 'm', true)
	-- vim.api.nvim_feedkeys(key, "t", true)
end

local dispatch_key = function(key)
	-- CTX.last_key = key
	-- CTX.last_key =vim.api.nvim_replace_termcodes(key, true, true, true)

	-- Use a cheesy method to filter down to keys we care about
	if vim.fn.strlen(key) == 1 then
		CTX.last_key = key
		-- vim.print("dispatch_key last key ->", key)
	end

	return key
end

local setup_auto_commands = function(opts)
	vim.on_key(dispatch_key)

	vim.keymap.set("n", "<leader>pr", function()
		R("DoubleTap")
	end, { noremap = true, desc = "Double Tap Reload" })

	for _, val in ipairs(opts.jump_out) do
		-- vim.print("key: " .. val.key)
		-- vim.print("capture: ", val.capture)
		vim.keymap.set("i", val.key, function()
			local k = val.key
			local c = val.capture
			jumpOut(k, c)
		end)
	end
end

DoubleTap.setup = function(opts)
	CTX.config = dtConfig.setup_config(opts)

	setup_auto_commands(CTX.config)
end

-- M.setup = function(opts)
-- 	if opts == nil then
-- 		opts = {}
-- 	end
--
-- 	opts = {
-- 		threshold = 0.4, -- In seconds
-- 		jump_out = {
-- 			{ key = ")" },
-- 			{ key = "}" },
-- 			{ key = "'", capture = { "string", "string.documentation" } },
-- 			{ key = '"', capture = { "string", "string.documentation" } },
-- 		},
-- 		finish_line = {
-- 			[";"] = { ";", trim = true },
-- 		},
-- 	}
--
-- 	--  P(opts)
--
-- 	-- table.merge(M, opts)
-- 	M.opts = opts
--
-- 	for _, val in ipairs(opts.jump_out) do
--     -- vim.print("key: " .. val.key)
--     -- vim.print("capture: ", val.capture)
-- 		vim.keymap.set("i", val.key, function()
--       local k = val.key
--       local c = val.capture
-- 			jumpOut(k, c)
-- 		end)
-- 	end
--
-- 	-- P(M.opts)
-- 	return opts
-- end
--
-- function M.sayHelloWorld()
-- 	print("Hello World Again!!!")
-- end

-- vim.keymap.set("n", "<leader>ptt", function()
-- 	require("DoubleTap").sayHelloWorld()
-- end, { noremap = true, desc = "Double Tap Dev run" })

return DoubleTap
