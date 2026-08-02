import streamlit as st
from PIL import Image
from google import genai
import gspread
from google.oauth2.service_account import Credentials
import datetime

# --- 페이지 기본 설정 (한국환경공단 메인 테마) ---
st.set_page_config(
    page_title="한국환경공단 | AI 현장 위험요소 분석기",
    page_icon="🌱",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- 커스텀 CSS (한국환경공단 상징 컬러 & 깔끔한 카드 UI 적용) ---
st.markdown("""
    <style>
    /* 메인 배경 및 기본 폰트 설정 */
    .stApp {
        background-color: #F8FBF9;
    }
    
    /* 상단 KECO 브랜드 헤더 */
    .keco-header {
        background: linear-gradient(135deg, #007A33 0%, #10B981 100%);
        padding: 22px 18px;
        border-radius: 16px;
        color: white;
        text-align: center;
        margin-bottom: 20px;
        box-shadow: 0 4px 15px rgba(0, 122, 51, 0.15);
    }
    .keco-header h2 {
        color: white !important;
        font-size: 1.5rem !important;
        font-weight: 700 !important;
        margin: 0 !important;
        padding: 0 !important;
    }
    .keco-header p {
        color: #E6F4EA !important;
        font-size: 0.9rem !important;
        margin-top: 6px !important;
        margin-bottom: 0 !important;
    }

    /* 캐릭터 소개 박스 */
    .mascot-banner {
        background-color: #FFFFFF;
        border: 2px solid #E2E8F0;
        border-radius: 14px;
        padding: 12px 16px;
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 20px;
    }
    .mascot-icon {
        font-size: 2.2rem;
    }
    .mascot-text {
        font-size: 0.92rem;
        color: #334155;
        line-height: 1.4;
    }
    .mascot-text strong {
        color: #007A33;
    }

    /* 카드 스타일 */
    .result-card {
        background-color: #FFFFFF;
        border-radius: 12px;
        padding: 18px;
        border-left: 5px solid #007A33;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
        margin-top: 15px;
        margin-bottom: 15px;
    }

    /* Streamlit 기본 버튼 커스텀 */
    div.stButton > button {
        background: linear-gradient(135deg, #007A33 0%, #059669 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 10px !important;
        font-weight: bold !important;
        height: 48px !important;
        font-size: 1.05rem !important;
        box-shadow: 0 3px 6px rgba(0, 122, 51, 0.2) !important;
    }
    div.stButton > button:hover {
        background: linear-gradient(135deg, #005F27 0%, #047857 100%) !important;
        transform: translateY(-1px);
    }
    </style>
""", unsafe_allow_html=True)


# --- 1. Google Sheets 연동 함수 ---
@st.cache_resource
def get_gspread_client():
    credentials = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
    )
    client = gspread.authorize(credentials)
    return client

def save_to_google_sheet(filename, result_text):
    try:
        client = get_gspread_client()
        sheet_id = st.secrets["SPREADSHEET_ID"]
        sheet = client.open_by_key(sheet_id).sheet1
        
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sheet.append_row([now_str, filename, result_text])
        return True
    except Exception as e:
        st.error(f"구글 시트 저장 중 오류가 발생했습니다: {e}")
        return False

def get_google_sheet_records():
    try:
        client = get_gspread_client()
        sheet_id = st.secrets["SPREADSHEET_ID"]
        sheet = client.open_by_key(sheet_id).sheet1
        records = sheet.get_all_values()
        return records
    except Exception as e:
        st.error(f"구글 시트 데이터 불러오기 오류: {e}")
        return []


# --- 2. API Key 확인 ---
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    st.error("🔑 API Key를 찾을 수 없습니다. Streamlit Cloud의 Settings -> Secrets 설정을 확인해 주세요.")
    st.stop()


# --- 3. 헤더 UI (한국환경공단 맞춤) ---
st.markdown("""
    <div class="keco-header">
        <h2>🌱 한국환경공단 KECO</h2>
        <p>AI 기반 현장 안전 & 환경 위험요소 스마트 점검 시스템</p>
    </div>
""", unsafe_allow_html=True)

# 마스코트 환영 메시지
st.markdown("""
    <div class="mascot-banner">
        <div class="mascot-icon">💧🌱</div>
        <div class="mascot-text">
            안녕하세요! <strong>푸루 & 그루</strong>입니다.<br>
            현장 사진을 올리시면 AI가 안전 및 환경 위험요소를 정밀 분석해 드립니다!
        </div>
    </div>
""", unsafe_allow_html=True)


# --- 4. 메인 탭 구성 ---
tab1, tab2 = st.tabs(["🔍 현장 위험 분석 (푸루 AI)", "📋 전체 점검 이력 (그루 DB)"])

# ---------------- Tab 1: AI 신규 점검 ----------------
with tab1:
    st.subheader("📸 현장 점검 사진 업로드")
    
    uploaded_file = st.file_uploader("분석할 현장 사진을 선택하거나 촬영해 주세요 (JPG, PNG)", type=["jpg", "jpeg", "png"])

    if uploaded_file is not None:
        image = Image.open(uploaded_file).convert("RGB")
        st.image(image, caption=f"📷 선택된 현장 사진: {uploaded_file.name}", use_container_width=True)
        
        if st.button("🚀 AI 현장 위험요소 정밀 분석 시작", use_container_width=True):
            status_box = st.empty()
            status_box.info("⏳ **푸루가 정밀 분석 중입니다...** 현장의 안전 및 환경 위험요소를 진단하고 있습니다.")
            
            try:
                client = genai.Client(api_key=api_key)
                
                prompt = (
                    "당신은 한국환경공단(KECO)의 현장 안전 및 환경 점검 전문 AI입니다. "
                    "이 사진은 작업 현장 사진입니다. "
                    "사진 속에서 발생할 수 있는 산업안전 및 환경 관련 위험요소를 정밀하게 분석하고, "
                    "각 위험요소별 '예방대책 및 개선 권고사항'을 항목별로 보기 쉽게 작성해 주세요."
                )

                all_models = list(client.models.list())
                valid_model_names = [m.name.replace("models/", "") for m in all_models]

                response = None
                used_model = ""

                for m_name in valid_model_names:
                    if any(skip in m_name for skip in ["embed", "text-", "bison", "imagen", "audio", "realtime"]):
                        continue
                    
                    try:
                        response = client.models.generate_content(
                            model=m_name,
                            contents=[image, prompt]
                        )
                        used_model = m_name
                        break
                    except Exception:
                        continue

                if response:
                    status_box.empty()
                    
                    result_text = response.text
                    
                    # 💾 Google Sheets에 자동 저장
                    if save_to_google_sheet(uploaded_file.name, result_text):
                        st.toast("✅ 구글 시트에 분석 기록이 영구 저장되었습니다!", icon="🌱")

                    # 결과 카드 스타일 출력
                    st.markdown("### 📋 푸루의 위험요소 분석 리포트")
                    st.markdown(f"""
                        <div class="result-card">
                            {result_text.replace('\n', '<br>')}
                        </div>
                    """, unsafe_allow_html=True)
                    
                    st.download_button(
                        label="📥 점검 리포트 텍스트(.txt) 다운로드",
                        data=result_text,
                        file_name=f"KECO_안전점검_{uploaded_file.name}.txt",
                        mime="text/plain",
                        use_container_width=True
                    )
                else:
                    status_box.empty()
                    st.error("❌ 연결 가능한 AI 모델을 찾지 못했습니다. API 키 권한을 확인해 주세요.")

            except Exception as e:
                status_box.empty()
                st.error(f"오류가 발생했습니다: {e}")

# ---------------- Tab 2: 저장된 이력 조회 ----------------
with tab2:
    st.subheader("📂 지난 위험요소 점검 이력")
    rows = get_google_sheet_records()
    
    if len(rows) <= 1:
        st.info("아직 저장된 점검 이력이 없습니다. 첫 번째 현장 사진을 올려 진단해 보세요!")
    else:
        data_rows = rows[1:]
        data_rows.reverse()  # 최신순 정렬
        
        st.write(f"📊 그루의 DB에 총 **{len(data_rows)}건**의 한국환경공단 현장 점검 기록이 보관되어 있습니다.")
        st.markdown("---")
        
        for row in data_rows:
            timestamp = row[0] if len(row) > 0 else "-"
            filename = row[1] if len(row) > 1 else "-"
            result_text = row[2] if len(row) > 2 else "-"
            
            with st.expander(f"🗓️ [{timestamp}] - {filename}"):
                st.markdown("**📋 당시 점검 리포트:**")
                st.write(result_text)
