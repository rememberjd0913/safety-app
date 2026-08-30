# -*- coding: utf-8 -*-
import streamlit as st
from streamlit_autorefresh import st_autorefresh
from google import genai
import gspread
from google.oauth2.service_account import Credentials
import datetime
from zoneinfo import ZoneInfo
import base64
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.header import Header
from PIL import Image
import io
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from fpdf import FPDF

# --- 페이지 기본 설정 ---
st.set_page_config(
    page_title="한국환경공단 수도권서부환경본부 환경시설관리처 | AI 안전 점검 시스템",
    page_icon="puru_guru.png",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown(
    """
    <style>
        [data-testid="block-container"] {
            max-width: 800px !important;  /* 원하는 중간 크기 (1100px ~ 1300px 조절 가능) */
            margin: auto !important;       /* 양옆 여백을 균등하게 중앙 정렬 */
            padding-top: 2rem;
            padding-bottom: 2rem;
            padding-left: 3rem;
            padding-right: 3rem;
        }
    </style>
""",
    unsafe_allow_html=True,
)

# ---------------- PDF 생성 함수 정의 ----------------
def generate_pdf(title, content):
    pdf = FPDF()
    pdf.add_page()
    
    # 윈도우 환경 기본 한글 폰트 등록 (NanumGothic 이나 malgun 등 사용 가능)
    # 리눅스 환경(Streamlit Cloud 등)인 경우 나눔고딕 폰트 파일을 경로에 포함해야 합니다.
    font_path = "C:/Windows/Fonts/malgun.ttf"  # 윈도우 기준 경로
    if os.path.exists(font_path):
        pdf.add_font("Malgun", "", font_path, uni=True)
        pdf.set_font("Malgun", size=12)
    else:
        # 폰트 파일이 없을 경우 기본 폰트 사용 (한글이 깨질 수 있으므로 위 폰트 경로 확인 필요)
        pdf.set_font("Arial", size=12)

    # 문서 제목 추가
    pdf.cell(200, 10, text=title, new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(10)
    
    # 본문 내용 추가 (줄바꿈 자동 처리)
    # 멀티라인 텍스트 입력
    pdf.multi_cell(0, 10, text=content)
    
    # PDF를 바이트로 반환
    return pdf.output()

# --- Base64 이미지 변환 함수 ---
def get_base64_image(image_path):
    try:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except Exception:
        return ""

img_base64 = get_base64_image("Keco_logo.png")

# --- 커스텀 CSS (모바일 & 다크모드 가독성 완벽 대응) ---
st.markdown("""
    <style>
    html, body, [data-testid="stAppViewContainer"] {
        color: #1E293B !important;
    }
    .stMarkdown, p, div, span, label {
        word-break: keep-all !important;
        white-space: normal !important;
    }
    .stTable, div[data-testid="stTable"] {
        overflow-x: auto !important;
    }
    label, div[data-baseweb="select"] span, .stSelectbox label, .stTextInput label, .stTextArea label, .stFileUploader label {
        color: #1E293B !important;
        font-weight: 600 !important;
    }
    div[role="listbox"] div {
        color: #1E293B !important;
    }
    .stApp {
        background-color: #F8FBF9;
    }
    .keco-header {
        background: linear-gradient(135deg, #007A33 0%, #10B981 100%);
        padding: 22px 18px;
        border-radius: 16px;
        color: white;
        text-align: center;
        margin-bottom: 15px;
        box-shadow: 0 4px 15px rgba(0, 122, 51, 0.15);
    }
    .keco-header h2 {
        color: white !important;
        font-size: 1.5rem !important;
        font-weight: 700 !important;
        margin: 0 !important;
    }
    .keco-header p {
        color: #E6F4EA !important;
        font-size: 0.9rem !important;
        margin-top: 6px !important;
        margin-bottom: 0 !important;
    }
    .top-status-bar {
        background-color: #E6F4EA;
        border: 1.5px solid #10B981;
        border-radius: 12px;
        padding: 10px 18px;
        margin-bottom: 20px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 0.92rem;
        color: #005F27;
        font-weight: 600;
        box-shadow: 0 2px 6px rgba(0, 122, 51, 0.05);
    }
    .mascot-banner {
        background: white;
        border-radius: 16px;
        padding: 20px;
        text-align: center;
        border: 2px solid #E2E8F0;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        margin-bottom: 20px;
    }
    .mascot-card {
        background-color: #FFFFFF;
        border: 1.5px solid #E2E8F0;
        border-radius: 14px;
        padding: 14px 18px;
        margin-bottom: 20px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
        color: #1E293B !important;
    }
    .select-card {
        background-color: #E6F4EA;
        border: 1.5px solid #10B981;
        border-radius: 12px;
        padding: 12px 16px;
        margin-bottom: 18px;
        color: #005F27 !important;
        font-weight: 600;
        box-shadow: 0 2px 6px rgba(0, 122, 51, 0.05);
    }
    .analysis-box {
        background-color: #FEF2F2;
        border: 1.5px solid #FCA5A5;
        border-radius: 12px;
        padding: 14px 16px;
        margin-top: 10px;
        margin-bottom: 15px;
        font-size: 0.93rem;
        color: #991B1B !important;
    }
    .item-card {
        background-color: #FFFFFF;
        border: 1.5px solid #CBD5E1;
        border-radius: 12px;
        padding: 18px;
        margin-bottom: 20px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.03);
        color: #1E293B !important;
    }
    div.stButton > button {
        background: linear-gradient(135deg, #007A33 0%, #059669 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 10px !important;
        font-weight: bold !important;
        height: 48px !important;
        font-size: 1rem !important;
        box-shadow: 0 3px 8px rgba(0, 122, 51, 0.2) !important;
    }
    div.stTabs [data-baseweb="tab-list"] {
        background-color: #F1F5F9;
        padding: 6px;
        border-radius: 12px;
    }
    div.stTabs [data-baseweb="tab"] {
        background-color: transparent;
        border-radius: 8px;
        padding: 8px 16px;
        font-weight: bold;
        color: #475569;
    }
    div.stTabs [aria-selected="true"] {
        background-color: #1E293B !important;
        color: #FFFFFF !important;
    }
    </style>
""", unsafe_allow_html=True)


# ==========================================
# 🔒 [보안] 감독관 로그인 제어 게이트웨이 (상하 간격 및 높이 확대 버전)
# ==========================================
def check_password():
    if st.session_state.get("password_correct", False):
        return True

    # 1. 자동 새로고침 설정 (우측 슬라이드쇼 4초 간격 전환)
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=4000, key="login_slide_refresh")

    # 상단 여백
    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

    # 2. 한국환경공단 공식 스타일 상단 헤더 바
    logo_html = f'<img src="data:image/png;base64,{img_base64}" style="height: 42px; vertical-align: middle; margin-right: 12px;">' if img_base64 else '🌱'
    
    st.markdown(f"""
        <div style="background-color: #FFFFFF; border: 1.5px solid #E2E8F0; padding: 18px 30px; display: flex; justify-content: space-between; align-items: center; margin-bottom: 45px; border-radius: 16px; box-shadow: 0 4px 12px rgba(0,0,0,0.04);">
            <div style="display: flex; align-items: center;">
                {logo_html}
                <span style="font-size: 1.5rem; font-weight: 800; color: #1E293B; letter-spacing: -0.5px;">한국환경공단</span>
                <span style="font-size: 1rem; color: #64748B; margin-left: 14px; border-left: 2px solid #CBD5E1; padding-left: 14px; font-weight: 600;">수도권서부환경본부 환경시설관리처</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # 3. 메인 2열 레이아웃 (좌측: 로그인 폼 / 우측: 환경 시설 슬라이드쇼)
    col_login, col_slide = st.columns([1, 1.1], gap="large")

    # --- [좌측 열]: 로그인 입력 카드 (세로 크기 확대) ---
    with col_login:
        st.markdown("""
            <div style="background: white; border: 1.5px solid #E2E8F0; border-radius: 16px; padding: 45px 35px; box-shadow: 0 6px 16px rgba(0,0,0,0.05); min-height: 250px; display: flex; flex-direction: column; justify-content: center;">
                <h3 style="color: #007A33; margin-top: 0; margin-bottom: 10px; font-size: 2rem; font-weight: 700;"> 스마트 건설현장 안전관리 시스템 인증</h3>
                <p style="color: #64748B; font-size: 1.5rem; margin-bottom: 30px;">&nbsp;&nbsp;&nbsp;&nbsp;인증된 사내 감독관만 접근 가능합니다.</p>
                <div style="background-color: #F8FBF9; border-left: 4px solid #10B981; padding: 12px 16px; border-radius: 8px; margin-bottom: 20px; font-size: 0.88rem; color: #334155; text-align: left; box-shadow: 0 2px 4px rgba(0,0,0,0.02);">
                    <b>✨ 시스템 안내:</b> 환경시설설치사업 통합 관리를 위해 안전한 계정 로그인이 필요합니다.
                </div>
        """, unsafe_allow_html=True)

        allowed_users = st.secrets.get("passwords", {})
        
        user_id = st.text_input("👤 감독관 ID (사번)", key="username_input")
        user_pw = st.text_input("🔑 비밀번호", type="password", key="password_input")
        
        st.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True)
        
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
                
        st.markdown("</div>", unsafe_allow_html=True)

    # --- [우측 열]: 환경 관련 이미지 슬라이드쇼 (세로 크기 확대) ---
    with col_slide:
        slide_images = [
            ("https://images.unsplash.com/photo-1542601906990-b4d3fb778b09?auto=format&fit=crop&w=1000&q=80", "지속 가능한 친환경 녹색 인프라 관리"),
            ("https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=1000&q=80", "깨끗하고 안전한 수도권 환경 생태계 조성"),
            ("https://images.unsplash.com/photo-1470071459604-3b5ec3a7fe05?auto=format&fit=crop&w=1000&q=80", "자연과 공존하는 생태환경 복원 및 보전"),
            ("https://images.unsplash.com/photo-1466611653911-95081537e5b7?auto=format&fit=crop&w=1000&q=80", "신재생에너지 및 탄소중립 실천 인프라"),
            ("https://images.unsplash.com/photo-1500382017468-9049fed747ef?auto=format&fit=crop&w=1000&q=80", "맑고 깨끗한 수자원 및 대기환경 관리")
        ]

        if "slide_index" not in st.session_state:
            st.session_state["slide_index"] = 0
        else:
            st.session_state["slide_index"] = (st.session_state["slide_index"] + 1) % len(slide_images)

        current_img_url, current_caption = slide_images[st.session_state["slide_index"]]

        st.markdown(f"""
            <div style="background: white; border: 1.5px solid #E2E8F0; border-radius: 16px; padding: 30px; box-shadow: 0 6px 16px rgba(0,0,0,0.05); text-align: center; min-height: 460px; display: flex; flex-direction: column; justify-content: center;">
                <div style="overflow: hidden; border-radius: 12px; height: 400px; background-color: #f1f5f9;">
                    <img src="{current_img_url}" style="width: 100%; height: 100%; object-fit: cover; transition: opacity 0.5s ease-in-out;">
                </div>
                <div style="margin-top: 20px; font-weight: 700; color: #007A33; font-size: 1.15rem;">
                    ✨ {current_caption}
                </div>
                <div style="color: #94A3B8; font-size: 0.9rem; margin-top: 6px;">
                    한국환경공단 수도권서부환경본부 환경시설관리처
                </div>
            </div>
        """, unsafe_allow_html=True)

    # 하단 여백 추가
    st.markdown("<div style='height: 40px;'></div>", unsafe_allow_html=True)

    return False

if not check_password():
    st.stop()
    
logged_user_id = st.session_state.get('logged_user')
user_emails_map = st.secrets.get("user_emails", {})
mapped_email = user_emails_map.get(str(logged_user_id), st.secrets.get("smtp", {}).get("receiver_email", ""))

# --- 사이드바 영역 ---
st.sidebar.markdown("### 🔒 감독관 인증 정보")
st.sidebar.write(f"접속 사번: **{logged_user_id}**")
st.sidebar.write(f"수신 이메일: **{mapped_email if mapped_email else '미등록(기본값 사용)'}**")

st.sidebar.markdown("---")
st.sidebar.markdown("### ⏱️ 실시간 업무 현황")

try:
    kst_now = datetime.datetime.now(ZoneInfo("Asia/Seoul"))
except Exception:
    kst_now = datetime.datetime.utcnow() + datetime.timedelta(hours=9)

current_date_str = kst_now.strftime('%Y년 %m월 %d일')
current_time_str = kst_now.strftime('%H시 %M분')

st.sidebar.write(f"**오늘 날짜:** {current_date_str}")
st.sidebar.write(f"**현재 시각:** {current_time_str}")

st.sidebar.markdown("---")
st.sidebar.markdown("### 🚨 긴급 연락망")
st.sidebar.info(
    "**수도권서부환경본부 상황실**\n\n"
    "📞 02-3153-0600\n\n"
    "⚠️ **중대재해 신고 직통**\n\n"
    "📞 02-3153-0660"
)

st.sidebar.markdown("---")
st.sidebar.markdown("### ⚡ 현장 3대 안전 수칙")
st.sidebar.markdown(
    "> 1. **추락 방지:** 안전모·안전대 필수 착용\n\n"
    "> 2. **끼임 방지:** 방호덮개 및 정비 중 LOTO\n\n"
    "> 3. **화재 예방:** 용접 작업 시 소화기 비치"
)

st.sidebar.markdown("---")
if st.sidebar.button("🔓 로그아웃", use_container_width=True):
    st.session_state["password_correct"] = False
    st.rerun()


# --- 1. Google Sheets & 내부망 폴더 & 이메일 연동 설정 ---
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
        st.error(f"내부망 폴더 사진 저장 실패: {e}")
        return None

def send_inspection_email(dept_name, site_name, inspector_id, form_data):
    try:
        smtp_conf = st.secrets.get("smtp", {})
        smtp_server = smtp_conf.get("server", "smtp.gmail.com")
        smtp_port = smtp_conf.get("port", 587)
        sender_email = smtp_conf.get("sender_email", "")
        sender_password = smtp_conf.get("sender_password", "")

        if not sender_email or not sender_password:
            return False, "이메일 설정(SMTP)이 누락되었습니다."

        user_emails_map = st.secrets.get("user_emails", {})
        receiver_email = user_emails_map.get(str(inspector_id), smtp_conf.get("receiver_email", sender_email))

        if not receiver_email:
            return False, f"해당 사번({inspector_id})에 매핑된 이메일 주소가 없습니다."

        msg = MIMEMultipart()
        
        subject_str = f"[안전점검 보고] {dept_name} - {site_name} (작성자: {inspector_id})"
        msg['Subject'] = Header(subject_str, 'utf-8')
        msg['From'] = Header(f"KECO 안전점검시스템 <{sender_email}>", 'utf-8')
        msg['To'] = Header(receiver_email, 'utf-8')

        body_html = f"""
        <h3>🌱 한국환경공단 현장 안전 점검 보고</h3>
        <p><b>- 담당 부서:</b> {dept_name}</p>
        <p><b>- 점검 현장:</b> {site_name}</p>
        <p><b>- 작성 감독관 사번:</b> {inspector_id}</p>
        <p><b>- 점검 일시:</b> {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <hr>
        <h4>📋 점검 항목별 상세 내용</h4>
        """

        for k, v in form_data.items():
            loc_str = f"📍 도면 위치(X:{v['coord_x']}, Y:{v['coord_y']})<br>" if v.get('coord_x') is not None else ""
            body_html += f"<p><b>[항목 #{k}]</b><br>{loc_str}• 조치 내용: {v['desc']}<br>• AI 분석: {v['ai_analysis'].replace(chr(10), '<br>')}</p>"

        msg.attach(MIMEText(body_html, 'html', 'utf-8'))

        for k, v in form_data.items():
            if 'before_files' in v and v['before_files']:
                for idx, img_f in enumerate(v['before_files']):
                    try:
                        img_f.seek(0)
                        img_bytes = io.BytesIO(img_f.read()).getvalue()
                        if img_bytes:
                            filename = f"Before_Item{k}_{idx+1}.jpg"
                            part = MIMEApplication(img_bytes, Name=filename)
                            part['Content-Disposition'] = f'attachment; filename="{filename}"'
                            msg.attach(part)
                    except Exception as img_err:
                        print(f"Before 이미지 첨부 실패: {img_err}")
                
            if 'after_files' in v and v['after_files']:
                for idx, img_f in enumerate(v['after_files']):
                    try:
                        img_f.seek(0)
                        img_bytes = io.BytesIO(img_f.read()).getvalue()
                        if img_bytes:
                            filename = f"After_Item{k}_{idx+1}.jpg"
                            part = MIMEApplication(img_bytes, Name=filename)
                            part['Content-Disposition'] = f'attachment; filename="{filename}"'
                            msg.attach(part)
                    except Exception as img_err:
                        print(f"After 이미지 첨부 실패: {img_err}")
                
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
        sheet_id = st.secrets["SPREADSHEET_ID"]
        sheet = client.open_by_key(sheet_id).sheet1
        
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sheet.append_row([now_str, dept_name, site_name, f"{set_count}개 항목", analysis_summary, summary_detail, inspector_id, photo_info_str])
        return True
    except Exception as e:
        st.error(f"구글 시트 저장 중 오류: {e}")
        return False

def get_google_sheet_records():
    try:
        creds = get_gcp_credentials()
        client = gspread.authorize(creds)
        sheet_id = st.secrets["SPREADSHEET_ID"]
        sheet = client.open_by_key(sheet_id).sheet1
        return sheet.get_all_values()
    except Exception as e:
        st.error(f"구글 시트 불러오기 오류: {e}")
        return []


# --- 2. AI 위험 분석 함수 ---
def analyze_hazard_auto(api_key, img_file):
    client = genai.Client(api_key=api_key)
    img_file.seek(0)
    img = Image.open(img_file)
    
    prompt = (
        "당신은 한국환경공단(KECO) 현장 안전 전문 AI 검수원입니다.\n"
        "제공된 조치 전 사진을 분석하여 다음 3가지 항목만 핵심 요약해서 짧게 답변하세요.\n\n"
        "1. **주요 위험 요소:** (1문장)\n"
        "2. **위험 등급:** [상/중/하 중 선택]\n"
        "3. **권장 조치 사항:** (1문장)"
    )

    candidate_models = ["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.5-pro"]
    last_error = None

    for model_name in candidate_models:
        try:
            response = client.models.generate_content(model=model_name, contents=[prompt, img])
            if response and response.text:
                return response.text
        except Exception as e:
            last_error = e
            continue

    try:
        available_models = [m.name.replace("models/", "") for m in client.models.list()]
        for m_name in available_models:
            if "flash" in m_name or "pro" in m_name:
                try:
                    response = client.models.generate_content(model=m_name, contents=[prompt, img])
                    if response and response.text:
                        return response.text
                except Exception as e:
                    last_error = e
                    continue
    except Exception as list_err:
        last_error = list_err

    raise Exception(f"사용 가능한 Gemini 모델을 찾을 수 없습니다. (상세: {last_error})")


# --- 3. API Key 확인 ---
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    st.error("🔑 API Key를 찾을 수 없습니다. Streamlit Secrets 설정을 확인해 주세요.")
    st.stop()


# --- 4. 세션 상태 초기화 ---
if "item_count" not in st.session_state:
    st.session_state.item_count = 1

if "ai_results" not in st.session_state:
    st.session_state.ai_results = {}

if "item_coords" not in st.session_state:
    st.session_state.item_coords = {}  # {idx: {"x": x, "y": y}}


# --- 5. 헤더 UI 및 상단 실시간 시계 바 ---
st.markdown("""
    <div class="keco-header">
        <h2>🌱 한국환경공단 수도권서부환경본부</h2>
        <p>환경시설관리처 현장 안전 조치 전·후 스마트 점검 시스템 (도면 실시간 검측 연동형)</p>
    </div>
""", unsafe_allow_html=True)

st.markdown(f"""
    <div class="top-status-bar">
        <span>📅 <b>오늘 날짜:</b> {current_date_str}</span>
        <span>⏱️ <b>실시간 시각:</b> <span style="color:#007A33; font-size:1.05rem;">{current_time_str}</span></span>
        <span>👤 <b>접속 사번:</b> {logged_user_id}</span>
    </div>
""", unsafe_allow_html=True)

image_html = f'<img src="data:image/png;base64,{img_base64}" style="max-height: 100px;">' if img_base64 else '🌱'

st.markdown(f"""
    <div class="mascot-banner">
        <div style="margin-bottom: 8px;">{image_html}</div>
        <h4 style="margin:0; color:#007A33;">"안전점검 시작! 푸루와 그루가 안내해 드릴게요."</h4>
        <p style="margin-top:6px; font-size:0.88rem; color:#64748B;"> 현장 도면을 보며 검측 위치를 찍고 스마트하게 점검하세요.</p>
    </div>
""", unsafe_allow_html=True)


# --- 부서 및 현장 매핑 정의 ---
department_sites_map = {
    "시설사업1부": [
        "파주 환경순환센터 현대화사업",
        "수도권서부환경본부 청사 건립사업"
    ],
    "시설사업2부": [
        "김포시 통진레코파크 증설사업(2단계)",
        "김포시 통진레코파크 증설사업(3단계)",
        "광명 소각"
    ],
    "시설사업3부": [
        "부천시 굴포천 비점오염저감시설 설치사업",
        "평택축협 가축분뇨 공공처리시설 설치사업",
        "안성시 공공하수도시설 하수처리수 재이용사업",
        "평택 브레인시티 일반산업단지 공공폐수처리시설 설치사업(1-2단계)"
    ]
}

departments = list(department_sites_map.keys())

# --- 메인 탭 확장 ---
main_tab1, main_tab2, main_tab3, main_tab4 = st.tabs([
    "안전 점검 등록", 
    "🗺️ 실시간 도면 검측 뷰어", 
    "부서별 점검 이력 및 대시보드", 
    "📖 AI 안전 가이드 Q&A (RAG)"
])

with main_tab1:
    st.markdown("""
        <div class="mascot-card">
            <div>
                <strong style="color:#EC4899;">[그루의 현장 안내]</strong><br>
                <span style="font-size:0.92rem; color:#334155;">담당 부서와 현장을 선택하고 각 항목별 조치 내용과 사진을 등록하세요.</span>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    col_dept, col_site = st.columns(2)
    with col_dept:
        selected_dept = st.selectbox("📌 담당 부서 선택", departments, key="selected_dept_box")
    
    available_sites = department_sites_map.get(selected_dept, ["현장 없음"])
    
    with col_site:
        selected_site = st.selectbox("🏗️ 점검 현장 선택", available_sites, key="selected_site_box")

    st.markdown(f"""
        <div class="select-card">
            📍 선택된 점검 대상: <strong>[{selected_dept}] - {selected_site}</strong> (작성자 사번: {logged_user_id})
        </div>
    """, unsafe_allow_html=True)

    st.subheader("📸 안전 점검 사진 등록 및 AI 위험 분석")
    st.caption("💡 각 항목마다 여러 장의 사진을 다중 선택하여 동시에 첨부할 수 있습니다.")

    form_data = {}

    for idx in range(1, st.session_state.item_count + 1):
        coord_info = st.session_state.item_coords.get(idx)
        coord_badge = f"📍 도면 좌표 지정됨 (X: {coord_info['x']}, Y: {coord_info['y']})" if coord_info else "📍 도면 위치 미지정 (상단 [실시간 도면 검측 뷰어] 탭에서 지정 가능)"
        
        st.markdown(f"""
            <div class="item-card">
                <h4 style="margin-top:0; color:#007A33;">🔹 [점검 항목 #{idx}] <span style="font-size:0.8rem; color:#64748B; font-weight:normal;">({coord_badge})</span></h4>
        """, unsafe_allow_html=True)
        
        col_b, col_a = st.columns(2)
        
        with col_b:
            st.markdown("##### 🔴 조치 전 (Before) - 다중 선택 가능")
            before_img_files = st.file_uploader(
                f"#{idx} 조치 전 사진 첨부",
                type=["jpg", "jpeg", "png"],
                accept_multiple_files=True,
                key=f"before_imgs_{idx}"
            )
            
            if before_img_files:
                st.write(f"📷 첨부된 조치 전 사진: **{len(before_img_files)}장**")
                cols = st.columns(min(len(before_img_files), 2))
                for img_i, img_f in enumerate(before_img_files):
                    cols[img_i % 2].image(img_f, caption=f"조치 전 #{img_i+1}", use_container_width=True)
                
                if st.button(f"🔍 [항목 #{idx}] 조치 전 사진 전체 AI 분석", key=f"btn_ai_{idx}", use_container_width=True):
                    with st.spinner("푸루 AI가 조치 전 사진들의 위험요인을 분석 중..."):
                        if idx not in st.session_state.ai_results:
                            st.session_state.ai_results[idx] = {}
                        
                        for img_i, img_f in enumerate(before_img_files, start=1):
                            try:
                                result_text = analyze_hazard_auto(api_key, img_f)
                                st.session_state.ai_results[idx][img_i] = result_text
                            except Exception as e:
                                st.session_state.ai_results[idx][img_i] = f"분석 오류: {e}"

            if idx in st.session_state.ai_results and st.session_state.ai_results[idx]:
                st.markdown("**🤖 AI 위험 분석 결과:**")
                for img_i, res_text in st.session_state.ai_results[idx].items():
                    st.markdown(f"""
                        <div class="analysis-box">
                            <strong>[사진 #{img_i}]</strong><br>
                            {res_text.replace('\n', '<br>')}
                        </div>
                    """, unsafe_allow_html=True)

        with col_a:
            st.markdown("##### 🟢 조치 후 (After) - 다중 선택 가능")
            after_img_files = st.file_uploader(
                f"#{idx} 조치 후 사진 첨부",
                type=["jpg", "jpeg", "png"],
                accept_multiple_files=True,
                key=f"after_imgs_{idx}"
            )
            if after_img_files:
                st.write(f"📷 첨부된 조치 후 사진: **{len(after_img_files)}장**")
                cols = st.columns(min(len(after_img_files), 2))
                for img_i, img_f in enumerate(after_img_files):
                    cols[img_i % 2].image(img_f, caption=f"조치 후 #{img_i+1}", use_container_width=True)

        desc = st.text_area(
            f"✍️ [항목 #{idx}] 현장 조치 내용 및 설명", 
            placeholder=f"예: 항목 #{idx} - 개구부 안전난간 설치 및 추락방지망 추가 고정 완료", 
            key=f"desc_{idx}"
        )
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        if before_img_files or after_img_files or desc.strip():
            ai_summary_list = []
            if idx in st.session_state.ai_results:
                for img_i, res_text in st.session_state.ai_results[idx].items():
                    ai_summary_list.append(f"(사진#{img_i}) {res_text}")
            
            c_info = st.session_state.item_coords.get(idx)
            form_data[idx] = {
                "before_files": before_img_files if before_img_files else [],
                "after_files": after_img_files if after_img_files else [],
                "desc": desc.strip(),
                "ai_analysis": "\n".join(ai_summary_list) if ai_summary_list else "분석 미실행",
                "coord_x": c_info['x'] if c_info else None,
                "coord_y": c_info['y'] if c_info else None
            }

    btn_col1, btn_col2 = st.columns(2)
    with btn_col1:
        if st.button("➕ 점검 항목 추가하기", use_container_width=True):
            st.session_state.item_count += 1
            st.rerun()

    with btn_col2:
        if st.session_state.item_count > 1:
            if st.button("➖ 마지막 항목 삭제", use_container_width=True):
                last_idx = st.session_state.item_count
                if last_idx in st.session_state.ai_results:
                    del st.session_state.ai_results[last_idx]
                if last_idx in st.session_state.item_coords:
                    del st.session_state.item_coords[last_idx]
                st.session_state.item_count -= 1
                st.rerun()

    st.markdown("---")

    if st.button(f"💾 [{selected_dept} {selected_site}] 전체 점검 내역 저장, 이메일 전송 및 완료", use_container_width=True):
        if not form_data:
            st.warning("⚠️ 최소 1개 이상의 항목에 사진이나 설명글을 작성해 주세요.")
        else:
            internal_folder = st.secrets.get("INTERNAL_FOLDER_PATH", "./KecoSafetyImages")
            
            with st.spinner("🔄 구글 시트 동기화 및 이메일 전송 중입니다..."):
                all_ai_summaries = []
                details = []
                all_photo_paths = []
                
                for k, v in form_data.items():
                    if v['ai_analysis'] != "분석 미실행":
                        all_ai_summaries.append(f"[항목 #{k}]:\n{v['ai_analysis']}")
                    
                    b_paths = []
                    for img_f in v['before_files']:
                        saved_path = save_image_to_internal_network(img_f, internal_folder, f"Before_{selected_dept}_{selected_site}_Item{k}")
                        if saved_path: 
                            b_paths.append(saved_path)
                    
                    a_paths = []
                    for img_f in v['after_files']:
                        saved_path = save_image_to_internal_network(img_f, internal_folder, f"After_{selected_dept}_{selected_site}_Item{k}")
                        if saved_path: 
                            a_paths.append(saved_path)

                    coord_txt = f"핀좌표(X:{v['coord_x']}, Y:{v['coord_y']})" if v.get('coord_x') is not None else "좌표미지정"
                    path_text = f"[항목#{k} | {coord_txt}] 전:{len(b_paths)}장, 후:{len(a_paths)}장"
                    if b_paths or a_paths: 
                        combined_files_path = b_paths + a_paths
                        path_text += f" (경로: {', '.join(combined_files_path)})"
                    
                    all_photo_paths.append(path_text)
                    details.append(f"[항목 #{k}] {coord_txt}, 전:{len(v['before_files'])}장, 후:{len(v['after_files'])}장 ({v['desc'][:10]})")
                
                combined_ai = "\n\n".join(all_ai_summaries) if all_ai_summaries else "조치 전 AI 분석 미실행"
                combined_detail = " | ".join(details)
                combined_paths_str = " || ".join(all_photo_paths)
                
                sheet_success = save_to_google_sheet(selected_dept, selected_site, len(form_data), combined_ai, combined_detail, logged_user_id, combined_paths_str)
                email_success, email_msg = send_inspection_email(selected_dept, selected_site, logged_user_id, form_data)
                
                if sheet_success and email_success:
                    st.success(f"🎉 [{selected_dept} {selected_site}] 점검 내역이 구글 시트 기록 및 담당자 메일({mapped_email}) 전송이 완료되었습니다!")
                elif sheet_success:
                    st.warning(f"⚠️ 저장 및 구글 시트는 완료되었으나 이메일 전송에 실패했습니다. (사유: {email_msg})")
                else:
                    st.error("❌ 저장 및 전송 과정에서 오류가 발생했습니다.")

# ---------------- Tab 2: 실시간 도면 검측 뷰어 (Plotly 기반 안정 버전) ----------------
with main_tab2:
    st.subheader("🗺️ 현장 도면 실시간 핀 찍기 및 검측 뷰어")
    st.markdown("도면 이미지를 올린 후 아래 입력창에 **도면 상에서 클릭할 X, Y 좌표**를 입력하거나, 하단에 표시되는 팁을 참고하여 위치를 매칭하세요.")

    col_map_setting1, col_map_setting2 = st.columns([2, 1])
    with col_map_setting1:
        map_file = st.file_uploader("📂 현장 도면 이미지 업로드 (JPG, PNG)", type=["jpg", "jpeg", "png"], key="blueprint_upload")
    
    with col_map_setting2:
        target_item_to_pin = st.selectbox(
            "📌 매칭할 점검 항목 선택", 
            options=list(range(1, st.session_state.item_count + 1)),
            format_func=lambda x: f"점검 항목 #{x}",
            key="pin_target_item"
        )

    if map_file is not None:
        try:
            image = Image.open(map_file)
            img_width, img_height = image.size

            st.markdown(f"**🎯 [점검 항목 #{target_item_to_pin}] 위치 설정** (도면 해상도: 가로 {img_width}px × 세로 {img_height}px)")
            
            fig = px.imshow(image)
            
            if st.session_state.item_coords:
                pin_x = [pos['x'] for pos in st.session_state.item_coords.values()]
                pin_y = [pos['y'] for pos in st.session_state.item_coords.values()]
                pin_text = [f"항목 #{k}" for k in st.session_state.item_coords.keys()]
                
                fig.add_trace(go.Scatter(
                    x=pin_x, y=pin_y,
                    mode="markers+text",
                    text=pin_text,
                    textposition="top center",
                    marker=dict(size=14, color="red", symbol="cross")
                ))

            fig.update_layout(
                xaxis=dict(showgrid=False, zeroline=False),
                yaxis=dict(showgrid=False, zeroline=False),
                margin=dict(l=0, r=0, t=0, b=0),
                height=500
            )

            selected_point = st.plotly_chart(fig, use_container_width=True, on_select="rerun", selection_mode="points")

            clicked_x, clicked_y = None, None
            if selected_point and "selection" in selected_point and "points" in selected_point["selection"]:
                points = selected_point["selection"]["points"]
                if points:
                    clicked_x = int(points[0].get("x", 0))
                    clicked_y = int(points[0].get("y", 0))

            st.markdown("##### 📍 좌표 직접 입력 또는 확인")
            col_px, col_py, col_pbtn = st.columns([1, 1, 1])
            with col_px:
                input_x = st.number_input("X 좌표", min_value=0, max_value=img_width, value=clicked_x if clicked_x is not None else 100, key=f"input_x_{target_item_to_pin}")
            with col_py:
                input_y = st.number_input("Y 좌표", min_value=0, max_value=img_height, value=clicked_y if clicked_y is not None else 100, key=f"input_y_{target_item_to_pin}")
            with col_pbtn:
                st.write("")
                st.write("")
                if st.button(f"📌 [항목 #{target_item_to_pin}] 위치 저장", key=f"save_coord_btn_{target_item_to_pin}", use_container_width=True):
                    st.session_state.item_coords[target_item_to_pin] = {"x": input_x, "y": input_y}
                    st.success(f"항목 #{target_item_to_pin} 위치(X:{input_x}, Y:{input_y}) 저장 완료!")

        except Exception as e:
            st.error(f"도면을 불러오는 중 오류가 발생했습니다: {e}")
    else:
        st.info("💡 검측을 시작하려면 먼저 상단에서 현장 도면 이미지(JPG 또는 PNG)를 업로드해 주세요.")
        
        if st.session_state.item_coords:
            st.markdown("---")
            st.markdown("##### 📌 현재까지 지정된 도면 핀 현황")
            for item_idx, pos in st.session_state.item_coords.items():
                st.write(f"- **점검 항목 #{item_idx}**: X = {pos['x']}, Y = {pos['y']}")

# ---------------- Tab 3: 이력 조회 및 인터랙티브 대시보드 ----------------
with main_tab3:
    st.subheader("📊 인터랙티브 안전 트렌드 및 재발 방지 대시보드")
    
    rows = get_google_sheet_records()
    
    if len(rows) > 1:
        header = rows[0]
        data_values = rows[1:]
        df = pd.DataFrame(data_values)
        
        expected_cols = ["날짜", "점검 부서", "점검 현장", "항목수", "AI분석", "지적 분류", "작성자", "사진경로"]
        if len(df.columns) == len(expected_cols):
            df.columns = expected_cols
        else:
            cols = expected_cols[:len(df.columns)]
            while len(cols) < len(df.columns):
                cols.append(f"추가컬럼_{len(cols)+1}")
            df.columns = cols
        
        if "날짜" in df.columns:
            df["날짜"] = pd.to_datetime(df["날짜"], errors='coerce').dt.date

        col_a, col_b = st.columns(2)
        
        with col_a:
            st.markdown("##### 🏗️ 현장 및 부서별 안전 지적 빈도")
            if "점검 현장" in df.columns and not df.empty:
                group_cols = ["점검 현장"]
                if "점검 부서" in df.columns:
                    group_cols.append("점검 부서")
                
                site_counts = df.groupby(group_cols).size().reset_index(name="건수")
                
                pastel_colors = {
                    "시설사업1부": "#A3C1AD",
                    "시설사업2부": "#A0C4FF",
                    "시설사업3부": "#FFD6A5"
                }
                
                fig_bar = px.bar(
                    site_counts, 
                    x="점검 현장", 
                    y="건수", 
                    color="점검 부서" if "점검 부서" in df.columns else None,
                    color_discrete_map=pastel_colors,
                    barmode="group",
                    text="건수"
                )
                
                fig_bar.update_layout(
                    xaxis_title="", 
                    yaxis_title="건수", 
                    margin=dict(t=10, b=10, l=10, r=10),
                    showlegend=True if "점검 부서" in df.columns else False
                )
                st.plotly_chart(fig_bar, use_container_width=True)

        with col_b:
            st.markdown("##### ⚠️ 주요 사고 유형별 비율")
            if not df.empty:
                def classify_accident_type(text):
                    text_str = str(text)
                    if any(k in text_str for k in ["추락", "난간", "개구부", "비계", "발판"]):
                        return "추락 위험"
                    elif any(k in text_str for k in ["끼임", "협착", "벨트", "롤러", "회전체"]):
                        return "끼임 위험"
                    elif any(k in text_str for k in ["화재", "용접", "불꽃", "소화기", "인화성"]):
                        return "화재/폭발 위험"
                    elif any(k in text_str for k in ["전기", "누전", "배선", "충전부"]):
                        return "전기 안전"
                    else:
                        return "기타 일반 안전"

                df["사고유형"] = df["AI분석"].apply(classify_accident_type)
                type_counts = df["사고유형"].value_counts().reset_index()
                type_counts.columns = ["유형", "건수"]

                fig_pie = px.pie(
                    type_counts, 
                    names="유형", 
                    values="건수", 
                    hole=0.4,
                    color_discrete_sequence=px.colors.qualitative.Pastel
                )
                fig_pie.update_layout(
                    margin=dict(t=10, b=10, l=10, r=10),
                    legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5)
                )
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.info("데이터가 부족하여 사고 유형 분석을 표시할 수 없습니다.")

        st.markdown("---")
        st.markdown("##### 📋 전체 점검 이력 원본 데이터")
        st.dataframe(df, use_container_width=True)
    else:
        st.info("📝 아직 구글 시트에 저장된 점검 이력이 없습니다. [안전 점검 등록] 탭에서 첫 점검을 완료해 보세요.")

import os

# ---------------- Tab 4: AI 안전 가이드 Q&A (RAG) ----------------
with main_tab4:
    st.subheader("📖 AI 환경시설 안전 가이드 및 규정 Q&A")
    st.markdown("환경시설 건설현장 안전에 관련된 모든것을 물어보세요.")

    if "qa_messages" not in st.session_state:
        st.session_state.qa_messages = [
            {"role": "assistant", "content": "안녕하세요! 푸루·그루입니다. 환경시설 건설현장 안전 규정이나 지침에 대해 무엇이든 물어보세요!"}
        ]

    # 기존 대화 기록 출력
    for msg in st.session_state.qa_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # 단 하나의 채팅 입력창
    if user_query := st.chat_input("예: 밀폐공간 작업 시 산소 및 유해가스 측정 기준이 어떻게 되나요?"):
        st.session_state.qa_messages.append({"role": "user", "content": user_query})
        with st.chat_message("user"):
            st.markdown(user_query)

        with st.chat_message("assistant"):
            with st.spinner("관련 안전 규정을 검토 중입니다..."):
                try:
                    data_dir = "DATA"
                    context_text = ""
                    
                    if os.path.exists(data_dir):
                        for filename in os.listdir(data_dir):
                            file_path = os.path.join(data_dir, filename)
                            if filename.endswith(".txt") and os.path.isfile(file_path):
                                with open(file_path, "r", encoding="utf-8") as f:
                                    context_text += f"\n--- [문서 파일: {filename}] ---\n" + f.read()

                    client = genai.Client(api_key=api_key)
                    
                    rag_prompt = (
                        "당신은 한국환경공단(KECO) 수도권서부환경본부의 전문 안전 기술 자문 AI입니다.\n"
                        "아래 제공된 참고 문서 및 산업안전보건기준에 관한 규칙을 바탕으로, "
                        "다음 질문에 대해 정확하고 실무에 도움이 되는 조치 사항을 친절하게 답변해주세요.\n\n"
                        f"[참고 문서 내용]\n{context_text if context_text else '추가 문서 없음'}\n\n"
                        f"질문: {user_query}"
                    )
                    
                    response = client.models.generate_content(model="gemini-3.6-flash", contents=rag_prompt)
                    answer_text = response.text if response and response.text else "답변을 생성하지 못했습니다."
                    
                    # AI 답변 화면 출력
                    st.markdown(answer_text)
                    st.session_state.qa_messages.append({"role": "assistant", "content": answer_text})

                    # ====================================================
                    # 📄 PDF 문서 출력 및 다운로드 기능 (답변 바로 밑에 통합)
                    # ====================================================
                    st.markdown("---")
                    st.subheader("📄 보고서 문서 출력")
                    
                    # PDF 생성 버튼 (Streamlit 특성상 버튼 클릭 시 실행)
                    if st.button("📥 PDF 문서로 다운로드", key="pdf_download_btn"):
                        try:
                            # PDF 바이트 데이터 생성
                            pdf_data = generate_pdf("KECO 현장 안전 점검 및 규정 검토 보고서", answer_text)
                            
                            # 다운로드 버튼 제공
                            st.download_button(
                                label="클릭하여 PDF 파일 저장",
                                data=pdf_data,
                                file_name="safety_inspection_report.pdf",
                                mime="application/pdf",
                                key="final_pdf_download"
                            )
                            st.success("PDF 문서가 성공적으로 준비되었습니다! 위 버튼을 눌러 저장하세요.")
                        except Exception as pdf_err:
                            st.error(f"PDF 생성 중 오류가 발생했습니다: {pdf_err}")
                    # ====================================================

                except Exception as e:
                    err_msg = f"답변 생성 중 오류가 발생했습니다: {e}"
                    st.error(err_msg)
                    st.session_state.qa_messages.append({"role": "assistant", "content": err_msg})
