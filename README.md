# Versebot for Slack
A Bible verse bot built for [Slack](https://slack.com/) that has actively been in use in several [Slack](https://slack.com/) groups since 2016.  
All Bible verses are pulled from the [English Standard Version (ESV)](https://www.esv.org/translation/) translation.

------

The bot has two main features:  
1. Posting Bible verses after detecting a Bible verse reference in a [Slack](https://slack.com/) message (e.g. John 3:16-19 or Eph 2:8)
2. Posting a scheduled daily Bible verse to a specified [Slack](https://slack.com/) channel

------

Versebot allows for many custom options that can be configured via chat commands or directly in the `bot.cfg` configuration file.

These commands allow the user to:
- Enable/Disable the bot's two main features
- Set the bot's displayed username and icon (either an emoji or image url)
- Set the time of day for the bot to post the daily verse
- Set the channel where the daily verse is posted

------

Versebot is currently not available on the official [Slack App Directory](https://slack.com/apps).  
It is recommended to deploy the bot on a cloud application platform such as [Heroku](https://www.heroku.com/).

------

![Example Versebot Usage](https://i.imgur.com/nZeC59W.png)
