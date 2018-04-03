#!/usr/bin/lua

local json = require("luci.json")
local LuciUtil = require("luci.util")
require("turbo.game.game_util")

local string, tonumber, pcall, type, table = string, tonumber, pcall, type, table

local function valid_input(cmd)
    return 0
end

function ccgame_get_vpn_server(cmd)
    local vpnlistInfo = {}

    local vpnlist = cc_func_get_vpn_server_list(cmd)
    --print("**got vpnlist: " .. (vpnlist or "[]"))  

   local gameid = GAME_INFO.gameid                                                                                           
   local regionid = GAME_INFO.regionid 

   
    
    if vpnlist then
        local it = split(vpnlist, ',')

        if it then
            vpnlistInfo = cc_ping_vpn_list(it)
        end
    else
        return nil, nil
    end

    serverip = cc_func_get_vpn_server_ip(cmd, vpnlistInfo,gameid,regionid)
    return serverip, vpnlistInfo
end


function game_speedup_start(cmd)
    print("game_speedup_start starting ")
    local code = valid_input(cmd)
    if (code ~= 0) then
        return code
    end

    if not cmd.data.gameid or not cmd.data.regionid then
        return -10010
    end

    local ret_v, ret_data = cc_func_ccserver_request(7, cmd)
    print(ret_v)
    if ret_v ~= 0 or not ret_data then
        return -10010
    end

    return 0, ret_data
end


function apply_route_new_game(dst_ip,mask_ip,gateway_ip)
    print("route add new game")
    for key, value in pairs(dst_ip) do  

        print("ip:" .. value)
        addRoute(value,mask_ip,gateway_ip)
        print("route add sucess")
    end
end






