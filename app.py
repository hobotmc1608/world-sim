import streamlit as st
from supabase import create_client, Client
import requests

# --- НАСТРОЙКИ (ВСТАВЬТЕ СЮДА ВАШИ ДАННЫЕ) ---
SUPABASE_URL = "https://xbmooipheiqnwnchkprm.supabase.co/rest/v1/" # Замените на ваш Project URL
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InhibW9vaXBoZWlxbnduY2hrcHJtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODA2NzQxNzQsImV4cCI6MjA5NjI1MDE3NH0.mYmnk7rNjxJNfe-bf0LLOjKV9nn5fMpJr3eS8fhjJYs" # Замените на ваш anon public key
HF_TOKEN = "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" # Замените на ваш токен Hugging Face
ADMIN_PASSWORD = "nilapsi12" # Пароль для входа в режим создателя

# Инициализация клиента Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="Симуляция Мира", layout="wide")

# --- ФУНКЦИИ БАЗЫ ДАННЫХ ---

def get_world_rules():
    """Загружает правила мира"""
    try:
        response = supabase.table("world_rules").select("*").execute()
        return "\n".join([f"- {r['rule_text']}" for r in response.data]) if response.data else "Нет правил."
    except: return "Ошибка загрузки правил."

def get_location(loc_id):
    """Информация о локации"""
    response = supabase.table("locations").select("*").eq("id", loc_id).single().execute()
    return response.data if response.data else {"name": "Неизвестно", "description": "Пустота"}

def get_characters(loc_id):
    """Персонажи + их статы"""
    chars_resp = supabase.table("characters").select("*").eq("location_id", loc_id).execute()
    result = []
    for char in chars_resp.data:
        stats_resp = supabase.table("character_stats").select("*").eq("character_id", char['id']).single().execute()
        stats = stats_resp.data if stats_resp.data else {}
        result.append({**char, "stats": stats})
    return result

def add_character(name, role, personality, loc_id, h, w, t):
    """Добавление персонажа и статов"""
    res = supabase.table("characters").insert({"name": name, "role": role, "personality": personality, "location_id": loc_id}).execute()
    if res.data:
        supabase.table("character_stats").insert({"character_id": res.data[0]['id'], "height": h, "weight": w, "alcohol_tolerance": t}).execute()

# --- ЛОГИКА ИИ ---

def ask_ai(prompt, context, rules):
    API_URL = "https://api-inference.huggingface.co/models/mistralai/Mistral-Nemo-Instruct-2407"
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}    
    full_prompt = f"""
    ТЫ — ДВИЖОК РОЛЕВОЙ СИМУЛЯЦИИ.
    
    ЖЕЛЕЗНЫЕ ЗАКОНЫ (НЕ НАРУШАТЬ):
    {rules}
    
    КОНТЕКСТ:
    {context}
    
    ДЕЙСТВИЕ ПОЛЬЗОВАТЕЛЯ: "{prompt}"
    
    ОПИШИ РЕАКЦИЮ МИРА И ПЕРСОНАЖЕЙ. Учитывай физику, опьянение и характеры.
    ОТВЕТ:
    """
    
    try:
        r = requests.post(API_URL, headers=headers, json={"inputs": full_prompt, "parameters": {"max_new_tokens": 300, "return_full_text": False}})
        return r.json()[0]['generated_text']
    except Exception as e:
        return f"Ошибка ИИ: {e}"

# --- ИНТЕРФЕЙС ---

with st.sidebar:
    st.title("🌍 Управление Миром")
    loc_id = st.number_input("ID Локации", min_value=1, value=1)
    
    admin = st.checkbox("🔑 Режим Создателя")
    if admin:
        pwd = st.text_input("Пароль", type="password")
        if pwd == ADMIN_PASSWORD:
            st.success("Доступ разрешен")
            n = st.text_input("Имя"); r = st.text_input("Роль"); d = st.text_area("Характер")
            c1, c2, c3 = st.columns(3)
            with c1: h = st.number_input("Рост", value=170)
            with c2: w = st.number_input("Вес", value=65)
            with c3: t = st.slider("Толерантность", 1, 10, 5)
            
            if st.button("Создать жителя"):
                add_character(n, r, d, loc_id, h, w, t)
                st.success("Готово!"); st.rerun()
        else: st.error("Неверный пароль")

st.header("💬 Диалог с миром")

loc = get_location(loc_id)
chars = get_characters(loc_id)
rules = get_world_rules()
ctx = f"Локация: {loc['name']} ({loc['description']}).\nПерсонажи:\n"
for c in chars:
    s = c.get('stats', {})
    ctx += f"- {c['name']} ({c['role']}): {c['personality']}. [Рост:{s.get('height')}см, Вес:{s.get('weight')}кг, Алк-тол:{s.get('alcohol_tolerance')}/10]\n"

if "msgs" not in st.session_state: st.session_state.msgs = []
for m in st.session_state.msgs:
    with st.chat_message(m["role"]): st.markdown(m["content"])

if p := st.chat_input("Ваши действия..."):
    st.session_state.msgs.append({"role": "user", "content": p})
    with st.chat_message("user"): st.markdown(p)
    
    with st.chat_message("assistant"):
        with st.spinner("Мир реагирует..."):
            ans = ask_ai(p, ctx, rules)
            st.markdown(ans)
            st.session_state.msgs.append({"role": "assistant", "content": ans})