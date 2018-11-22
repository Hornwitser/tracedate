from datetime import datetime
import json
import logging
from time import time

from discord import Object
from discord.ext.commands import Bot, is_owner

from tracedate import date_trace

logging.basicConfig(level=logging.INFO)


bot = Bot("}", fetch_offline_members=False)

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

@bot.command()
async def trace(ctx, ch_msg_id):
    """Trace the version of discord.py used from a traceback

    Argument is channel_id-message_id, same as shift right click "copy id"
    on a message yeilds.
    """

    ch_id, msg_id = ch_msg_id.split('-')
    channel = bot.get_channel(int(ch_id))
    print("trace")
    # Why does get_message exist?
    #msg = await channel.get_message(int(msg_id))
    msg = await channel.history(after=Object(id=int(msg_id) - 1), limit=1).get()
    print("do_trace")
    result = date_trace(msg.content)
    if result is None:
        await ctx.send("No results")
        return

    start = result['time-start']
    end = result['time-end']
    tags = result['tags']
    branches = result['branches']

    print("send result")
    await ctx.send(f"""\
**Period:** {ptime(start)} to {ptime(end)} ({pdelta(start, end)} span)
**Age:** At least {pdelta(end, time())}
**Branches:** {", ".join(branches) if branches else "*None match*"}
**Tags:** {", ".join(tags) if tags else "*None match*"}""")

@bot.command(hidden=True)
@is_owner()
async def stop(ctx):
    """Stop running the bot"""
    await bot.logout()

if __name__ == '__main__':
    with open("config.json") as json_file:
        config = json.load(json_file)
    bot.run(config['token'])
