import streamlit as st
from PIL import Image
from google import genai
import sqlite3
import io
import datetime

st.set_page_config(page_title="AI 위험요소 분석기", page_icon="📸", layout="centered")

# --- 1. SQLite 데이터베이스 초기화 함수 ---
def init_db():
    conn = sqlite3.connect("safety_logs.db")
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            filename TEXT,
            image_bytes BLOB,
            result_text TEXT
        )
    ''')
    conn.commit()
    conn.close()

# DB 테이블 생성 실행
init_db()

# DB에 데이터 저장 함수
def save_to_db(filename, image, result_text):
    # 이미지 PIL 객체를 바이너리(Bytes)로 변환
    img_byte_arr = io.BytesIO()
    image.save(img_byte_arr, format='JPEG')
    img_bytes = img_byte_arr.getvalue()
    
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    conn = sqlite3.connect("safety_logs.db")
    c = conn.cursor()
    c.execute(
        "INSERT INTO logs (timestamp, filename, image_bytes, result_text) VALUES (?, ?, ?, ?)",
        (now_str, filename, img_bytes, result_text)
    )
    conn.commit()
    conn.close()

# DB에서 전체 이력 가져오기 함수
def get_all_logs():
    conn = sqlite3.connect("safety_logs.db")
    c = conn.cursor()
    c.execute("SELECT id, timestamp, filename, image_bytes, result_text FROM logs ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()
    return rows


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
    st.write("현장 사진을 업로드하면 Gemini AI가 위험 요소를 분석하고 결과를 DB에 자동 저장합니다.")
    
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
                    
                    # 💾 DB에 데이터 자동 저장
                    save_to_db(uploaded_file.name, image, result_text)
                    st.toast("💾 분석 결과가 DB에 저장되었습니다!", icon="✅")

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
    st.subheader("📂 지난 위험요소 분석 이력")
    logs = get_all_logs()
    
    if not logs:
        st.info("아직 저장된 분석 이력이 없습니다. 첫 번째 사진을 올려 분석해 보세요!")
    else:
        st.write(f"총 **{len(logs)}건**의 점검 기록이 저장되어 있습니다.")
        st.markdown("---")
        
        for log in logs:
            log_id, timestamp, filename, img_bytes, result_text = log
            
            # 드롭다운(Expander) 형태로 과거 기록을 깔끔하게 보여줍니다.
            with st.expander(f"🗓️ [{timestamp}] - {filename} (ID: {log_id})"):
                col1, col2 = st.columns([1, 1.5])
                
                with col1:
                    # 바이너리에서 PIL 이미지 복원
                    saved_img = Image.open(io.BytesIO(img_bytes))
                    st.image(saved_img, caption=f"업로드 파일: {filename}", width="stretch")
                    
                with col2:
                    st.markdown("**📋 당시 분석 결과:**")
                    st.write(result_text)
