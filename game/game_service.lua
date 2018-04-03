#!/usr/bin/lua
--[[
game service deamon program
Author: wenbin.pu
--]]

local uci = require 'luci.model.uci'
local fs = require "nixio.fs"
local LuciUtil = require("luci.util")
local LuciJson = require("luci.jsonc")
local XQCCGame = require("turbo.game.game_interface")
local math = require "math"


-- init uloop
local uloop = require "uloop"
uloop.init()

-- init ubus
local ubus = require "ubus"
local conn = ubus.connect()
if not conn then
    logger("init ubus failed.")
    os.exit(-1)
end

function get_connected_iplist()
    local cmd = "grep ASSURED /proc/net/nf_conntrack "
    local ps = cc_func_execl(cmd)
    if not ps then
        return nil, nil
    end

    local dstlist = {}
    local dstlist1 = {}

    for i, line in pairs(ps) do
        local _, _, dip, dport = string.find(line, "dst=([0-9.]+) sport=%d+ dport=(%d+)")
        if dip and dport then
            dstlist[dip] = dport
            table.insert(dstlist1,dip)
        end
    end

    --get game ips from route

    ps = cc_func_execl("route -e")

    if not ps then
        return nil,nil 
    end 

    local onlineIP, onlinePort

    local ipinfo = {}
    for i,line in pairs(ps) do         
        local isMatch = string.find(line,"l2tp%-vpn_cc")                                                                  
        if  isMatch then                                                                                                                    
            local ip = string.match(line,"%d+.%d+.%d+.%d+")
            table.insert(ipinfo,ip)
        end                                                
    end    

    local hit_ip = {}                                                                    
                                                                                         
    local hit_ip1 = {}

    for key,value in pairs(dstlist1) do
        for key, line in pairs(ipinfo) do
            if value == line then
                local hit_ip_port = line .. ":" .. dstlist[value]                        
                table.insert(hit_ip,hit_ip_port) 
                table.insert(hit_ip1,line)
            end
        end 
    end

    if next(hit_ip1) ~=nil then                                                            
                                                                                         
       onlineIP = hit_ip1[1]                                                             
       print("onlineIP:" .. onlineIP)                                                    
       onlinePort = dstlist[onlineIP]     
  end    

    return hit_ip, onlineIP, onlinePort
end




local para = { devicetype = 1101, version = '0.1', usertype = '2' }


-- timer for ping target periodly
local ping_timer
local online_ip_timer
--
local get_vpnserver_ip_timer
local get_vpnstate_timer
local start_turbo_game_timer

-- upload info to cc
local upload_log2cc_timer
local check_cc_gamelist_timer

-- update_LPG_iplist
local update_LPG_iplist_timer


GAME_INFO = {

    vpnStatus = 0, -- 0: not running, 1: running
    --ruleStatus = 0, -- 0: not loaded, 1: loaded done
    vpnInfo = nil,
    gameid = -1, -- -1: no game, >=0 : gameid
    regionid = 1,
    game_version = -1,
    leftPingCount = 0, -- invoke will fill leftPingCount = 5, ping will stop if leftPingCount = 0
    pingInfo = nil,
    data = {},
    online_ip = nil,
    online_port = nil,
    hit_ip = nil,
    
    ping_interval = 5 * 1000, -- 5s
    online_ip_interval = 3 * 60 * 1000, -- 3min
    uid = nil,
    passwd = nil,
    passwd_try_num = 3,
    vpn_server = nil,
    vpn_server_try_num = 3,
    get_vpnstate_interval = 1000,
    get_vpnstate_try_num = 10,
    upload_log2cc_interval = 5 * 60 * 1000, --30 min

    check_cc_gamelist_interval = 12 * 60 * 60 * 1000, --check ccgame iplist per 12 hours

    report_LPG_gameid_interval = 30 * 60 * 1000, -- per 30 min report LPG gameid

    --get_vpnserver_ip_timer_interval = 1 * 60 * 1000,

    get_vpnserver_ip_timer_interval = 0,

    mask_ip = "255.255.255.255",
    gateway_ip = "x.x.x.x",

    detect_ip = "x.x.x.x",                                                                               
    detect_port = 31414,

    -- ccgame upload info
    upload_log2cc = function(isAct)
        local data = para
        if not isAct then
            upload_log2cc_timer:set(GAME_INFO.upload_log2cc_interval)
            -- just return if turbo_ccgame not enabled or vpn not start
            if GAME_INFO.gameid < 0 or GAME_INFO.vpnStatus == 0 then
                return
            end
        end

        if GAME_INFO.vpnInfo or isAct then
            data.data = {}
            -- set if it's user trigger
            data.data.user = isAct
            data.data.vpnserver = GAME_INFO.vpn_server
            data.data.vpnstatus = GAME_INFO.vpnInfo
            data.data.qos = GAME_INFO.pingInfo
            data.data.online = (GAME_INFO.online_ip or '0') .. ':' .. (GAME_INFO.online_port or '0')

            data.data.hit_ip = GAME_INFO.hit_ip
            data.uid = GAME_INFO.uid
            data.data.passwd = ''

            local ret_v, ret_data = cc_func_ccserver_request(2, data)
        end
    end,


    -- init fun
    init = function()
        math.randomseed(os.time())

        print("read game id from /etc/config/turbo")

        local gameid = 355
        --local gameid = 200
        local regionid = 1
        local rule = 1

        GAME_INFO.gameid = gameid                                                                   
        GAME_INFO.regionid = regionid
        GAME_INFO.rule = 1
        GAME_INFO.ruleStatus = 0

        -- get passport
        GAME_INFO.get_passport()


        -- check VPN
        get_vpnstate_timer = uloop.timer(GAME_INFO.read_vpnstate)
        GAME_INFO.read_vpnstate()

        -- get vpn server
        get_vpnserver_ip_timer = uloop.timer(GAME_INFO.get_vpnserver)
        get_vpnserver_ip_timer:set(math.random(3000, 2 * 60 * 1000))

        -- ping worker
        ping_timer = uloop.timer(GAME_INFO.ping_worker)
        ping_timer:set(500)

        -- get online ip worker
        online_ip_timer = uloop.timer(GAME_INFO.online_ip_check)
        online_ip_timer:set(1000)

        -- upload log2cc
        upload_log2cc_timer = uloop.timer(GAME_INFO.upload_log2cc)
        upload_log2cc_timer:set(GAME_INFO.upload_log2cc_interval)


    --check_vpn_state
    check_vpn_state = function()
        GAME_INFO.get_vpnstate_try_num = 10
        get_vpnstate_timer:set(GAME_INFO.get_vpnstate_interval)
    end,

    -- read/update current VPN state
    read_vpnstate = function(not_repeat)
        print("fun: read_vpnstate")
        local vpnStateRet, vpnState = CCFUNC_GET_VPN_STATE()
        print(vpnStateRet .. LuciJson.encode(vpnState or {}))
        if vpnStateRet and vpnStateRet == 0 and vpnState and vpnState.ip ~= "" then
            GAME_INFO.vpnStatus = 1
            GAME_INFO.vpnInfo = vpnState
        else
            GAME_INFO.vpnStatus = 0
            GAME_INFO.vpnInfo = nil
        end

        -- vpn On, need check if it's true
        if not not_repeat then
            if GAME_INFO.vpnStatus == 1 then
                GAME_INFO.get_vpnstate_try_num = 0
            end
            if GAME_INFO.get_vpnstate_try_num > 0 then
                GAME_INFO.get_vpnstate_try_num = GAME_INFO.get_vpnstate_try_num - 1
                get_vpnstate_timer:set(GAME_INFO.get_vpnstate_interval)
            end
        end
    end,

    -- get password

    get_passport = function()

        print("get uid ,passwd")
        GAME_INFO.uid = "miwifi_test "
        GAME_INFO.passwd = "45eec17b0aefabf098816a1f738f5283"
    end,

    -- read vpn server from cc periodly
    get_vpnserver = function()
        print("fun: get_vpnserver")

        if not GAME_INFO.uid or not GAME_INFO.passwd then
            GAME_INFO.get_passport()
        end

        -- get vpn server info from cc
        para.data = {}
        para.uid = GAME_INFO.uid
        para.data.passwd = GAME_INFO.passwd
        para.time = os.time()

        local ip, info = ccgame_get_vpn_server(para)

        GAME_INFO.vpn_server = { ip = ip, info = info }

        local ping_value = {}

        if ip then
            GAME_INFO.get_vpnserver_ip_timer_interval = math.random(12 * 3600, 24 * 3600)
            get_vpnserver_ip_timer:set(GAME_INFO.get_vpnserver_ip_timer_interval * 1000)
            GAME_INFO.get_vpnserver_ip_timer_interval = 0
        else
            if GAME_INFO.get_vpnserver_ip_timer_interval <= 0 then
                GAME_INFO.get_vpnserver_ip_timer_interval = 1
                get_vpnserver_ip_timer:set(GAME_INFO.get_vpnserver_ip_timer_interval * 60 * 1000)
            elseif GAME_INFO.get_vpnserver_ip_timer_interval > 64 then
                GAME_INFO.get_vpnserver_ip_timer_interval = 0
            else
                GAME_INFO.get_vpnserver_ip_timer_interval = GAME_INFO.get_vpnserver_ip_timer_interval * 2
                get_vpnserver_ip_timer:set(GAME_INFO.get_vpnserver_ip_timer_interval * 60 * 1000)
            end
        end
    end,

    -- VPN status change callback
    update_vpn_status = function(onFlag)
        if not onFlag then
            -- vpn Off
            GAME_INFO.vpnStatus = 0
            GAME_INFO.vpnInfo = nil
        else
            GAME_INFO.read_vpnstate(true)
        end
    end,

    -- update game detect ip and port
    update_detect_target = function(ip, port, vpn)
        if ip and port and vpn then
            GAME_INFO.detect_ip = ip
            GAME_INFO.detect_port = tonumber(port)
            GAME_INFO.byvpn = vpn
        end
    end,

    -- check online_ip and online_port periodly
    online_ip_check = function(kill)
        print("fun: online_ip_check")
        if not kill then
            online_ip_timer:set(GAME_INFO.online_ip_interval)
        end
        if GAME_INFO.vpnStatus == 1 then
            
            if GAME_INFO.gameid > 0 then
                GAME_INFO.hit_ip, GAME_INFO.online_ip, GAME_INFO.online_port = get_connected_iplist()

                for key,value in pairs(GAME_INFO.hit_ip) do
                    print("GAME_INFO.hit_ip:" .. value)
                end

                if GAME_INFO.online_ip and GAME_INFO.online_port then
                    print("retrive current online ip/port : " .. (GAME_INFO.online_ip or 0) .. ":" .. (GAME_INFO.online_port or 0))
                end
            else
                GAME_INFO.online_ip, GAME_INFO.online_port = nil, nil
            end
           
           --GAME_INFO.online_ip, GAME_INFO.online_port = "149.202.202.198",11005
        end
    end,

    --get ping cmd
    get_ping_cmd = function()
        local targetIP, targetPort
        if GAME_INFO.online_ip and GAME_INFO.online_port then
            targetIP = GAME_INFO.online_ip
            targetPort = GAME_INFO.online_port
        else
            targetIP = GAME_INFO.detect_ip
            targetPort = GAME_INFO.detect_port
        end

        --print("detected ip:" .. GAME_INFO.detect_ip .. ':' .. GAME_INFO.detect_port)
        --local cmd = "tcpping " .. "-c 2 " .. targetIP .. " -p " ..targetPort

        local cmd = "ping " .. "-c 2 " .. targetIP 
        return cmd, targetIP, targetPort
    end,

    -- try to ping game dst ip:port periodly, note: better larger than 4second
    ping_ip = function()

        local cmd, tip, tport = GAME_INFO.get_ping_cmd()
        if GAME_INFO.vpnStatus and GAME_INFO.vpnStatus == 1 then
            cmd = cmd .. " -I l2tp-vpn_cc"
        end
        cmd = cmd .. " 2>/dev/null"

        -- ICMP, 4 sent, 4 received, 0% lost, avg=1.39 ms
        local ps = cc_func_exec(cmd)

        local info = {}

        if not ps then
            return nil
        else
            local pingState = {}
            --type=ICMP-0,seq=0,ttl=64,ts=0.42 ms, ts2=0.32 ms                     
            local isMatch = string.find(ps,"ttl")      
                            
            if not isMatch then                                                    
                pingState.ttl = 9999                                               
            else                                                                   
               pingState.ttl = string.match(ps, "ttl=(%d+)")                      
            end                                                                    
                                                                                       
                                                                                       
            --ICMP, 4 sent, 4 received, 0 lost, avg=0.34 ms                        
                                                                                 
            pingState.lose = string.match(ps, "(%d+)%%%s+packet ")
                                                                      
            local st = string.find(ps,"round%-trip") 

            if not st then                                                                       
                pingState.rtt = 9999                                                             
            else                                                                                 
                local eb = string.find(ps,"=",st)                                                
                local abc_sub = string.sub(ps,eb+1,#ps)                                          
                local st_1 = string.find(abc_sub,"/")                                                                        
                local abc_sub_1 = string.sub(abc_sub,st_1+1,#abc_sub)                                                        
                local st_2 = string.find(abc_sub_1,"/")                                                                      
                pingState.rtt = string.sub(abc_sub_1,1,st_2-1)                                                               
                                                                                                                                 
            end                                                                                                               
                                                                                                                                 
            table.insert(info, pingState) 
        end 

        return info
    end,

    -- fill leftPingCount
    fill_leftPingCount = function()
        GAME_INFO.leftPingCount = 5
    end,

    -- check if need Ping again
    check_leftPingCount = function()
        GAME_INFO.leftPingCount = GAME_INFO.leftPingCount - 1
        if GAME_INFO.leftPingCount < 0 then
            --clear pingInfo because it's no use
            --GAME_INFO.pingInfo = nil
            return false
        end
        return true
    end,

    -- ping loop worker
    ping_worker = function()
        print("fun: ping_worker")
        ping_timer:set(GAME_INFO.ping_interval)
        if GAME_INFO.vpnStatus == 0 then
            return
        end
        --[[
        if GAME_INFO.check_leftPingCount() then
            GAME_INFO.pingInfo = GAME_INFO.ping_ip(GAME_INFO.byvpn)
            --logger(LuciJson.encode(GAME_INFO.pingInfo or {}))
        end
       --]]
       for i=1,5,1 do
           GAME_INFO.pingInfo = GAME_INFO.ping_ip()
           break
       end
    end,

    
    off_vpn = function()
        stop_vpn_config()
        GAME_INFO.vpnStatus = 0
        return 0
    end,

    --
    on_game = function(gameid, regionid)
        print("fun: on_game(" .. gameid .. "," .. regionid .. ") +++++++++++++++++")
        local ret_code = 0

        -- report vpn info to cc
        GAME_INFO.upload_log2cc(true)

        if GAME_INFO.vpnStatus ~= 1 then
            para.time = os.time()
            para.cmdid = 2
            para.uid = GAME_INFO.uid
            para.data = {
                passwd = GAME_INFO.passwd
            }

            if not GAME_INFO.vpn_server or not GAME_INFO.vpn_server.ip then
                print("start1 get vpn_server")

                GAME_INFO.get_vpnserver()
                if not GAME_INFO.vpn_server.ip then
                    GAME_INFO.off_vpn()
                    print("get vpn-server failed......")
                    return
                end
            end

            -- start vpn

            --print("start vpn" .. ",uid:" .. GAME_INFO.uid .. ",passwd:" .. GAME_INFO.passwd .. ",vpn_ip:" .. GAME_INFO.vpn_server.ip)
        
            local ret_code = start_vpn_config(GAME_INFO.uid, GAME_INFO.passwd, GAME_INFO.vpn_server.ip)

            --vpnOn(GAME_INFO.uid, GAME_INFO.passwd, GAME_INFO.vpn_server.ip)
            --vpnOn(GAME_INFO.uid, GAME_INFO.passwd, "223.202.201.205")

            if ret_code ~= 0 then
                GAME_INFO.off_vpn()
                print("set vpn config and start vpn failed.....")
                return
            end

            -- checking timer to update VPN status
            GAME_INFO.check_vpn_state()

        end

        -- download gameinfo and load gameinfo now
        if ret_code == 0 then
            para.time = os.time()
            para.cmdid = 5
            para.uid = GAME_INFO.uid
            para.data = { gameid = GAME_INFO.gameid, regionid = GAME_INFO.regionid }

            --para.data.vpn_server = { ip = GAME_INFO.vpn_server.ip,info = GAME_INFO.vpn_server.ip.info}
            

            

            local code, info = game_speedup_start(para)
            local ip_ret = string.split(info,",")                                
                                                                                  
            local ret_data3 = {}                                                      
                                                                                  
            for key, value in pairs(ip_ret) do                                        
                local ip = string.match(value,"%d+.%d+.%d+.%d+")      

                table.insert(ret_data3,ip)                                            
                                                                                  
            end    

            print("code:" .. code)

            if code == 0 then
                -- apply ruleStatus 1stly
                GAME_INFO.update_gameid(gameid, regionid, 1)
                --code = apply_route_new_game(ipset_name, info)
                print("add route : apply_route_new_game")
                apply_route_new_game(ret_data3,GAME_INFO.mask_ip,GAME_INFO.gateway_ip)

                -- just del old conntrack to enforce create new conntrack
                GAME_INFO.online_ip_check(1)
            end
        end
    end,
}


--try to start ccgame service
local function ccgame_service()
    print("ccgame service loading.....")
    GAME_INFO.init()
    uloop.run()
end

-- main
ccgame_service()













