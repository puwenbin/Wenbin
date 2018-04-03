#!/usr/bin/lua
module("turbo.ccgame.ccgame_interface", package.seeall)

local LuciJson = require("luci.jsonc")
local LuciUtil = require("luci.util")
local string, tonumber, pcall, type, table = string, tonumber, pcall, type, table

require "turbo.game.game"
require "turbo.game.game_util"
