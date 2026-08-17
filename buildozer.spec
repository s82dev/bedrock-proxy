[app]
title = Console Proxy
package.name = consoleproxy
package.domain = org.bedrock

source.dir = .
source.include_exts = py,html,json

version = 1.0
requirements = python3

orientation = portrait
fullscreen = 0

android.permissions = INTERNET, ACCESS_NETWORK_STATE
android.accept_sdk_license = True
android.features = 

android.api = 31
android.minapi = 21
android.ndk = 25b

p4a.bootstrap = webview
p4a.requirements = python3
