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
    page_title="한국환경공단 수도권서부환경본부 | AI 스마트 안전 점검 시스템",
    page_icon="puru_guru.png",
    layout="centered",
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

# --- 🎨 프리미엄 커스텀 CSS (모던 공공기관 스타일) ---
st.markdown("""
    <style>
    /* 전체 폰트 및 배경 기본 설정 */
    html, body, [data-testid="stAppViewContainer"] {
        color: #0F172A !important;
        font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, system-ui, Roboto, sans-serif !important;
    }
    .stApp {
        background-color: #F1F5F9;
    }
    .stMarkdown, p, div, span, label {
        word-break: keep-all !important;
        white-space: normal !important;
    }
    
    /* 사이드바 스타일링 */
    [data-testid="stSidebar"] {
        background-color: #FFFFFF;
        border-right: 1px solid #E2E8F0;
    }

    /* 상단 헤더 배너 디자인 */
    .keco-header {
        background: linear-gradient(135deg, #00662B 0%, #009846 100%);
        padding: 28px 24px;
        border-radius: 20px;
        color: white;
        text-align: center;
        margin-bottom: 24px;
        box-shadow: 0 10px 25px -5px rgba(0, 102, 43, 0.25);
    }
    .keco-header h2 {
        color: white !important;
        font-size: 1.65rem !important;
        font-weight: 800 !important;
        margin: 0 !important;
        letter-spacing: -0.5px;
    }
    .keco-header p {
        color: #D1FAE5 !important;
        font-size: 0.95rem !important;
        margin-top: 8px !important;
        margin-bottom: 0 !important;
        font-weight: 400;
    }

    /* 마스코트 안내 배너 */
    .mascot-banner {
        background: white;
        border-radius: 18px;
        padding: 22px;
        text-align: center;
        border: 1px solid #E2E8F0;
        box-shadow: 0 4px 15px rgba(0,0,0,0.03);
        margin-bottom: 24px;
    }

    /* 섹션 카드 디자인 */
    .mascot-card {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 16px;
        padding: 16px 20px;
        margin-bottom: 20px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.02);
    }
    
    /* 선택 대상 안내 박스 */
    .select-card {
        background: linear-gradient(135deg, #ECFDF5 100%, #D1FAE5 0%);
        border: 1px solid #34D399;
        border-radius: 14px;
        padding: 16px 20px;
        margin-bottom: 24px;
        color: #065F46 !important;
        font-weight: 600;
        box-shadow: 0 4px 12px rgba(16, 185, 129, 0.08);
    }

    /* 개별 점검 항목 카드 */
    .item-card {
        background-color: #FFFFFF;
        border: 1px solid #CBD5E1;
        border-radius: 16px;
        padding: 22px;
        margin-bottom: 24px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.03);
    }

    /* AI 분석 결과 박스 */
    .analysis-box {
        background-color: #FFF1F2;
        border: 1px solid #FECDD3;
        border-left: 5px solid #E11D48;
        border-radius: 12px;
        padding: 16px;
        margin-top: 12px;
        margin-bottom: 15px;
        font-size: 0.94rem;
        color: #881337 !important;
        box-shadow: 0 2px 6px rgba(225, 29, 72, 0.04);
    }

    /* 라벨 텍스트 가독성 강화 */
    label, div[data-baseweb="select"] span, .stSelectbox label, .stTextInput label, .stTextArea label, .stFileUploader label {
        color: #334155 !important;
        font-weight: 700 !important;
        font-size: 0.95rem !important;
    }

    /* 메인 액션 버튼 스타일 (그라데이션 & 입체감) */
    div.stButton > button {
        background: linear-gradient(135deg, #00662B 0%, #009846 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        font-weight: 700 !important;
        height: 52px !important;
        font-size: 1.05rem !important;
        box-shadow: 0 4px 14px rgba(0, 102, 43, 0.25) !important;
        transition: all 0.2s ease-in-out;
    }
    div.stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 6px 20px rgba(0, 102, 43, 0.35) !important;
    }

    /* 탭 디자인 현대화 */
    div.stTabs [data-baseweb="tab-list"] {
        background-color: #E2E8F0;
        padding: 6px;
        border-radius: 14px;
        gap: 4px;
    }
    div.stTabs [data-baseweb="tab"] {
        background-color: transparent;
        border-radius: 10px;
        padding: 10px 20px;
        font-weight: 700;
        color: #64748B;
        border: none;
    }
    div.stTabs [aria-selected="true"] {
        background-color: #FFFFFF !important;
        color: #00662B !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
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
            <h2 style="color:#00662B; font-weight:800;">🌱 한국환경공단 감독관 인증</h2>
            <p style="color:#64748B; font-size:1rem;">인증된 사내 감독관 계정으로 로그인해 주세요.</p>
        </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        user_id = st.text_input("👤 감독관 ID (사번)", key="username_input")
        user_pw = st.text_input("🔑 비밀번호", type="password", key="password_input")
        
        st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
        if st.button("안전시스템 로그인", use_container_width=True):
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

# 로그인된 사번을 바탕으로 자동 매핑된 이메일 가져오기
logged_user_id = st.session_state.get('logged_user')
user_emails_map = st.secrets.get("user_emails", {})
mapped_email = user_emails_map.get(str(logged_user_id), st.secrets.get("smtp", {}).get("receiver_email", ""))

st.sidebar.markdown("### 🔒 접속 계정 정보")
st.sidebar.info(f"사번: **{logged_user_id}**\n\n자동 매핑 이메일:\n`{mapped_email if mapped_email else '미등록'}`")

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
    """업로드된 이미지를 사내망 공용 폴더(경로)에 저장하는 함수"""
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
    """로그인된 사번(inspector_id)을 기반으로 secrets에서 이메일을 자동 매핑하여 전송하는 함수"""
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

        # 본문 구성
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
            body_html += f"<p><b>[항목 #{k}]</b><br>• 조치 내용: {v['desc']}<br>• AI 분석: {v['ai_analysis'].replace(chr(10), '<br>')}</p>"

        msg.attach(MIMEText(body_html, 'html', 'utf-8'))

        # 이미지 첨부 (BytesIO 활용)
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
                    
        # SMTP 전송
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


# --- 5. 헤더 UI ---
st.markdown("""
    <div class="keco-header">
        <h2>🌱 한국환경공단 수도권서부환경본부</h2>
        <p>환경시설관리처 현장 안전 조치 전·후 스마트 점검 시스템</p>
    </div>
""", unsafe_allow_html=True)

image_html = f'<img src="data:image/png;base64,{img_base64}" style="max-height: 90px; border-radius: 10px;">' if img_base64 else '🌱'

st.markdown(f"""
    <div class="mascot-banner">
        <div style="margin-bottom: 8px;">{image_html}</div>
        <h4 style="margin:0; color:#00662B; font-weight:700;">"안전점검 시작! 푸루와 그루가 든든하게 지원합니다."</h4>
        <p style="margin-top:6px; font-size:0.9rem; color:#64748B;">사내망 자동 저장, 구글 시트 실시간 기록 및 담당자 메일 자동 발송 시스템</p>
    </div>
""", unsafe_allow_html=True)


# --- 6. 메인 탭 ---
main_tab1, main_tab2 = st.tabs(["📝 안전 점검 등록", "📊 부서별 점검 이력"])

with main_tab1:
    st.markdown("""
        <div class="mascot-card">
            <div>
                <strong style="color:#059669;">📌 점검 기본 정보 설정</strong><br>
                <span style="font-size:0.9rem; color:#475569;">점검을 진행할 담당 부서와 현장을 선택해 주세요.</span>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    departments = ["시설사업1부", "시설사업2부", "시설사업3부"]
    sites = ["1현장", "2현장", "3현장", "4현장"]

    col_dept, col_site = st.columns(2)
    with col_dept:
        selected_dept = st.selectbox("담당 부서", departments)
    with col_site:
        selected_site = st.selectbox("점검 현장", sites)

    st.markdown(f"""
        <div class="select-card">
            📍 선택 대상: <strong>[{selected_dept}] - {selected_site}</strong> &nbsp;|&nbsp; 작성자 사번: <code>{logged_user_id}</code>
        </div>
    """, unsafe_allow_html=True)

    st.subheader("📸 현장 사진 등록 및 AI 위험성 평가")
    st.caption("💡 각 항목별로 '조치 전'과 '조치 후' 사진을 여러 장 다중 첨부할 수 있습니다.")

    form_data = {}

    for idx in range(1, st.session_state.item_count + 1):
        st.markdown(f"""
            <div class="item-card">
                <h4 style="margin-top:0; color:#00662B; font-weight:700;">🔹 점검 항목 #{idx}</h4>
        """, unsafe_allow_html=True)
        
        col_b, col_a = st.columns(2)
        
        # --- [조치 전 섹션] ---
        with col_b:
            st.markdown("##### 🔴 조치 전 (Before)")
            before_img_files = st.file_uploader(
                f"항목 #{idx} 조치 전 사진",
                type=["jpg", "jpeg", "png"],
                accept_multiple_files=True,
                key=f"before_imgs_{idx}"
            )
            
            if before_img_files:
                st.write(f"📷 선택된 사진: **{len(before_img_files)}장**")
                cols = st.columns(min(len(before_img_files), 2))
                for img_i, img_f in enumerate(before_img_files):
                    cols[img_i % 2].image(img_f, caption=f"조치 전 #{img_i+1}", use_container_width=True)
                
                if st.button(f"🔍 [항목 #{idx}] 조치 전 사진 AI 위험 분석", key=f"btn_ai_{idx}", use_container_width=True):
                    with st.spinner("푸루 AI가 위험 요소를 분석 중입니다..."):
                        if idx not in st.session_state.ai_results:
                            st.session_state.ai_results[idx] = {}
                        
                        for img_i, img_f in enumerate(before_img_files, start=1):
                            try:
                                result_text = analyze_hazard_auto(api_key, img_f)
                                st.session_state.ai_results[idx][img_i] = result_text
                            except Exception as e:
                                st.session_state.ai_results[idx][img_i] = f"분석 오류: {e}"

            if idx in st.session_state.ai_results and st.session_state.ai_results[idx]:
                st.markdown("**🤖 AI 위험 분석 결과**")
                for img_i, res_text in st.session_state.ai_results[idx].items():
                    st.markdown(f"""
                        <div class="analysis-box">
                            <strong>[사진 #{img_i}]</strong><br>
                            {res_text.replace('\n', '<br>')}
                        </div>
                    """, unsafe_allow_html=True)

        # --- [조치 후 섹션] ---
        with col_a:
            st.markdown("##### 🟢 조치 후 (After)")
            after_img_files = st.file_uploader(
                f"항목 #{idx} 조치 후 사진",
                type=["jpg", "jpeg", "png"],
                accept_multiple_files=True,
                key=f"after_imgs_{idx}"
            )
            if after_img_files:
                st.write(f"📷 선택된 사진: **{len(after_img_files)}장**")
                cols = st.columns(min(len(after_img_files), 2))
                for img_i, img_f in enumerate(after_img_files):
                    cols[img_i % 2].image(img_f, caption=f"조치 후 #{img_i+1}", use_container_width=True)

        desc = st.text_area(
            f"✍️ 항목 #{idx} 조치 내용 상세 입력", 
            placeholder="예: 개구부 주변 안전난간 보강 및 추락방지망 추가 설치 완료", 
            key=f"desc_{idx}"
        )
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        if before_img_files or after_img_files or desc.strip():
            ai_summary_list = []
            if idx in st.session_state.ai_results:
                for img_i, res_text in st.session_state.ai_results[idx].items():
                    ai_summary_list.append(f"(사진#{img_i}) {res_text}")
            
            form_data[idx] = {
                "before_files": before_img_files if before_img_files else [],
                "after_files": after_img_files if after_img_files else [],
                "desc": desc.strip(),
                "ai_analysis": "\n".join(ai_summary_list) if ai_summary_list else "분석 미실행"
            }

    # --- 동적 항목 추가 / 삭제 버튼 ---
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
                st.session_state.item_count -= 1
                st.rerun()

    st.markdown("<div style='margin: 30px 0;'></div>", unsafe_allow_html=True)

    # 최종 제출 버튼
    if st.button(f"💾 [{selected_dept} {selected_site}] 점검 최종 제출 및 자동 발송", use_container_width=True):
        if not form_data:
            st.warning("⚠️ 최소 1개 이상의 항목에 사진이나 조치 내용을 작성해 주세요.")
        else:
            internal_folder = st.secrets.get("INTERNAL_FOLDER_PATH", "./KecoSafetyImages")
            
            with st.spinner("🔄 사내망 저장, 구글 시트 기록 및 담당자 메일 발송 처리 중입니다..."):
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

                    path_text = f"[항목#{k}] 전:{len(b_paths)}장, 후:{len(a_paths)}장"
                    if b_paths or a_paths: 
                        combined_files_path = b_paths + a_paths
                        path_text += f" (경로: {', '.join(combined_files_path)})"
                    
                    all_photo_paths.append(path_text)
                    details.append(f"[항목 #{k}] 전:{len(v['before_files'])}장, 후:{len(v['after_files'])}장 ({v['desc'][:15]})")
                
                combined_ai = "\n\n".join(all_ai_summaries) if all_ai_summaries else "조치 전 AI 분석 미실행"
                combined_detail = " | ".join(details)
                combined_paths_str = " || ".join(all_photo_paths)
                
                # 1. 구글 시트 저장
                sheet_success = save_to_google_sheet(selected_dept, selected_site, len(form_data), combined_ai, combined_detail, logged_user_id, combined_paths_str)
                
                # 2. 이메일 전송
                email_success, email_msg = send_inspection_email(selected_dept, selected_site, logged_user_id, form_data)
                
                if sheet_success and email_success:
                    st.success(f"🎉 [{selected_dept} {selected_site}] 점검 내역이 사내망 저장, 구글 시트 기록 및 담당자 메일({mapped_email}) 전송까지 모두 완료되었습니다!")
                elif sheet_success:
                    st.warning(f"⚠️ 사내망 저장 및 구글 시트 기록은 완료되었으나 이메일 전송에 실패했습니다. (사유: {email_msg})")
                else:
                    st.error("❌ 저장 및 전송 과정에서 오류가 발생했습니다.")

# ---------------- Tab 2: 이력 조회 ----------------
with main_tab2:
    st.subheader("📂 부서별 점검 이력 조회")
    rows = get_google_sheet_records()
    
    if len(rows) <= 1:
        st.info("저장된 점검 이력이 없습니다.")
    else:
        filter_col1, filter_col2 = st.columns(2)
        with filter_col1:
            filter_dept = st.selectbox("🔍 부서 필터", ["전체 부서"] + departments, key="hist_dept")
        with filter_col2:
            filter_site = st.selectbox("🔍 현장 필터", ["전체 현장"] + sites, key="hist_site")

        data_rows = rows[1:][::-1]
        
        for r in data_rows:
            timestamp = r[0] if len(r) > 0 else "-"
            dept = r[1] if len(r) > 1 else "-"
            site = r[2] if len(r) > 2 else "-"
            count = r[3] if len(r) > 3 else "-"
            ai_text = r[4] if len(r) > 4 else "-"
            detail = r[5] if len(r) > 5 else "-"
            inspector = r[6] if len(r) > 6 else "기록 없음"
            photo_paths = r[7] if len(r) > 7 else "사진 경로 없음"
            
            if (filter_dept in ["전체 부서", dept]) and (filter_site in ["전체 현장", site]):
                with st.expander(f"🗓️ [{timestamp}] {dept} | {site} ({count}) — 작성자 사번: {inspector}"):
                    st.write(f"**현장 조치 요약:** {detail}")
                    st.info(ai_text)
                    st.markdown("---")
                    st.markdown(f"📁 **사내망 사진 저장 경로:**\n`{photo_paths}`")
