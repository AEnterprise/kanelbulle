from discord.ext import commands
import pymongo, discord, asyncio, re, config
from utils import text_handler

class Setup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def settings(self, ctx):
        database = self.bot.client["kanelbulle"]
        servers = database["servers"]
        query = servers.find({"id": ctx.guild.id}, {"_id": 0}).limit(1)
        #will only run once anyway
        for server in query:
            embed = discord.Embed().from_dict(
                {
                    "title": "> Settings",
                    "color": 15575881,
                    "fields": [
                        {
                            "name":  text_handler.translate(
                                server["language"],
                                "settings_channels_title"
                            ),
                            "value": text_handler.translate(
                                server["language"],
                                "settings_channels",
                                moderator_actions_channel=server['log_channels']['moderator_actions'],
                                messages_channel=server['log_channels']['messages']
                            )
                        }
                    ]
                }
            )
            await ctx.send(embed=embed)
            return
        await ctx.send()

    @commands.command()
    async def setup(self, ctx):
        database = self.bot.client["kanelbulle"]
        servers = database["servers"]
        query = servers.find({"id": ctx.guild.id}, {"_id": 0}).limit(1)
        def reaction_check(reaction, user):
            return user.id == ctx.author.id and (str(reaction.emoji) == "❌" or str(reaction.emoji) == "✅")
        def message_check(message):
            return message.author.id == ctx.author.id and message.channel.id == ctx.channel.id
        if query.count() != 0:
            m = await ctx.send("Hmm. It looks like this server is already set up.. Would you like to start over?")
            await m.add_reaction("✅")
            await m.add_reaction("❌")
            try:
                reaction, user = await self.bot.wait_for("reaction_add", timeout=20.0, check=reaction_check)
                if str(reaction.emoji) == "❌":
                    await ctx.send("Okay. I have canceled the setup for you.")
                    await m.delete()
                    return
                elif str(reaction.emoji) == "✅":
                    await m.delete()
                    servers.delete_one({"id": ctx.guild.id})
            except asyncio.TimeoutError:
                await ctx.send("You didn't click any of the reactions in time, so to be safe I canceled it.")
                return
            servers.delete_one({"id": ctx.guild.id})
        m = await ctx.send("Welcome to the Kanelbulle setup! I will ask you a couple of questions, and set up the server for you! It's that easy. Are you ready?")
        await m.add_reaction("✅")
        await m.add_reaction("❌")
        reaction, user = await self.bot.wait_for("reaction_add", check=reaction_check)
        if str(reaction.emoji) == "❌":
            await ctx.send("That's fine, I'll be here when you're ready!")
            await m.delete()
            return
        elif str(reaction.emoji) == "✅":
            await m.delete()
        language_question = await ctx.send(
            "Glad to hear! :) "
            +"Now let's get started, shall we? Should you accidentally click the wrong reaction, or answer wrongly, no need to start over you can all change this later on."
            +f"\nWhat language do you prefer? You can choose from this list:\n{config.supported_languages_str}"
        )
        language = await self.bot.wait_for("message", check=message_check)
        if not language.content.lower() in config.supported_languages:
            await ctx.send("Heck. It appears that we do not support that language yet, or maybe you made a typo in your message?")
            return
        else:
            msg = language
            await language.delete()
            await language_question.delete()
            language = msg
        m1 = await text_handler.send_lang(ctx, "setup_enable_moderation", language.content)
        await m1.add_reaction("✅")
        await m1.add_reaction("❌")
        reaction1, user = await self.bot.wait_for("reaction_add", check=reaction_check)
        res = None
        moderation_enabled = str(reaction1.emoji) == "✅"
        if moderation_enabled:
            res = await text_handler.send_lang(ctx, "setup_enable", language.content)
            await m1.delete()
        else:
            res = await text_handler.send_lang(ctx, "setup_not_enable", language.content)
            await m1.delete()
        moderation_channel = None
        finished_msg = None
        if moderation_enabled:
            m2 = await text_handler.send_lang(ctx, "setup_mod_log_question", language.content)
            await m2.add_reaction("✅")
            await m2.add_reaction("❌")
            reaction2, user = await self.bot.wait_for("reaction_add", check=reaction_check)
            await res.delete()
            if str(reaction2.emoji) == "✅":
                _m = await text_handler.send_lang(ctx, "setup_where_to_log", language.content)
                m3 = await self.bot.wait_for("message", check=message_check)
                await m2.delete()
                mod_actions_log_input = None
                try:
                    mod_actions_log_input = ctx.guild.get_channel(int(m3.content))
                    await _m.delete()
                    await m3.delete()
                except ValueError:
                    try:
                        mod_actions_log_input = ctx.guild.get_channel(int(m3.content.split("<#")[1].split(">")[0]))
                        await _m.delete()
                        await m3.delete()
                    except ValueError:
                        await ctx.send("Oh no! That doesn't seem like a valid channel..")
                        return
                if mod_actions_log_input is None:
                    await text_handler.send_lang(ctx, "setup_channel_not_found", language.content)
                    return
                moderation_channel = mod_actions_log_input.id
                finished_msg = await text_handler.send_lang(ctx, "setup_mod_log_channel_success", language.content, channel_id=mod_actions_log_input.id)
        messages_channel = None
        m2 = await text_handler.send_lang(ctx, "setup_enable_message_logs", language.content)
        await m2.add_reaction("✅")
        await m2.add_reaction("❌")
        reaction2, user = await self.bot.wait_for("reaction_add", check=reaction_check)
        if finished_msg is not None:
            await finished_msg.delete()
            finished_msg = None
        if not moderation_enabled:
            await res.delete()
        if str(reaction2.emoji) == "✅":
            _m = await text_handler.send_lang(ctx, "setup_where_to_log", language.content)
            m3 = await self.bot.wait_for("message", check=message_check)
            await m2.delete()
            messages_log_input = None
            try:
                messages_log_input = ctx.guild.get_channel(int(m3.content))
                await _m.delete()
                await m3.delete()
            except ValueError:
                try:
                    messages_log_input = ctx.guild.get_channel(int(m3.content.split("<#")[1].split(">")[0]))
                    await _m.delete()
                    await m3.delete()
                except ValueError:
                    # not translated yet bc borks
                    await ctx.send("Oh no! That doesn't seem like a valid channel..")
                    await _m.delete()
                    return
            if messages_log_input is None:
                await text_handler.send_lang(ctx, "setup_channel_not_found", language.content)
                await _m.delete()
                return
            messages_channel = messages_log_input.id
            finished_msg = await text_handler.send_lang(ctx, "setup_message_log_channel_success", language.content, channel_id=messages_channel)
        else:
            await m2.delete()
        m3 = await text_handler.send_lang(ctx, "setup_custom_prefix", language.content)
        await m3.add_reaction("✅")
        await m3.add_reaction("❌")
        reaction3, user = await self.bot.wait_for("reaction_add", check=reaction_check)
        if finished_msg is not None:
            await finished_msg.delete()
        prefix = ">."
        await m3.delete()
        if str(reaction3.emoji) == "✅":
            _m = await text_handler.send_lang(ctx, "setup_custom_prefix_yes", language.content)
            m4 = await self.bot.wait_for("message", check=message_check)
            prefix = m4.content
            await m4.delete()
            await _m.delete()
        servers.insert_one(
            {
                "id": ctx.guild.id,
                "prefix": prefix,
                "language": language.content,
                "experiments": 0,
                "log_channels": {
                    "moderator_actions": moderation_channel,
                    "messages": messages_channel
                }
            }
        )
        await text_handler.send_lang(ctx, "setup_finished", language.content)


def setup(bot):
    bot.add_cog(Setup(bot))
