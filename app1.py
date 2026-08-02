import streamlit as st
import google.generativeai as genai  # 라이브러리 변경
import gspread
from google.oauth2.service_account import Credentials
import datetime
import base64
from PIL import Image

# ... (기타 UI/CSS 설정 동일) ...

# --- 2. 안정적인 AI 분석 함수 (google-generativeai 교체 버전) ---
def analyze_hazard_auto(api_key, img_file):
    """google-generativeai SDK를 사용하여 gemini-1.5-flash 모델로 분석합니다."""
    genai.configure(api_key=api_key)
    img = Image.open(img_file)
    
    prompt = (
        "당신은 한국환경공단(KECO) 현장 안전 전문 AI 검수원입니다.\n"
        "제공된 조치 전 사진을 분석하여 다음 3가지 항목만 핵심 요약해서 짧게 답변하세요.\n\n"
        "1. **주요 위험 요소:** (1문장)\n"
        "2. **위험 등급:** [상/중/하 중 선택]\n"
        "3. **권장 조치 사항:** (1문장)"
    )

    # 가장 광범위하게 지원되는 멀티모달 기본 모델 사용
    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content([prompt, img])
    
    if response and response.text:
        return response.text
    else:
        raise Exception("AI 응답이 비어 있습니다.")
