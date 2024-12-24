import discord
from discord.ext import commands
from discord.ui import View
import asyncio
import re  # Import the 're' module
import discord.utils

# Set your values here
DISCORD_BOT_TOKEN = "MTMyMDQ1OTk4OTk0ODU2MzU1MA.GFn7Cd.pN7rSyf16ZdIc72Jy6h7H8LyYfCZAGryEcnKhM"
GUILD_ID = 1307296745197273158  
STAFF_ROLE_ID = 1320459703603433482 

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='?', intents=intents)

# Dictionary to keep track of user prompts
user_prompts = {}

class Confirm(View):
    def __init__(self, user):
        super().__init__()
        self.value = None
        self.user = user

    @discord.ui.button(label="  ✅  ", style=discord.ButtonStyle.grey)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user:
            await interaction.response.send_message("This is not for you!", ephemeral=True)
            return
        self.value = True
        await interaction.response.edit_message(content="Processing...", view=None)
        self.stop()

    @discord.ui.button(label="  ❌  ", style=discord.ButtonStyle.grey)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user:
            await interaction.response.send_message("This is not for you!", ephemeral=True)
            return
        self.value = False

        embed = discord.Embed(
            title="Cancelled",
            description="The action has been cancelled!",
            color=discord.Color.red()
        )

        await interaction.response.edit_message(embed=embed, view=None)
        self.stop()


class TicketType(View):
    def __init__(self, user):
        super().__init__()
        self.value = None
        self.user = user

    @discord.ui.select(
        placeholder="Select the type of ticket...",
        options=[
            discord.SelectOption(label="Staff Report", description="Report a staff member", emoji="📢"),
            discord.SelectOption(label="General Support", description="Get help with a general issue", emoji="❓"),
            discord.SelectOption(label="Giveaway Claim", description="Claim a giveaway prize", emoji="🎉"),
            discord.SelectOption(label="Appeal", description="Appeal a decision or action", emoji="📝"),
        ]
    )
    async def select_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
        if interaction.user != self.user:
            await interaction.response.send_message("This is not for you!", ephemeral=True)
            return
        self.value = select.values[0]
        await interaction.response.edit_message(content=f"Selected {self.value}", view=None)
        self.stop()

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    await asyncio.sleep(5)  # Wait for a few seconds to ensure the bot is fully connected
    guild = bot.get_guild(GUILD_ID)
    if guild:
        print(f"Connected to guild: {guild.name} (ID: {GUILD_ID})")
    else:
        print(f"Guild with ID {GUILD_ID} not found!")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if message.guild is None:  # Check if the message is in a DM
        print(f"Received DM from {message.author}")

        # Check if the user already has an active ticket channel
        guild = bot.get_guild(GUILD_ID)
        if guild is None:
            return

        ticket_channel = discord.utils.get(guild.text_channels, name=f"ticket-{message.author.id}")
        if ticket_channel:
            # Forward the user's message to the ticket channel
            embed = discord.Embed(
                description=message.content,
                timestamp=message.created_at
            )
            embed.set_author(name=message.author.display_name, icon_url=message.author.display_avatar.url)
            embed.set_footer(text=f"User ID: {message.author.id}")
            await ticket_channel.send(embed=embed)
            return

        if message.author.id not in user_prompts:
            user_prompts[message.author.id] = False

        if not user_prompts[message.author.id]:
            try:
                view = Confirm(message.author)
                embed = discord.Embed(
                    title="Support Request",
                    description="Please choose an option below to proceed.",
                    color=discord.Color.light_grey()
                )
                await message.author.send(embed=embed, view=view)
            except discord.Forbidden:
                print(f"Cannot send message to {message.author}, they might have DMs disabled.")
                return

            user_prompts[message.author.id] = True

            await view.wait()

            if view.value is None:
                await message.author.send("No response, ticket creation cancelled.")
                print("No response from the user.")
                user_prompts[message.author.id] = False
            elif view.value:
                if guild is None:
                    await message.author.send("Guild not found!")
                    print("Guild not found!")
                    return

                # Create the ticket channel with the user's ID in the topic
                ticket_channel = await guild.create_text_channel(f"ticket-{message.author.id}", overwrites={
                    guild.default_role: discord.PermissionOverwrite(view_channel=False),
                    guild.get_role(STAFF_ROLE_ID): discord.PermissionOverwrite(view_channel=True)
                })
                await ticket_channel.edit(topic=str(message.author.id))

                member = guild.get_member(message.author.id)
                if member:
                    roles = [role.name for role in member.roles if role.name != "@everyone"]
                    role_text = ', '.join(roles) if roles else 'No Roles'

                    ticket_type_view = TicketType(message.author)
                    await message.author.send("Please select the type of ticket:", view=ticket_type_view)

                    await ticket_type_view.wait()

                    if ticket_type_view.value is None:
                        await message.author.send("No response, ticket type selection cancelled.")
                        print("No response for ticket type selection.")
                        user_prompts[message.author.id] = False
                        return

                    embed = discord.Embed(
                        title="Everyone",
                        description=f"{member.mention} has opened a ticket.",
                        color=discord.Color.blue(),
                        timestamp=message.created_at
                    )
                    embed.add_field(name="Joined Discord", value=member.created_at.strftime("%Y-%m-%d %H:%M:%S"), inline=True)
                    embed.add_field(name="Joined Server", value=member.joined_at.strftime("%Y-%m-%d %H:%M:%S"), inline=True)
                    embed.add_field(name="Roles", value=role_text, inline=True)
                    embed.add_field(name="Ticket Type", value=ticket_type_view.value, inline=True)

                    # Send the embed to the ticket channel instead of modmail notifications
                    await ticket_channel.send(embed=embed)

                await message.author.send("Your ticket has been created. Staff will respond to you here.")
                print(f"Ticket created for {message.author}.")
                user_prompts[message.author.id] = False
            else:
                await message.author.send("")
                print("Ticket creation cancelled by the user.")
                user_prompts[message.author.id] = False
    else:
        await bot.process_commands(message)

@bot.command(name='r')
async def r(ctx, *, message: str):
    if ctx.channel.name.startswith('ticket-'):
        embed = discord.Embed(
            description=message,
            timestamp=ctx.message.created_at
        )
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
        highest_role = ctx.author.roles[-1] if ctx.author.roles else None
        embed.set_footer(text=f"{highest_role.name if highest_role else 'No Role'}")
        await ctx.send(embed=embed)

        # Retrieve the user's ID from the channel topic
        ticket_user_id = int(ctx.channel.topic)
        ticket_user = ctx.guild.get_member(ticket_user_id)

        if ticket_user:
            await ticket_user.send(embed=embed)
    else:
        await ctx.send("This command can only be used in ticket channels.", delete_after=10)

@bot.command(name='close')
@commands.has_permissions(administrator=True)
async def close(ctx, *, duration: str = None):
    if ctx.channel.name.startswith('ticket-'):
        if duration is None:
            await ctx.send("Please specify a duration for closing the ticket, e.g., `?close in 2 seconds`.")
            return

        duration_match = re.match(r'(\d+)\s*(seconds?|minutes?|hours?|days?)', duration, re.IGNORECASE)
        if duration_match:
            time_value, unit = duration_match.groups()
            time_value = int(time_value)
            if 'second' in unit.lower():
                seconds = time_value
            elif 'minute' in unit.lower():
                seconds = time_value * 60
            elif 'hour' in unit.lower():
                seconds = time_value * 3600
            elif 'day' in unit.lower():
                seconds = time_value * 86400
            else:
                await ctx.send("Invalid time unit. Please specify seconds, minutes, hours, or days.", delete_after=10)
                return

            embed = discord.Embed(
                description=f"{ctx.author.mention} has scheduled this Modmail thread to be closed in {time_value} {unit}.\n\n*Replying will create a new thread.*",
                timestamp=ctx.message.created_at
            )
            embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
            highest_role = ctx.author.roles[-1] if ctx.author.roles else None
            embed.set_footer(text=f"{highest_role.name if highest_role else 'No Role'}")
            countdown_message = await ctx.send(embed=embed)

            # Schedule the closure with a countdown
            await countdown_and_close(countdown_message, seconds, ctx.author, time_value, unit, ctx.channel)
        else:
            await ctx.send("Invalid duration format. Please specify a duration like '2 seconds' or '5 minutes'.", delete_after=10)
    else:
        await ctx.send("This command can only be used in ticket channels.", delete_after=10)

async def countdown_and_close(message, seconds, author, time_value, unit, channel):
    while seconds > 0:
        msg = f"This Modmail thread will be closed in {seconds} seconds."
        await message.edit(content=msg)
        await asyncio.sleep(1)
        seconds -= 1

    msg = "This Modmail thread has been automatically closed.\n\n*Replying will create a new thread.*"
    await channel.send(content=msg)
    await channel.delete()

@bot.command(name='move')
@commands.has_permissions(manage_channels=True)
async def move(ctx, *, category_name: str):
    if not ctx.channel.name.startswith('ticket-'):
        await ctx.send("This command can only be used in ticket channels.", delete_after=10)
        return

    category = discord.utils.get(ctx.guild.categories, name=category_name)
    if category is None:
        await ctx.send(f"Category '{category_name}' not found.", delete_after=10)
        return

    await ctx.channel.edit(category=category)
    await ctx.send(f"Channel has been moved to category '{category_name}'.")

@bot.command(name='re')
@commands.has_permissions(manage_channels=True)
async def rename_channel(ctx, *, new_name: str):
    # Check if the new name is valid
    if len(new_name) > 100:
        await ctx.send("Channel name too long. Please choose a name with 100 characters or fewer.", delete_after=10)
        return

    await ctx.channel.edit(name=new_name)
    await ctx.send(f"Channel has been renamed to '{new_name}'.")

@bot.command(name='apply')
async def apply(ctx):
    # Create the embed message
    embed = discord.Embed(
        title="Application Form",
        description=(
            "Please answer the following questions:\n\n"
            "1. Why should we choose you?\n"
            "2. What are your strengths and weaknesses?\n"
            "3. On a scale of 1-10, how active will you be? (1 least, 10 very)\n\n"
            "For the following, please correct the grammar:\n\n"
            "1. Wheeer is the STAFF ROOM\n"
            "2. WELCOME TO FRESH RETAIL HOW CAN I II HELP\n"
            "3. Haw r u"
        ),
        color=discord.Color.blue()
    )

    # Send the embed message in the current channel
    await ctx.send(embed=embed)

    # Send the embed message as a DM to the user
    try:
        await ctx.author.send(embed=embed)
    except discord.Forbidden:
        await ctx.send("I couldn't send you a DM. Please make sure your DMs are open.", delete_after=10)

@bot.command(name='hi')
async def hi(ctx):
    user = ctx.author  # Person sending the command (support staff)
    support_person = ctx.author  # The support staff's name

    if ctx.channel.name.startswith('ticket-'):  # Ensure it's within a ticket channel
        # Extract the user's ID from the channel topic
        try:
            ticket_user_id = int(ctx.channel.topic)
            ticket_user = ctx.guild.get_member(ticket_user_id)
            if ticket_user:
                embed = discord.Embed(
                    title="Welcome to RexoMart Roblox Support",
                    description=(
                        f"Hello {ticket_user.mention}, and thank you for contacting Fresh Retail Roblox support. "
                        f"My name is {support_person.display_name}. You are now connected to our support line. "
                        "How can we assist you today? We log and monitor all tickets in case of misconduct by yourself or our staff."
                    ),
                    color=discord.Color.green()
                )
                embed.add_field(name="Important Information", value="Please note that all conversations are logged and monitored for quality assurance.")
                embed.add_field(name="Support Hours", value="Our support team is available 24/7 to assist you with your needs.")
                embed.add_field(name="Contact", value="If you need further assistance, please don't hesitate to reach out to our team.")

                await ctx.send(embed=embed)

                try:
                    await ticket_user.send(embed=embed)
                except discord.Forbidden:
                    await ctx.send("I couldn't send a DM to the user. They might have their DMs closed.")
            else:
                await ctx.send("Could not find the user associated with this ticket.")
        except ValueError:
            await ctx.send("This ticket's topic is not set up correctly. Please check the channel topic.")
    else:
        await ctx.send("This command can only be used in ticket channels.", delete_after=10)




@bot.command(name='s')
@commands.has_permissions(manage_channels=True)
async def subscribe(ctx):
    channel = ctx.channel
    user = ctx.author

    if channel.id not in ticket_subscribers:
        ticket_subscribers[channel.id] = []

    if user in ticket_subscribers[channel.id]:
        embed = discord.Embed(
            description=f"{user.mention} already subscribed to this modmail thread.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
    else:
        ticket_subscribers[channel.id].append(user)
        embed = discord.Embed(
            description=f"{user.mention} has been subscribed to this modmail thread.",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)

@bot.command(name='sub')
@commands.has_permissions(manage_channels=True)
async def subscribe_alias(ctx):
    await subscribe(ctx)




@bot.command(name='reply')
async def reply(ctx, *, message: str):
    await r(ctx, message=message)

@bot.command(name='bye')
@commands.has_permissions(manage_channels=True)
async def bye(ctx):
    user = ctx.author

    highest_role = user.roles[-1] if user.roles else None

    embed = discord.Embed(
        title="Ticket Closed",
        description=(
            "Thank you so much for reaching out to us today; we really appreciate your effort to get in touch. "
            "If you have any other questions or need further assistance in the future, please do not hesitate to contact us again. "
            "We're always here to help!\n\n"
            "This ticket has now been closed. If you respond to this message it will create a new ticket."
        ),
        color=discord.Color.blue(),
        timestamp=ctx.message.created_at
    )
    embed.set_author(name=user.display_name, icon_url=user.display_avatar.url)
    embed.add_field(name="User ID", value=user.id, inline=True)
    embed.add_field(name="Highest Role", value=highest_role.name if highest_role else 'No Role', inline=True)
    embed.set_footer(text="Thank you for contacting support")

    await ctx.send(embed=embed)

    try:
        await ctx.author.send(embed=embed)
    except discord.Forbidden:
        await ctx.send("I couldn't send you a DM. Please make sure your DMs are open.", delete_after=10)

    await ctx.channel.delete()

@bot.command(name='resolved')
@commands.has_permissions(manage_channels=True)
async def resolved(ctx):
    user = ctx.author

    embed = discord.Embed(
        title="Ticket Resolved",
        description=(
            "Thank you so much for reaching out to us today. We appreciate your effort to get in touch. "
            "We hope we were able to assist you with your issue. If you have any other questions or need further assistance in the future, "
            "please do not hesitate to contact us again. We're always here to help!\n\n"
            "This ticket has now been closed. If you respond to this message, it will create a new ticket. "
            "We hope you have a great day!"
        ),
        color=discord.Color.green(),
        timestamp=ctx.message.created_at
    )
    embed.set_author(name=user.display_name, icon_url=user.display_avatar.url)
    embed.set_footer(text="Thank you for contacting support")

    await ctx.send(embed=embed)

    try:
        await ctx.author.send(embed=embed)
    except discord.Forbidden:
        await ctx.send("I couldn't send you a DM. Please make sure your DMs are open.", delete_after=10)

@bot.command(name='staffreport')
async def staffreport(ctx):
    user = ctx.author

    embed = discord.Embed(
        title="Report User",
        description=(
            f"Hello {user.mention}! We appreciate you taking the time to reach out to us. "
            "Could you please provide the username of the person you are reporting and attach any relevant proof or details? "
            "This will help us handle the situation more effectively and ensure a fair resolution."
        ),
        color=discord.Color.orange()
    )

    embed.set_author(name=user.display_name, icon_url=user.display_avatar.url)
    embed.set_footer(text="Thank you for helping us maintain a safe and respectful community.")

    await ctx.send(embed=embed)

    try:
        await ctx.author.send(embed=embed)
    except discord.Forbidden:
        await ctx.send("I couldn't send you a DM. Please make sure your DMs are open.", delete_after=10)



bot.run(DISCORD_BOT_TOKEN)

