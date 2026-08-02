import streamlit as st
from google import genai  # 최신 공식 SDK
import gspread
from google.oauth2.service_account import Credentials
import datetime
import base64
from PIL import Image

# --- 페이지 기본 설정 (한국환경공단 맞춤) ---
st.set_page_config(
    page_title="한국환경공단 수도권서부환경본부 환경시설관리처 | AI 안전 점검 시스템",
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
    }
    .select-card {
        background-color: #E6F4EA;
        border: 1.5px solid #10B981;
        border-radius: 12px;
        padding: 12px 16px;
        margin-bottom: 18px;
        color: #005F27;
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
    }
    .item-card {
        background-color: #FFFFFF;
        border: 1.5px solid #CBD5E1;
        border-radius: 12px;
        padding: 18px;
        margin-bottom: 20px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.03);
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


# --- 1. Google Sheets 연동 ---
@st.cache_resource
def get_gspread_client():
    credentials = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    )
    return gspread.authorize(credentials)

def save_to_google_sheet(dept_name, site_name, set_count, analysis_summary, summary_detail):
    try:
        client = get_gspread_client()
        sheet_id = st.secrets["SPREADSHEET_ID"]
        sheet = client.open_by_key(sheet_id).sheet1
        
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sheet.append_row([now_str, dept_name, site_name, f"{set_count}개 항목", analysis_summary, summary_detail])
        return True
    except Exception as e:
        st.error(f"구글 시트 저장 중 오류: {e}")
        return False

def get_google_sheet_records():
    try:
        client = get_gspread_client()
        sheet_id = st.secrets["SPREADSHEET_ID"]
        sheet = client.open_by_key(sheet_id).sheet1
        return sheet.get_all_values()
    except Exception as e:
        st.error(f"구글 시트 불러오기 오류: {e}")
        return []


# --- 2. 동적 탐색형 AI 위험 분석 함수 ---
def analyze_hazard_auto(api_key, img_file):
    """현재 API Key 계정에서 사용 가능한 모델을 동적으로 탐색하여 분석합니다."""
    client = genai.Client(api_key=api_key)
    img = Image.open(img_file)
    
    prompt = (
        "당신은 한국환경공단(KECO) 현장 안전 전문 AI 검수원입니다.\n"
        "제공된 조치 전 사진을 분석하여 다음 3가지 항목만 핵심 요약해서 짧게 답변하세요.\n\n"
        "1. **주요 위험 요소:** (1문장)\n"
        "2. **위험 등급:** [상/중/하 중 선택]\n"
        "3. **권장 조치 사항:** (1문장)"
    )

    candidate_models = [
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
        "gemini-2.5-pro"
    ]

    last_error = None

    for model_name in candidate_models:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=[prompt, img]
            )
            if response and response.text:
                return response.text
        except Exception as e:
            last_error = e
            continue

    try:
        available_models = [
            m.name.replace("models/", "") 
            for m in client.models.list() 
        ]
        
        for m_name in available_models:
            if "flash" in m_name or "pro" in m_name:
                try:
                    response = client.models.generate_content(
                        model=m_name,
                        contents=[prompt, img]
                    )
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


# --- 4. 세션 상태 초기화 (동적 추가/삭제용) ---
if "item_count" not in st.session_state:
    st.session_state.item_count = 1  # 기본 1개부터 시작

if "ai_results" not in st.session_state:
    st.session_state.ai_results = {}  # {item_idx: {img_idx: result_text}}


# --- 5. 헤더 UI ---
st.markdown("""
    <div class="keco-header">
        <h2>🌱 한국환경공단 수도권서부환경본부</h2>
        <p>환경시설관리처 현장 안전 조치 전·후 스마트 점검 시스템</p>
    </div>
""", unsafe_allow_html=True)

image_html = f'<img src="data:image/png;base64,{img_base64}" style="max-height: 100px;">' if img_base64 else '🌱'

st.markdown(f"""
    <div class="mascot-banner">
        <div style="margin-bottom: 8px;">{image_html}</div>
        <h4 style="margin:0; color:#007A33;">"안전점검 시작! 푸루와 그루가 안내해 드릴게요."</h4>
        <p style="margin-top:6px; font-size:0.88rem; color:#64748B;">필요한 만큼 점검 항목을 추가하고, 여러 장의 사진을 한 번에 올려보세요.</p>
    </div>
""", unsafe_allow_html=True)


# --- 6. 메인 탭 ---
main_tab1, main_tab2 = st.tabs(["안전 점검 등록", "부서별 점검 이력"])

with main_tab1:
    st.markdown("""
        <div class="mascot-card">
            <div>
                <strong style="color:#EC4899;">[그루의 현장 안내]</strong><br>
                <span style="font-size:0.92rem; color:#334155;">담당 부서와 현장 번호를 선택해 주세요.</span>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
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

    st.subheader("📸 안전 점검 사진 등록 및 AI 위험 분석")
    st.caption("💡 각 항목마다 여러 장의 사진을 다중 선택하여 동시에 첨부할 수 있습니다.")

    form_data = {}

    # 동적으로 생성된 항목 수만큼 반복
    for idx in range(1, st.session_state.item_count + 1):
        st.markdown(f"""
            <div class="item-card">
                <h4 style="margin-top:0; color:#007A33;">🔹 [점검 항목 #{idx}]</h4>
        """, unsafe_allow_html=True)
        
        col_b, col_a = st.columns(2)
        
        # --- [조치 전 섹션 - 다중 파일 업로드] ---
        with col_b:
            st.markdown("##### 🔴 조치 전 (Before) - 다중 선택 가능")
            before_img_files = st.file_uploader(
                f"#{idx} 조치 전 사진 첨부 (여러 장 선택 가능)",
                type=["jpg", "jpeg", "png"],
                accept_multiple_files=True,
                key=f"before_imgs_{idx}"
            )
            
            if before_img_files:
                st.write(f"📷 첨부된 조치 전 사진: **{len(before_img_files)}장**")
                # 이미지 미리보기 (2열 Grid)
                cols = st.columns(min(len(before_img_files), 2))
                for img_i, img_f in enumerate(before_img_files):
                    cols[img_i % 2].image(img_f, caption=f"조치 전 #{img_i+1}", use_container_width=True)
                
                # AI 분석 버튼
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

            # AI 분석 결과 출력
            if idx in st.session_state.ai_results and st.session_state.ai_results[idx]:
                st.markdown("**🤖 AI 위험 분석 결과:**")
                for img_i, res_text in st.session_state.ai_results[idx].items():
                    st.markdown(f"""
                        <div class="analysis-box">
                            <strong>[사진 #{img_i}]</strong><br>
                            {res_text.replace('\n', '<br>')}
                        </div>
                    """, unsafe_allow_html=True)

        # --- [조치 후 섹션 - 다중 파일 업로드] ---
        with col_a:
            st.markdown("##### 🟢 조치 후 (After) - 다중 선택 가능")
            after_img_files = st.file_uploader(
                f"#{idx} 조치 후 사진 첨부 (여러 장 선택 가능)",
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
            # AI 분석 텍스트 취합
            ai_summary_list = []
            if idx in st.session_state.ai_results:
                for img_i, res_text in st.session_state.ai_results[idx].items():
                    ai_summary_list.append(f"(사진#{img_i}) {res_text}")
            
            form_data[idx] = {
                "before_count": len(before_img_files) if before_img_files else 0,
                "after_count": len(after_img_files) if after_img_files else 0,
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
                # 마지막 항목 데이터 정리
                last_idx = st.session_state.item_count
                if last_idx in st.session_state.ai_results:
                    del st.session_state.ai_results[last_idx]
                st.session_state.item_count -= 1
                st.rerun()

    st.markdown("---")

    # 최종 제출 버튼
    if st.button(f"💾 [{selected_dept} {selected_site}] 전체 점검 내역 구글 시트 저장 및 완료", use_container_width=True):
        if not form_data:
            st.warning("⚠️ 최소 1개 이상의 항목에 사진이나 설명글을 작성해 주세요.")
        else:
            all_ai_summaries = []
            details = []
            
            for k, v in form_data.items():
                if v['ai_analysis'] != "분석 미실행":
                    all_ai_summaries.append(f"[항목 #{k}]:\n{v['ai_analysis']}")
                details.append(f"[항목 #{k}] 전:{v['before_count']}장, 후:{v['after_count']}장 ({v['desc'][:15]})")
            
            combined_ai = "\n\n".join(all_ai_summaries) if all_ai_summaries else "조치 전 AI 분석 미실행"
            combined_detail = " | ".join(details)
            
            if save_to_google_sheet(selected_dept, selected_site, len(form_data), combined_ai, combined_detail):
                st.success(f"🎉 [{selected_dept} {selected_site}] 총 {len(form_data)}개 점검 항목이 구글 시트에 성공적으로 저장되었습니다!")

# ---------------- Tab 2: 이력 조회 ----------------
with main_tab2:
    st.subheader("📂 지난 점검 이력 조회")
    rows = get_google_sheet_records()
    
    if len(rows) <= 1:
        st.info("저장된 점검 이력이 없습니다.")
    else:
        filter_col1, filter_col2 = st.columns(2)
        with filter_col1:
            filter_dept = st.selectbox("🔍 부서 선택", ["전체 부서"] + departments)
        with filter_col2:
            filter_site = st.selectbox("🔍 현장 선택", ["전체 현장"] + sites)

        data_rows = rows[1:][::-1]
        
        for r in data_rows:
            timestamp = r[0] if len(r) > 0 else "-"
            dept = r[1] if len(r) > 1 else "-"
            site = r[2] if len(r) > 2 else "-"
            count = r[3] if len(r) > 3 else "-"
            ai_text = r[4] if len(r) > 4 else "-"
            detail = r[5] if len(r) > 5 else "-"
            
            if (filter_dept in ["전체 부서", dept]) and (filter_site in ["전체 현장", site]):
                with st.expander(f"🗓️ [{timestamp}] {dept} | {site} ({count})"):
                    st.write(f"**현장 메모:** {detail}")
                    st.info(ai_text)
