#!/bin/sh

IP=$1

[ -z "$IP" ] && exit 0

scp game_service.lua root@*.*.*.*.$IP:/usr/sbin/
scp lib/* root@*.*.*.*.$IP:/usr/lib/lua/turbo/game/

echo "copy done"
