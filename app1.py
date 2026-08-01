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

            # 1. 내 API 키로 호출 가능한 정식 모델 목록 가져오기
            all_models = list(client.models.list())
            valid_model_names = [m.name.replace("models/", "") for m in all_models]

            # 2. 이미지 분석(generateContent)이 가능한 모델 추출
            response = None
            used_model = ""

            for m_name in valid_model_names:
                # 텍스트 전용, 임베딩, 오디오 전용 모델은 제외
                if any(skip in m_name for skip in ["embed", "text-", "bison", "imagen", "audio", "realtime"]):
                    continue
                
                try:
                    status_box.info(f"⏳ 연결 시도 중... ({m_name})")
                    response = client.models.generate_content(
                        model=m_name,
                        contents=[image, prompt]
                    )
                    used_model = m_name
                    break  # 성공하면 즉시 탈출
                except Exception:
                    continue  # 에러 발생 시 다음 모델 시도

            if response:
                status_box.empty()
                st.success(f"분석이 완료되었습니다! (연결 모델: {used_model})")
                st.markdown("---")
                st.subheader("📋 분석 결과")
                st.write(response.text)
            else:
                status_box.empty()
                st.error(
                    "❌ 사용 가능한 모델 연결에 실패했습니다.\n\n"
                    "**[해결 방법]**\n"
                    "1. Google AI Studio(https://aistudio.google.com/)에 접속합니다.\n"
                    "2. `Create API Key` -> **`Create API Key in new project`**로 새 키를 만듭니다.\n"
                    "3. Streamlit Cloud의 `Secrets`에 새 키를 붙여넣고 저장하세요."
                )

        except Exception as e:
            status_box.empty()
            err_msg = str(e)
            if "API_KEY_INVALID" in err_msg or "API key not valid" in err_msg:
                st.error("❌ Secrets에 입력하신 API Key가 올바르지 않습니다. 키를 다시 확인해 주세요.")
            else:
                st.error(f"오류가 발생했습니다: {e}")
