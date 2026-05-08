import re

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
    'mm': 'Mm', 'mm': 'Mm',
    'glo': 'Glo', 'global': 'Glo', 'ဂလို': 'Glo'
}

def extract_agent_from_text(text):
    words = text.lower().split()
    for word in words:
        if word in AGENT_ALIASES:
            return AGENT_ALIASES[word]
    return None

def normalize_agent(agent_text):
    return AGENT_ALIASES.get(agent_text.lower(), 'Du')

def get_cashback_percent(agent):
    return AGENT_PERCENT.get(agent, 7)

def extract_numbers_from_text(text):
    numbers = re.findall(r'\d{1,2}(?=\D|$)', text)
    numbers = [n for n in numbers if len(n) in [1, 2]]
    return list(dict.fromkeys(numbers))

def calculate_bet(text):
    text = text.strip()
    
    numbers = extract_numbers_from_text(text)
    n = len(numbers)
    if n == 0:
        return 0
    
    is_r = bool(re.search(r'[Rrအာ]', text))
    has_direct = bool(re.search(r'[-=ဒဲ့]', text))
    
    amount_match = re.findall(r'(\d+)(?:\D|$)', text)
    amounts = [int(a) for a in amount_match if int(a) > 0 and int(a) < 1000000]
    
    if not amounts:
        return 0
    
    if has_direct and is_r:
        direct_amount = amounts[0] if len(amounts) > 0 else 0
        r_amount = amounts[1] if len(amounts) > 1 else 0
        total_amount = direct_amount + r_amount
        total_slots = n * 2
        return total_slots * total_amount
    elif is_r:
        amount = amounts[0] if amounts else 0
        total_slots = n * 2
        return total_slots * amount
    else:
        amount = amounts[0] if amounts else 0
        return n * amount
