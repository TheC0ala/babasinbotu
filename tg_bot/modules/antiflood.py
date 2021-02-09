import html
from typing import Optional, List

from telegram import Message, Chat, User, ParseMode, Update, Bot
from telegram.error import BadRequest
from telegram.ext import Filters, MessageHandler, CommandHandler, run_async
from telegram.utils.helpers import mention_html

from tg_bot import dispatcher
from tg_bot.modules.helper_funcs.chat_status import is_user_admin, user_admin
from tg_bot.modules.helper_funcs.string_handling import extract_time
from tg_bot.modules.log_channel import loggable
from tg_bot.modules.sql import antiflood_sql as sql
from tg_bot.modules.connection import connected

from tg_bot.modules.helper_funcs.alternate import send_message

FLOOD_GROUP = 3


@run_async
@loggable
def check_flood(bot: Bot, update: Update) -> str:
    user = update.effective_user  # type: Optional[User]
    chat = update.effective_chat  # type: Optional[Chat]
    msg = update.effective_message  # type: Optional[Message]

    if not user:  # ignore channels
        return ""

    # ignore admins
    if is_user_admin(chat, user.id):
        sql.update_flood(chat.id, None)
        return ""

    should_ban = sql.update_flood(chat.id, user.id)
    if not should_ban:
        return ""

    try:
        getmode, getvalue = sql.get_flood_setting(chat.id)
        if getmode == 1:
            chat.kick_member(user.id)
            execstrings = "Banned"
            tag = "BANNED"
        elif getmode == 2:
            chat.kick_member(user.id)
            chat.unban_member(user.id)
            execstrings = "Kicked"
            tag = "KICKED"
        elif getmode == 3:
            bot.restrict_chat_member(chat.id, user.id, can_send_messages=False)
            
            execstrings = "Muted"
            tag = "MUTED"
        elif getmode == 4:
            bantime = extract_time(msg, getvalue)
            chat.kick_member(user.id, until_date=bantime)
            execstrings = "Banned for {}".format(getvalue)
            tag = "TBAN"
        elif getmode == 5:
            mutetime = extract_time(msg, getvalue)
            bot.restrict_chat_member(chat.id, user.id, can_send_messages=False, until_date=mutetime)
            
            execstrings = "Səssizləşdirildi {}".format(getvalue)
            tag = "TMUTE"
        send_message(
            update.effective_message,
            "Flood ?"
            "sən sadəcə bir uğursuzluq idin... {}!".format(execstrings),
        )

        return (
            "<b>{}:</b>"
            "\n#FLOOD{}"
            "\n<b>User:</b> {}"
            "\nQrup.".format(
                tag, html.escape(chat.title), mention_html(user.id, user.first_name)
            )
        )

    except BadRequest:
        msg.reply_text(
            "Bunu edə bilməyim üçün əvvəlcə mənə lazımlı yətkiləri verməlisən! Lazım olan yetkilər verilənə qədər bu funksiya deaktiv edildi!."
        )
        sql.set_flood(chat.id, 0)
        return (
            "<b>{}:</b>"
            "\n#INFO"
            "\nLazım olan yetkilər açıə olmadığına görə funksiya deaktiv edildi!".format(
                chat.title
            )
        )


@run_async
@user_admin
@loggable
def set_flood(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    message = update.effective_message  # type: Optional[Message]

    conn = connected(bot, update, chat, user.id, need_admin=True)
    if conn:
        chat_id = conn
        chat_name = dispatcher.bot.getChat(conn).title
    else:
        if update.effective_message.chat.type == "private":
            send_message(
                update.effective_message,
                "Bu əmr PM'də işləməz!",
            )
            return ""
        chat_id = update.effective_chat.id
        chat_name = update.effective_message.chat.title

    if len(args) >= 1:
        val = args[0].lower()
        if val in ["off", "no", "0"]:
            sql.set_flood(chat_id, 0)
            if conn:
                text = message.reply_text(
                    "AntiFlood {} qrupunda deaktiv edildi.".format(chat_name)
                )
            else:
                text = message.reply_text("AntiFlood deaktiv edildi.")
            send_message(message, text, parse_mode="markdown")

        elif val.isdigit():
            amount = int(val)
            if amount <= 0:
                sql.set_flood(chat_id, 0)
                if conn:
                    text = message.reply_text(
                        "AntiFlood {} qrupunda deaktiv edildi.".format(chat_name)
                    )
                else:
                    text = message.reply_text("AntiFlood deaktiv edildi.")
                return (
                    "<b>{}:</b>"
                    "\n#SETFLOOD"
                    "\n<b>Admin:</b> {}"
                    "\nAntiFlood Deaktiv Edildi".format(
                        html.escape(chat_name), mention_html(user.id, user.first_name)
                    )
                )

            elif amount < 3:
                send_message(
                    message,
                    "AntiFlood 0 (deaktiv) ən az 3-dən böyük olmalıdır!",
                )
                return ""

            else:
                sql.set_flood(chat_id, amount)
                if conn:
                    text = message.reply_text(
                        "Anti-flood qrupda {} ayarlandı: {}".format(
                            amount, chat_name
                        )
                    )
                else:
                    text = message.reply_text(
                        "AntiFlood uğurla *{}* güncəlləndi!".format(amount)
                    )
                send_message(message, text, parse_mode="markdown")
                return (
                    "<b>{}:</b>"
                    "\n#SETFLOOD"
                    "\n<b>Admin:</b> {}"
                    "\nAntiFlood <code>{}</code>.".format(
                        html.escape(chat_name),
                        mention_html(user.id, user.first_name),
                        amount,
                    )
                )

        else:
            message.reply_text("Keçərsiz arqument, 'off' or 'no'")
    else:
        message.reply_text(
            (
                "`/setflood rəqəm` AntiFlood aktivləşdir.\nVə ya`/setflood off` AntiFlood deaktivləşdir."
            ),
            parse_mode="markdown",
        )
    return ""


@run_async
@user_admin
@loggable
def flood(bot: Bot, update: Update):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    msg = update.effective_message

    conn = connected(bot, update, chat, user.id, need_admin=False)
    if conn:
        chat_id = conn
        chat_name = dispatcher.bot.getChat(conn).title
    else:
        if update.effective_message.chat.type == "private":
            send_message(
                update.effective_message,
                "Bu əmr PM'də işləməz! Qrupda yazın!",
            )
            return
        chat_id = update.effective_chat.id
        chat_name = update.effective_message.chat.title

    limit = sql.get_flood_limit(chat_id)
    if limit == 0:
        if conn:
            text = msg.reply_text(
                "{}'da Flood yoxlanışı etmirəm!".format(chat_name)
            )
        else:
            text = msg.reply_text("Burda hər hansı Flood yoxlanışı etmirəm")
    else:
        if conn:
            text = msg.reply_text(
                "Hal hazırda {}'da arxa arxaya {} mesaj yazan isdifadəçiləri susdururam.".format(
                    limit, chat_name
                )
            )
        else:
            text = msg.reply_text(
                "Hal hazırda {} mesajdan sonra isdifadəçiləri susdururam.".format(
                    limit
                )
            )

    send_message(update.effective_message, text, parse_mode="markdown")


@run_async
@user_admin
@loggable
def set_flood_mode(bot: Bot, update: Update, args: List[str]):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    msg = update.effective_message  # type: Optional[Message]
    

    conn = connected(bot, update, chat, user.id, need_admin=True)
    if conn:
        chat = dispatcher.bot.getChat(conn)
        chat_id = conn
        chat_name = dispatcher.bot.getChat(conn).title
    else:
        if update.effective_message.chat.type == "private":
            send_message(
                update.effective_message,
                "Bu əmr PM'də işləməz! Qrupda yaz!",
            )
            return ""
        chat = update.effective_chat
        chat_id = update.effective_chat.id
        chat_name = update.effective_message.chat.title

    if args:
        if args[0].lower() == "ban":
            settypeflood = "ban"
            sql.set_flood_strength(chat_id, 1, "0")
        elif args[0].lower() == "kick":
            settypeflood = "kick"
            sql.set_flood_strength(chat_id, 2, "0")
        elif args[0].lower() == "mute":
            settypeflood = "mute"
            sql.set_flood_strength(chat_id, 3, "0")
        elif args[0].lower() == "tban":
            if len(args) == 1:
                teks = """AntiFlood üçün zaman dəyərini ayarlamağa çalışmısız amma edə bilməmisiz. Yoxlayın, `/setfloodmode tban <vaxt dəyəri>`.

Nümunə: 4m = 4 minutes, 3h = 3 hours, 6d = 6 days, 5w = 5 weeks."""
                send_message(update.effective_message, teks, parse_mode="markdown")
                return
            settypeflood = "tban for {}".format(args[1])
            sql.set_flood_strength(chat_id, 4, str(args[1]))
        elif args[0].lower() == "tmute":
            if len(args) == 1:
                teks = """AntiFlood üçün zaman dəyərini ayarlamağa çalışmısız amma edə bilməmisiz. Yoxlayın, `/setfloodmode tmute <vaxt dəyəri>`.

Nümunə: 4m = 4 minutes, 3h = 3 hours, 6d = 6 days, 5w = 5 weeks."""
                send_message(update.effective_message, teks, parse_mode="markdown")
                return
            settypeflood = "tmute for {}".format(args[1])
            sql.set_flood_strength(chat_id, 5, str(args[1]))
        else:
            send_message(
                update.effective_message, "Sadəcə ban/kick/mute/tban/tmute yazın."
            )
            return
        if conn:
            text = msg.reply_text(
                "Ardıcıl Flood limtini aşmaə {} {} ilə nəticələnəcəkdir!".format(
                    settypeflood, chat_name
                )
            )
        else:
            text = msg.reply_text(
                "Ardıcıl Flood limitini aşmaq {} ilə nəticələnəcək!".format(
                    settypeflood
                )
            )
        send_message(message, text, parse_mode="markdown")
        return (
            "<b>{}:</b>\n"
            "<b>Admin:</b> {}\n"
            "AntiFlood modu dəyişdi. İsdifadəçi olaraq {}.".format(
                settypeflood,
                html.escape(chat.title),
                mention_html(user.id, user.first_name),
            )
        )
    else:
        getmode, getvalue = sql.get_flood_setting(chat.id)
        if getmode == 1:
            settypeflood = "ban"
        elif getmode == 2:
            settypeflood = "kick"
        elif getmode == 3:
            settypeflood = "mute"
        elif getmode == 4:
            settypeflood = "tban for {}".format(getvalue)
        elif getmode == 5:
            settypeflood = "tmute for {}".format(getvalue)
        if conn:
            text = msg.reply_text(
                "Sending more messages than flood limit will result in {} in {}.".format(
                    settypeflood, chat_name
                )
            )
        else:
            text = msg.reply_text(
                "AntiFlood limitindən çox mesaj göndərən {} ilə nəticələnəcək.".format(
                    settypeflood
                )
            )
        send_message(update.effective_message, text, parse_mode=ParseMode.MARKDOWN)
    return ""


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    limit = sql.get_flood_limit(chat_id)
    if limit == 0:
        return "Flood yoxlanması."
    else:
        return "AntiFlood  `{}`  olaraq ayarlandı.".format(limit)


__help__ = """
AntiFlood funksiyasını  köməyi ilə qrupunuza Flood edənlərə qarşı tədbir ala bilərsiz.

 × /flood: hazırkı Flood limitini göstərər

*Adminlər Üçün*:

 × /setflood <int/'no'/'off'>: AntiFlood modunu aktiv/deaktiv edər
 × /setfloodmode <ban/kick/mute/tban/tmute> <value>: AntiFlood limitini aşanlara nə edilsin. ban/kick/mute/tmute/tban

 *NOT*
 - TBan və TMute üçün bir dəyər vermək məcburidir!!

 It can be:
 5m = 5 dəqiqə
 6h = 6 saat
 3d = 3 gün
 1w = 1 həftə
 """

__mod_name__ = "Antiflood"

FLOOD_BAN_HANDLER = MessageHandler(
    Filters.all & ~Filters.status_update & Filters.group, check_flood
)
SET_FLOOD_HANDLER = CommandHandler(
    "setflood", set_flood, pass_args=True
)  # , filters=Filters.group)
SET_FLOOD_MODE_HANDLER = CommandHandler(
    "setfloodmode", set_flood_mode, pass_args=True
)  # , filters=Filters.group)
FLOOD_HANDLER = CommandHandler("flood", flood)  # , filters=Filters.group)

dispatcher.add_handler(FLOOD_BAN_HANDLER, FLOOD_GROUP)
dispatcher.add_handler(SET_FLOOD_HANDLER)
dispatcher.add_handler(SET_FLOOD_MODE_HANDLER)
dispatcher.add_handler(FLOOD_HANDLER)
