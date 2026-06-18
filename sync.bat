@echo off
cd C:\Users\marsh\Documents\SAIRN
curl -H "Accept: application/vnd.github.raw" -o stonedesk.html https://api.github.com/repos/SAIRN1/SAIRN/contents/stonedesk.html
curl -H "Accept: application/vnd.github.raw" -o stonedesk-intake.html https://api.github.com/repos/SAIRN1/SAIRN/contents/stonedesk-intake.html
npx vercel --prod
