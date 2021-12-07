# lurk-bot-slayer
 OBS Script that uses your StreamElements bot to ban outside bots from your Twitch stream.
 
 Requires your StreamElements JWT Token to use your chat and ban bots. This token can be found at https://streamelements.com/dashboard/account/channels under "Show secrets".
 
 Even without this token, it can still identify and name lurker bots in the script logs, but bans will not actually work.
 
 To activate in OBS:
* Go to Tools->Scripts
* Press + to find and add lurkbotslayer.py
* Copy your StreamElements JWT Token from the page mentioned above
* Paste it into its own file on your computer, ensuring the file is empty except for the token, and save
* Click "Browse" next to "SE token file" in the OBS Scripts window to open that file
* Check "Activate" to begin monitoring for bots
 