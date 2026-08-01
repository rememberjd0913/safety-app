import streamlit as st
from PIL import Image
from google import genai

st.set_page_config(page_title="AI 위험요소 분석기", page_icon="📸")

# 🔑 Streamlit Secrets에서 API 키를 불러옵니다.
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    st.error("🔑 API Key를 찾을 수 없습니다. Streamlit Cloud의 Settings -> Secrets 설정을 확인해 주세요.")
    st.stop()

st.title("📸 AI 건설/현장 위험요소 분석")
st.write("현장 사진을 업로드하면 Gemini AI가 위험 요소를 분석해 드립니다.")

uploaded_file = st.file_uploader("분석할 사진을 선택하세요 (JPG, PNG)", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="업로드된 사진", width="stretch")
    
    if st.button("🔍 AI 위험요소 분석 시작", type="primary"):
        status_box = st.empty()
        status_box.info("⏳ AI가 현장 사진의 위험요소를 정밀 분석 중입니다...")
        
        try:
            client = genai.Client(api_key=api_key)
            
            prompt = (
                "이 사진은 작업 현장 사진입니다. "
                "사진 속에서 발생할 수 있는 안전 위험요소를 정밀하게 분석해 주고, "
                "각 위험요소에 대한 예방대책을 항목별로 깔끔하게 작성해 주세요."
            )

            # 구글 표준 최신 모델
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[image, prompt]
            )

            status_box.empty()
            st.success("분석이 완료되었습니다!")
            st.markdown("---")
            st.subheader("📋 분석 결과")
            st.write(response.text)

        except Exception as e:
            status_box.empty()
            err_msg = str(e)
            if "API_KEY_INVALID" in err_msg or "API key not valid" in err_msg:
                st.error("❌ Secrets에 입력하신 API Key가 올바르지 않습니다. 키를 다시 확인해 주세요.")
            else:
                st.error(f"오류가 발생했습니다: {e}")
