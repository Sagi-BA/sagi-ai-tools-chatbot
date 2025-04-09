import streamlit as st
import time

# הגדרת כותרת הדף ותצורת העמוד
st.set_page_config(
    page_title="צ'אטבוט",
    page_icon="💬",
    layout="centered"
)

# הוספת CSS מותאם אישית לתמיכה ב-RTL ועיצוב
st.markdown("""
<style>
    body {
        direction: rtl;
    }
    .stTextInput, .stButton {
        direction: rtl;
    }
    .chat-container {
        display: flex;
        flex-direction: column;
    }
    .user-bubble {
        background-color: #3b82f6;
        color: white;
        padding: 10px 14px;
        border-radius: 20px;
        border-bottom-right-radius: 0;
        margin: 5px 0;
        margin-left: auto;
        max-width: 80%;
        align-self: flex-end;
    }
    .bot-bubble {
        background-color: #e5e7eb;
        color: #111827;
        padding: 10px 14px;
        border-radius: 20px;
        border-bottom-left-radius: 0;
        margin: 5px 0;
        margin-right: auto;
        max-width: 80%;
        align-self: flex-start;
    }
    .stApp {
        background-color: #f3f4f6;
    }
    .header {
        background: linear-gradient(90deg, #3b82f6, #8b5cf6);
        padding: 16px;
        color: white;
        font-weight: bold;
        border-radius: 5px;
        margin-bottom: 20px;
        text-align: center;
    }
    .main-container {
        background-color: white;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
    }
</style>
""", unsafe_allow_html=True)

# הצגת הכותרת
st.markdown('<div class="header">צ\'אט עם הבינה של שגיא</div>', unsafe_allow_html=True)

# אתחול היסטוריית הצ'אט בסשן אם לא קיימת
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "שלום! איך אפשר לעזור לך היום?"}
    ]

# פונקציה להחזרת תגובת הבוט
def get_bot_response(user_input):
    # כאן תוכל לשלב לוגיקה אמיתית או חיבור ל-AI
    return 'זוהי תגובה אוטומטית :)'

# יצירת מיכל עיקרי
with st.container():
    st.markdown('<div class="main-container">', unsafe_allow_html=True)
    
    # הצגת ההודעות הקיימות
    for message in st.session_state.messages:
        if message["role"] == "user":
            st.markdown(f'<div class="user-bubble">{message["content"]}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="bot-bubble">{message["content"]}</div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

# קלט המשתמש
user_input = st.text_input("הקלד הודעה...", key="user_input")

# כפתור שליחה
if st.button("שלח"):
    if user_input:
        # הוספת הודעת המשתמש להיסטוריה
        st.session_state.messages.append({"role": "user", "content": user_input})
        
        # הצג את ההיסטוריה המעודכנת (כולל הודעת המשתמש)
        st.rerun()

# תהליך זה יופעל רק אם המשתמש הכניס הודעה חדשה
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    # קבל תגובה מהבוט
    bot_response = get_bot_response(st.session_state.messages[-1]["content"])
    
    # הוסף אפקט של הקלדה
    with st.spinner("מקליד..."):
        time.sleep(0.5)  # המתנה קצרה ליצירת אפקט הקלדה
    
    # הוסף את תגובת הבוט להיסטוריה
    st.session_state.messages.append({"role": "assistant", "content": bot_response})
    
    # הצג את ההיסטוריה המעודכנת (כולל תגובת הבוט)
    st.rerun()