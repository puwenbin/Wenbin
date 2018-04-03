#!/usr/bin/lua

local fs = require "nixio.fs"
local json = require("luci.jsonc")
require "turbo.game.iface_game"


local string, tonumber, pcall, type, table = string, tonumber, pcall, type, table

local cc_var_vpnserver = "*.*.*.*"

local cc_var_serverurl = "http://x.x.x.x/"
local cc_var_conntrack_file = "/proc/net/nf_conntrack"
local cc_var_version = "0.1"

-- global function

function ip2str(hex_ip)
    if not hex_ip then return "" end
    return turbo.ip2string(tonumber(hex_ip, 16))
end

function cc_func_get_serverurl()
    return cc_var_serverurl
end

function cc_func_exec_c(string)
    local res = io.popen(string)
    local tmpstr = res:read("*all")
    res:close()
    return string.match(tmpstr, "(.+)%c$") or ""
end

function cc_func_exec(command)
    local pp = io.popen(command)
    local data = pp:read("*a")
    pp:close()

    return data
end

function cc_func_execl(command)
    local pp = io.popen(command)
    local line = ""
    local data = {}

    while true do
        line = pp:read()
        if (line == nil) then break end
        data[#data + 1] = line
    end
    pp:close()

    return data
end

function cc_func_getpwd()
    local curr_dir = cc_func_exec_c("pwd")
    if not curr_dir then
        return false
    else
        return curr_dir
    end
end


split = function(str, pat, max, regex)
    pat = pat or "\n"
    max = max or #str

    local t = {}
    local c = 1

    if #str == 0 then
        return { "" }
    end

    if #pat == 0 then
        return nil
    end

    if max == 0 then
        return str
    end

    repeat
        local s, e = str:find(pat, c, not regex)
        max = max - 1
        if s and max < 0 then
            t[#t + 1] = str:sub(c)
        else
            t[#t + 1] = str:sub(c, s and s - 1)
        end
        c = e and e + 1 or #str + 1
    until not s or max < 0

    return t
end

trim = function(str)
    return str:gsub("^%s*(.-)%s*$", "%1")
end


-- ccgame function
function CCFUNC_GET_VPN_STATE()
    local cmd = getVpnStatCmd()
    --ifconfig l2tp-ccgame 2>/dev/null
    local res = {}
    local ps = cc_func_execl(cmd)
    if not ps then
        return -1
    end

    local isMatch = false
    for i, line in pairs(ps) do
        if i == 1 then
            --i:1, l2tp-ccgame Link encap:Point-to-Point Protocol
            isMatch = string.find(line, "ppp0")
            if not isMatch then
                break
            end
        elseif i == 2 then
            --i:2, line:          inet addr:10.11.0.10  P-t-P:10.10.0.1  Mask:255.255.255.255
            res.ip, res.ptp, res.mask = string.match(line, "inet addr:(%d+.%d+.%d+.%d+)%s+P%-t%-P:(%d+.%d+.%d+.%d+)%s+Mask:(%d+.%d+.%d+.%d+)")
        elseif i == 3 then
            --i:3, line:          UP POINTOPOINT RUNNING NOARP MULTICAST  MTU:1404  Metric:1
            res.mtu, res.metric = string.match(line, "MTU:(%w+)%s+Metric:(%w+)")
        elseif i == 4 then
            --i:4, line:          RX packets:114 errors:0 dropped:0 overruns:0 frame:0
            res.rx_packets, res.rx_errors, res.rx_dropped, res.rx_overruns, res.rx_frame = string.match(line, "packets:(%d+)%s+errors:(%d+)%s+dropped:(%d+)%s+overruns:(%d+)%s+frame:(%d+)")
        elseif i == 5 then
            --i:5, line:          TX packets:115 errors:0 dropped:0 overruns:0 carrier:0
            res.tx_packets, res.tx_errors, res.tx_dropped, res.tx_overruns, res.tx_carrier = string.match(line, "packets:(%d+)%s+errors:(%d+)%s+dropped:(%d+)%s+overruns:(%d+)%s+carrier:(%d+)")
        elseif i == 6 then
            --i:6, line:          collisions:0 txqueuelen:3
            res.collisions, res.txqueuelen = string.match(line, "collisions:(%d+)%s+txqueuelen:(%d+)")
        elseif i == 7 then
            --i:7, line:           RX bytes:830 (830.0 B)  TX bytes:844 (844.0 B)
            res.rx_bytes, res.tx_bytes = string.match(line, "bytes:(%d+).+:(%d+)")
        end
    end

    local vpn_state = {}
    if isMatch then
        vpn_state.status = 1
        vpn_state.ip = res.ip and res.ip or ""
        vpn_state.rx = res.rx_bytes and res.rx_bytes or "-1"
        vpn_state.tx = res.tx_bytes and res.tx_bytes or "-1"

        return 0, vpn_state
    else
        vpn_state.status = 0
        return -2, vpn_state
    end
end

function cc_ping_vpn_list(ips)
    if not ips then
        return nil
    end
    local count = 4

   print("start to ping vpn_list")

    local res = {}
    for i, v in pairs(ips) do
        local myip, myport = string.match(v, "(%d+.%d+.%d+.%d+):(%d+)")
        if not myip or not myport then
            myip = string.match(v, "(%d+.%d+.%d+.%d+)")
            if myip then
                myport = 0
            else
                myip = nil
                myport = nil
            end
        end


        if myip and myport then
            local cmd = ""
            if byvpn then
                cmd = "ping -c " .. "2 " .. myip .. " -I l2tp-vpn_cc"
                --print("ping cmd:" .. cmd)
            else
                cmd = "ping -c " .. "2 " .. myip
                --print(cmd)
            end
            --print("cc_func_ping_state before cmd:" .. cmd .. "$$")

            local ps = cc_func_exec(cmd)
            if not ps then
                --res[myip]=nil
            else

                --print("cc_func_ping_state cmd:" .. cmd .. ", ret:" .. ps .. "$$")

                local pingState = {}

                --type=ICMP-0,seq=0,ttl=64,ts=0.42 ms, ts2=0.32 ms
                --local ttl_value = string.match(ps, "ttl=(%d+)")
                local isMatch = string.find(ps,"ttl")
                if not isMatch then
                    pingState.ttl = 9999
                else
                    pingState.ttl = string.match(ps, "ttl=(%d+)") 
                end

                pingState.lose = string.match(ps, "(%d+)%%%s+packet ")

                --print ("vpn_ip:" .. myip .. ", ttl:" .. pingState.ttl .. ", lose:" .. pingState.lose) 

                
                local st = string.find(ps,"round%-trip")

                if not st then
                    pingState.rtt = 9999
                else
                    local eb = string.find(ps,"=",st)
                    local abc_sub = string.sub(ps,eb+1,#ps)
                    --print("adc_sub:" .. abc_sub)           
                    local st_1 = string.find(abc_sub,"/")
                    local abc_sub_1 = string.sub(abc_sub,st_1+1,#abc_sub)
                    local st_2 = string.find(abc_sub_1,"/")              
                    pingState.rtt = string.sub(abc_sub_1,1,st_2-1)

               end

                --print ("vpn_ip:" .. myip .. ", ttl:" .. pingState.ttl .. ", lose:" .. pingState.lose .. ",rtt:" .. pingState.rtt)

                if tonumber(myport) ~= 0 then
                    pingState.ip = myip .. ":" .. myport
                else
                    pingState.ip = myip
                end
                table.insert(res, pingState)
            end
        end
    end

    --print(json.encode(res))
    return res
end


function cc_func_ccserver_request(cmdid, para, refCmd)
    if not cmdid or not para then
        return -10010
    end

    local cmdhead = {}
    cmdhead.cmdid = cmdid
    cmdhead.uid = para.uid and para.uid or "-1"
    cmdhead.version = para.version and para.version or "-1"
    cmdhead.devicetype = para.devicetype and para.devicetype or "-1"
    cmdhead.usertype = para.usertype and para.usertype or "-1"
    cmdhead.time = para.time
    cmdhead.data = para.data

    local cmd = string.format('curl -H "Content-type: application/json" -X POST --data \'%s\' %s  2>/dev/null ', json.encode(cmdhead), cc_func_get_serverurl())
    print("cc_func_ccserver_request cmd " .. cmd) 

    local retCurl, curl_ret = pcall(cc_func_exec, cmd)
    if not retCurl or not curl_ret then
        return -11006
    end

    if cmdid == 7 then

        print("cc_func_ccserver_request curl success:" ..curl_ret)
        return 0, curl_ret
    end

    curl_ret = trim(curl_ret)
    if not retCurl or not curl_ret or curl_ret == "" then
        --print("cc_func_ccserver_request curl faild:" ..curl_ret)
        return -11006
    end

    print("cc_func_ccserver_request curl success:" ..curl_ret)

    local ret
    local curl_ret_sturct = { code = 0 }

    ret, curl_ret_struct = pcall(function() return json.decode(curl_ret) end)

    if not ret or not curl_ret_struct then
        return -11007
    end

    if not curl_ret_struct.code then
        return -11007
    end

    if curl_ret_struct.code ~= 0 then
        return curl_ret_struct.code
    end

    return 0, curl_ret_struct.data
end

function cc_func_get_vpn_server_ip(cmd, vpnlistInfo,gameid,regionid)

    local data = cmd
    if vpnlistInfo then
        if not cmd.data then
            cmd.data = {}
        end
        cmd.data.info = vpnlistInfo
        cmd.data.gameid = gameid
        cmd.data.regionid = regionid
    end
    local ret_v, ret_data = cc_func_ccserver_request(3, cmd)
    if ret_v ~= 0 then
        --print("cc_func_get_vpn_server_ip cc_func_ccserver_request return:" .. ret_v .. ".")
        return nil
    end

    if not ret_data or not ret_data.serverip then
        print("cc_func_get_vpn_server_ip cc_func_ccserver_request data is empty.")
        return nil
    end

    return ret_data.serverip
end

function cc_func_get_vpn_server_list(cmd)

    print("get vpn_serevr_list from cc_server")
    local data = cmd
    local ret_v, ret_data = cc_func_ccserver_request(5, data)

    --print("ret_v" .. ret_v)
    if ret_v ~= 0 then
        print("cc_func_get_vpn_server_list cc_func_ccserver_request return:" .. ret_v .. ".")
        return nil
    end

    if not ret_data or not ret_data.iplist then
        print("cc_func_get_vpn_server_list cc_func_ccserver_request data is empty.") 
        return nil
    end

    return ret_data.iplist
end
