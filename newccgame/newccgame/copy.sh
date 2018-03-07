#!/bin/sh

IP=$1

[ -z "$IP" ] && exit 0

scp ccgame_service.lua root@*.*.*.*.$IP:/usr/sbin/
scp lib/* root@*.*.*.*.$IP:/usr/lib/lua/turbo/ccgame/

echo "copy done"
