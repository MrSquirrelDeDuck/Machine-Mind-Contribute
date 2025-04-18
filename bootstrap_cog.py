from discord.ext import commands
import typing
import os
import importlib
import traceback

import verification



class Bootstrap_cog(commands.Cog, name="Bootstrap"):

    # these extensions are loaded from outside files of the given name. Works like import.
    extensions = ['json_cog', 'talk', 'roles', 'chess_bot', 'bread_cog', 'enforcement', ] #used to include `chess_bot`, add back when migrated from cairosvg's bullshit



    bot_ref = None

    async def _load_all_modules(self: typing.Self) -> None:
        """Loads all extensions."""
        print("Extensions are: "+str(self.extensions))
        for extension in self.extensions:
            await self._load_internal(extension)
            #bot_ref.load_extension(extension)

    async def _load_internal(
            self: typing.Self,
            extension: str
        ) -> None:
        """Loads an extension from the name of it as a string."""
        print("Loading " + extension + "...")
        if (extension not in self.extensions):
            print("This extension has not been seen before.")

        try:

            await self.bot_ref.load_extension(extension)
            if (extension not in self.extensions):
                self.extensions.append(extension)

        except commands.ExtensionAlreadyLoaded:
        #    try:
        #        self.bot_ref.reload_extension(extension)
        #    except:
        #        print("Failed to reload module.")
        #        raise
        #    else:
        #        print("Module reloaded.")
            print(extension+" was already loaded")
        except:
            print("Failed.")
            raise
        else:
            print("Success.")

    

    @commands.command(
        brief = "Updates the bot from Git",
        hidden = True
    )
    @commands.check(verification.is_admin_check)
    async def update(self, ctx):
        await ctx.reply("Pulling from Git.")

        os.system("git pull")

        await ctx.send("Done, reloading everything.")
        
        for extension in self.bot_ref.extensions.copy():
            try:
                await self.bot_ref.reload_extension(extension)
            except:
                error = traceback.format_exc()
                await ctx.reply(f"Error when reloading {extension}:```\n"+ error + "```")
                print(error)
        
        await ctx.reply("Done.")

    @commands.command(
        brief = "Loads new extension",
        hidden = True,
        aliases = ["reload"]
    )
    @commands.check(verification.is_admin_check)
    async def load(self, ctx, *args):
        print("Running Load command. Bot Ref is "+str(self))
        
        if len(args) == 0:
            print("\n\n\n\n\n\nLoading all modules")
            for extension in self.extensions:
                await self.load(ctx, extension)
            
            
            await ctx.send("All modules loaded.")

        else:
            for extension in args:
                print("Loading " + extension + "...")

                
                try:
                    #self.bot_ref.load_extension(extension)

                    #first we'll see if it actually exists
                    #print("checking extensions")
                    #print(f"extensions are: {self.bot_ref.extensions}")
                    if extension not in self.bot_ref.extensions:
                        await ctx.send(f"Loading {extension}...")
                        await self.bot_ref.load_extension(extension)
                    else:

                        await ctx.send(f"Reloading {extension}...")
                        await self.bot_ref.reload_extension(extension)
                        # await ctx.send(extension+" reloaded.")

                    if (extension not in self.extensions):
                        self.extensions.append(extension)

                except commands.ExtensionAlreadyLoaded:
                    try:
                        self.bot_ref.reload_extension(extension)
                    except:
                        await ctx.send("Failed to reload module.")
                        raise
                    else:
                        await ctx.send(extension+" reloaded.")
                except commands.errors.ExtensionNotFound:
                    await ctx.send("Failed. Extension name not recognized.")
                except:
                    await ctx.send("Failed.")
                    raise
                else:
                    await ctx.send("Success.")

    @commands.command(
        brief = "Unloads extensions",
        hidden = True,
    )
    @commands.is_owner()
    async def unload(self, ctx, *args):
        print(f"unload called for {args}")
        for extension in args:
            print("Unloading " + extension + "...")
            if extension in self.bot_ref.extensions:
                await ctx.send(f"Unloading {extension}...")
                await self.bot_ref.unload_extension(extension)
                self.extensions.remove(extension)
                #await ctx.send(f"{extension} unloaded.")
        await ctx.send("Done.")
        print(f"extensions are now: {self.bot_ref.extensions}")





"""
@commands.command(
    hidden = True,
    brief = "reloads all extensions"
)
@commands.is_owner()
async def reload(ctx):
    print("\n\n\n\n\n\n\nreloading modules")
    for extension in self.extensions:
        await load(ctx, extension)
    await ctx.send("All modules loaded.")
"""



async def setup(bot: commands.Bot):
    print("Setting up Bootstrap Cog")
    importlib.reload(verification)
    
    cog = Bootstrap_cog(bot)
    cog.bot_ref = bot
    await bot.add_cog(cog)
    await cog._load_all_modules()
    """
    print("Starting bootstrap with bot "+str(bot))
    bot_ref = bot
    #bot.add_command(reload)
    bot.add_command(load)
    _load_all_modules(bot)
    print ("Bot ref is now "+str(bot_ref))
    """