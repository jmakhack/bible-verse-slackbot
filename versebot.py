import os
import json
import datetime
import re
import time
import urllib2
import ConfigParser
import sys
from slackclient import SlackClient

config = ConfigParser.RawConfigParser()
config.read('bot.cfg')

#Setup slack token associated to this bot
if config.has_section('slack') and config.has_option('slack', 'token'):
    slack_client = SlackClient(config.get('slack', 'token'))
else:
    sys.exit('Token is not properly set in configuration file')

def make_post(text, channel, section=None):
    """Makes a post message API call to the slack client with given arguments.

    Keyword arguments:
    text -- the text to post as a message
    channel -- the channel to post this text to
    section -- name of config section to get from (default None)
    """
    username, icon_url, icon_emoji = get_username_and_icons(section)
    try:
        #If icon_url and icon_emoji are both supplied, icon_url takes precedence
        if username and icon_url:
            slack_client.api_call('chat.postMessage', channel=channel, text=text, as_user=False, username=username, icon_url=icon_url)
        elif username and icon_emoji:
            slack_client.api_call('chat.postMessage', channel=channel, text=text, as_user=False, username=username, icon_emoji=icon_emoji)
        elif username:
            slack_client.api_call('chat.postMessage', channel=channel, text=text, as_user=False, username=username)
        elif icon_url:
            slack_client.api_call('chat.postMessage', channel=channel, text=text, as_user=False, icon_url=icon_url)
        elif icon_emoji:
            slack_client.api_call('chat.postMessage', channel=channel, text=text, as_user=False, icon_emoji=icon_emoji)
        else:
            slack_client.api_call('chat.postMessage', channel=channel, text=text, as_user=True)
    except Exception as e:
        sys.exit(e)

def get_config_time(option, mod, default=0):
    """Get value of the daily verse time set in the config file.

    Keyword arguments:
    option -- a string representing the unit of time equal to the config option
    mod -- value to mod the value by
    default -- default value if config is not found (default 0)
    """
    if config.has_option('daily_verse', option):
        try:
            value = config.getint('daily_verse', option)
            return value % mod
        except:
            pass
    return default

def is_time_to_post_daily_verse():
    """Return True if the current time is the time to post the daily verse."""
    time = datetime.datetime.now()
    is_hour = time.hour == get_config_time('hour', 24, 6)
    is_minute = time.minute == get_config_time('minute', 60)
    is_second = time.second == get_config_time('second', 60)
    return is_hour and is_minute and is_second

def post_daily_verse(channel, section):
    """Retrieve the text for the daily verse and post it.

    Keyword arguments:
    channel -- the channel to post this text to
    section -- name of config section to get from
    """
    api_url = 'http://www.esvapi.org/v2/rest/dailyVerse?key=IP&output-format=plain-text&include-footnotes=0' \
        '&include-short-copyright=0&include-passage-horizontal-lines=0&include-heading-horizontal-lines=0' \
        '&include-headings=0&include-subheadings=0&include-selahs=0&include-content-type=0&line-length=0' \
        '&include-verse-numbers=0&include-first-verse-numbers=0'
    text = urllib2.urlopen(api_url).read()
    make_post(text, channel, section)

def post_verses(ref, channel, section):
    """Retrieve the text for the user requested verses and post it if found.

    Keyword arguments:
    ref -- the string reference to the requested verses
    channel -- the channel to post this text to
    section -- name of config section to get from
    """
    api_url = 'http://www.esvapi.org/v2/rest/passageQuery?key=IP&include-passage-references=1' \
        '&output-format=plain-text&include-footnotes=0&include-short-copyright=0' \
        '&include-passage-horizontal-lines=0&include-heading-horizontal-lines=0&include-headings=0' \
        '&include-subheadings=0&include-selahs=1&include-content-type=0&line-length=0' \
        '&include-verse-numbers=0&include-first-verse-numbers=0&passage=' + ref
    text = urllib2.urlopen(api_url).read()
    if 'ERROR' not in text and '<html>' not in text:
        make_post(text, channel, section)

def get_ref_in_text(text):
    """Return the reference to the user requested verses if found.

    Keyword arguments:
    text -- the message to parse for verse reference
    """
    text = text.replace('solomon', 'songs')
    words = re.split(' |\.|;|\?|!|\n', text)
    for i in range(len(words)):
        if re.match('^[0-9]+:[0-9\-,]+$', words[i]):
            if len(words) > 2 and re.match('^[1-3]$', words[i-2]):
                return words[i-2] + words[i-1] + words[i]
            else:
                return words[i-1] + words[i]
        if re.match('^[A-Za-z]+[0-9]+:[0-9\-,]+$', words[i]):
            return words[i]
    return None

def is_user_bot(output):
    """Return True if latest message is written by a bot.

    Keyword arguments:
    output -- output given by slack real time message API
    """
    return 'bot_id' in output

def parse_for_verses(slack_rtm_output):
    """Return verse reference and channel in latest messages if found.

    Keyword agruments:
    slack_rtm_output -- output read from slack client
    """
    output_list = slack_rtm_output
    if output_list and len(output_list) > 0:
        for output in output_list:
            if output and 'text' in output:
                ref = None if is_user_bot(output) else get_ref_in_text(output['text'])
                return ref, output['channel']
    return None, None

def is_section_disabled(section):
    """Return True if config section exists and is not disabled.

    Keyword arguments:
    section -- name of config section to check
    """
    try:
        if (not config.has_section(section)) or (config.has_option(section, 'disabled') and config.getboolean(section, 'disabled')):
            return True
    except:
        pass
    return False

def get_username_and_icons(section):
    """Return username, icon_url, and icon_emoji as set in the config section.

    Keyword arguments:
    section -- name of config section to get from
    """
    if not section or not config.has_section(section):
        return None, None, None
    username = None if not config.has_option(section, 'username') else config.get(section, 'username')
    icon_url = None if not config.has_option(section, 'icon_url') else config.get(section, 'icon_url')
    icon_emoji = None if not config.has_option(section, 'icon_emoji') else config.get(section, 'icon_emoji')
    if icon_emoji and icon_emoji[0] + icon_emoji[-1] != '::':
        icon_emoji = ':' + icon_emoji + ':'
    return username, icon_url, icon_emoji

def run_daily_verse_bot():
    """Run logic for versebot posting a daily verse if enabled."""
    section = 'daily_verse'
    if not is_section_disabled(section) and is_time_to_post_daily_verse():
        if config.has_option(section, 'channel'):
            channel = config.get(section, 'channel')
            username, icon_url, icon_emoji = get_username_and_icons(section)
            post_daily_verse(channel, section)

def run_verse_bot(slack_rtm_output):
    """Run logic for versebot parsing user input to check for verse posting requests

    Keyword arguments:
    slack_rtm_output -- output read from slack client
    """
    section = 'versebot'
    if not is_section_disabled(section):
        ref, channel = parse_for_verses(slack_rtm_output)
        if ref and channel:
            post_verses(ref, channel, section)

def post_greeting_message(channel, section=None):
    """Post greeting message when versebot is triggered.

    Keyword arguments:
    channel -- the channel to post this text to
    section -- name of config section to get from (default None)
    """
    post = lambda x: make_post(x, channel, section)
    post('Greetings! I am versebot, your ESV Bible verse Slack assistant! :smiley:')
    post('Current version: versebot 1.0.0')
    post('If you need help, you can review the online documentation located <https://github.com/himsoncafe/versebot/blob/master/README.md|here>!')

def get_sections_from_function(function):
    """Return tuple of applicable conf sections given the inputted function.

    Keyword arguments:
    function -- the function of the bot that the command applies to
    """
    sections = {'daily': ('daily_verse',), 'all': ('versebot', 'daily_verse'), None: ('versebot',)}
    return sections[function]

def represents_int(string):
    """Return True if string represents an integer value.

    Keyword arguments:
    string -- string to check if int
    """
    try:
        int(string)
        return True
    except ValueError:
        return False

def run_command(function, command, values, channel):
    """Run user inputted command for versebot.

    Keyword arguments:
    function -- the function of the bot that the command applies to
    command -- the command to execute
    values -- any additional values that the command accepts
    channel -- the channel to post this text to
    """
    sections = get_sections_from_function(function)
    post = lambda x: make_post(x, channel, sections[0])
    if command == 'enable':
        for section in sections:
            config.set(section, 'disabled', '0')
            post(section + ' has been enabled.')
    elif command == 'disable':
        for section in sections:
            config.set(section, 'disabled', '1')
            post(section + ' has been disabled.')
    elif command == 'status':
        for section in sections:
            status = 'disabled' if config.getint(section, 'disabled') else 'enabled'
            post(section + ' is currently ' + status + '.')
    elif command == 'reset':
        for section in sections:
            config.remove_section(section)
            config.add_section(section)
            config.set(section, 'disabled', '1')
            post(section + ' has been reset.')
    elif command == 'username' and len(values):
        for section in sections:
            config.set(section, 'username', ' '.join(values))
            post(section + '\'s username is now _' + ' '.join(values) + '_.')
    elif command == 'icon' and len(values) == 1:
        option = 'icon_emoji' if values[0][0] == ':' and values[0][-1] == ':' else 'icon_url'
        for section in sections:
            config.set(section, option, values[0])
            post(section + ' now has a new icon.')
    elif function == 'daily' and command == 'time' and 0 < len(values) < 4:
        if len(values) == 1 and ':' in values[0]:
            values = values[0].split(':')
        config.set(sections[0], 'hour', values[0] if represents_int(values[0]) else 6)
        config.set(sections[0], 'minute', values[1] if len(values) > 1 and represents_int(values[1]) else 0)
        config.set(sections[0], 'second', values[2] if len(values) > 2 and represents_int(values[2]) else 0)
        hour = str(get_config_time('hour', 24, 6))
        minute = str(get_config_time('minute', 60))
        second = str(get_config_time('second', 60))
        post(sections[0] + '\'s posting time is now ' + hour + ':' + minute + ':' + second + '.')
    elif function == 'daily' and command == 'channel' and len(values) == 1:
        if re.match('^<#[A-Z0-9]+\|[a-z0-9_]+>$', values[0]):
            values[0] = '#' + values[0].split('|')[-1][:-1]
        if values[0][0] != '#':
            values[0] = '#' + values[0]
        config.set(sections[0], 'channel', values[0])
        post(sections[0] + ' will now be posting to _' + values[0] + '_.')
    elif command == 'debug':
        for section in config.sections():
            if section == 'slack':
                continue
            post('[' + section + ']')
            for item in config.items(section):
                post(item[0] + ' = ' + item[1])
            post(' ')
    else:
        post('Invalid command received. Type _versebot_ for help.')
    with open('bot.cfg', 'wb') as configfile:
        config.write(configfile)

def parse_for_commands(slack_rtm_output):
    """Parse output for commands and run them if found.

    Keyword arguments:
    slack_rtm_output -- output read from slack client
    """
    output_list = slack_rtm_output
    if output_list and len(output_list) > 0:
        for output in output_list:
            if output and 'text' in output and not is_user_bot(output):
                words = output['text'].split()
                if words and words[0] == 'versebot':
                    if len(words) == 1 or words[1] == 'help':
                        post_greeting_message(output['channel'], 'versebot')
                    else:
                        function, command, values = None, None, []
                        cur_index = 1
                        if words[cur_index] in ('daily', 'all'):
                            function = words[cur_index]
                            cur_index += 1
                        if cur_index < len(words):
                            command = words[cur_index]
                            cur_index += 1
                        if cur_index < len(words):
                            values = [word for word in words[cur_index:]]
                        run_command(function, command, values, output['channel'])

if __name__ == '__main__':
    if slack_client.rtm_connect():
        print 'Versebot connected and running! It\'s time for some Bible verses! :)'
        while True:
            slack_rtm_output = slack_client.rtm_read()
            parse_for_commands(slack_rtm_output)
            run_verse_bot(slack_rtm_output)
            run_daily_verse_bot()
            time.sleep(1)
    else:
        sys.exit('Connection failed. Invalid Slack token?')
