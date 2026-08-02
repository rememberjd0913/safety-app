import streamlit as st
from PIL import Image
from google import genai
import gspread
from google.oauth2.service_account import Credentials
import datetime

st.set_page_config(page_title="AI 위험요소 분석기", page_icon="📸", layout="centered")

# --- 1. Google Sheets 연동 함수 ---
@st.cache_resource
def get_gspread_client():
    # Secrets에서 GCP 인증정보 가져오기
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

# --- 3. 메인 UI (탭 구성) ---
st.title("📸 AI 건설/현장 위험요소 분석")

tab1, tab2 = st.tabs(["🔍 AI 분석 실행", "📋 지난 이력 조회"])

# ---------------- Tab 1: 신규 사진 분석 ----------------
with tab1:
    st.write("현장 사진을 업로드하면 Gemini AI가 위험 요소를 분석하고 결과를 Google Sheets에 영구 저장합니다.")
    
    uploaded_file = st.file_uploader("분석할 사진을 선택하세요 (JPG, PNG)", type=["jpg", "jpeg", "png"])

    if uploaded_file is not None:
        image = Image.open(uploaded_file).convert("RGB")
        st.image(image, caption="업로드된 사진", width="stretch")
        
        if st.button("🔍 AI 위험요소 분석 시작", type="primary", use_container_width=True):
            status_box = st.empty()
            status_box.info("⏳ AI가 현장 사진의 위험요소를 정밀 분석 중입니다...")
            
            try:
                client = genai.Client(api_key=api_key)
                
                prompt = (
                    "이 사진은 작업 현장 사진입니다. "
                    "사진 속에서 발생할 수 있는 안전 위험요소를 정밀하게 분석해 주고, "
                    "각 위험요소에 대한 예방대책을 항목별로 깔끔하게 작성해 주세요."
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
                    st.success("분석이 완료되었습니다!")
                    
                    result_text = response.text
                    
                    # 💾 Google Sheets에 데이터 영구 저장
                    if save_to_google_sheet(uploaded_file.name, result_text):
                        st.toast("📊 구글 스프레드시트에 결과가 영구 저장되었습니다!", icon="✅")

                    st.markdown("---")
                    st.subheader("📋 분석 결과")
                    st.write(result_text)
                    
                    st.download_button(
                        label="📥 분석 결과 텍스트 파일(.txt)로 저장하기",
                        data=result_text,
                        file_name=f"현장위험분석_{uploaded_file.name}.txt",
                        mime="text/plain"
                    )
                else:
                    status_box.empty()
                    st.error("❌ 연결 가능한 AI 모델을 찾지 못했습니다. API 키 권한을 확인해 주세요.")

            except Exception as e:
                status_box.empty()
                st.error(f"오류가 발생했습니다: {e}")

# ---------------- Tab 2: 저장된 지난 이력 조회 ----------------
with tab2:
    st.subheader("📂 지난 위험요소 분석 이력 (Google Sheets 연동)")
    rows = get_google_sheet_records()
    
    # 1행(헤더: 일시, 파일명, 분석결과) 제외
    if len(rows) <= 1:
        st.info("아직 저장된 분석 이력이 없습니다. 첫 번째 사진을 올려 분석해 보세요!")
    else:
        header = rows[0]
        data_rows = rows[1:]
        # 최신순 정렬
        data_rows.reverse()
        
        st.write(f"총 **{len(data_rows)}건**의 점검 기록이 구글 시트에 안전하게 보관되어 있습니다.")
        st.markdown("---")
        
        for row in data_rows:
            timestamp = row[0] if len(row) > 0 else "-"
            filename = row[1] if len(row) > 1 else "-"
            result_text = row[2] if len(row) > 2 else "-"
            
            with st.expander(f"🗓️ [{timestamp}] - {filename}"):
                st.markdown("**📋 분석 결과:**")
                st.write(result_text)
