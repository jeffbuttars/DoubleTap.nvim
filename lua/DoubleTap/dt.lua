require("DoubleTap.globals")

local M = {}
M.last_key_ts = 0
M.last_key = ""
M.clean_lines = {""}
M.opts = {}

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

local catchJumpOutKey = function(key, capture)
	local now = vim.fn.reltimefloat(vim.fn.reltime())

  -- Store the line, before the key is typed
	local c = vim.api.nvim_win_get_cursor(0)
	local orig_line = vim.api.nvim_buf_get_lines(0, c[1] - 1, c[1], false)

	-- vim.print("capture: ", capture)
	-- vim.print("inString: ", canJumpOut(capture))

	if not (key == M.last_key) then
		-- Not a DoubleTap (yet), we don't care about this key
		M.last_key = key
    M.last_key_ts = now
    -- Before the line is altered, we'll consider this the 'clean' line
    M.clean_lines = orig_line

		vim.api.nvim_feedkeys(key, "n", false)

    vim.print("DoubleTap Just a single " .. key)
		return
	end

  -- In order to inspect the text, we have to return it to how it was
  -- before the characters we're typed and we detected a DoubleTap

  vim.print("Reseting to clean lines:")
  P(M.clean_lines)
	vim.api.nvim_buf_set_lines(0, c[1] - 1, c[1], false, M.clean_lines)
  -- vim.print("Reset? :")
  -- P(vim.api.nvim_buf_get_lines(0, c[1] - 1, c[1], false))

  -- Is this key in a context that allows a jump out?
  if not canJumpOut(capture) then

    -- restore the 'dirty' line
    vim.api.nvim_buf_set_lines(0, c[1] - 1, c[1], false, orig_line)
    M.last_key = key
    M.clean_lines = orig_line
		vim.api.nvim_feedkeys(key, "n", false)

    vim.print("DoubleTap not in context " .. key)
    return
  end

  -- The DoubleTap must be quick enough
	local delta = now - M.last_key_ts
  M.last_key_ts = now
  M.last_key = key
	vim.print("DoubleTap Catch key '" .. key .. "'delta:" .. delta .. " - " .. M.opts.threshold)

	if delta > M.opts.threshold then
		-- we don't care about this key, it's been to long
		M.last_key = key
    -- restore the 'dirty' line
    vim.api.nvim_buf_set_lines(0, c[1] - 1, c[1], false, orig_line)
    M.clean_lines = orig_line
		vim.api.nvim_feedkeys(key, "n", false)

    vim.print("DoubleTap to slow " .. key)
    -- To slow
		return
	end

	-- Going to take action
	M.last_key = ""

	-- local r, c = vim.api.nvim_win_get_cursor(0)
	vim.print("DoubleTap Caught pos :" .. c[1] .. " " .. c[2])

	-- vim.api.nvim_feedkeys(key, 'n', false)

	-- vim.print("DoubleTap Caught pos :" .. c)
	-- P(c)
	vim.print("DoubleTap Caught key :" .. key .. " " .. delta .. " - " .. M.opts.threshold)
	n_pos = vim.fn.searchpos(key, "nWz")
	P(n_pos)

	if n_pos[1] == 0 then
		-- Nothing found
		vim.print("DoubleTap no pos found")
    M.clean_lines = orig_line
    vim.api.nvim_buf_set_lines(0, c[1] - 1, c[1], false, orig_line)
		vim.api.nvim_feedkeys(key, "n", false)
		return
	end

	vim.print("Line to fix:" .. c[1] - 1 .. "," .. c[1])

	-- local updated_line = orig_line[1]:sub(1, c[2] - 1) .. orig_line[1]:sub(c[2] + 1)

	P(orig_line)
	P(M.clean_lines)

  -- Restore the 'clean' line
	vim.api.nvim_buf_set_lines(0, c[1] - 1, c[1], false, M.clean_lines)

	vim.print("DoubleTap set cursor")
	vim.print("DoubleTap get buf:" .. vim.api.nvim_win_get_buf(0))
	P(vim.api.nvim_win_get_buf(0))
	vim.api.nvim_win_set_cursor(0, { n_pos[1], n_pos[2] })

	-- vim.api.nvim_feedkeys(key, 'm', true)
	-- vim.api.nvim_feedkeys(key, "t", true)
end

M.setup = function(opts)
	if opts == nil then
		opts = {}
	end

	opts = {
		threshold = 0.4, -- In seconds
		jump_out = {
			{ key = ")" },
			{ key = "}" },
			{ key = "'", capture = { "string", "string.documentation" } },
			{ key = '"', capture = { "string", "string.documentation" } },
		},
		finish_line = {
			[";"] = { ";", trim = true },
		},
	}

	--  P(opts)

	-- table.merge(M, opts)
	M.opts = opts

	for _, val in ipairs(opts.jump_out) do
    -- vim.print("key: " .. val.key)
    -- vim.print("capture: ", val.capture)
		vim.keymap.set("i", val.key, function()
      local k = val.key
      local c = val.capture
			catchJumpOutKey(k, c)
		end)
	end

	-- P(M.opts)
	return opts
end

function M.sayHelloWorld()
	print("Hello World Again!!!")
end

vim.keymap.set("n", "<leader>pr", function()
	R("DoubleTap")
end, { noremap = true, desc = "Double Tap Reload" })

-- vim.keymap.set("n", "<leader>ptt", function()
-- 	require("DoubleTap").sayHelloWorld()
-- end, { noremap = true, desc = "Double Tap Dev run" })

return M
