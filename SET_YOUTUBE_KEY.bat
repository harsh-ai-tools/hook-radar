@echo off
title Reel Radar: save YouTube key
echo.
echo  Paste your YouTube API key (from README: Scout setup) and press Enter.
echo  It stays hidden, and is saved only in your Windows user settings.
echo.
powershell -NoProfile -Command "$s = Read-Host 'Key' -AsSecureString; $k = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($s)).Trim(); if ($k -notmatch '^AIza[0-9A-Za-z_-]{35}$') { Write-Host 'That does not look like a YouTube API key (it starts with AIza and is 39 characters). Nothing saved.'; exit 1 }; [Environment]::SetEnvironmentVariable('YOUTUBE_API_KEY', $k, 'User'); Write-Host 'Saved! Now ask Claude: Scout competitors for my niche'"
echo.
pause
