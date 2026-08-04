# -*- coding: utf-8 -*-
import streamlit as st
from google import genai
import gspread
from google.oauth2.service_account import Credentials
import datetime
import base64
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.header import Header
from PIL import Image
import io

# --- 페이지 기본 설정 ---
st.set_page_config(
    page_title="한국환경공단 수도권서부환경본부 | AI 스마트 안전 관리",
    page_icon="puru_guru.png",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- Base64 이미지 변환 함수 ---
def get_base64_image(image_path):
    try:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except Exception:
        return ""

img_base64 = get_base64_image("puru_guru.png")

# --- 🌙 미니멀리즘 & 다크모드 대응 프리미엄 CSS ---
st.markdown("""
    <style>
    /* 전체 기본 설정 및 폰트 */
    html, body, [data-testid="stAppViewContainer"] {
        font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, system-ui, Roboto, sans-serif !important;
    }
    
    /* 📱 모바일 최적화 레이아웃 및 넉넉한 여백 */
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 5rem !important;
        max-width: 680px !important;
    }

    /* 🎨 라이트/다크 모드 동적 컬러 변수 (미니멀리즘) */
    @media (prefers-color-scheme: dark) {
        :root {
            --bg-color: #0F172A;
            --card-bg: #1E293B;
            --text-main: #F8FAFC;
            --text-sub: #94A3B8;
            --border-color: #334155;
            --accent-green: #10B981;
        }
    }
    @media (prefers-color-scheme: light) {
        :root {
            --bg-color: #F8FAFC;
            --card-bg: #FFFFFF;
            --text-main: #0F172A;
            --text-sub: #64748B;
            --border-color: #E2E8F0;
            --accent-green: #059669;
        }
    }

    .stApp {
        background-color: var(--bg-color);
    }

    /* 🧱 카드 기반 UI & 둥근 모서리 (16~24px) */
    .minimal-card {
        background-color: var(--card-bg);
        border: 1px solid var(--border-color);
        border-radius: 20px;
        padding: 24px;
        margin-bottom: 20px;
        box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.04);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .minimal-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 30px -4px rgba(0, 0, 0, 0.08);
    }

    /* 상단 브랜드 헤더 */
    .brand-header {
        text-align: center;
        padding: 20px 0 30px 0;
    }
    .brand-header h1 {
        font-size: 1.5rem;
        font-weight: 800;
        color: var(--text-main);
        margin: 10px 0 5px 0;
        letter-spacing: -0.5px;
    }
    .brand-header p {
        font-size: 0.9rem;
        color: var(--text-sub);
        margin: 0;
    }

    /* 🎛️ 하단 탭 스타일 모방형 네비게이션 강조 */
    .stTabs [data-baseweb="tab-list"] {
        background-color: var(--card-bg);
        padding: 6px;
        border-radius: 16px;
        border: 1px solid var(--border-color);
        gap: 6px;
        margin-bottom: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 12px;
        padding: 10px 16px;
        font-weight: 700;
        color: var(--text-sub);
        border: none;
        transition: all 0.2s;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #059669 0%, #10B981 100%) !important;
        color: #FFFFFF !important;
        box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
    }

    /* 입력 폼 & 라벨 미니멀 스타일 */
    label, .stSelectbox label, .stTextInput label, .stTextArea label, .stFileUploader label {
        color: var(--text-main) !important;
        font-weight: 700 !important;
        font-size: 0.9rem !important;
    }
    
    /* 버튼 스타일 (부드러운 애니메이션) */
    div.stButton > button {
        background: linear-gradient(135deg, #059669 0%, #10B981 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 16px !important;
        font-weight: 700 !important;
        height: 50px !important;
        font-size: 1rem !important;
        box-shadow: 0 4px 15px rgba(5, 150, 105, 0.2) !important;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
    }
    div.stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(5, 150, 105, 0.35) !important;
    }

    /* AI 채팅창 전용 스타일 */
    .chat-container {
        background-color: var(--card-bg);
        border: 1px solid var(--border-color);
        border-radius: 20px;
        padding: 20px;
        margin-bottom: 20px;
    }
    </style>
""", unsafe_allow_html=True)


# ==========================================
# 🔒 감독관 로그인 게이트웨이
# ==========================================
def check_password():
    if st.session_state.get("password_correct", False):
        return True

    allowed_users = st.secrets.get("passwords", {})

    st.markdown("""
        <div style="text-align:center; padding: 60px 20px 20px 20px;">
            <h2 style="font-weight:800; margin-bottom: 8px;">🌱 KECO 안전 시스템</h2>
            <p style="color: #64748B; font-size: 0.95rem;">안전 관리 감독관 인증을 진행해 주세요.</p>
        </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        user_id = st.text_input("👤 사번 (ID)", key="username_input")
        user_pw = st.text_input("🔑 비밀번호", type="password", key="password_input")
        
        st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
        if st.button("로그인", use_container_width=True):
            user_id_clean = str(user_id).strip()
            user_pw_clean = str(user_pw).strip()
            allowed_users_str = {str(k): str(v) for k, v in allowed_users.items()}
            
            if user_id_clean in allowed_users_str and allowed_users_str[user_id_clean] == user_pw_clean:
                st.session_state["password_correct"] = True
                st.session_state["logged_user"] = user_id_clean
                st.rerun()
            else:
                st.error("❌ 아이디 또는 비밀번호가 올바르지 않습니다.")

    return False

if not check_password():
    st.stop()

logged_user_id = st.session_state.get('logged_user')
user_emails_map = st.secrets.get("user_emails", {})
mapped_email = user_emails_map.get(str(logged_user_id), st.secrets.get("smtp", {}).get("receiver_email", ""))

# 사이드바 최소화 정보
with st.sidebar:
    st.markdown(f"### 👤 인증 계정: `{logged_user_id}`")
    st.write(f"연동 이메일: {mapped_email}")
    if st.button("로그아웃", use_container_width=True):
        st.session_state["password_correct"] = False
        st.rerun()


# --- 핵심 함수 정의 (구글시트, 사내망 저장, 이메일, AI 분석) ---
@st.cache_resource
def get_gcp_credentials():
    return Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )

def save_image_to_internal_network(uploaded_file, folder_path, prefix):
    try:
        if not os.path.exists(folder_path):
            os.makedirs(folder_path, exist_ok=True)
        timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_filename = f"{prefix}_{timestamp_str}_{uploaded_file.name}"
        full_path = os.path.join(folder_path, safe_filename)
        uploaded_file.seek(0)
        with open(full_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        return full_path
    except Exception as e:
        return None

def send_inspection_email(dept_name, site_name, inspector_id, form_data):
    try:
        smtp_conf = st.secrets.get("smtp", {})
        smtp_server = smtp_conf.get("server", "smtp.gmail.com")
        smtp_port = smtp_conf.get("port", 587)
        sender_email = smtp_conf.get("sender_email", "")
        sender_password = smtp_conf.get("sender_password", "")
        receiver_email = user_emails_map.get(str(inspector_id), smtp_conf.get("receiver_email", sender_email))

        if not sender_email or not sender_password:
            return False, "SMTP 설정 누락"

        msg = MIMEMultipart()
        msg['Subject'] = Header(f"[안전점검] {dept_name} - {site_name} ({inspector_id})", 'utf-8')
        msg['From'] = Header(f"KECO 안전시스템 <{sender_email}>", 'utf-8')
        msg['To'] = Header(receiver_email, 'utf-8')

        body_html = f"<h3>🌱 현장 안전 점검 보고</h3><p><b>부서/현장:</b> {dept_name} / {site_name}</p><hr>"
        for k, v in form_data.items():
            body_html += f"<p><b>[항목 #{k}]</b><br>• 조치: {v['desc']}<br>• AI 분석: {v['ai_analysis']}</p>"
        msg.attach(MIMEText(body_html, 'html', 'utf-8'))

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, receiver_email, msg.as_string())
        return True, "성공"
    except Exception as e:
        return False, str(e)

def save_to_google_sheet(dept_name, site_name, set_count, analysis_summary, summary_detail, inspector_id, photo_info_str):
    try:
        creds = get_gcp_credentials()
        client = gspread.authorize(creds)
        sheet = client.open_by_key(st.secrets["SPREADSHEET_ID"]).sheet1
        sheet.append_row([datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), dept_name, site_name, f"{set_count}개", analysis_summary, summary_detail, inspector_id, photo_info_str])
        return True
    except Exception as e:
        return False

def get_google_sheet_records():
    try:
        creds = get_gcp_credentials()
        client = gspread.authorize(creds)
        return client.open_by_key(st.secrets["SPREADSHEET_ID"]).sheet1.get_all_values()
    except Exception as e:
        return []

def analyze_hazard_auto(api_key, img_file):
    client = genai.Client(api_key=api_key)
    img_file.seek(0)
    img = Image.open(img_file)
    prompt = "안전 전문 AI로서 사진을 분석해 1. 주요 위험 요소 (1문장) 2. 위험 등급 (상/중/하) 3. 권장 조치 사항 (1문장)으로 요약하세요."
    for m in ["gemini-2.5-flash", "gemini-2.5-pro"]:
        try:
            res = client.models.generate_content(model=m, contents=[prompt, img])
            if res and res.text: return res.text
        except: continue
    return "AI 분석 실패"


# --- API Key 체크 ---
api_key = st.secrets.get("GEMINI_API_KEY", "")

# --- 세션 상태 초기화 ---
if "item_count" not in st.session_state: st.session_state.item_count = 1
if "ai_results" not in st.session_state: st.session_state.ai_results = {}
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = [{"role": "assistant", "content": "안녕하세요! 푸루와 그루입니다. 현장 안전 점검이나 규정에 대해 무엇이든 물어보세요!"}]


# --- 헤더 배너 (미니멀 & 큰 아이콘 느낌) ---
image_html = f'<img src="data:image/png;base64,{img_base64}" style="width: 72px; height: 72px; border-radius: 18px; object-fit: cover; box-shadow: 0 4px 12px rgba(0,0,0,0.08);">' if img_base64 else '🌱'

st.markdown(f"""
    <div class="brand-header">
        {image_html}
        <h1>한국환경공단 수도권서부환경본부</h1>
        <p>AI 스마트 현장 안전 관리 시스템</p>
    </div>
""", unsafe_allow_html=True)


# --- 탭 구성 (하단 탭 스타일 느낌의 상단바) ---
tab1, tab2, tab3 = st.tabs(["📝 점검 등록", "💬 푸루·그루 AI", "📊 이력 조회"])

# ================= Tab 1: 점검 등록 =================
with tab1:
    st.markdown("""
        <div class="minimal-card">
            <h3 style="margin-top:0; font-size:1.1rem; font-weight:700;">📌 점검 대상 선택</h3>
        </div>
    """, unsafe_allow_html=True)

    departments = ["시설사업1부", "시설사업2부", "시설사업3부"]
    sites = ["1현장", "2현장", "3현장", "4현장"]

    c1, c2 = st.columns(2)
    with c1: selected_dept = st.selectbox("담당 부서", departments)
    with c2: selected_site = st.selectbox("점검 현장", sites)

    st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)

    form_data = {}
    for idx in range(1, st.session_state.item_count + 1):
        st.markdown(f"""
            <div class="minimal-card">
                <h3 style="margin-top:0; color:#059669; font-size:1.05rem;">🔹 점검 항목 #{idx}</h3>
        """, unsafe_allow_html=True)
        
        col_b, col_a = st.columns(2)
        with col_b:
            b_files = st.file_uploader(f"조치 전 사진 #{idx}", type=["jpg", "png", "jpeg"], accept_multiple_files=True, key=f"b_{idx}")
            if b_files and st.button(f"🔍 항목 #{idx} AI 분석", key=f"ai_btn_{idx}", use_container_width=True):
                with st.spinner("AI 분석 중..."):
                    if idx not in st.session_state.ai_results: st.session_state.ai_results[idx] = {}
                    for i, f in enumerate(b_files, 1):
                        st.session_state.ai_results[idx][i] = analyze_hazard_auto(api_key, f)
            
            if idx in st.session_state.ai_results:
                for i, txt in st.session_state.ai_results[idx].items():
                    st.info(f"[사진 #{i}]\n{txt}")

        with col_a:
            a_files = st.file_uploader(f"조치 후 사진 #{idx}", type=["jpg", "png", "jpeg"], accept_multiple_files=True, key=f"a_{idx}")

        desc = st.text_area(f"✍️ 항목 #{idx} 조치 내용 입력", placeholder="예: 개구부 안전난간 및 방호망 설치 완료", key=f"d_{idx}")
        st.markdown("</div>", unsafe_allow_html=True)

        if b_files or a_files or desc.strip():
            ai_texts = [v for v in st.session_state.ai_results.get(idx, {}).values()]
            form_data[idx] = {
                "before_files": b_files or [], "after_files": a_files or [],
                "desc": desc.strip(), "ai_analysis": "\n".join(ai_texts) or "미실행"
            }

    bc1, bc2 = st.columns(2)
    with bc1:
        if st.button("➕ 항목 추가", use_container_width=True):
            st.session_state.item_count += 1; st.rerun()
    with bc2:
        if st.session_state.item_count > 1 and st.button("➖ 항목 삭제", use_container_width=True):
            st.session_state.item_count -= 1; st.rerun()

    st.markdown("<div style='margin: 20px 0;'></div>", unsafe_allow_html=True)

    if st.button(f"💾 [{selected_dept} {selected_site}] 최종 제출 및 전송", use_container_width=True):
        if not form_data:
            st.warning("⚠️ 최소 하나의 항목을 입력해주세요.")
        else:
            folder = st.secrets.get("INTERNAL_FOLDER_PATH", "./KecoSafetyImages")
            with st.spinner("저장 및 전송 처리 중..."):
                details, paths = [], []
                for k, v in form_data.items():
                    for f in v['before_files']: save_image_to_internal_network(f, folder, f"B_{selected_dept}_{selected_site}")
                    for f in v['after_files']: save_image_to_internal_network(f, folder, f"A_{selected_dept}_{selected_site}")
                    details.append(f"항목#{k}: {v['desc']}")

                s_ok = save_to_google_sheet(selected_dept, selected_site, len(form_data), "AI분석완료", " | ".join(details), logged_user_id, folder)
                e_ok, e_msg = send_inspection_email(selected_dept, selected_site, logged_user_id, form_data)
                
                if s_ok and e_ok: st.success("🎉 사내망 저장, 구글시트 기록 및 메일 전송이 완료되었습니다!")
                else: st.error("❌ 처리 중 오류가 발생했습니다.")


# ================= Tab 2: AI 채팅 인터페이스 =================
with tab2:
    st.markdown("""
        <div class="minimal-card">
            <h3 style="margin-top:0; color:#059669; font-size:1.1rem;">💬 푸루·그루 안전 비서</h3>
            <p style="font-size:0.9rem; color:var(--text-sub); margin-bottom:0;">현장 안전 규정, 위험성 평가 가이드, 조치 요령에 대해 대화하세요.</p>
        </div>
    """, unsafe_allow_html=True)

    # 채팅 메시지 출력 영역
    for message in st.session_state.chat_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # 채팅 입력창
    if prompt := st.chat_input("안전 관련 궁금한 점을 입력하세요..."):
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("푸루·그루가 답변을 생각중입니다..."):
                try:
                    client = genai.Client(api_key=api_key)
                    chat_history = [
                        {"role": m["role"], "parts": [m["content"]]} 
                        for m in st.session_state.chat_messages[:-1]
                    ]
                    chat = client.chats.create(model="gemini-2.5-flash", history=chat_history)
                    response = chat.send_message(prompt)
                    reply_text = response.text
                except Exception as e:
                    reply_text = f"죄송합니다. 답변 생성 중 오류가 발생했습니다. ({e})"
                
                st.markdown(reply_text)
                st.session_state.chat_messages.append({"role": "assistant", "content": reply_text})


# ================= Tab 3: 이력 조회 =================
with tab3:
    st.markdown("""
        <div class="minimal-card">
            <h3 style="margin-top:0; font-size:1.1rem; font-weight:700;">📊 부서별 점검 이력</h3>
        </div>
    """, unsafe_allow_html=True)

    rows = get_google_sheet_records()
    if len(rows) <= 1:
        st.info("등록된 이력이 없습니다.")
    else:
        fc1, fc2 = st.columns(2)
        with fc1: f_dept = st.selectbox("부서 필터", ["전체 부서"] + departments, key="h_dept")
        with fc2: f_site = st.selectbox("현장 필터", ["전체 현장"] + sites, key="h_site")

        for r in rows[1:][::-1]:
            ts, dept, site, cnt, ai_t, det, inspector = r[0], r[1], r[2], r[3], r[4], r[5], r[6]
            if (f_dept in ["전체 부서", dept]) and (f_site in ["전체 현장", site]):
                with st.expander(f"🗓️ [{ts}] {dept} - {site} ({cnt})"):
                    st.markdown(f"**작성자 사번:** `{inspector}`")
                    st.write(f"**조치 내용:** {det}")
                    st.info(f"**AI 분석 내용:**\n{ai_t}")
