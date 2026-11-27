#!/bin/bash
# HookRadar: save your YouTube API key for Scout (hidden input, saved in ~/.zshrc only).
echo "Paste your YouTube API key (from README: Scout setup) and press Enter. It stays hidden."
read -rs KEY; echo
if [[ ! "$KEY" =~ ^AIza[0-9A-Za-z_-]{35}$ ]]; then echo "That does not look like a YouTube API key (starts with AIza, 39 characters). Nothing saved."; read -n1 -p "Press any key..."; exit 1; fi
touch ~/.zshrc; grep -v '^export YOUTUBE_API_KEY=' ~/.zshrc > ~/.zshrc.rr && mv ~/.zshrc.rr ~/.zshrc
echo "export YOUTUBE_API_KEY=\"$KEY\"" >> ~/.zshrc
launchctl setenv YOUTUBE_API_KEY "$KEY" 2>/dev/null
echo "Saved! Reopen Claude, then ask: Scout competitors for my niche"; read -n1 -p "Press any key..."
