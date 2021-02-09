import html

from typing import List

from telegram import Update, Bot
from telegram.ext import CommandHandler, Filters
from telegram.ext.dispatcher import run_async

from tg_bot import dispatcher, SUDO_USERS, OWNER_USERNAME, OWNER_ID
from tg_bot.modules.helper_funcs.extraction import extract_user
from tg_bot.modules.helper_funcs.chat_status import bot_admin


@bot_admin
@run_async
def addsudo(bot: Bot, update: Update, args: List[str]):
    message = update.effective_message
    banner = update.effective_user
    user_id = extract_user(message, args)
    
    if not user_id:
        message.reply_text("Əvvəlcə bir isdifadəçini yönləndirin...")
        return ""
        
    if int(user_id) == OWNER_ID:
        message.reply_text("Əlavə etmək istədiyiniz şəxs onsuzda mənim sahibimdir!")
        return ""
        
    if int(user_id) in SUDO_USERS:
        message.reply_text("Dosdum, bu isdiafadəçi onsuzda SUDO siyahısında var.")
        return ""
    
    with open("sudo_users.txt","a") as file:
        file.write(str(user_id) + "\n")
    
    SUDO_USERS.append(user_id)
    message.reply_text("Uğurla SUDO siyahısına əlavə edildi!")
        
    return ""

@bot_admin
@run_async
def rsudo(bot: Bot, update: Update, args: List[str]):
    message = update.effective_message
    user_id = extract_user(message, args)
    
    if not user_id:
        message.reply_text("Əvvəlcə bir isdifadəçini yönləndirin")
        return ""

    if int(user_id) == OWNER_ID:
        message.reply_text("Yazdığınız isdifadəçi mənim sahibimdir! Onu SUDO_LIST siyahısındam silməyəcəm!")
        return ""

    if user_id not in SUDO_USERS:
        message.reply_text("{} SUDO isdifadəçisi deyil.".format(user_id))
        return ""

    users = [line.rstrip('\n') for line in open("sudo_users.txt")]

    with open("sudo_users.txt","w") as file:
        for user in users:
            if not int(user) == user_id:
                file.write(str(user) + "\n")

    SUDO_USERS.remove(user_id)
    message.reply_text("İsdifadəçi SUDO siyahısından uğurla silindi!")
    
    return ""


__help__ = """
*Sadəcə sahib üçün:*
 - /addsudo: isdifadəçini SUDO siyahısına əlavə edər
 - /rsudo: isdifadəçini SUDO siayhısından silər
"""

__mod_name__ = "Sudo"

addsudo_HANDLER = CommandHandler("addsudo", addsudo, pass_args=True, filters=Filters.user(OWNER_ID))
rsudo_HANDLER = CommandHandler("rsudo", rsudo, pass_args=True, filters=Filters.user(OWNER_ID))

dispatcher.add_handler(addsudo_HANDLER)
dispatcher.add_handler(rsudo_HANDLER)
