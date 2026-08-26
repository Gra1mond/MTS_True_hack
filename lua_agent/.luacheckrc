-- Luacheck configuration for MWS Octapi LowCode Lua scripts

-- Allow platform-specific globals
globals = {
    "wf",         -- workflow object (wf.vars.*, wf.initVariables.*)
    "_utils",     -- utility functions (_utils.array.new, etc.)
}

-- Allow setting globals that aren't declared with 'local'
-- (platform uses global assignments in scripts)
allow_defined = true

-- Standard: Lua 5.4 (closest to 5.5)
std = "lua54"

-- Ignore some warnings not relevant for LowCode scripts
ignore = {
    "211",  -- unused variable (scripts often define intermediate vars)
    "212",  -- unused argument
    "213",  -- unused loop variable
}

-- Max line length (relaxed for generated code)
max_line_length = 200
