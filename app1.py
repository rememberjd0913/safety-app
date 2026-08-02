import streamlit as st
from google import genai
from google.genai import types
import gspread
from google.oauth2.service_account import Credentials
import datetime
import base64
from PIL import Image

# --- 페이지 기본 설정 (한국환경공단 맞춤) ---
st.set_page_config(
    page_title="한국환경공단 수도권서부환경본부 환경시설관리처 | AI 안전 조치 전·후 스마트 점검",
    page_icon="puru_guru.png",  # 브라우저 탭 파비콘 이미지 설정
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- Base64 이미지 변환 함수 (st.markdown 내 이미지 로드용) ---
def get_base64_image(image_path):
    try:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except FileNotFoundError:
        return ""

# 푸루&그루 이미지 Base64 인코딩
img_base64 = get_base64_image("puru_guru.png")

# --- 커스텀 CSS (한국환경공단 K-ECO 브랜드 및 건설 UI 적용) ---
st.markdown("""
    <style>
    /* 메인 배경 및 기본 폰트 설정 */
    .stApp {
        background-color: #F8FBF9;
    }
    
    /* 상단 K-ECO 브랜드 헤더 */
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

    /* 캐릭터 배너 / 카드 스타일 */
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

    /* 선택 부서 및 현장 카드 */
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

    /* 결과 카드 스타일 */
    .result-card {
        background-color: #FFFFFF;
        border-radius: 12px;
        padding: 20px;
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
        height: 52px !important;
        font-size: 1.05rem !important;
        box-shadow: 0 3px 8px rgba(0, 122, 51, 0.2) !important;
        transition: background 0.3s, transform 0.2s;
    }
    div.stButton > button:hover {
        background: linear-gradient(135deg, #005F27 0%, #047857 100%) !important;
        transform: translateY(-2px);
    }
    
    /* 탭 스타일 조정 (초록색 음영 제거 -> 세련된 모노톤 적용) */
    div.stTabs [data-baseweb="tab-list"] {
        background-color: #F1F5F9;
        padding: 6px;
        border-radius: 12px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.03);
    }
    div.stTabs [data-baseweb="tab"] {
        background-color: transparent;
        border-radius: 8px;
        padding: 8px 16px;
        font-weight: bold;
        color: #475569;
        border: none;
    }
    div.stTabs [aria-selected="true"] {
        background-color: #1E293B !important;
        color: #FFFFFF !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
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


# --- 3. KECO 헤더 및 마스코트 UI ---
st.markdown("""
    <div class="keco-header">
        <h2>🌱 한국환경공단 수도권서부환경본부</h2>
        <p>환경시설관리처 현장 안전 조치 전·후 스마트 점검 시스템</p>
    </div>
""", unsafe_allow_html=True)

# 메인 푸루 & 그루 환영 배너 (Base64 이미지 적용)
image_html = f'<img src="data:image/png;base64,{img_base64}" style="max-height: 110px; object-fit: contain;">' if img_base64 else '🌱'

st.markdown(f"""
    <div class="mascot-banner">
        <div style="margin-bottom: 8px;">
            {image_html}
        </div>
        <h4 style="margin:0; color:#007A33;">"안전점검 시작! 푸루와 그루가 안내해 드릴게요."</h4>
        <p style="margin-top:6px; font-size:0.88rem; color:#64748B;">각 번호별 조치 전·후 사진 첨부 및 현장 설명을 입력해 주세요.</p>
    </div>
""", unsafe_allow_html=True)


# --- 4. 메인 탭 구성 ---
main_tab1, main_tab2 = st.tabs(["전·후 점검 등록 및 AI 진단", "부서별 점검 이력"])

# ---------------- Tab 1: AI 전후 점검 ----------------
with main_tab1:
    # 그루 가이드 카드 (아이콘 제거 완료)
    st.markdown("""
        <div class="mascot-card">
            <div>
                <strong style="color:#EC4899;">[그루의 현장 안내]</strong><br>
                <span style="font-size:0.92rem; color:#334155;">점검을 진행할 <strong>담당 부서</strong>와 <strong>현장 번호</strong>를 선택해 주세요.</span>
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

    # 푸루 가이드 카드 (아이콘 제거 완료)
    st.markdown("""
        <div class="mascot-card">
            <div>
                <strong style="color:#007A33;">[푸루의 입력 가이드]</strong><br>
                <span style="font-size:0.92rem; color:#334155;">하단 탭에서 <strong>🔴 조치 전 사진</strong> 및 <strong>🟢 조치 후 사진</strong>을 업로드해 주세요!</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

    st.subheader("📸 안전 조치 전·후 사진 등록 (최대 4개)")
    
    # 탭 명칭 변경: 1번사진, 2번사진, 3번사진, 4번사진
    set_tabs = st.tabs(["1번 사진", "2번 사진", "3번 사진", "4번 사진"])
    
    set_inputs = {} # 각 번호별 데이터 저장 사전

    # 1번사진 ~ 4번사진 입력 화면 구성
    for idx, set_tab in enumerate(set_tabs, start=1):
        with set_tab:
            st.markdown(f"#### 🔹 [{idx}번 사진] 현장 조치 전·후 첨부")
            
            col_b, col_a = st.columns(2)
            
            with col_b:
                before_img_file = st.file_uploader(
                    f"🔴 [{idx}번] 조치 전(Before) 사진",
                    type=["jpg", "jpeg", "png"],
                    key=f"before_img_{idx}"
                )
                if before_img_file:
                    st.image(before_img_file, caption=f"{idx}번 조치 전 사진 미리보기", use_container_width=True)

            with col_a:
                after_img_file = st.file_uploader(
                    f"🟢 [{idx}번] 조치 후(After) 사진",
                    type=["jpg", "jpeg", "png"],
                    key=f"after_img_{idx}"
                )
                if after_img_file:
                    st.image(after_img_file, caption=f"{idx}번 조치 후 사진 미리보기", use_container_width=True)

            desc = st.text_area(
                f"✍️ [{idx}번] 현장 위치 및 작업 설명", 
                placeholder=f"예: {idx}번 - A동 2층 남측 개구부 안전난간 설치 현장", 
                key=f"desc_{idx}"
            )
            
            # 사진이나 설명 중 하나라도 등록된 경우 유효 항목으로 등록
            if before_img_file or after_img_file or desc.strip():
                set_inputs[idx] = {
                    "set_num": idx,
                    "before_img": before_img_file,
                    "after_img": after_img_file,
                    "desc": desc.strip()
                }

    st.markdown("---")

    # AI 분석 버튼
    if st.button(f"🚀 [{selected_dept} {selected_site}] 전·후 대조 AI 정밀 분석", use_container_width=True):
        if not set_inputs:
            st.warning("⚠️ 최소 1개 이상의 사진 탭에서 조치 전/후 사진이나 설명글을 첨부해 주세요.")
        else:
            active_sets = list(set_inputs.values())
            
            # AI 분석 로딩 안내
            loading_container = st.container()
            with loading_container:
                st.markdown(f"""
                    <div style="text-align:center; padding:15px; background:#E6F4EA; border-radius:12px; margin-bottom:15px; border: 1.5px solid #10B981;">
                        <p style="margin-top:10px; color:#007A33; font-weight:bold;">푸루 & 그루 AI가 [{selected_dept} {selected_site}] 총 {len(active_sets)}개 현장의 전·후 이미지 데이터를 분석하고 있습니다...</p>
                    </div>
                """, unsafe_allow_html=True)
            
            try:
                client = genai.Client(api_key=api_key)
                
                # 프롬프트 및 멀티모달 콘텐트 구성
                contents_payload = []
                
                system_prompt = (
                    f"당신은 한국환경공단(KECO) {selected_dept} {selected_site}의 현장 안전 전문 AI 검수원입니다.\n"
                    "제공된 각 번호별 '안전 조치 전(Before) 사진'과 '안전 조치 후(After) 사진', 그리고 설명을 종합적으로 비교 및 정밀 분석하세요.\n\n"
                    "각 번호별 분석 가이드라인:\n"
                    "1. 조치 전 사진 분석: 시각적 위험 요소 및 산업안전 위험도 평가\n"
                    "2. 조치 후 사진 분석: 안전 조치의 시각적 완성도 및 관련 법규 준수 여부\n"
                    "3. 총평 및 추가 개선 조치 제안\n\n"
                )
                contents_payload.append(system_prompt)

                summary_detail_list = []

                for s in active_sets:
                    num = s["set_num"]
                    d_txt = s["desc"] if s["desc"] else "설명 없음"
                    
                    contents_payload.append(f"\n--- [{num}번 사진 세트] ---")
                    contents_payload.append(f"위치/설명: {d_txt}")

                    b_status = "첨부됨" if s["before_img"] else "미첨부"
                    a_status = "첨부됨" if s["after_img"] else "미첨부"

                    if s["before_img"]:
                        contents_payload.append(f"[{num}번 조치 전(Before) 이미지]:")
                        contents_payload.append(Image.open(s["before_img"]))
                    
                    if s["after_img"]:
                        contents_payload.append(f"[{num}번 조치 후(After) 이미지]:")
                        contents_payload.append(Image.open(s["after_img"]))

                    summary_detail_list.append(f"[{num}번] 전:{b_status},후:{a_status}({d_txt[:15]})")

                # 최신 AI 모델 호출 (gemini-2.5-flash 우선)
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=contents_payload
                )

                if response:
                    loading_container.empty()
                    result_text = response.text
                    summary_detail = " | ".join(summary_detail_list)
                    
                    # Google Sheets 저장
                    if save_to_google_sheet(selected_dept, selected_site, len(active_sets), result_text, summary_detail):
                        st.toast(f"✅ [{selected_dept} {selected_site}] 전·후 점검 기록이 구글 시트에 저장되었습니다!", icon="🌱")

                    # 결과 리포트 출력 카드
                    st.markdown(f"""
                        <div class="result-card">
                            <div style="display:flex; align-items:center; gap:12px; border-bottom:2px solid #E2E8F0; padding-bottom:10px; margin-bottom:12px;">
                                <div>
                                    <h4 style="margin:0; color:#007A33;">푸루 AI의 전·후 사진 비교 분석 리포트</h4>
                                    <span style="font-size:0.85rem; color:#64748B;">[{selected_dept}] - {selected_site}</span>
                                </div>
                            </div>
                            {result_text.replace('\n', '<br>')}
                        </div>
                    """, unsafe_allow_html=True)
                    
                    st.download_button(
                        label="📥 전·후 점검 리포트 (.txt) 다운로드",
                        data=result_text,
                        file_name=f"KECO_전후점검_{selected_dept}_{selected_site}_{datetime.datetime.now().strftime('%Y%m%d')}.txt",
                        mime="text/plain",
                        use_container_width=True
                    )

            except Exception as e:
                loading_container.empty()
                st.error(f"AI 분석 처리 중 오류가 발생했습니다: {e}")

# ---------------- Tab 2: 저장된 이력 조회 ----------------
with main_tab2:
    st.subheader("📂 지난 전·후 점검 이력 (부서/현장별 필터링)")
    rows = get_google_sheet_records()
    
    if len(rows) <= 1:
        st.info("아직 저장된 점검 이력이 없습니다. 첫 번째 전·후 점검을 작성해 보세요!")
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
        
        st.write(f"📊 조건에 해당하는 점검 기록: 총 **{len(filtered_rows)}건**")
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
                st.markdown(f"**✍️ 현장 작성 요약:** {detail}")
                st.markdown("**📋 AI 전·후 진단 리포트:**")
                st.write(result_text)
