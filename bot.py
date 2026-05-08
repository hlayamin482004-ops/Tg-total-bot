import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ChatMemberStatus
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from database import init_db, get_user, create_user, update_total, set_agent, add_pending_bet, has_agent
from parser import calculate_bet, get_cashback_percent, normalize_agent, extract_agent_from_text

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]
GROUP_ID = int(os.getenv("GROUP_ID", "0")) if os.getenv("GROUP_ID") else None

logging.basicConfig(level=logging.INFO)

def is_admin(user_id):
    return user_id in ADMIN_IDS

async def get_group_admins(application, chat_id):
    try:
        admins = await application.bot.get_chat_administrators(chat_id)
        admin_mentions = []
        for admin in admins:
            if admin.user.username:
                admin_mentions.append(f"@{admin.user.username}")
            else:
                admin_mentions.append(f"<a href='tg://user?id={admin.user.id}'>{admin.user.first_name}</a>")
        return admin_mentions
    except:
        return []

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not get_user(user.id):
        create_user(user.id, user.username or user.first_name)
    await update.message.reply_text("Bot စတင်ပြီး။ /total နဲ့ ကြည့်ပါ။")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Commands:\n"
        "/total - ကိုယ်ပိုင် ledger ကြည့်\n"
        "/myagent - ကိုယ့် Agent ကြည့်\n\n"
        "Admin commands:\n"
        "/addbet [စာကြောင်း] - ထိုးငွေထည့်\n"
        "/setagent @username [agent] - Agent သတ်မှတ်\n"
        "/resetuser @username - User ကို ပြန်စမယ်"
    )

async def total(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = get_user(user.id)
    if not user_data:
        create_user(user.id, user.username or user.first_name)
        user_data = get_user(user.id)
    
    total_bet = user_data['total_bet']
    agent = user_data['agent']
    
    if agent is None:
        await update.message.reply_text("သင့်အတွက် Agent မသတ်မှတ်ရသေးပါ။ Admin ကို ဆက်သွယ်ပါ။")
        return
    
    percent = get_cashback_percent(agent)
    cashback = int(total_bet * percent / 100)
    final_amount = total_bet - cashback
    
    message = f"""👤 {user_data['username'] or user.first_name}
{agent} Total = {total_bet:,} ကျပ်
{percent}% Cash Back = {cashback:,} ကျပ်
လွဲရမည့်ငွေ = {final_amount:,} ကျပ်ဘဲ လွဲပါရှင့်
ကံကောင်းပါစေ"""
    
    await update.message.reply_text(message)

async def myagent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = get_user(user.id)
    if user_data and user_data['agent']:
        percent = get_cashback_percent(user_data['agent'])
        await update.message.reply_text(f"သင့် Agent: {user_data['agent']} ({percent}% Cashback)")
    else:
        await update.message.reply_text("သင့်အတွက် Agent မသတ်မှတ်ရသေးပါ။")

async def addbet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("Admin မဟုတ်ပါ")
        return
    
    if not context.args:
        await update.message.reply_text("ဥပမာ: /addbet 23 44 56ဒဲ့500R200")
        return
    
    # Reply to user ရှိမရှိ စစ်
    if not update.message.reply_to_message:
        await update.message.reply_text("User တစ်ယောက်ကို Reply လုပ်ပြီး /addbet ထည့်ပါ")
        return
    
    target_user = update.message.reply_to_message.from_user
    bet_text = " ".join(context.args)
    total_amount = calculate_bet(bet_text)
    
    if total_amount == 0:
        await update.message.reply_text("တွက်လို့မရပါ။ စာကြောင်းစစ်ပါ။")
        return
    
    user_data = get_user(target_user.id)
    if not user_data:
        create_user(target_user.id, target_user.username or target_user.first_name)
    
    # Agent ရှိရင် တိုက်ရိုက်ထည့်၊ မရှိရင် pending
    if has_agent(target_user.id):
        update_total(target_user.id, total_amount)
        await update.message.reply_text(f"✅ {target_user.first_name} အတွက် {total_amount:,} ကျပ် ထည့်ပြီး")
    else:
        add_pending_bet(target_user.id, bet_text, total_amount)
        # Group admin တွေကို mention လုပ်မယ်
        if update.message.chat_id == GROUP_ID or GROUP_ID is None:
            admins = await get_group_admins(context.application, update.message.chat_id)
            admin_mentions = " ".join(admins) if admins else "အုပ်စု Admin များ"
            await update.message.reply_text(
                f"{admin_mentions}\n"
                f"2d name မပါလို ဒါလေး လာစစ်ပေးပါရှင့်\n\n"
                f"📝 Bet: {bet_text}\n"
                f"👤 User: {target_user.first_name}\n"
                f"💰 Amount: {total_amount:,} ကျပ်\n\n"
                f"👉 /setagent @{target_user.username or target_user.first_name} [Du/Me/Maxi/Landon/Lao/Mm/Glo]"
            )
        else:
            await update.message.reply_text(f"⚠️ {target_user.first_name} အတွက် Agent မရှိသေးပါ။ /setagent နဲ့ သတ်မှတ်ပေးပါ။")

async def setagent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("Admin မဟုတ်ပါ")
        return
    
    if len(context.args) < 1:
        await update.message.reply_text("ဥပမာ: /setagent @username Du")
        return
    
    if not update.message.reply_to_message:
        await update.message.reply_text("User တစ်ယောက်ကို Reply လုပ်ပြီး /setagent ထည့်ပါ")
        return
    
    target_user = update.message.reply_to_message.from_user
    agent_raw = context.args[0]
    agent = normalize_agent(agent_raw)
    
    set_agent(target_user.id, agent)
    await update.message.reply_text(f"✅ {target_user.first_name} ကို {agent} Agent ({get_cashback_percent(agent)}%) သတ်မှတ်ပြီး")

async def resetuser(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("Admin မဟုတ်ပါ")
        return
    
    if not update.message.reply_to_message:
        await update.message.reply_text("User တစ်ယောက်ကို Reply လုပ်ပြီး /resetuser ထည့်ပါ")
        return
    
    target_user = update.message.reply_to_message.from_user
    user_data = get_user(target_user.id)
    if user_data:
        update_total(target_user.id, -user_data['total_bet'])
        await update.message.reply_text(f"✅ {target_user.first_name} ကို ပြန်စပြီး")

def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("total", total))
    app.add_handler(CommandHandler("myagent", myagent))
    app.add_handler(CommandHandler("addbet", addbet))
    app.add_handler(CommandHandler("setagent", setagent))
    app.add_handler(CommandHandler("resetuser", resetuser))
    
    app.run_polling()

if __name__ == "__main__":
    main()
