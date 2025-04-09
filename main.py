import streamlit as st
import random
import time
import json
import os
import requests
from datetime import datetime, timedelta
import pathlib
from dotenv import load_dotenv

# טעינת מודול הלקוח של Groq
from groq_client import ask_about_tool, ask_about_multiple_tools

# הוספת CSS מותאם אישית לתמיכה ב-RTL
st.markdown("""
<style>
    body {
        direction: rtl;
    }
    .stTextInput, .stButton, p, h1, h2, h3, .stMarkdown, .stChatMessage, .stChatInput, .stSelectbox, .stMultiSelect {
        direction: rtl;
        text-align: right;
    }
    .stChatMessageContent {
        text-align: right;
        direction: rtl;
    }
    .stMultiSelect [data-baseweb=select] span {
        text-align: right;
        direction: rtl;
    }
</style>
""", unsafe_allow_html=True)

# טעינת משתני סביבה מקובץ .env
load_dotenv()

# קביעת מספר ההודעות המקסימלי לשמירה בהיסטוריה
MAX_HISTORY_MESSAGES = int(os.getenv("MAX_HISTORY_MESSAGES", 5))

# יצירת ספריית data אם היא לא קיימת
DATA_DIR = pathlib.Path("data")
DATA_DIR.mkdir(exist_ok=True)

TOOLS_FILE = DATA_DIR / "tools.json"
CONFIG_FILE = DATA_DIR / "config.json"

# קריאת כתובת ה-URL מקובץ .env
AI_TOOLS_URL = os.getenv("AI_TOOLS_URL", "https://thewitcher-sagi-ai-tools.static.hf.space/tools.json")

# פונקציה לבדיקה האם הקובץ התעדכן היום
def is_file_updated_today():
    if not CONFIG_FILE.exists():
        return False
    
    try:
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
        
        last_update_str = config.get("last_update")
        if not last_update_str:
            return False
        
        last_update = datetime.strptime(last_update_str, "%Y-%m-%d")
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        return last_update == today
    except Exception as e:
        st.error(f"שגיאה בקריאת קובץ התצורה: {e}")
        return False

# פונקציה להורדת קובץ הכלים
def download_tools_file():
    try:
        response = requests.get(AI_TOOLS_URL)
        response.raise_for_status()
        
        # שמירת תוכן הקובץ
        with open(TOOLS_FILE, "wb") as f:
            f.write(response.content)
        
        # עדכון הגדרות
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        config = {"last_update": today.strftime("%Y-%m-%d")}
        
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f)
        
        return True
    except Exception as e:
        st.error(f"שגיאה בהורדת קובץ הכלים: {e}")
        return False

# פונקציה לטעינת רשימת הכלים
def load_tools():
    try:
        if not TOOLS_FILE.exists() or not is_file_updated_today():
            if not download_tools_file():
                if not TOOLS_FILE.exists():
                    return []
        
        with open(TOOLS_FILE, "r", encoding="utf-8") as f:
            tools_data = json.load(f)
        
        # החזרת רשימת שמות הכלים
        tools = []
        if isinstance(tools_data, list):
            tools = [tool.get("name", "") for tool in tools_data if tool.get("name")]
        elif isinstance(tools_data, dict) and "tools" in tools_data:
            tools = [tool.get("name", "") for tool in tools_data["tools"] if tool.get("name")]
        
        return tools
    except Exception as e:
        st.error(f"שגיאה בטעינת רשימת הכלים: {e}")
        return []

# פונקציה להכנת היסטוריית שיחה לשליחה למודל השפה
def prepare_conversation_history(messages, max_history=MAX_HISTORY_MESSAGES):
    """הכנת היסטוריית שיחה לשליחה למודל השפה"""
    if not messages or len(messages) < 2:  # אם אין מספיק הודעות להיסטוריה
        return []
    
    # בחירת ההודעות האחרונות (עד למקסימום שהוגדר)
    recent_messages = messages[-max_history*2:] if len(messages) > max_history*2 else messages
    
    # המרת הודעות לפורמט המתאים ל-API
    conversation_history = []
    for msg in recent_messages:
        if msg["role"] in ["user", "assistant"]:
            conversation_history.append({"role": msg["role"], "content": msg["content"]})
    
    return conversation_history

# טעינת רשימת הכלים
tools = load_tools()

# הצגת מידע על הכלים
if tools:
    st.info(f"נמצאו {len(tools)} כלים זמינים להתייעצות")
else:
    st.warning("לא נמצאו כלים זמינים. בדוק את החיבור לאינטרנט ונסה שוב.")

# יצירת בחירת כלים מרובים
tool_options = ["שיחה כללית"] + tools
selected_tools = st.multiselect("בחר כלים לשיחה (ניתן לבחור יותר מאחד):", tool_options, default=["שיחה כללית"])

if "שיחה כללית" in selected_tools:
    if len(selected_tools) > 1:
        st.info("מצב שיחה כללית וגם על כלים ספציפיים")
        tools_str = ", ".join([tool for tool in selected_tools if tool != "שיחה כללית"])
        st.write(f"כלים שנבחרו: {tools_str}")
    else:
        st.info("מצב שיחה כללית - אפשר לשוחח על כל נושא!")
else:
    tools_str = ", ".join(selected_tools)
    st.info(f"מצב שיחה על הכלים: {tools_str}")

# אתחול היסטוריית צ'אט
if "messages" not in st.session_state:
    st.session_state.messages = []

# איתחול הודעת פתיחה לפי הכלים שנבחרו
if not st.session_state.messages:
    if "שיחה כללית" in selected_tools and len(selected_tools) == 1:
        st.session_state.messages = [{"role": "assistant", "content": "הי,  \nשמי ברק הראל ואני העוזר האישי של שגיא בר און.  \nאשמח לענות על שאלות בנושא ארגז כלי בינה מלאכותית ששגיא המליץ, שימושים שלהם, והשוואות ביניהם. אז במה אוכל לעזור לך היום? 👋"}]
    elif "שיחה כללית" in selected_tools:
        tools_str = ", ".join([tool for tool in selected_tools if tool != "שיחה כללית"])
        st.session_state.messages = [{"role": "assistant", "content": f"ברוך הבא! אשמח לשוחח על נושאים כלליים בתחום ה-AI וגם על הכלים הספציפיים: {tools_str}. אתה יכול לשאול על יכולות, הבדלים בין כלים, מקרי שימוש או כל נושא אחר 👋"}]
    else:
        tools_str = ", ".join(selected_tools)
        st.session_state.messages = [{"role": "assistant", "content": f"ברוך הבא לשיחה על הכלים: {tools_str}! אשמח לענות על שאלות לגבי יכולות, מגבלות, יתרונות וחסרונות של כלים אלו 👋"}]

# הצגת הודעות צ'אט מההיסטוריה
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# קבלת קלט מהמשתמש
if prompt := st.chat_input("הקלד את שאלתך כאן..."):
    # הוספת הודעת משתמש להיסטוריית הצ'אט
    st.session_state.messages.append({"role": "user", "content": prompt})
    # הצגת הודעת המשתמש במיכל הצ'אט
    with st.chat_message("user"):
        st.markdown(prompt)

    # הכנת היסטוריית השיחה לשליחה למודל
    conversation_history = prepare_conversation_history(st.session_state.messages[:-1])  # לא כולל השאלה הנוכחית

    # הצגת תגובת הבוט במיכל הצ'אט
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        
        # קבלת תשובה באמצעות Groq API
        with st.spinner('מחפש תשובה...'):
            if "שיחה כללית" in selected_tools and len(selected_tools) == 1:
                # מצב שיחה כללית בלבד
                response = ask_about_tool("AI Tools", prompt, general_chat=True, conversation_history=conversation_history)
            elif "שיחה כללית" in selected_tools:
                # מצב משולב - שיחה כללית וכלים ספציפיים
                specific_tools = [tool for tool in selected_tools if tool != "שיחה כללית"]
                response = ask_about_multiple_tools(specific_tools, prompt, conversation_history=conversation_history)
            elif len(selected_tools) == 1:
                # כלי אחד בלבד
                response = ask_about_tool(selected_tools[0], prompt, conversation_history=conversation_history)
            else:
                # מספר כלים
                response = ask_about_multiple_tools(selected_tools, prompt, conversation_history=conversation_history)
        
        # סימולציה של זרימת תשובה עם השהייה קצרה
        for chunk in response.split():
            full_response += chunk + " "
            time.sleep(0.01)  # השהייה קצרה יותר כי התשובות ארוכות יותר
            # הוספת סמן מהבהב לסימולציית הקלדה
            message_placeholder.markdown(full_response + "▌")
        message_placeholder.markdown(full_response)
    
    # הוספת תגובת הבוט להיסטוריית הצ'אט
    st.session_state.messages.append({"role": "assistant", "content": full_response})