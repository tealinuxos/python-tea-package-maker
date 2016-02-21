# Tea Package Maker
Create a single file installer for linux ubuntu and debian derivatives software for offline usage.
Currently developed for [TeaLinuxOS](http://tealinuxos.org)

## Requiremets
1. python-apt >= 0.9.3.5
2. python-gobject >= 3.12

## how to use:
You will need a 'status' file. It can be obtained from /var/lib/dpkg/status.
Tt can be your own OS or your friend's OS if you want to provide offline installer for him/her.

Open the app, select the 'status' file, input a valid package name, click 'Build'.
