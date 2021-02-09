import html
import json
from typing import Optional, List

import requests
from telegram import Message, Chat, Update, Bot, User
from telegram import ParseMode
from telegram.error import BadRequest
from telegram.ext import CommandHandler, Filters
from telegram.ext.dispatcher import run_async
from telegram.utils.helpers import escape_markdown, mention_html

from tg_bot import dispatcher, SUDO_USERS, TOKEN
from tg_bot.modules.disable import DisableAbleCommandHandler
from tg_bot.modules.helper_funcs.chat_status import (
    bot_admin,
    can_promote,
    user_admin,
    can_pin,
)
from tg_bot.modules.helper_funcs.extraction import extract_user, extract_user_and_text
from tg_bot.modules.helper_funcs.admin_rights import (
    user_can_pin,
    user_can_promote,
    user_can_changeinfo,
)
from tg_bot.modules.log_channel import loggable
from tg_bot.modules.connection import connected

@run_async
@bot_admin
@user_admin
@loggable
def promote(bot: Bot, update: Update, args: List[str]) -> str:
    chat_id = update.effective_chat.id
    message = update.effective_message
    chat = update.effective_chat
    user = update.effective_user

    if not chat.get_member(bot.id).can_promote_members:
        update.effective_message.reply_text("Burda insanları promote/demote etmirəm! "
                                            "Admin olduğumdan və yeni adminlər əlavə etmə yetkimin açıq olduğundan əmin olun")
        exit(1)

    if user_can_promote(chat, user, bot.id) is False:
        message.reply_text("Birini admin etmək üçün yetərli yetkiyə sahib deyilsiz!")
        return ""

    user_id = extract_user(message, args)
    if not user_id:
        message.reply_text("Deyəsən bir isdifadəçini nəzərdə tutmursan.")
        return ""

    user_member = chat.get_member(user_id)
    if user_member.status in ["administrator", "creator"]:
        message.reply_text("Bu isdifadəçi onsuzda admindir!")
        return ""

    if user_id == bot.id:
        message.reply_text("Özümü admin edə bilmərəm! Bunun üçün başqa bir admin tap.")
        return ""

    # set same perms as bot - bot can't assign higher perms than itself!
    bot_member = chat.get_member(bot.id)

    bot.promoteChatMember(chat.id, user_id,
                          can_change_info=bot_member.can_change_info,
                          can_post_messages=bot_member.can_post_messages,
                          can_edit_messages=bot_member.can_edit_messages,
                          can_delete_messages=bot_member.can_delete_messages,
                          #can_invite_users=bot_member.can_invite_users,
                          can_restrict_members=bot_member.can_restrict_members,
                          can_pin_messages=bot_member.can_pin_messages,
                          can_promote_members=bot_member.can_promote_members)

    message.reply_text("{} uğurla <b>{}</b> qrupunda admin edildi!".format(mention_html(user_member.user.id, user_member.user.first_name), (chat.title)), parse_mode=ParseMode.HTML)
    return (
        "<b>{}:</b>"
        "\n#PROMOTED"
        "\n<b>Admin:</b> {}"
        "\n<b>User:</b> {}".format(
            html.escape(chat.title),
            mention_html(user.id, user.first_name),
            mention_html(user_member.user.id, user_member.user.first_name),
        )
    )

@run_async
@bot_admin
@can_promote
@user_admin
def title(bot: Bot, update: Update, args):
    chat = update.effective_chat
    user = update.effective_user
    message = update.effective_message
    
    if user_can_promote(chat, user, bot.id) is False:
        message.reply_text("Bunu etmək üçün yetərli haqqın yoxdur!")
        return ""
    
    user_id, title = extract_user_and_text(message, args)
    if not user_id:
        message.reply_text("Bir isdifadəçi haqqında yazmırsan deyəsən...")
        return
    if not title:
        message.reply_text("Başlıq yoxdur.")
        return

    response = requests.post(
        f"https://api.telegram.org/bot{TOKEN}/setChatAdministratorCustomTitle"
        f"?chat_id={chat.id}"
        f"&user_id={user_id}"
        f"&custom_title={title}"
    )
    
    if response.status_code != 200:
        resp_text = json.loads(response.text)
        text = f"An error occurred:\n`{resp_text.get('description')}`"
    else:
        text = f"Successfully set title to `{title}`!"
    message.reply_text(text, parse_mode="MARKDOWN")

@run_async
@bot_admin
@user_admin
@loggable
def demote(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat
    message = update.effective_message
    user = update.effective_user

    if not chat.get_member(bot.id).can_promote_members:
        update.effective_message.reply_text("Burda insanları promote/demote etmirəm! "
                                            "Admin olduğumdan və yeni adminlər əlavə etmə yetkimin açıq olduğundan əmin olun")
        exit(1)

    if user_can_promote(chat, user, bot.id) is False:
        message.reply_text("Birini admin etmək üçün yetərli yetkiyə sahib deyilsiz!")
        return ""

    user_id = extract_user(message, args)
    if not user_id:
        message.reply_text("V.")
        return ""

    user_member = chat.get_member(user_id)
    if user_member.status == "creator":
        message.reply_text("Sahibin yetkisini ala bilmərəm.")
        return ""

    if user_member.status != "administrator":
        message.reply_text(
            "Admin olmayan birinin yetkisini necə alım?"
        )
        return ""

    if user_id == bot.id:
        message.reply_text("Öz yetkimi almayacağam!!")
        return ""

    try:
        bot.promoteChatMember(int(chat.id), int(user_id),
                              can_change_info=False,
                              can_post_messages=False,
                              can_edit_messages=False,
                              can_delete_messages=False,
                              can_invite_users=False,
                              can_restrict_members=False,
                              can_pin_messages=False,
                              can_promote_members=False)
        message.reply_text("{} yetkisi uğurla <b>{}</b> qrupunda alındı!".format(mention_html(user_member.user.id, user_member.user.first_name), (chat.title)), parse_mode=ParseMode.HTML)
        return f"<b>{html.escape(chat.title)}:</b>" \
                "\n#DEMOTED" \
               f"\n<b>Admin:</b> {mention_html(user.id, user.first_name)}" \
               f"\n<b>User:</b> {mention_html(user_member.user.id, user_member.user.first_name)}"

    except BadRequest:
        message.reply_text(
            "Yetki alınmadı. Admin olmaya bilərəm və ya adminlik başqa bir şəxs tərəfindən verilib "
            "buna görə onda dəyişiklik edilmədi!"
        )
        return ""

        


@run_async
@bot_admin
@can_pin
@user_admin
@loggable
def pin(bot: Bot, update: Update, args: List[str]) -> str:
    user = update.effective_user
    chat = update.effective_chat
    message = update.effective_message

    is_group = chat.type not in ["private", "channel"]

    prev_message = update.effective_message.reply_to_message

    if user_can_pin(chat, user, bot.id) is False:
        message.reply_text("Mesaj sabitləmə yetkiniz yoxdur :(")
        return ""

    is_silent = True
    if len(args) >= 1:
        is_silent = args[0].lower() not in ["notify", "loud", "violent"]

    if prev_message and is_group:
        try:
            bot.pinChatMessage(
                chat.id, prev_message.message_id, disable_notification=is_silent
            )
        except BadRequest as excp:
            if excp.message != "Chat_not_modified":
                raise
        return (
            "<b>{}:</b>"
            "\n#SABITLENDI"
            "\n<b>Admin:</b> {}".format(
                html.escape(chat.title), mention_html(user.id, user.first_name)
            )
        )

    return ""


@run_async
@bot_admin
@can_pin
@user_admin
@loggable
def unpin(bot: Bot, update: Update) -> str:
    chat = update.effective_chat
    user = update.effective_user
    if user_can_pin(chat, user, bot.id) is False:
        message = update.effective_message

        message.reply_text("Bir mesajı sabitdən çıxarmaq üçün yetkiniz yoxdur!")
        return ""

    try:
        bot.unpinChatMessage(chat.id)
    except BadRequest as excp:
        if excp.message != "Chat_not_modified":
            raise

    return (
        "<b>{}:</b>"
        "\n#SABITLENMEDI"
        "\n<b>Admin:</b> {}".format(
            html.escape(chat.title), mention_html(user.id, user.first_name)
        )
    )

@run_async
@bot_admin
@user_admin
def invite(bot: Bot, update: Update):
    user = update.effective_user
    msg = update.effective_message
    chat = update.effective_chat

    conn = connected(bot, update, chat, user.id, need_admin=True)
    if conn:
        chat = dispatcher.bot.getChat(conn)
    else:
        if msg.chat.type == "private":
            msg.reply_text("Bu əmr PM'də isdifadə edilə bilməz!")
            return ""
        chat = update.effective_chat

    if chat.username:
        msg.reply_text("@{}".format(chat.username))
    elif chat.type in [chat.SUPERGROUP, chat.CHANNEL]:
        bot_member = chat.get_member(bot.id)
        if bot_member.can_invite_users:
            invitelink = bot.exportChatInviteLink(chat.id)
            link = "Bağlantı yaradıldı *{}:*\n`{}`".format(chat.title, invitelink)
            msg.reply_text(link, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
        else:
            msg.reply_text("Bağlantı ilə dəvət etmə yetkim yoxdur!")
    else:
        msg.reply_text("Sizə sadəcə SuperGroup'lar üçün link verə bilərəm...")

@run_async
def adminlist(bot: Bot, update: Update):
    administrators = update.effective_chat.get_administrators()
    msg = update.effective_message
    text = "*{}* qrupundakı adminlər:".format(update.effective_chat.title or "this chat")
    for admin in administrators:
        user = admin.user
        status = admin.status
        name = "[{}](tg://user?id={})".format(user.first_name + " " + (user.last_name or ""), user.id)
        if user.username:
            name = name = escape_markdown("@" + user.username)
        if status == "creator":
            text += "\n 👑 Sahib:"
            text += "\n` • `{} \n\n • *Adminlər*:".format(name)
    for admin in administrators:
        user = admin.user
        status = admin.status
        chat = update.effective_chat
        count = chat.get_members_count()
        name = "[{}](tg://user?id={})".format(user.first_name + " " + (user.last_name or ""), user.id)
        if user.username:
            name = escape_markdown("@" + user.username)
            
        if status == "administrator":
            text += "\n`👮🏻 `{}".format(name)
            members = "\n\n*Qrup Sayı:*\n`✨ ` {} users".format(count)
            
    msg.reply_text(text + members, parse_mode=ParseMode.MARKDOWN)



def __chat_settings__(chat_id, user_id):
    return "Sən *adminsən*: `{}`".format(
        dispatcher.bot.get_chat_member(chat_id, user_id).status in ("administrator", "creator"))


__help__ = """
 - /adminlist: qrupdakı adminləri göstərər

*Adminlər üçün:*
 - /pin: mesajı sabitləyər *səssizcə* sabitləyər - səsli sabitləmək üçün `loud` və ya `notify` əlavə edin
 - /unpin: sabitdəki mesajı sabitdən çıxarar
 - /invitelink: qrupun dəvət linkini verər
 - /promote: cavab verilən isdifadəçini admin edər
 - /title <başlıq>: adminin başlığını dəyişər
 - /demote: cavab verilən isdifadəçinin admin yetkisini alar
"""

__mod_name__ = "Admin"

PIN_HANDLER = CommandHandler("pin", pin, pass_args=True, filters=Filters.group)
UNPIN_HANDLER = CommandHandler("unpin", unpin, filters=Filters.group)

INVITE_HANDLER = CommandHandler("invitelink", invite) #, filters=Filters.group)

PROMOTE_HANDLER = CommandHandler("promote", promote, pass_args=True, filters=Filters.group)
TITLE_HANDLER = CommandHandler("title", title, pass_args=True, filters=Filters.group)
DEMOTE_HANDLER = CommandHandler("demote", demote, pass_args=True, filters=Filters.group)

ADMINLIST_HANDLER = DisableAbleCommandHandler("adminlist", adminlist, filters=Filters.group)

dispatcher.add_handler(PIN_HANDLER)
dispatcher.add_handler(UNPIN_HANDLER)
dispatcher.add_handler(INVITE_HANDLER)
dispatcher.add_handler(PROMOTE_HANDLER)
dispatcher.add_handler(TITLE_HANDLER)
dispatcher.add_handler(DEMOTE_HANDLER)
dispatcher.add_handler(ADMINLIST_HANDLER)
