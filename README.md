# lurk-bot-slayer
 OBS Script that uses your StreamElements bot to ban outside bots from your Twitch stream.
 
 It checks twitchinsights.net's list of active bots, and bans any of them that show up in your chat, ignoring the ones modded in your channel.
 
 Requires your StreamElements JWT Token to use your chat and ban bots. This token can be found at https://streamelements.com/dashboard/account/channels under "Show secrets".
 
 Even without this token, it can still identify and name lurker bots in the script logs, but bans will not actually work.
 
## To activate in OBS:
* Go to Tools->Scripts
* Press + to find and add lurkbotslayer.py
* Copy your StreamElements JWT Token from the page mentioned above
* Paste it into its own file on your computer, ensuring the file is empty except for the token, and save
* Click "Browse" next to "SE token file" in the OBS Scripts window to open that file
* Check "Activate" to begin monitoring for bots

## Whitelisting names:
 Bots that are already moderators of your channel are already ignored by this script. However, if there's a known bot that you don't want to mod but don't want to ban, you can use the script's whitelist feature to keep them in your chat.
 
 The whitelist should be a file with one account name on each line, such as the one shown below.
```
memebot1
toomanytabsman
```
 Renaming or deleting the whitelist file will disconnect it from the script.