require("DoubleTap.globals")
local dtConfig = require("DoubleTap.config")

-- Public Object/Interface
local DoubleTap = {}

-- Local context/state
local CTX = {
	config = dtConfig.defaults,
	last_key_ts = 0,
	last_key = "",
	ts_node = nil,
	ts_captures = nil,
  ts_start_char = nil,
}

function CTX:reset ()
  self.last_key_ts = 0
	self.last_key = ""
	self.ts_node = nil
	self.ts_captures = nil
  self.ts_start_char = nil
end

local hasEntry = function(table, value)
	-- vim.print("hasEntry: " .. type(table))
	-- vim.print(table, value)

	if not (type(table) == "table") then
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

  if not (key == CTX.ts_start_char) then
		vim.print("isInString: does not match start char:" .. key .. " != " .. CTX.ts_start_char)
    return false
  end
  vim.print("isInString: matched start char:" .. key .. " == " .. CTX.ts_start_char)

	if not CTX.ts_capture then
		vim.print("isInString: false, no capture:")
		vim.print(CTX.ts_capture)
		return false
	end

	local ts_captures = CTX.ts_capture
	-- local ts_node = CTX.ts_node

	vim.print(ts_captures)
	-- vim.print(ts_node)
	-- vim.print(ts_node:type())

	-- local matched_capture = ""
	for _, v in ipairs(ts_captures) do
		if hasEntry(capture, v) then
			vim.print("isInString matched capture:" .. v)
			-- matched_capture = v
      return true
		end
	end

  vim.print("isInString capture not matched:" .. capture)
  do
		return false
	end

	-- local start_row, start_col, end_row, end_col = ts_node:range()
	-- vim.print(
	-- 	"node range: " .. ts_node:type() .. ", " .. start_row .. ":" .. start_col .. ":" .. end_row .. ":" .. end_col
	-- )
	-- vim.print("node text: " .. vim.treesitter.get_node_text(ts_node, 0))

	do
		return true
	end

	--
	-- local start_line = vim.api.nvim_buf_get_lines(0, start_row, start_row + 1, false)[1]
	-- vim.print("start line " .. start_line)
	-- local end_line = vim.api.nvim_buf_get_lines(0, end_row, end_row + 1, false)[1]
	-- vim.print("end line " .. start_line)
	--
	-- local start_char = string.sub(start_line, start_col, start_col)
	-- local end_char = string.sub(end_line, end_col, end_col)
	-- --
	-- vim.print("start char:" .. start_char)
	-- vim.print("end char:" .. end_char)
	--
	-- if (key == start_char) or (key == end_char) then
	-- 	vim.print("In string " .. key)
	-- 	return true
	-- end
	--
	-- return false
	--
	-- -- vim.print(node.start())
	-- -- vim.print(node.end_)
	-- -- vim.treesitter.get_node(0, row, col)
	-- -- If the node is a string delem, return that char
	-- -- otherwise, use the prev/next nodes to figure out the delim
end

local isDoubleTap = function(key)
	local now = vim.fn.reltimefloat(vim.fn.reltime())

	if not (key == CTX.last_key) then
		-- Not a DoubleTap (yet)
		-- Store what's happened into the CTX so we can know if a DoubleTap occurs
		-- on the next stroke
		-- vim.api.nvim_feedkeys(key, "n", false)

		-- CTX.last_key = key
		CTX.last_key_ts = now

		-- vim.print("DoubleTap last key no match: " .. CTX.last_key .. key)
		-- vim.print(CTX.last_key)
		-- vim.print(key)
		-- Remember the node we're at so we can easily reference it later
		-- and access the ts node of before the line was changed
		CTX.ts_node = vim.treesitter.get_node()
		CTX.ts_capture = vim.treesitter.get_captures_at_cursor(0)

    local start_row, start_col = CTX.ts_node:start()
    local start_line = vim.fn.getline(start_row + 1)

    -- vim.print("Start line: " .. start_line)
		CTX.ts_start_char = string.sub(start_line, start_col, start_col)
    vim.print("Start char: " .. CTX.ts_start_char)

		-- vim.print("remember capture and node: ")
		-- vim.print(CTX.ts_capture)
		-- vim.print(CTX.ts_node)

		return false
	end

	local delta = now - CTX.last_key_ts
	CTX.last_key_ts = now
	if delta > CTX.config.threshold then
		-- it's been to long, effectively reset our state.
		-- CTX.last_key = key
		-- restore the 'dirty' line
		-- vim.api.nvim_buf_set_lines(0, c[1] - 1, c[1], false, orig_line)
		-- CTX.clean_lines = orig_line
		-- vim.api.nvim_feedkeys(key, "n", false)

		vim.print("DoubleTap to slow " .. key)
		-- To slow
		return false
	end

	vim.print("DoubleTap valid match: " .. CTX.last_key .. key .. delta)
	-- vim.print("isInString: " .. tostring(isInString(key)))

	-- Squash the time stamp down so a quick 3rd key doesn't sneek in.
	-- We'll have to change this when we need to support some triples
	--   like '"""' in Python
	-- CTX.last_key_ts = 0
	return true
end

-- local canJumpOut = function(capture, row, col)
-- 	if not capture then
-- 		-- This key doesn't need to be captured to jump,
-- 		-- so it can jump out
-- 		vim.print("canJumpOut true, no capture")
-- 		return true
-- 	end
--
-- 	if not row then
-- 		row = vim.fn.line(".") - 1
-- 	end
--
-- 	if not col then
-- 		col = vim.fn.col(".") - 1
-- 	end
--
-- 	-- local ts_captures = vim.treesitter.get_captures_at_pos(0, row, col)
-- 	vim.treesitter.get_parser(0):parse(true)
-- 	local ts_captures = vim.treesitter.get_captures_at_cursor(0)
--
-- 	vim.print(row, col)
-- 	vim.print(ts_captures)
--
-- 	for _, v in ipairs(ts_captures) do
-- 		if hasEntry(capture, v) then
-- 			vim.print("canJumpOut true, has entry:" .. v)
-- 			return true
-- 		end
-- 	end
--
-- 	vim.print("canJumpOut false")
-- 	return false
-- end

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
		vim.print("Under cursor:" .. string.sub(dirty_lines[1], col + 1, col + 1))
		jump_to_col = jump_to_col + 1
	else
		jump_to_row, jump_to_col = unpack(vim.fn.searchpos(key, "nWz"))
		if jump_to_row == 0 and jump_to_col == 0 then
			-- vim.print("Jump to pos not found: " .. jump_to_row .. " " .. jump_to_col)
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

  CTX:reset()

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

	-- -- Store the line, before the key is typed
	-- local c = vim.api.nvim_win_get_cursor(0)
	-- local orig_line = vim.api.nvim_buf_get_lines(0, c[1] - 1, c[1], false)
	--
	-- -- vim.print("capture: ", capture)
	-- -- vim.print("inString: ", canJumpOut(capture))
	--
	-- if not (key == CTX.last_key) then
	-- 	-- Not a DoubleTap (yet), we don't care about this key
	-- 	CTX.last_key = key
	-- 	CTX.last_key_ts = now
	-- 	-- Before the line is altered, we'll consider this the 'clean' line
	-- 	CTX.clean_lines = orig_line
	--
	-- 	vim.api.nvim_feedkeys(key, "n", false)
	--
	-- 	vim.print("DoubleTap Just a single " .. key)
	-- 	return
	-- end
	--
	-- -- In order to inspect the text, we have to return it to how it was
	-- -- before the characters we're typed and we detected a DoubleTap
	--
	-- vim.print("Resetting to clean lines:")
	-- P(CTX.clean_lines)
	-- vim.api.nvim_buf_set_lines(0, c[1] - 1, c[1], false, CTX.clean_lines)
	-- -- vim.print("Reset? :")
	-- -- P(vim.api.nvim_buf_get_lines(0, c[1] - 1, c[1], false))
	--
	-- -- Is this key in a context that allows a jump out?
	-- if not canJumpOut(capture) then
	-- 	-- restore the 'dirty' line
	-- 	vim.api.nvim_buf_set_lines(0, c[1] - 1, c[1], false, orig_line)
	-- 	CTX.last_key = key
	-- 	CTX.clean_lines = orig_line
	-- 	vim.api.nvim_feedkeys(key, "n", false)
	--
	-- 	vim.print("DoubleTap not in context " .. key)
	-- 	return
	-- end
	--
	-- -- The DoubleTap must be quick enough
	-- local delta = now - CTX.last_key_ts
	-- CTX.last_key_ts = now
	-- CTX.last_key = key
	-- vim.print("DoubleTap Catch key '" .. key .. "'delta:" .. delta .. " - " .. CTX.config.threshold)
	--
	-- if delta > CTX.config.threshold then
	-- 	-- we don't care about this key, it's been to long
	-- 	CTX.last_key = key
	-- 	-- restore the 'dirty' line
	-- 	vim.api.nvim_buf_set_lines(0, c[1] - 1, c[1], false, orig_line)
	-- 	CTX.clean_lines = orig_line
	-- 	vim.api.nvim_feedkeys(key, "n", false)
	--
	-- 	vim.print("DoubleTap to slow " .. key)
	-- 	-- To slow
	-- 	return

	-- -- Going to take action
	-- CTX.last_key = ""
	--
	-- -- local r, c = vim.api.nvim_win_get_cursor(0)
	-- vim.print("DoubleTap Caught pos :" .. c[1] .. " " .. c[2])
	--
	-- -- vim.api.nvim_feedkeys(key, 'n', false)
	--
	-- -- vim.print("DoubleTap Caught pos :" .. c)
	-- -- P(c)
	-- vim.print("DoubleTap Caught key :" .. key .. " " .. delta .. " - " .. CTX.config.threshold)
	-- local n_pos = vim.fn.searchpos(key, "nWz")
	-- P(n_pos)
	--
	-- if n_pos[1] == 0 then
	-- 	-- Nothing found
	-- 	vim.print("DoubleTap no pos found")
	-- 	CTX.clean_lines = orig_line
	-- 	vim.api.nvim_buf_set_lines(0, c[1] - 1, c[1], false, orig_line)
	-- 	vim.api.nvim_feedkeys(key, "n", false)
	-- 	return
	-- end
	--
	-- vim.print("Line to fix:" .. c[1] - 1 .. "," .. c[1])
	--
	-- -- local updated_line = orig_line[1]:sub(1, c[2] - 1) .. orig_line[1]:sub(c[2] + 1)
	--
	-- P(orig_line)
	-- P(CTX.clean_lines)
	--
	-- -- Restore the 'clean' line
	-- vim.api.nvim_buf_set_lines(0, c[1] - 1, c[1], false, CTX.clean_lines)
	--
	-- vim.print("DoubleTap set cursor")
	-- vim.print("DoubleTap get buf:" .. vim.api.nvim_win_get_buf(0))
	-- P(vim.api.nvim_win_get_buf(0))
	-- vim.api.nvim_win_set_cursor(0, { n_pos[1], n_pos[2] })
	--
	-- -- vim.api.nvim_feedkeys(key, 'm', true)
	-- -- vim.api.nvim_feedkeys(key, "t", true)
end

local jumpInOrOut = function(key_spec)
	vim.print(CTX.ts_captures)
	vim.print(CTX.ts_node)

	local key = key_spec.key
	local capture = key_spec.out_condition

	if isInString(key, capture) then
		vim.print("jumpInOrOut: Out " .. key)
		jumpOut(key_spec)
	else
		vim.print("jumpInOrOut: In " .. key)
		jumpIn(key_spec)
	end
	-- vim.api.nvim_feedkeys(key, "n", false)
end

local dispatch_key = function(key)
	-- Use a cheesy method to filter down to keys we care about.
	-- Track keys to look for doubles in the auto commands
	if vim.fn.strlen(key) == 1 then
		CTX.last_key = key
		-- vim.print("dispatch_key last key ->", key)
	end

	return key
end

local setup_auto_commands = function(opts)
	-- Watch every key to help detect the DoubleTap
	vim.on_key(dispatch_key)

	vim.keymap.set("n", "<leader>pr", function()
		R("DoubleTap")
	end, { noremap = true, desc = "Double Tap Reload" })

	for _, spec in ipairs(opts.jump_out) do
		-- vim.print("key: " .. val.key)
		-- vim.print("capture: ", val.capture)
		vim.keymap.set("i", spec.key, function()
			local key = spec.key

			if not isDoubleTap(key) then
				vim.api.nvim_feedkeys(key, "n", false)
				return
			end

			jumpOut(spec)
		end, { nowait = true, noremap = true })
	end

	for _, spec in ipairs(opts.jump_in) do
		vim.keymap.set("i", spec.key, function()
			local key = spec.key

			if not isDoubleTap(key) then
				vim.api.nvim_feedkeys(key, "n", false)
				return
			end

			jumpIn(spec)
		end, { nowait = true, noremap = true })
	end

	for _, spec in ipairs(opts.jump_in_or_out) do
		vim.keymap.set("i", spec.key, function()
			local key = spec.key

			if not isDoubleTap(key) then
				vim.api.nvim_feedkeys(key, "n", false)
				return
			end

			jumpInOrOut(spec)
		end, { nowait = true, noremap = true })
	end
end

DoubleTap.setup = function(opts)
	CTX.config = dtConfig.setup_config(opts)

	setup_auto_commands(CTX.config)
end

return DoubleTap
