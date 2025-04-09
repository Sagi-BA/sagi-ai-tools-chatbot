import os
import json
import random
from functools import lru_cache
import groq
from dotenv import load_dotenv

# טעינת משתני סביבה
load_dotenv()

# קביעת ה-API Key של Groq
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
# מודלים זמינים לשימוש, יוחלפו באופן אקראי אם אחד לא זמין
GROQ_MODELS = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile,llama3-70b-8192").split(",")
# מספר הטוקנים המקסימלי לתשובה
GROQ_MAX_TOKENS = int(os.getenv("GROQ_MAX_TOKENS", 2024))
# מספר ההודעות לשמירה בהיסטוריה
MAX_HISTORY_MESSAGES = int(os.getenv("MAX_HISTORY_MESSAGES", 5))

# אתחול הלקוח של Groq
groq_client = groq.Groq(api_key=GROQ_API_KEY)

# נתיב לקובץ של ההנחיות לכלי AI
TOOLS_PROMPTS_FILE = os.path.join("data", "tools_prompts.json")
TOOLS_FILE = os.path.join("data", "tools.json")

def load_tool_prompts():
    """טעינת הנחיות לכלי AI מקובץ JSON"""
    if os.path.exists(TOOLS_PROMPTS_FILE):
        with open(TOOLS_PROMPTS_FILE, 'r', encoding='utf-8') as file:
            return json.load(file)
    return {}

def save_tool_prompt(tool_name, prompt):
    """שמירת הנחייה לכלי AI בקובץ JSON"""
    prompts = load_tool_prompts()
    prompts[tool_name] = prompt
    os.makedirs(os.path.dirname(TOOLS_PROMPTS_FILE), exist_ok=True)
    with open(TOOLS_PROMPTS_FILE, 'w', encoding='utf-8') as file:
        json.dump(prompts, file, indent=2, ensure_ascii=False)

def load_tools_data():
    """טעינת נתוני כלים מקובץ JSON"""
    if os.path.exists(TOOLS_FILE):
        with open(TOOLS_FILE, 'r', encoding='utf-8') as file:
            return json.load(file)
    return []

def find_tool_in_local_data(tool_name):
    """חיפוש כלי בנתונים המקומיים והחזרת המידע עליו"""
    tools_data = load_tools_data()
    for tool in tools_data:
        if tool.get("name") == tool_name:
            return tool
    return None

def find_tools_in_local_data(tool_names):
    """חיפוש מספר כלים בנתונים המקומיים והחזרת המידע עליהם"""
    tools_data = load_tools_data()
    found_tools = []
    
    for tool_name in tool_names:
        for tool in tools_data:
            if tool.get("name") == tool_name:
                found_tools.append(tool)
                break
    
    return found_tools

# הסרנו את הדקורטור lru_cache כי הוא לא יכול לעבוד עם רשימות
def get_or_create_tool_prompt(tool_name):
    """קבלת הנחייה לכלי AI או יצירת הנחייה חדשה אם לא קיימת"""
    prompts = load_tool_prompts()
    if tool_name in prompts:
        return prompts[tool_name]
    
    # בדיקה אם קיים מידע בסיסי על הכלי בקובץ tools.json
    tool_info = find_tool_in_local_data(tool_name)
    
    # הכנת הנחייה למודל השפה
    if tool_info:
        # אם יש מידע מקומי, נשתמש בו כבסיס לבניית ההנחייה
        system_prompt = f"""Create a system prompt for an AI tool named {tool_name}.
        
        Here is some basic information about the tool:
        Description: {tool_info.get('description', 'Unknown')}
        Category: {tool_info.get('category', 'Unknown')}
        Rating: {tool_info.get('rating', 'Unknown')}
        
        Based on this information, expand the prompt to include:
        1. A detailed description of what the tool does
        2. Main capabilities of the tool
        3. Common use cases
        4. Known limitations and disadvantages
        5. Similar alternatives
        
        The prompt should be comprehensive and present the tool in a balanced way.
        
        Always answer in Hebrew and keep responses concise."""
    else:
        # אם אין מידע מקומי, נבקש מהמודל ליצור הנחייה מאפס
        system_prompt = f"""Create a system prompt for an AI tool named {tool_name}.
        The prompt should include:
        1. A detailed description of what the tool does
        2. Main capabilities of the tool
        3. Common use cases
        4. Known limitations and disadvantages
        5. Similar alternatives
        
        The prompt should be comprehensive and present the tool in a balanced way.
        
        Always answer in Hebrew and keep responses concise."""
    
    try:
        # ערבוב המודלים כדי להשתמש באחד הזמין
        random.shuffle(GROQ_MODELS)
        for model in GROQ_MODELS:
            try:
                response = groq_client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": "You are an expert in AI tools and advanced technologies."},
                    ],
                    model=model,
                    temperature=0.7,
                    max_tokens=GROQ_MAX_TOKENS,
                    stream=False,
                )
                new_prompt = response.choices[0].message.content
                save_tool_prompt(tool_name, new_prompt)
                return new_prompt
            except Exception as e:
                print(f"שגיאה עם מודל {model}: {str(e)}. מנסה מודל הבא.")
                continue
    except Exception as e:
        print(f"שגיאה ביצירת הנחייה עבור {tool_name}: {str(e)}")
        return f"מידע בסיסי על {tool_name}"

# הסרנו את הדקורטור lru_cache כי אנחנו עכשיו מעבירים רשימה
def ask_about_tool(tool_name, question, general_chat=False, conversation_history=None):
    """שאילת שאלה על כלי AI או שיחה כללית, עם תמיכה בהיסטוריית שיחה"""
    if general_chat:
        system_prompt = """You are a helpful and accurate information assistant. You are an expert in AI tools, machine learning models, 
        and software development. You answer in Hebrew and strive to provide accurate and useful information."""
    else:
        # בדיקה אם יש מידע מקומי על הכלי
        tool_info = find_tool_in_local_data(tool_name)
        tool_prompt = get_or_create_tool_prompt(tool_name)
        
        if tool_info:
            # הוספת מידע מקומי להנחייה
            system_prompt = f"""You are an expert in the tool {tool_name}. Here is information about the tool:
            
            Basic information:
            Description: {tool_info.get('description', 'Unknown')}
            Category: {tool_info.get('category', 'Unknown')}
            Rating: {tool_info.get('rating', 'Unknown')}
            URL: {tool_info.get('url', 'Unknown')}
            
            Additional information:
            {tool_prompt}
            
            Answer in Hebrew in a concise and accurate manner. If you don't have information, simply say so."""
        else:
            system_prompt = f"""You are an expert in the tool {tool_name}. Here is information about the tool:
            {tool_prompt}
            
            Answer in Hebrew in a concise and accurate manner. If you don't have information, simply say so."""

    # בניית ההודעות עם היסטוריית השיחה אם קיימת
    messages = [{"role": "system", "content": system_prompt}]
    
    if conversation_history and len(conversation_history) > 0:
        # הוספת היסטוריית השיחה להודעות
        messages.extend(conversation_history)
    
    # הוספת השאלה הנוכחית
    user_prompt = f"Question about {tool_name if not general_chat else 'AI tools'}: {question}"
    messages.append({"role": "user", "content": user_prompt})
    
    # ערבוב המודלים כדי להשתמש באחד הזמין
    random.shuffle(GROQ_MODELS)
    
    for model in GROQ_MODELS:
        try:
            response = groq_client.chat.completions.create(
                messages=messages,
                model=model,
                temperature=0.7,
                max_tokens=GROQ_MAX_TOKENS,
                stream=False,
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"שגיאה עם מודל {model}: {str(e)}. מנסה מודל הבא.")
            continue
    
    # אם כל המודלים נכשלו
    return "מצטער, לא הצלחתי לקבל תשובה כרגע. אנא נסה שוב מאוחר יותר."

def ask_about_multiple_tools(tools, question, conversation_history=None):
    """שאילת שאלה על מספר כלי AI, עם תמיכה בהיסטוריית שיחה"""
    tools_str = ", ".join(tools)
    
    # איסוף מידע מקומי על הכלים
    tools_info = find_tools_in_local_data(tools)
    tools_details = ""
    
    if tools_info:
        # הכנת מידע מפורט על הכלים מהנתונים המקומיים
        for tool in tools_info:
            tools_details += f"""
            כלי: {tool.get('name', 'Unknown')}
            תיאור: {tool.get('description', 'Unknown')}
            קטגוריה: {tool.get('category', 'Unknown')}
            דירוג: {tool.get('rating', 'Unknown')}
            URL: {tool.get('url', 'Unknown')}
            """
    
    system_prompt = f"""אתה מומחה בכלי AI, במיוחד: {tools_str}.
    
    מידע בסיסי על הכלים:
    {tools_details}
    
    אתה עונה בעברית ובצורה תמציתית ומדויקת. נסה להשוות בין הכלים כאשר רלוונטי."""
    
    # בניית ההודעות עם היסטוריית השיחה אם קיימת
    messages = [{"role": "system", "content": system_prompt}]
    
    if conversation_history and len(conversation_history) > 0:
        # הוספת היסטוריית השיחה להודעות
        messages.extend(conversation_history)
    
    # הוספת השאלה הנוכחית
    user_prompt = f"שאלה על הכלים הבאים: {tools_str}. השאלה: {question}"
    messages.append({"role": "user", "content": user_prompt})
    
    # ערבוב המודלים כדי להשתמש באחד הזמין
    random.shuffle(GROQ_MODELS)
    
    for model in GROQ_MODELS:
        try:
            response = groq_client.chat.completions.create(
                messages=messages,
                model=model,
                temperature=0.1,
                max_tokens=GROQ_MAX_TOKENS,
                stream=False,
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"שגיאה עם מודל {model}: {str(e)}. מנסה מודל הבא.")
            continue
    
    # אם כל המודלים נכשלו
    return "מצטער, לא הצלחתי לקבל תשובה כרגע. אנא נסה שוב מאוחר יותר."