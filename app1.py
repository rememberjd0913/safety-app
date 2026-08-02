import streamlit as st
from PIL import Image
from google import genai
import gspread
from google.oauth2.service_account import Credentials
import datetime

# --- 페이지 기본 설정 (한국환경공단 메인 테마) ---
st.set_page_config(
    page_title="한국환경공단 | AI 안전 조치 전·후 점검 시스템",
    page_icon="🌱",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- 커스텀 CSS ---
st.markdown("""
    <style>
    .stApp {
        background-color: #F8FBF9;
    }
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
    }
    .keco-header p {
        color: #E6F4EA !important;
        font-size: 0.9rem !important;
        margin-top: 6px !important;
        margin-bottom: 0 !important;
    }
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
    .select-card {
        background-color: #E6F4EA;
        border: 1.5px solid #10B981;
        border-radius: 12px;
        padding: 12px 16px;
        margin-bottom: 18px;
        color: #005F27;
        font-weight: 600;
    }
    .set-box {
        background-color: #FFFFFF;
        border: 1px solid #CBD5E1;
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 20px;
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.03);
    }
    .result-card {
        background-color: #FFFFFF;
        border-radius: 12px;
        padding: 18px;
        border-left: 5px solid #007A33;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
        margin-top: 15px;
        margin-bottom: 15px;
    }
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

def save_to_google_sheet(dept_name, site_name, set_count, result_text, summary_detail):
    try:
        client = get_gspread_client()
        sheet_id = st.secrets["SPREADSHEET_ID"]
        sheet = client.open_by_key(sheet_id).sheet1
        
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sheet.append_row([now_str, dept_name, site_name, f"{set_count}개 세트", result_text, summary_detail])
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


# --- 3. 헤더 UI ---
st.markdown("""
    <div class="keco-header">
        <h2>🌱 한국환경공단 KECO</h2>
        <p>시설사업부 현장 안전 조치 전·후 스마트 점검 시스템</p>
    </div>
""", unsafe_allow_html=True)

st.markdown("""
    <div class="mascot-banner">
        <div class="mascot-icon">💧🌱</div>
        <div class="mascot-text">
            안녕하세요! <strong>푸루 & 그루</strong>입니다.<br>
            부서와 현장을 선택하고 <strong>안전 조치 전/후 사진과 설명(총 4세트)</strong>을 입력해 주세요!
        </div>
    </div>
""", unsafe_allow_html=True)


# --- 4. 메인 탭 구성 ---
tab1, tab2 = st.tabs(["📸 전·후 사진 등록 및 AI 진단", "📋 부서별 점검 이력"])

# ---------------- Tab 1: AI 전후 사진 점검 ----------------
with tab1:
    st.subheader("🏢 점검 부서 및 현장 선택")
    
    departments = ["시설사업1부", "시설사업2부", "시설사업3부"]
    sites = ["1현장", "2현장", "3현장", "4현장"]

    col_dept, col_site = st.columns(2)
    with col_dept:
        selected_dept = st.selectbox("📌 담당 부서 선택", departments)
    with col_site:
        selected_site = st.selectbox("🏗️ 점검 현장 선택", sites)

    st.markdown(f"""
        <div class="select-card">
            📍 선택된 점검 대상: <strong>[{selected_dept}] - {selected_site}</strong>
        </div>
    """, unsafe_allow_html=True)

    st.subheader("📋 안전 조치 전·후 현장 사진 등록 (총 4개 세트)")
    
    set_data = [] # 4개 세트 입력 정보 저장용
    prompt_contents = [] # AI 전달용 이미지 및 텍스트 리스트
    
    # 4개 세트 UI 생성
    for i in range(1, 5):
        st.markdown(f"### 🔹 [세트 {i}] 안전 조치 전/후 현장 점검")
        
        with st.container():
            col_before, col_after = st.columns(2)
            
            with col_before:
                st.caption("🔴 **안전 조치 전 (Before)**")
                img_before = st.file_uploader(f"세트 {i} - 조치 전 사진", type=["jpg", "png", "jpeg"], key=f"before_{i}")
                if img_before:
                    st.image(img_before, use_container_width=True)
                    
            with col_after:
                st.caption("🟢 **안전 조치 후 (After)**")
                img_after = st.file_uploader(f"세트 {i} - 조치 후 사진", type=["jpg", "png", "jpeg"], key=f"after_{i}")
                if img_after:
                    st.image(img_after, use_container_width=True)
            
            desc = st.text_area(f"✍️ 세트 {i} - 작업 위치 및 조치 내용 설명", placeholder=f"예: 세트{i} - 2층 작업대 개구부 추락방지망 및 안전난간 설치 완료", key=f"desc_{i}")
            st.markdown("---")
            
            # 입력 데이터 정리
            if img_before or img_after or desc.strip():
                set_data.append({
                    "set_num": i,
                    "img_before": img_before,
                    "img_after": img_after,
                    "desc": desc
                })

    # AI 분석 버튼
    if st.button(f"🚀 [{selected_dept} {selected_site}] 전·후 대조 AI 정밀 분석", use_container_width=True):
        if not set_data:
            st.warning("⚠️ 최소 1개 세트 이상의 사진이나 설명글을 입력해 주세요.")
        else:
            status_box = st.empty()
            status_box.info(f"⏳ **푸루가 [{selected_dept} {selected_site}] 총 {len(set_data)}개 세트의 조치 전·후 상태를 비교 분석 중입니다...**")
            
            try:
                client = genai.Client(api_key=api_key)
                
                # AI 프롬프트 구성
                prompt_text = (
                    f"당신은 한국환경공단(KECO) {selected_dept} {selected_site}의 현장 안전 전문 AI 검수원입니다.\n"
                    "제공된 각 세트별 '안전 조치 전(Before)' 사진과 '안전 조치 후(After)' 사진, 그리고 담당자의 조치 설명을 비교 검토하세요.\n"
                    "각 세트별로 다음 사항을 분석해 주세요:\n"
                    "1. 조치 전 위험 요소 판단\n"
                    "2. 조치 후 적정성 평가 (안전 기준 준수 여부)\n"
                    "3. 추가 개선 필요 사항 및 종합 의견\n\n"
                )
                
                ai_input = [prompt_text]
                summary_detail_list = []

                for s in set_data:
                    num = s["set_num"]
                    desc_txt = s["desc"]
                    ai_input.append(f"\n--- [세트 {num} 설명]: {desc_txt} ---\n")
                    summary_detail_list.append(f"[세트{num}] {desc_txt}")
                    
                    if s["img_before"]:
                        ai_input.append(f"세트 {num} - 조치 전 사진:")
                        ai_input.append(Image.open(s["img_before"]).convert("RGB"))
                    if s["img_after"]:
                        ai_input.append(f"세트 {num} - 조치 후 사진:")
                        ai_input.append(Image.open(s["img_after"]).convert("RGB"))

                # 모델 호출
                all_models = list(client.models.list())
                valid_model_names = [m.name.replace("models/", "") for m in all_models]

                response = None
                for m_name in valid_model_names:
                    if any(skip in m_name for skip in ["embed", "text-", "bison", "imagen", "audio", "realtime"]):
                        continue
                    try:
                        response = client.models.generate_content(
                            model=m_name,
                            contents=ai_input
                        )
                        break
                    except Exception:
                        continue

                if response:
                    status_box.empty()
                    result_text = response.text
                    summary_detail = " | ".join(summary_detail_list)
                    
                    # Google Sheets 영구 저장
                    if save_to_google_sheet(selected_dept, selected_site, len(set_data), result_text, summary_detail):
                        st.toast(f"✅ [{selected_dept} {selected_site}] 전·후 점검 기록이 구글 시트에 저장되었습니다!", icon="🌱")

                    # 결과 리포트 출력
                    st.markdown(f"### 📋 푸루의 전·후 비교 분석 리포트 ({selected_dept} {selected_site})")
                    st.markdown(f"""
                        <div class="result-card">
                            {result_text.replace('\n', '<br>')}
                        </div>
                    """, unsafe_allow_html=True)
                    
                    st.download_button(
                        label="📥 전·후 점검 리포트 (.txt) 다운로드",
                        data=result_text,
                        file_name=f"KECO_전후점검_{selected_dept}_{selected_site}.txt",
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
    st.subheader("📂 지난 전·후 점검 이력 (부서/현장별 필터링)")
    rows = get_google_sheet_records()
    
    if len(rows) <= 1:
        st.info("아직 저장된 점검 이력이 없습니다. 첫 번째 전·후 사진을 등록해 보세요!")
    else:
        filter_col1, filter_col2 = st.columns(2)
        with filter_col1:
            filter_dept = st.selectbox("🔍 조회할 부서 선택", ["전체 부서"] + departments)
        with filter_col2:
            filter_site = st.selectbox("🔍 조회할 현장 선택", ["전체 현장"] + sites)

        data_rows = rows[1:]
        filtered_rows = []
        
        for r in data_rows:
            row_dept = r[1] if len(r) > 1 else ""
            row_site = r[2] if len(r) > 2 else ""
            
            dept_match = (filter_dept == "전체 부서") or (filter_dept == row_dept)
            site_match = (filter_site == "전체 현장") or (filter_site == row_site)
            
            if dept_match and site_match:
                filtered_rows.append(r)
                
        filtered_rows.reverse()
        
        st.write(f"📊 저장된 점검 기록: 총 **{len(filtered_rows)}건**")
        st.markdown("---")
        
        for row in filtered_rows:
            timestamp = row[0] if len(row) > 0 else "-"
            dept = row[1] if len(row) > 1 else "-"
            site = row[2] if len(row) > 2 else "-"
            set_cnt = row[3] if len(row) > 3 else "-"
            result_text = row[4] if len(row) > 4 else "-"
            detail = row[5] if len(row) > 5 else "-"
            
            with st.expander(f"🗓️ [{timestamp}] {dept} | {site} ({set_cnt})"):
                st.markdown(f"**🏢 부서/현장:** {dept} - {site} ({set_cnt})")
                st.markdown(f"**✍️ 현장 설명 요약:** {detail}")
                st.markdown("**📋 AI 전·후 진단 리포트:**")
                st.write(result_text)
