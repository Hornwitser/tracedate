from datetime import datetime
import json
import logging
from time import time

from discord import Forbidden, Object
from discord.ext.commands import Bot, is_owner, command

from tracedate import date_trace

logging.basicConfig(level=logging.INFO)


def ptime(timestamp):
    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d")

def pdelta(a, b):
    time_a = datetime.fromtimestamp(a)
    time_b = datetime.fromtimestamp(b)
    delta = time_b - time_a
    if delta.days == 1:
        return "1 day"
    else:
        return f"{delta.days} days"

def filter_code_block(content):
    # Quoted tracebacks where the last line ends in tripple or single
    # backticks get in the way for the line matching algorithm
    def filter_line(line):
        if line.endswith("```"):
            return line[:-3]
        if line.endswith("`"):
            return line[:-1]
        return line

    return "\n".join(map(filter_line, content.split("\n")))

@command()
async def trace(ctx, ch_msg_id):
    """Trace the version of discord.py used from a traceback

    Argument is channel_id-message_id, same as shift right click "copy id"
    on a message yeilds.
    """

    ch_id, msg_id = ch_msg_id.split('-')
    channel = bot.get_channel(int(ch_id))
    try:
        msg = await channel.get_message(int(msg_id))
    except Forbidden:
        await ctx.channel.send("Bot does not have access to that channel")
        return

    result = date_trace(filter_code_block(msg.content))
    if result is None:
        await ctx.send("No results")
        return

    start = result['time-start']
    end = result['time-end']
    tags = result['tags']
    branches = result['branches']

    await ctx.send(f"""\
**Period:** {ptime(start)} to {ptime(end)} ({pdelta(start, end)} span)
**Age:** At least {pdelta(end, time())}
**Branches:** {", ".join(branches) if branches else "*None match*"}
**Tags:** {", ".join(tags) if tags else "*None match*"}""")

@command(hidden=True)
@is_owner()
async def stop(ctx):
    """Stop running the bot"""
    await bot.logout()


class Trace(Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_command(trace)
        self.add_command(stop)


if __name__ == '__main__':
    with open("config.json") as json_file:
        config = json.load(json_file)

    bot = Trace(config['prefix'], fetch_offline_members=False)
    bot.run(config['token'])
