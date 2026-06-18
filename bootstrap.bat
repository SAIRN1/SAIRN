@echo off
cd C:\Users\marsh\Documents\SAIRN
curl -H "Accept: application/vnd.github.raw" -o sync.bat https://api.github.com/repos/SAIRN1/SAIRN/contents/sync.bat
sync.bat
