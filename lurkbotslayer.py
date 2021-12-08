import requests
import keyring
import os
import sched
import time
import obspython as obs


# OBS Script params
threshold = 0
keep_active = False
list_refresh_minutes = 180
chat_refresh_seconds = 30
whitelist_path = ''

# Auto-configured parameters
twitch_user = ''
default_ban_reason = "on the bot list"
ban_interval_seconds = 1

# StreamElements relevant data
service_id = "LurkBotSlayer"
twitch_user_id = ''
se_api_url = "https://api.streamelements.com/kappa/v2/"
acc = "application/json"

# Working Lists
activeBotList = {}
ignoreList = set()
ban_queue = []

botListScheduler = sched.scheduler(time.time, time.sleep)
chatListScheduler = sched.scheduler(time.time, time.sleep)

"""SECTION: PRIMARY ACTIONS"""


def start_clearing_bots():
    obs.timer_add(fulfill_ban, ban_interval_seconds * 1000)


def start_ban_checks():
    ban_check()
    obs.timer_add(ban_check, chat_refresh_seconds * 1000)


def decide_to_activate():
    global keep_active
    global chat_refresh_seconds
    global botListScheduler
    global chatListScheduler
    if keep_active:
        # start periodically pulling info from twitch chat and twitch insights
        refresh_stored_lists()
        obs.timer_add(refresh_stored_lists, list_refresh_minutes * 60000)
        start_clearing_bots()

        print("Activated bot checking.")
        print(f"Checking bots every {list_refresh_minutes} min, chat every {chat_refresh_seconds} sec")
    else:
        # cancel timers
        obs.timer_remove(refresh_stored_lists)
        obs.timer_remove(ban_check)
        obs.timer_remove(fulfill_ban)
        print("Bot checking is off.")


def fulfill_ban():
    if len(ban_queue) > 0:
        # only do bans at certain intervals to avoid overdoing API rates
        ban_user(ban_queue[0], default_ban_reason)
        ignoreList.add(ban_queue[0])
        print(f"Banned {ban_queue[0]}.")
        ban_queue.pop(0)
    else:
        # stop clearing bans and start looking for more bots
        obs.timer_remove(fulfill_ban)
        start_ban_checks()


def ban_check():
    global activeBotList
    global ignoreList
    global threshold

    chatters = get_chatters()
    # get all chatters also in the bot list
    to_ban = [viewer for viewer in chatters if viewer in activeBotList]
    # filter by amount of other channels they're in
    if threshold > 0:
        to_ban = [viewer for viewer in to_ban if activeBotList[viewer] >= threshold]
    # filter those already banned
    to_ban = [viewer for viewer in to_ban if viewer not in ignoreList]

    if len(to_ban) > 0:
        print(f'Found {len(to_ban)} bots in the {twitch_user} stream. Clearing...')
        print(to_ban)
        ban_queue.extend(to_ban)
        obs.timer_remove(ban_check)
        start_clearing_bots()


"""SECTION: REQUEST ACTIONS"""


def find_obs_twitch_name():
    # TODO is there a safer way to use twitch profile data?
    # If we don't touch appdata directly that'd be great
    profile = obs.obs_frontend_get_current_profile()
    path = profile.replace(' ', '_').replace('-', '')
    path = f'{os.getenv("APPDATA")}\\obs-studio\\basic\\profiles\\{path}\\basic.ini'

    firstLine = '[Twitch]\n'
    nameParam = "Name"
    foundTwitch = False

    foundName = ''

    with open(path, 'r') as file:
        li = ''
        while li is not None:
            li = file.readline()
            if li == firstLine:
                foundTwitch = True
            if foundTwitch and ('=' in li):
                prop, val = li[:-1].split('=', 1)
                if prop == nameParam:
                    foundName = val
                    li = None

    return foundName


def refresh_stored_lists():
    refresh_active_bots()
    # TODO This requires mod authority
    # currentBanList = get_banlist()
    print('Refreshed botlist.')


def refresh_active_bots():
    global activeBotList
    botListPage = 'https://api.twitchinsights.net/v1/bots/online'
    r = requests.get(botListPage)
    data = r.json()
    botDict = {}
    if 'bots' in data:
        # add name and active channel count to dict
        for val in data['bots']:
            botDict[val[0]] = val[1]
    activeBotList = botDict
    return botDict


def get_chatters():
    chatUserPage = f'https://tmi.twitch.tv/group/user/{twitch_user}/chatters'
    r = requests.get(chatUserPage)
    data = r.json()
    chatterSet = []
    if 'chatters' in data and 'viewers' in data['chatters']:
        chatterSet = data['chatters']['viewers']
    return chatterSet


def get_ban_list():
    # TODO this requires mod authority
    bannedUserPage = f'https://api.twitch.tv/{twitch_user}/moderation/banned'
    r = requests.get(bannedUserPage)
    data = r.json()
    return data


def get_whitelist_file_items(path:str):
    # Read whitelist as one bot name on each line
    if os.path.exists(path):
        with open(path, 'r') as file:
            return [name.strip() for name in file.readlines() if len(name.strip()) > 0]
    return []

"""Section: STREAMELEMENTS ACTIONS"""


def set_auth_token(token):
    keyring.set_password(service_id, service_id, token)


def has_auth_token():
    return keyring.get_password(service_id, service_id) is not None


def get_users_id(target: str):
    destination = f"{se_api_url}channels/{target}"
    data = {
        "channel": target,
        "Content-Type": acc,
        "Accept": acc,
    }
    p = requests.get(destination, data=data)
    response = p.json()

    if "_id" in response.keys():
        return response['_id']

    return ''


def bot_say(message: str):
    destination = f"{se_api_url}bot/{twitch_user_id}/say"
    token = keyring.get_password(service_id, service_id)
    if token is None:
        return False
    fullToken = f"Bearer {token}"
    head = {
        "Authorization": fullToken,
    }
    data = {
        "Authorization": fullToken,
        "channel": twitch_user_id,
        "message": message,
        "Content-Type": acc,
        "Accept": acc,
    }
    p = requests.post(destination, data=data, headers=head)
    return p


def ban_user(user, reason=None):
    message = f"/ban {user}"
    if reason is not None:
        message = f'{message} {reason}'
    p = bot_say(message)
    return p


def set_active_user(user: str):
    global twitch_user
    global twitch_user_id
    twitch_user = user
    twitch_user_id = get_users_id(twitch_user)
    return len(twitch_user_id) > 0


"""Section: OBS SCRIPT FUNCTIONS"""


def script_load(settings=None):
    global twitch_user
    print("Loading user info...")
    twitch_user = find_obs_twitch_name()
    if set_active_user(twitch_user):
        print(f'Hello, {twitch_user}!')
    else:
        print('Failed to get your twitch user data.')


def script_update(settings):
    global threshold
    global chat_refresh_seconds
    global list_refresh_minutes
    global keep_active
    global whitelist_path
    global ignoreList
    threshold = obs.obs_data_get_int(settings, 'threshold')

    new_chat_refresh_seconds = obs.obs_data_get_int(settings, 'chatters_seconds')
    new_list_refresh_minutes = obs.obs_data_get_int(settings, 'list_minutes')
    new_keep_active = obs.obs_data_get_bool(settings, 'keep_active')
    new_whitelist_path = obs.obs_data_get_string(settings, "nonmod_whitelist")

    needs_reboot = new_keep_active and (
        new_chat_refresh_seconds != chat_refresh_seconds or
        new_list_refresh_minutes != list_refresh_minutes
    )

    chat_refresh_seconds = new_chat_refresh_seconds
    list_refresh_minutes = new_list_refresh_minutes

    se_path = obs.obs_data_get_string(settings, "se_token")
    if len(se_path) > 0:
        with open(se_path, 'r') as file:
            set_auth_token(file.read())
    else:
        print("No token found. Can't post messages as StreamElements.")

    if keep_active != new_keep_active:
        keep_active = new_keep_active
        decide_to_activate()
    elif needs_reboot:
        keep_active = False
        decide_to_activate()
        keep_active = True
        decide_to_activate()

    if not os.path.exists(new_whitelist_path):
        obs.obs_data_set_string(settings, "nonmod_whitelist", '')
    if whitelist_path != new_whitelist_path:
        # remove old whitelist stuff from ignore list and add new stuff
        if len(whitelist_path) > 0:
            old_bots = get_whitelist_file_items(whitelist_path)
            ignoreList = ignoreList - set(old_bots)
        if len(new_whitelist_path) > 0:
            new_bots = get_whitelist_file_items(new_whitelist_path)
            ignoreList = ignoreList.union(new_bots)

        whitelist_path = new_whitelist_path


def script_properties():
    props = obs.obs_properties_create()
    obs.obs_properties_add_path(props, "se_token",
                                "SE token file",
                                obs.OBS_PATH_FILE, '*', None)

    obs.obs_properties_add_path(props, "nonmod_whitelist",
                                "Non-Mod Bot Whitelist",
                                obs.OBS_PATH_FILE, '*', None)

    obs.obs_properties_add_int(props, "threshold",
                               "Min Simultaneous Viewers to Ban", 0, 999999, 1)

    obs.obs_properties_add_int(props, "list_minutes",
                               "Botlist Refresh Rate (min)", 1, 999999, 1)
    obs.obs_properties_add_int(props, "chatters_seconds",
                               "Chatter Refresh Rate (sec)", 1, 999999, 1)

    obs.obs_properties_add_bool(props, "keep_active", "Activate")
    return props


def script_defaults(settings):
    obs.obs_data_set_default_int(settings, 'threshold', 100)
    obs.obs_data_set_default_int(settings, 'list_minutes', 180)
    obs.obs_data_set_default_int(settings, 'chatters_seconds', 30)


def script_description():
    return "Finds other people's bots in your chat, and " \
           "make StreamElements ban them automatically. -Sijiba"\
           "\n\nRequires your StreamElements JWT Token to use your chat. "\
           "This can be found at "\
           "https://streamelements.com/dashboard/account/channels "\
           'under "Show secrets".'
