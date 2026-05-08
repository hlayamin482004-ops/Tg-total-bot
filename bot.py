import os
import re
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not set")

# ==================== AGENT ====================
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

# ==================== CALCULATION ====================
def get_numbers_count(text):
    """Count 1-2 digit numbers in text"""
    numbers = re.findall(r'\b\d{1,2}\b', text)
    return len(numbers)

def get_slots_and_amount(text, default_amount=0):
    """
    Returns (total_slots, amount_to_use) for a single bet expression
    """
    text_lower = text.lower().strip()
    
    # Extract amount from this expression
    amounts = re.findall(r'\b(\d{3,6})\b', text_lower)
    amount = int(amounts[-1]) if amounts else default_amount
    if amount == 0:
        return 0, 0
    
    n = get_numbers_count(text_lower)
    if n == 0:
        return 0, 0
    
    # Check for R (reverse)
    is_r = bool(re.search(r'[rအာ]', text_lower))
    
    # === KEYWORD CHECK ===
    # Pw / ပါဝါ (10)
    if re.search(r'pw|ပဝ|ပါဝါ|power', text_lower):
        slots = 10
    # နက္ခတ် / Nk (10)
    elif re.search(r'nk|နက|နခ|နက္ခတ်', text_lower):
        slots = 10
    # ပတ်သီး (19)
    elif re.search(r'ပတ်|အပါ|ပါ|ch|p', text_lower):
        slots = 19
    # ပတ်ပူး (20)
    elif re.search(r'ပတ်ပူး|ပူးပို|ထန|ထပ|ထိပ်ပိတ်|ထိပ်နောက်', text_lower):
        slots = 20
    # ထိပ် / Top / T (10)
    elif re.search(r'ထိပ်|ထ|top|t', text_lower):
        slots = 10
    # ဘရိတ် / Bk (10)
    elif re.search(r'ဘရိတ်|bk', text_lower):
        slots = 10
    # စုံဘရိတ် (50)
    elif re.search(r'စုံဘရိတ်|စုံbk|မbk|စုံBk|မဘရိတ်', text_lower):
        slots = 50
    # စမ / စစ (25)
    elif re.search(r'စမ|စစ|မမ|စုံစုံ|စုံမ', text_lower):
        slots = 25
    # စပူး (5)
    elif re.search(r'စပူး|စုံပူး|မပူး', text_lower):
        slots = 5
    # အပူးစုံ / ပူး (10)
    elif re.search(r'အပူးစုံ|အပူး|ပူး', text_lower):
        slots = 10
    # ဆယ်ပြည့် (10)
    elif re.search(r'ဆယ်ပြည့်|ဆယ်ပြည်', text_lower):
        slots = 10
    # ညီကို (20)
    elif re.search(r'ညီကို|ညီအကို', text_lower):
        slots = 20
    # ခွေပူး / ခပ (n x n)
    elif re.search(r'ခွေပူး|အပူးပါ|ခပ', text_lower):
        slots = n * n
    # ခွေ (n x (n-1))
    elif re.search(r'ခွေ|အခွေ|ခ', text_lower):
        slots = n * (n - 1) if n >= 2 else 0
    # ကပ် / ကို (a x b)
    elif re.search(r'ကပ်|အကပ်|ကို', text_lower):
        groups = re.findall(r'\b(\d{2,})\b', text_lower)
        if len(groups) >= 2:
            a = len(groups[0])
            b = len(groups[1])
            slots = a * b
        else:
            slots = 0
    else:
        # Default: direct bet
        slots = n
    
    if slots == 0:
        return 0, 0
    
    if is_r:
        # R means multiply by 2
        return slots * 2, amount
    else:
        return slots, amount


def calculate_total_bet(text):
    """
    Calculate total bet from multi-line or single line text
    Formula: (number_count × slot_per_keyword) × amount
    """
    text = text.strip()
    if not text:
        return 0
    
    total = 0
    current_amount = 0
    
    # Split by newline first
    lines = text.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Check if this line has an amount (3-6 digits)
        amounts_in_line = re.findall(r'\b(\d{3,6})\b', line)
        if amounts_in_line:
            current_amount = int(amounts_in_line[-1])
        
        # Split line by space, -, =, * for multiple bets
        parts = re.split(r'[\s\-=\*]+', line)
        
        for part in parts:
            part = part.strip()
            if not part or part.isdigit():
                continue
            
            slots, amt = get_slots_and_amount(part, current_amount)
            if slots > 0 and amt > 0:
                total += slots * amt
    
    return total


def extract_agent(text):
    """Extract agent from text (must appear as a separate word)"""
    words = text.lower().split()
    for w in words:
        if w in AGENT_ALIASES:
            return AGENT_ALIASES[w]
    return None


def get_cashback_percent(agent):
    return AGENT_PERCENT.get(agent, 7)


# ==================== BOT HANDLERS ====================
logging.basicConfig(level=logging.INFO)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    
    text = update.message.text.strip()
    user = update.effective_user
    name = user.username or user.first_name
    
    # Only respond if agent is present
    agent = extract_agent(text)
    if not agent:
        return
    
    total_bet = calculate_total_bet(text)
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
