import streamlit as st
from PIL import Image
from google import genai

st.set_page_config(page_title="AI 위험요소 분석기", page_icon="📸")

# 🔑 GitHub 보안 경고를 피하기 위해 secrets에서 키를 가져옵니다.
# (로컬 및 Streamlit Cloud 모두에서 안전하게 작동)
try:
    api_key = st.secrets["GEMINI_API_KEY"]
except Exception:
    # 로컬 테스트용 (키가 없을 경우 직접 입력)
api_key = "AQ.Ab8RN6K3oecvPuW8G706YYoNf2J0rM8qVWVG9vzxRQVADw61pw"

st.title("📸 AI 건설/현장 위험요소 분석")
st.write("현장 사진을 업로드하면 Gemini AI가 위험 요소를 분석해 드립니다.")

uploaded_file = st.file_uploader("분석할 사진을 선택하세요 (JPG, PNG)", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="업로드된 사진", Width="stretch")
    
    if st.button("🔍 AI 위험요소 분석 시작", type="primary"):
        status_box = st.empty()
        
        try:
            client = genai.Client(api_key=api_key)
            
            # 1. 내 API 키로 구글에서 가져올 수 있는 모든 모델 조회
            status_box.info("🔍 사용 가능한 Gemini 모델 목록을 불러오는 중입니다...")
            all_models = list(client.models.list())
            model_names = [m.name.replace("models/", "") for m in all_models]
            
            # 화면에 현재 계정에서 조회되는 모델 목록 표시 (확인용)
            st.write("📌 **현재 계정에서 조회된 모델 목록:**", model_names)

            prompt = (
                "이 사진은 작업 현장 사진입니다. "
                "사진 속에서 발생할 수 있는 안전 위험요소를 정밀하게 분석해 주고, "
                "각 위험요소에 대한 예방대책을 항목별로 깔끔하게 작성해 주세요."
            )

            response = None
            used_model = ""

            # 2. 조회된 모델 목록 중 하나씩 순서대로 실행 시도
            for m_name in model_names:
                # generateContent 기능을 지원하는 모델 위주로 시도
                try:
                    status_box.info(f"⏳ 분석 시도 중... (연결 모델: {m_name})")
                    response = client.models.generate_content(
                        model=m_name,
                        contents=[image, prompt]
                    )
                    used_model = m_name
                    break  # 성공 시 탈출
                except Exception as inner_e:
                    # 실패 시 다음 모델로 이동
                    continue

            if response:
                status_box.empty()
                st.success(f"분석이 완료되었습니다! (성공 모델: {used_model})")
                st.markdown("---")
                st.subheader("📋 분석 결과")
                st.write(response.text)
            else:
                status_box.empty()
                st.error("❌ 모든 모델 호출에 실패했습니다. 화면 상단에 출력된 모델 목록을 확인해 주세요.")

        except Exception as e:
            status_box.empty()
            err_msg = str(e)
            if "API_KEY_INVALID" in err_msg or "API key not valid" in err_msg:
                st.error("❌ 입력하신 API Key가 올바르지 않습니다. Google AI Studio에서 키를 다시 확인해 주세요.")
            else:
                st.error(f"오류가 발생했습니다: {e}")