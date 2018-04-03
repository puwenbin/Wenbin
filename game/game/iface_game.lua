#!/usr/bin/lua

--add vpn 
function start_vpn_config(user, passwd, server_ip)

     print("stat vpn")

     if not user then
        return -11101
    end

    if not passwd then
        return -11102
    end

    if not server_ip then
        return -11103
    end
 
    x = io.open("/etc/xl2tpd/xl2tpd.conf", "r")
    if x then
        x:close()
        os.execute("sed -i '/name/{s/=.*/= " .. user .. "/}' /etc/xl2tpd/xl2tpd.conf")
        os.execute("sed -i '/lns/{s/=.*/= " .. server_ip .. "/}' /etc/xl2tpd/xl2tpd.conf")
        p = io.open("/etc/ppp/options.xl2tpd", "r")
        if p then
            p:close()
            os.execute("sed -i '/user/{s/\".*\"/\"" .. user .. "\"/}' /etc/ppp/options.xl2tpd")
            os.execute("sed -i '/password/{s/\".*\"/\"" .. passwd .. "\"/}' /etc/ppp/options.xl2tpd")
            os.execute("xl2tpd -c /etc/xl2tpd/xl2tpd.conf; sleep 2;echo 'c ccvpn' >/var/run/xl2tpd/l2tp-control; sleep 1")
            --os.execute("iptables -t nat -L POSTROUTING | grep MASQUERADE | grep -v grep || iptables -t nat -A POSTROUTING -j MASQUERADE")
        end
    end

   return 0

end


--del vpn
 function stop_vpn_config()
    os.execute("echo 'd ccvpn' >/var/run/xl2tpd/l2tp-control; sleep 3;killall xl2tpd")
    --os.execute("iptables -t nat -L POSTROUTING | grep MASQUERADE|grep -v grep && iptables -t nat -D POSTROUTING -j MASQUERADE")
end


--get vpn stat command

function getVpnStatCmd()
    local cmd = "ifconfig " .. "ppp0"
    return cmd;
end


--Route add
function addRoute(dst_ip,mask_ip,gateway_ip)
    os.execute("route add -net " .. dst_ip .. " " .. "netmask " .. mask_ip .. " " .. "gw " .. gateway_ip)
end



--Route del
function delRoute(dst_ip,mask_ip)
    os.execute("route del -net " .. dst_ip .. "netmask " .. mask_ip)
end




