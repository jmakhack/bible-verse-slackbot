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

#If icon_url and icon_emoji are both supplied, icon_url takes precedence
def make_post(text, channel, username=None, icon_url=None, icon_emoji=None):
    """Makes a post message API call to the slack client with given arguments.

    Keyword arguments:
    text -- the text to post as a message
    channel -- the channel to post this text to
    username -- the name that this message is to be posted under (default None)
    icon_url -- url to an image to be used as the icon (default None)
    icon_emoji -- emoji to be used as the icon (default None)
    """
    try:
        if username and icon_url:
            slack_client.api_call('chat.postMessage', channel=channel, text=text, as_user=False, username=username, icon_url=icon_url)
        elif username and icon_emoji:
            slack_client.api_call('chat.postMessage', channel=channel, text=text, as_user=False, username=username, icon_emoji=icon_emoji)
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

def post_daily_verse(channel, username=None, icon_url=None, icon_emoji=None):
    """Retrieve the text for the daily verse and post it.

    Keyword arguments:
    channel -- the channel to post this text to
    username -- the name that this message is to be posted under (default None)
    icon_url -- url to an image to be used as the icon (default None)
    icon_emoji -- emoji to be used as the icon (default None)
    """
    api_url = 'http://www.esvapi.org/v2/rest/dailyVerse?key=IP&output-format=plain-text&include-footnotes=0' \
        '&include-short-copyright=0&include-passage-horizontal-lines=0&include-heading-horizontal-lines=0' \
        '&include-headings=0&include-subheadings=0&include-selahs=0&include-content-type=0&line-length=0' \
        '&include-verse-numbers=0&include-first-verse-numbers=0'
    text = urllib2.urlopen(api_url).read()
    make_post(text, channel, username, icon_url, icon_emoji)

def post_verses(ref, channel, username=None, icon_url=None, icon_emoji=None):
    """Retrieve the text for the user requested verses and post it if found.

    Keyword arguments:
    ref -- the string reference to the requested verses
    channel -- the channel to post this text to
    username -- the name that this message is to be posted under (default None)
    icon_url -- url to an image to be used as the icon (default None)
    icon_emoji -- emoji to be used as the icon (default None)
    """
    api_url = 'http://www.esvapi.org/v2/rest/passageQuery?key=IP&include-passage-references=1' \
        '&output-format=plain-text&include-footnotes=0&include-short-copyright=0' \
        '&include-passage-horizontal-lines=0&include-heading-horizontal-lines=0&include-headings=0' \
        '&include-subheadings=0&include-selahs=1&include-content-type=0&line-length=0' \
        '&include-verse-numbers=0&include-first-verse-numbers=0&passage=' + ref
    text = urllib2.urlopen(api_url).read()
    if 'ERROR' not in text and '<html>' not in text:
        make_post(text, channel, username, icon_url, icon_emoji)

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

def parse_slack_output(slack_rtm_output):
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
    username = None if not config.has_option(section, 'username') else config.get(section, 'username')
    icon_url = None if not config.has_option(section, 'icon_url') else config.get(section, 'icon_url')
    icon_emoji = None if not config.has_option(section, 'icon_emoji') or config.has_option(section, 'icon_url') else config.get(section, 'icon_emoji')
    if icon_emoji and icon_emoji[0] + icon_emoji[-1] != '::':
        icon_emoji = ':' + icon_emoji + ':'
    return username, icon_url, icon_emoji

def run_daily_verse_bot():
    """Run logic for versebot posting a daily verse if enabled."""
    if not is_section_disabled('daily_verse') and is_time_to_post_daily_verse():
        if config.has_option('daily_verse', 'channel'):
            channel = config.get('daily_verse', 'channel')
            username, icon_url, icon_emoji = get_username_and_icons('daily_verse')
            post_daily_verse(channel, username, icon_url, icon_emoji)

def run_verse_bot():
    """Run logic for versebot parsing user input to check for verse posting requests"""
    if not is_section_disabled('versebot'):
        ref, channel = parse_slack_output(slack_client.rtm_read())
        if ref and channel:
            username, icon_url, icon_emoji = get_username_and_icons('versebot')
            post_verses(ref, channel, username, icon_url, icon_emoji)

if __name__ == '__main__':
    if slack_client.rtm_connect():
        print 'Versebot connected and running! It\'s time for some Bible verses! :)'
        while True:
            run_daily_verse_bot()
            run_verse_bot()
            time.sleep(1)
    else:
        sys.exit('Connection failed. Invalid Slack token?')
