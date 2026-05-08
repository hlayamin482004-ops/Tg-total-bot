import os
import re
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not set")

# ==================== AGENT CONFIG ====================
AGENT_PERCENT = {
    'Du': 7, 'Me': 7, 'Maxi': 7, 'Landon': 7, 'Lao': 7,
    'Mm': 10, 'Glo': 3
}

AGENT_ALIASES = {
    'du': 'Du', 'dubai': 'Du', 'ဒူ': 'Du', 'ဒူဘိုင်း': 'Du',
    'me': 'Me', 'mega': 'Me', 'မီ': 'Me', 'မီဂါ': 'Me',
    'maxi': 'Maxi', 'max': 'Maxi', 'မက်ဆီ': 'Maxi', 'မက်စီ': 'Maxi', 'စီစီ': 'Maxi',
    'landon': 'Landon', 'london': 'Landon', 'လန်လန်': 'Landon', 'လန်ဒန်': 'Landon', 'ld': 'Landon',
    'lao': 'Lao', 'loa': 'Lao', 'loadon': 'Lao', 'laodon': 'Lao', 'လာလာ': 'Lao', 'လာအို': 'Lao',
    'mm': 'Mm',
    'glo': 'Glo', 'global': 'Glo', 'ဂလို': 'Glo'
}

# ==================== KEYWORD SLOTS ====================
KEYWORD_SLOTS = {
    # ပုံသေ အကွက်ရေ 10
    'ပါဝါ': 10, 'ပဝ': 10, 'pw': 10, 'power': 10,
    'နက္ခတ်': 10, 'nk': 10, 'နက': 10, 'နခ': 10,
    'ဘရိတ်': 10, 'bk': 10,
    'ထိပ်': 10, 'ထ': 10, 'top': 10, 't': 10,
    'အပူးစုံ': 10, 'အပူး': 10, 'ပူး': 10,
    'ဆယ်ပြည့်': 10, 'ဆယ်ပြည်': 10,
    # ပုံသေ 20
    'ညီကို': 20, 'ညီအကို': 20,
    'ပတ်ပူး': 20, 'ပူးပို': 20, 'ထန': 20, 'ထပ': 20, 'ထိပ်ပိတ်': 20, 'ထိပ်နောက်': 20,
    # ပုံသေ 19
    'ပတ်သီး': 19, 'အပါ': 19, 'ပါ': 19, 'ch': 19, 'p': 19,
    # ပုံသေ 25
    'စမ': 25, 'စစ': 25, 'မမ': 25, 'စုံစုံ': 25, 'စုံမ': 25,
    # ပုံသေ 50
    'စုံဘရိတ်': 50, 'စုံbk': 50, 'မbk': 50, 'မဘရိတ်': 50,
    # ပုံသေ 5
    'စပူး': 5, 'စုံပူး': 5, 'မပူး': 5,
}

def get_slots_from_text(text):
    """Return (slot_count, is_r, direct_amount, r_amount) from text"""
    text_lower = text.lower()
    
    # Check for R
    is_r = bool(re.search(r'[rအာ]', text_lower))
    
    # Extract amount
    amounts = re.findall(r'\b(\d{3,6})\b', text_lower)
    amounts = [int(a) for a in amounts if int(a) > 0]
    
    direct_amount = amounts[0] if len(amounts) > 0 else 0
    r_amount = amounts[1] if len(amounts) > 1 else 0
    
    # Check each keyword
    for kw, slots in KEYWORD_SLOTS.items():
        if kw in text_lower:
            return slots, is_r, direct_amount, r_amount
    
    # Check for ခွေပူး / ခပ
    if re.search(r'ခွေပူး|အပူးပါ|ခပ', text_lower):
        numbers = re.findall(r'\b\d{1,2}\b', text_lower)
        n = len(numbers)
        return (n * n), is_r, direct_amount, r_amount
    
    # Check for ခွေ
    if re.search(r'ခွေ|အခွေ|ခ', text_lower):
        numbers = re.findall(r'\b\d{1,2}\b', text_lower)
        n = len(numbers)
        if n >= 2:
            return (n * (n - 1)), is_r, direct_amount, r_amount
        return 0, is_r, direct_amount, r_amount
    
    # Check for ကပ် / ကို
    if re.search(r'ကပ်|အကပ်|ကို', text_lower):
        groups = re.findall(r'\b(\d{2,})\b', text_lower)
        if len(groups) >= 2:
            a = len(groups[0])
            b = len(groups[1])
            slots = a * b
            return slots, is_r, direct_amount, r_amount
    
    # Default: direct bet
    numbers = re.findall(r'\b\d{1,2}\b', text_lower)
    n = len(numbers)
    if n == 0:
        return 0, is_r, direct_amount, r_amount
    return n, is_r, direct_amount, r_amount


def extract_agent(text):
    words = text.lower().split()
    for w in words:
        if w in AGENT_ALIASES:
            return AGENT_ALIASES[w]
    return None


def get_cashback_percent(agent):
    return AGENT_PERCENT.get(agent, 7)


def calculate_line(text):
    """Calculate total amount for one bet line"""
    text = text.strip()
    if not text:
        return 0
    
    # Extract amount from the line (last 3-6 digit number)
    amounts = re.findall(r'\b(\d{3,6})\b', text)
    if not amounts:
        return 0
    
    line_amount = int(amounts[-1])
    
    # Split by space, -, =, * for multiple bets in one line
    parts = re.split(r'[\s\-=\*]+', text)
    
    total = 0
    for part in parts:
        if part == '' or part.isdigit():
            continue
        slots, is_r, direct_amt, r_amt = get_slots_from_text(part)
        if slots == 0:
            continue
        
        if is_r and direct_amt > 0 and r_amt > 0:
            # Both direct and R amounts present
            total += (slots * direct_amt) + (slots * r_amt)
        elif is_r:
            total += slots * line_amount
        else:
            total += slots * line_amount
    
    return total


def calculate_multiline(text):
    """Calculate total for multiline bet (separated by newline)"""
    lines = text.strip().split('\n')
    total = 0
    last_amount = 0
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Check if this line has its own amount
        amounts = re.findall(r'\b(\d{3,6})\b', line)
        if amounts:
            last_amount = int(amounts[-1])
        
        # Calculate this line
        line_total = calculate_line(line)
        total += line_total
    
    return total


# ==================== BOT ====================
logging.basicConfig(level=logging.INFO)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    
    text = update.message.text.strip()
    user = update.effective_user
    name = user.username or user.first_name
    
    # Check for agent
    agent = extract_agent(text)
    if not agent:
        return
    
    # Calculate total
    total_bet = calculate_multiline(text)
    if total_bet == 0:
        await update.message.reply_text("တွက်လို့မရပါ။ စာကြောင်းစစ်ပါ။")
        return
    
    percent = get_cashback_percent(agent)
    cashback = int(total_bet * percent / 100)
    final_total = total_bet - cashback
    
    reply = f"""👤 {name}
{agent} Total = {total_bet:,} ကျပ်
{percent}% Cash Back = {cashback:,} ကျပ်
Total = {final_total:,} ကျပ်ဘဲ လွဲပါရှင့်
ကံကောင်းပါစေ💞"""
    
    await update.message.reply_text(reply)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bot ready! Agent (Me/Du/Glo) ပါတဲ့ Bet ရေးပါ။")


def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()


if __name__ == "__main__":
    main()
