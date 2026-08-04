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
    page_title="한국환경공단 수도권서부환경본부 | Canvas AI 안전 점검 대시보드",
    page_icon="puru_guru.png",
    layout="wide",  # 대시보드 느낌을 살리기 위해 wide 모드 적용
    initial_sidebar_state="expanded"
)

# --- Base64 이미지 변환 함수 ---
def get_base64_image(image_path):
    try:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except Exception:
        return ""

img_base64 = get_base64_image("puru_guru.png")

# --- 커스텀 CSS (Canvas 대시보드 스타일링) ---
st.markdown("""
    <style>
    html, body, [data-testid="stAppViewContainer"] {
        color: #1E293B !important;
    }
    .stApp {
        background-color: #F8FAFC;
    }
    .dashboard-header {
        background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%);
        padding: 24px 28px;
        border-radius: 16px;
        color: white;
        margin-bottom: 24px;
        box-shadow: 0 4px 20px rgba(15, 23, 42, 0.15);
    }
    .dashboard-header h1 {
        color: #FFFFFF !important;
        font-size: 1.8rem !important;
        font-weight: 800 !important;
        margin: 0 !important;
    }
    .dashboard-header p {
        color: #94A3B8 !important;
        font-size: 0.95rem !important;
        margin-top: 6px !important;
        margin-bottom: 0 !important;
    }
    /* 캔버스 스타일 카드 컴포넌트 */
    .canvas-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 14px;
        padding: 20px;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.03);
        margin-bottom: 20px;
    }
    .metric-card {
        background: linear-gradient(135deg, #F0FDF4 0%, #DCFCE7 100%);
        border: 1px solid #86EFAC;
        border-radius: 12px;
        padding: 16px;
        text-align: center;
        box-shadow: 0 2px 6px rgba(0, 122, 51, 0.05);
    }
    .metric-card h3 {
        color: #166534 !important;
        margin: 0 !important;
        font-size: 1.6rem !important;
    }
    .metric-card p {
        color: #15803D !important;
        margin: 4px 0 0 0 !important;
        font-size: 0.85rem !important;
        font-weight: 600;
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
    </style>
""", unsafe_allow_html=True)


# ==========================================
# 🔒 [보안] 감독관 로그인 제어 게이트웨이
# ==========================================
def check_password():
    if st.session_state.get("password_correct", False):
        return True

    allowed_users = st.secrets.get("passwords", {})

    st.markdown("""
        <div style="text-align:center; padding: 40px 10px 20px 10px;">
            <h2 style="color:#007A33;">🌱 한국환경공단 Canvas 보안 인증</h2>
            <p style="color:#64748B;">인증된 사내 감독관 계정으로 로그인해 주세요.</p>
        </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        user_id = st.text_input("👤 감독관 ID (사번)", key="username_input")
        user_pw = st.text_input("🔑 비밀번호", type="password", key="password_input")
        
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

st.sidebar.markdown("### 🔒 감독관 세션 정보")
st.sidebar.write(f"접속 사번: **{logged_user_id}**")
st.sidebar.write(f"수신 이메일: **{mapped_email if mapped_email else '미등록(기본값 사용)'}**")

if st.sidebar.button("🔓 로그아웃", use_container_width=True):
    st.session_state["password_correct"] = False
    st.rerun()


# --- Google Sheets 연동 유틸 ---
@st.cache_resource
def get_gcp_credentials():
    return Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )

def get_google_sheet_records():
    try:
        creds = get_gcp_credentials()
        client = gspread.authorize(creds)
        sheet_id = st.secrets["SPREADSHEET_ID"]
        sheet = client.open_by_key(sheet_id).sheet1
        return sheet.get_all_values()
    except Exception:
        return []

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
    except Exception:
        return None

def send_inspection_email(dept_name, site_name, inspector_id, form_data):
    try:
        smtp_conf = st.secrets.get("smtp", {})
        smtp_server = smtp_conf.get("server", "smtp.gmail.com")
        smtp_port = smtp_conf.get("port", 587)
        sender_email = smtp_conf.get("sender_email", "")
        sender_password = smtp_conf.get("sender_password", "")

        if not sender_email or not sender_password:
            return False, "SMTP 설정 누락"

        user_emails_map = st.secrets.get("user_emails", {})
        receiver_email = user_emails_map.get(str(inspector_id), smtp_conf.get("receiver_email", sender_email))

        msg = MIMEMultipart()
        msg['Subject'] = Header(f"[안전점검 보고] {dept_name} - {site_name} (작성자: {inspector_id})", 'utf-8')
        msg['From'] = Header(f"KECO Canvas 시스템 <{sender_email}>", 'utf-8')
        msg['To'] = Header(receiver_email, 'utf-8')

        body_html = f"<h3>🌱 한국환경공단 현장 안전 점검 보고 (Canvas)</h3><p><b>- 부서:</b> {dept_name} / <b>현장:</b> {site_name}</p><hr>"
        for k, v in form_data.items():
            body_html += f"<p><b>[항목 #{k}]</b><br>• 조치내용: {v['desc']}<br>• AI 분석: {v['ai_analysis'].replace(chr(10), '<br>')}</p>"

        msg.attach(MIMEText(body_html, 'html', 'utf-8'))

        for k, v in form_data.items():
            for img_f in v.get('before_files', []):
                try:
                    img_f.seek(0)
                    part = MIMEApplication(io.BytesIO(img_f.read()).getvalue(), Name=f"Before_Item{k}.jpg")
                    part['Content-Disposition'] = f'attachment; filename="Before_Item{k}.jpg"'
                    msg.attach(part)
                except: pass

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
        sheet.append_row([datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), dept_name, site_name, f"{set_count}개 항목", analysis_summary, summary_detail, inspector_id, photo_info_str])
        return True
    except:
        return False

# --- AI 위험 분석 함수 ---
def analyze_hazard_auto(api_key, img_file):
    client = genai.Client(api_key=api_key)
    img_file.seek(0)
    img = Image.open(img_file)
    prompt = "당신은 한국환경공단(KECO) 안전 전문 AI입니다. 조치 전 사진을 분석하여 1. 주요 위험 요소 (1문장), 2. 위험 등급 [상/중/하], 3. 권장 조치 사항 (1문장)으로 요약하세요."
    
    for model_name in ["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.5-pro"]:
        try:
            res = client.models.generate_content(model=model_name, contents=[prompt, img])
            if res and res.text: return res.text
        except: continue
    return "AI 분석 실패"

if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    st.error("API Key가 설정되지 않았습니다.")
    st.stop()

if "item_count" not in st.session_state: st.session_state.item_count = 1
if "ai_results" not in st.session_state: st.session_state.ai_results = {}

# ==========================================
# 📊 [Canvas 대시보드 UI 영역]
# ==========================================
st.markdown("""
    <div class="dashboard-header">
        <h1>🌱 KECO Canvas 안전 모니터링 대시보드</h1>
        <p>수도권서부환경본부 환경시설관리처 실시간 현장 점검 및 AI 리스크 통합 제어 패널</p>
    </div>
""", unsafe_allow_html=True)

# 시트 데이터를 불러와 대시보드 지표 통계 계산
sheet_rows = get_google_sheet_records()
total_inspections = max(0, len(sheet_rows) - 1)

col_m1, col_m2, col_m3, col_m4 = st.columns(4)
with col_m1:
    st.markdown(f"""
        <div class="metric-card">
            <h3>{total_inspections}건</h3>
            <p>누적 안전 점검 보고</p>
        </div>
    """, unsafe_allow_html=True)
with col_m2:
    st.markdown("""
        <div class="metric-card">
            <h3>실시간</h3>
            <p>AI 위험도 자동 판별</p>
        </div>
    """, unsafe_allow_html=True)
with col_m3:
    st.markdown("""
        <div class="metric-card">
            <h3>자동 연동</h3>
            <p>구글 시트 & 사내망 저장</p>
        </div>
    """, unsafe_allow_html=True)
with col_m4:
    st.markdown("""
        <div class="metric-card">
            <h3>즉시 발송</h3>
            <p>사번 매핑 이메일 리포트</p>
        </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# --- 메인 탭 (점검 등록 & 이력 대시보드) ---
main_tab1, main_tab2 = st.tabs(["📋 신규 안전 점검 등록 (Canvas)", "📊 부서별 점검 이력 대시보드"])

with main_tab1:
    st.markdown('<div class="canvas-card">', unsafe_allow_html=True)
    st.subheader("🏗️ 현장 정보 및 점검 항목 구성")
    
    departments = ["시설사업1부", "시설사업2부", "시설사업3부"]
    sites = ["1현장", "2현장", "3현장", "4현장"]

    col_dept, col_site = st.columns(2)
    with col_dept:
        selected_dept = st.selectbox("📌 담당 부서 선택", departments)
    with col_site:
        selected_site = st.selectbox("🏗️ 점검 현장 선택", sites)

    st.markdown("---")

    form_data = {}
    for idx in range(1, st.session_state.item_count + 1):
        st.markdown(f"#### 🔹 점검 항목 #{idx}")
        col_b, col_a = st.columns(2)
        
        with col_b:
            before_img_files = st.file_uploader(f"조치 전 (Before) 사진 첨부 #{idx}", type=["jpg", "jpeg", "png"], accept_multiple_files=True, key=f"b_img_{idx}")
            if before_img_files:
                if st.button(f"🔍 [항목 #{idx}] 조치 전 사진 AI 위험 분석", key=f"ai_btn_{idx}"):
                    with st.spinner("AI가 위험 요소를 분석 중입니다..."):
                        if idx not in st.session_state.ai_results: st.session_state.ai_results[idx] = {}
                        for i, img_f in enumerate(before_img_files, start=1):
                            st.session_state.ai_results[idx][i] = analyze_hazard_auto(api_key, img_f)
            
            if idx in st.session_state.ai_results and st.session_state.ai_results[idx]:
                for i, res in st.session_state.ai_results[idx].items():
                    st.error(f"**[AI 분석 결과 #{i}]**\n{res}")

        with col_a:
            after_img_files = st.file_uploader(f"조치 후 (After) 사진 첨부 #{idx}", type=["jpg", "jpeg", "png"], accept_multiple_files=True, key=f"a_img_{idx}")

        desc = st.text_area(f"✍️ [항목 #{idx}] 현장 조치 내용 입력", key=f"desc_{idx}")
        st.markdown("---")
        
        if before_img_files or after_img_files or desc.strip():
            ai_list = [f"(사진#{i}) {r}" for i, r in st.session_state.ai_results.get(idx, {}).items()]
            form_data[idx] = {
                "before_files": before_img_files or [],
                "after_files": after_img_files or [],
                "desc": desc.strip(),
                "ai_analysis": "\n".join(ai_list) if ai_list else "분석 미실행"
            }

    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("➕ 항목 추가"):
            st.session_state.item_count += 1
            st.rerun()
    with col_btn2:
        if st.session_state.item_count > 1:
            if st.button("➖ 마지막 항목 삭제"):
                st.session_state.item_count -= 1
                st.rerun()

    if st.button("💾 전체 점검 내역 저장, 이메일 전송 및 대시보드 동기화", use_container_width=True):
        if not form_data:
            st.warning("작성된 항목이 없습니다.")
        else:
            internal_folder = st.secrets.get("INTERNAL_FOLDER_PATH", "./KecoSafetyImages")
            with st.spinner("처리 중..."):
                all_ai, details, all_paths = [], [], []
                for k, v in form_data.items():
                    if v['ai_analysis'] != "분석 미실행": all_ai.append(f"[항목 #{k}]: {v['ai_analysis']}")
                    b_paths = [save_image_to_internal_network(img, internal_folder, f"Before_{selected_dept}_{selected_site}_Item{k}") for img in v['before_files']]
                    a_paths = [save_image_to_internal_network(img, internal_folder, f"After_{selected_dept}_{selected_site}_Item{k}") for img in v['after_files']]
                    all_paths.append(f"[항목#{k}] 전:{len(b_paths)}, 후:{len(a_paths)}")
                    details.append(f"[항목 #{k}] {v['desc'][:15]}")
                
                sheet_ok = save_to_google_sheet(selected_dept, selected_site, len(form_data), "\n".join(all_ai), " | ".join(details), logged_user_id, " || ".join(all_paths))
                email_ok, email_msg = send_inspection_email(selected_dept, selected_site, logged_user_id, form_data)
                
                if sheet_ok and email_ok:
                    st.success(f"🎉 성공적으로 저장 및 이메일({mapped_email}) 전송이 완료되었습니다!")
                else:
                    st.error(f"저장 중 오류 발생 (메일 오류: {email_msg})")
    st.markdown('</div>', unsafe_allow_html=True)

with main_tab2:
    st.markdown('<div class="canvas-card">', unsafe_allow_html=True)
    st.subheader("📊 부서별 점검 이력 데이터 대시보드")
    rows = get_google_sheet_records()
    if len(rows) <= 1:
        st.info("등록된 이력이 없습니다.")
    else:
        f_dept = st.selectbox("부서 필터", ["전체 부서"] + departments, key="h_dept")
        f_site = st.selectbox("현장 필터", ["전체 현장"] + sites, key="h_site")
        
        for r in rows[1:][::-1]:
            ts, dept, site, cnt, ai, det, insp, paths = (r + [""]*8)[:8]
            if (f_dept in ["전체 부서", dept]) and (f_site in ["전체 현장", site]):
                with st.expander(f"🗓️ [{ts}] {dept} - {site} (작성자 사번: {insp})"):
                    st.write(f"**상세내용:** {det}")
                    st.info(ai)
                    st.text(f"저장 경로: {paths}")
    st.markdown('</div>', unsafe_allow_html=True)
