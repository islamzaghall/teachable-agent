from datetime import datetime
import json
import os
import time
from google import genai
frome google.genai import errors
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(
    page_title="زميلي الذكي", page_icon="🎒", layout="centered"
)

st.markdown(
    """
    <style>
        .stApp { direction: RTL; text-align: right; }
        .stChatInput { direction: RTL; text-align: right; }
    </style>
    """,
    unsafe_allow_html=True,
)


def speak_arabic_button(text: str, key_suffix: str):
  """ينشئ زر قراءة صوتية عربية عبر المتصفح"""
  safe_text = json.dumps(text, ensure_ascii=False)
  html_code = f"""
    <div style="direction: RTL; text-align: right; margin: 4px 0 10px 0;">
        <button id="btn_{key_suffix}" onclick="speak_{key_suffix}()"
            style="background-color:#eef4ff; color:#1a4b8c; border:1px solid #b8d0f8;
                   border-radius:8px; padding:5px 12px; font-size:14px; cursor:pointer;">
            🔊 اسمع صوت زيد
        </button>
    </div>
    <script>
        function speak_{key_suffix}() {{
            if (!('speechSynthesis' in window)) {{
                alert('المتصفح لا يدعم القراءة الصوتية');
                return;
            }}
            window.speechSynthesis.cancel();
            const utter = new SpeechSynthesisUtterance({safe_text});
            utter.lang = 'ar-SA';
            utter.rate = 0.95;

            // اختيار صوت عربي إذا توفر في الجهاز
            const voices = window.speechSynthesis.getVoices();
            const arVoice = voices.find(v => v.lang && v.lang.toLowerCase().startsWith('ar'));
            if (arVoice) {{
                utter.voice = arVoice;
            }}
            window.speechSynthesis.speak(utter);
        }}
    </script>
    """
  components.html(html_code, height=45)


MISCONCEPTION_DB = {
    "place_value_1": {
        "topic": "القيمة المنزلية",
        "question": "ما القيمة المنزلية للرقم ٤ في العدد ٣٤٥؟",
        "wrong_answer": "أظن أنها ٤ لأن الرقم مكتوب ٤.",
        "why_wrong": "الرقم ٤ يقع في منزلة العشرات، فقيمته ٤٠.",
    }
}

api_key = os.getenv("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY", "")
client = genai.Client(api_key=api_key) if api_key else None

if "state" not in st.session_state:
  st.session_state.state = "CHALLENGING"
  st.session_state.attempts = 0
  st.session_state.messages = [{
      "role": "assistant",
      "content": MISCONCEPTION_DB["place_value_1"]["wrong_answer"],
  }]
  st.session_state.logs = []

item = MISCONCEPTION_DB["place_value_1"]
st.title("🎒 تعلّم مع زميلك زيد")
st.caption(f"**الموضوع:** {item['topic']} | **السؤال:** {item['question']}")

# عرض سجل الرسائل مع زر صوت لكل رد من الوكيل
for idx, msg in enumerate(st.session_state.messages):
  with st.chat_message("assistant" if msg["role"] == "assistant" else "user"):
    st.write(msg["content"])
  if msg["role"] == "assistant":
    speak_arabic_button(msg["content"], f"hist_{idx}")

student_msg = st.chat_input("اكتب ردك أو اشرح لزيد ليش إجابته غلط...")

if student_msg:
  st.session_state.attempts += 1
  st.session_state.messages.append({"role": "user", "content": student_msg})
  with st.chat_message("user"):
    st.write(student_msg)

  if st.session_state.attempts >= 2 and len(student_msg.strip()) > 8:
    st.session_state.state = "PERSUADED"

  system_instruction = f"""
أنت "زيد"، زميل دراسة في المرحلة الأساسية تتعلم مع الطالب، ولست معلماً أو مساعداً آلياً.
الموضوع: {item['topic']}
السؤال: {item['question']}
إجابتك الخاطئة الحالية: {item['wrong_answer']}
المرجع العلمي الداخلي: {item['why_wrong']}
حالة الجلسة الحالية: {st.session_state.state} | عدد محاولات الطالب: {st.session_state.attempts}

القواعد:
- في حالة CHALLENGING: تمسّك برأيك الخاطئ بأدب واطلب من الطالب شرح السبب إذا اكتفى بتخطئتك.
- إذا قدّم الطالب تعليلاً صحيحاً ومقنعاً، انتقل لقبول الفكرة واشرح بلغتك البسيطة ما فهمته، واطلب تحققاً بسيطاً.
- اجعل الرد قصيراً ومناسباً لطفل في المرحلة الأساسية، واستخدم الأرقام (٠-٩) في الأعداد.
""".strip()

  history_text = "\n".join([
      f"{'طالب' if m['role']=='user' else 'زيد'}: {m['content']}"
      for m in st.session_state.messages[-6:]
  ])

  if client:
    res = None
        for attempt in range(3):
            try:
                res = client.models.generate_content(
                    model="gemini-3.8-flash-lite",
                    contents=f"سجل الحوار:\n\n{history_text}\n\nرد الآن كزميل طالب:",
                    config={"system_instruction": system_instruction, "temperature": 0.4},
                )
                break
            except errors.ServerError:
                if attempt == 2:
                    raise
                time.sleep(1.5)
    reply = res.text.strip()
  else:
    reply = "يرجى ضبط مفتاح GEMINI_API_KEY أولاً."

  st.session_state.messages.append({"role": "assistant", "content": reply})
  with st.chat_message("assistant"):
    st.write(reply)
  speak_arabic_button(reply, f"new_{st.session_state.attempts}")

  st.session_state.logs.append({
      "time": datetime.now().strftime("%H:%M:%S"),
      "attempt": st.session_state.attempts,
      "state": st.session_state.state,
      "student_input": student_msg,
      "agent_reply": reply,
  })

if st.session_state.logs:
  st.download_button(
      label="📥 تحميل سجل الجلسة (JSON)",
      data=json.dumps(st.session_state.logs, ensure_ascii=False, indent=2),
      file_name=f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
      mime="application/json",
  )
