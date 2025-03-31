# api_handler.py
import google.generativeai as genai
import google.api_core.exceptions
try: import anthropic
except ImportError: anthropic = None
try: import openai
except ImportError: openai = None
import os
from dotenv import load_dotenv
import tkinter.messagebox as messagebox # 초기 설정 오류용
import traceback
import time # 타임아웃 값 확인용

import constants

# --- API 설정 ---
def configure_gemini_api():
    """Gemini API 키를 로드하고 클라이언트 설정. 성공 시 True, 실패 시 False."""
    try: load_dotenv(dotenv_path=constants.ENV_FILE, override=True)
    except Exception as e: print(f"WARN: .env 파일 로드 중 오류 (무시): {e}")

    api_key = os.getenv(constants.GOOGLE_API_KEY_ENV)
    if not api_key:
        print(f"ℹ️ Gemini API 키({constants.GOOGLE_API_KEY_ENV}) 없음.")
        return False
    try:
        genai.configure(api_key=api_key)
        print(f"✅ Google Gemini API 설정 완료.")
        return True
    except Exception as e:
        print(f"❌ Gemini API 설정 오류: {e}")
        return False

def configure_claude_api():
    """Claude API 키를 로드하고 클라이언트 설정 준비. 성공 시 True, 실패 시 False."""
    try: load_dotenv(dotenv_path=constants.ENV_FILE, override=True)
    except Exception as e: print(f"WARN: .env 파일 로드 중 오류 (무시): {e}")

    api_key = os.getenv(constants.ANTHROPIC_API_KEY_ENV)
    if not api_key:
        print(f"ℹ️ Claude API 키({constants.ANTHROPIC_API_KEY_ENV}) 없음.")
        return False
    if anthropic is None:
        print("❌ Claude API 사용 불가: 'anthropic' 라이브러리 없음. `pip install anthropic`")
        return False
    try:
        # 실제 클라이언트 생성은 호출 시점에 수행
        print(f"✅ Anthropic Claude API 설정 준비 완료.")
        return True
    except Exception as e:
        print(f"❌ Claude API 설정 오류: {e}")
        return False

def configure_gpt_api():
    """OpenAI API 키를 로드하고 클라이언트 설정 준비. 성공 시 True, 실패 시 False."""
    try: load_dotenv(dotenv_path=constants.ENV_FILE, override=True)
    except Exception as e: print(f"WARN: .env 파일 로드 중 오류 (무시): {e}")

    api_key = os.getenv(constants.OPENAI_API_KEY_ENV)
    if not api_key:
        print(f"ℹ️ OpenAI API 키({constants.OPENAI_API_KEY_ENV}) 없음.")
        return False
    if openai is None:
        print("❌ OpenAI API 사용 불가: 'openai' 라이브러리 없음. `pip install openai`")
        return False
    try:
        # 실제 클라이언트 생성은 호출 시점에 수행
        print(f"✅ OpenAI GPT API 설정 준비 완료.")
        return True
    except Exception as e:
        print(f"❌ OpenAI API 설정 오류: {e}")
        return False

def configure_apis():
    """모든 API 클라이언트 설정. 각 API 설정 성공 여부 튜플 반환."""
    gemini_configured = configure_gemini_api()
    claude_configured = configure_claude_api()
    gpt_configured = configure_gpt_api()
    print(f"API 설정 결과: Gemini={gemini_configured}, Claude={claude_configured}, GPT={gpt_configured}")
    return gemini_configured, claude_configured, gpt_configured

# --- 모델 목록 조회 ---
def get_gemini_models():
    """Gemini API에서 사용 가능한 모델 목록 가져오기"""
    # Gemini API 설정 확인
    if not os.getenv(constants.GOOGLE_API_KEY_ENV): return []
    try:
        configure_gemini_api() # 호출 전에 재설정 시도
        all_models = genai.list_models()
        # generateContent 지원 모델 필터링
        return sorted([m.name for m in all_models if 'generateContent' in m.supported_generation_methods])
    except Exception as e:
        print(f"❌ Gemini 모델 목록 가져오기 실패: {e}")
        return []

def get_claude_models():
    """Anthropic API에서 사용 가능한 Claude 모델 목록 가져오기"""
    api_key = os.getenv(constants.ANTHROPIC_API_KEY_ENV)
    if not api_key or anthropic is None: return []

    try:
        # Anthropic 클라이언트 생성 (여기서 생성)
        client = anthropic.Anthropic(api_key=api_key)
        # Claude는 모델 목록 직접 제공 안 함 - 알려진 모델 목록 반환 (필요시 업데이트)
        # 또는, 특정 엔드포인트가 있다면 호출 (현재 공식 SDK에는 list models 없음)
        # 알려진 최신 모델 위주로 하드코딩 (Claude 3.5 Sonnet, Opus, Haiku 등)
        known_models = [
            "claude-3-5-sonnet-20240620",
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307",
            # "claude-2.1", # 필요시 이전 모델 추가
            # "claude-2.0",
            # "claude-instant-1.2"
        ]
        # TODO: Anthropic에서 모델 목록 API 제공 시 해당 로직으로 변경
        print(f"ℹ️ Claude 모델 목록: 알려진 목록 반환 ({len(known_models)}개)")
        return sorted(known_models)

    except Exception as e:
        print(f"❌ Claude 모델 목록 가져오기 실패 (알려진 목록 반환 중 오류): {e}")
        # 오류 발생 시 빈 리스트 반환
        return []


def get_gpt_models():
    """OpenAI API에서 사용 가능한 GPT 모델 목록 가져오기"""
    api_key = os.getenv(constants.OPENAI_API_KEY_ENV)
    if not api_key or openai is None: return []

    try:
        # OpenAI 클라이언트 생성
        client = openai.OpenAI(api_key=api_key)
        models = client.models.list()
        # 채팅 및 최신 모델 위주 필터링 (예: gpt-4, gpt-3.5)
        gpt_models = [m.id for m in models.data if m.id.startswith(('gpt-4', 'gpt-3.5'))]
        print(f"✅ OpenAI GPT 모델 로드 완료 ({len(gpt_models)}개)")
        return sorted(gpt_models)
    except Exception as e:
        print(f"❌ GPT 모델 목록 가져오기 실패: {e}")
        return []

def get_available_models():
    """모든 API에서 사용 가능한 모델 목록 가져오기"""
    models = {
        constants.API_TYPE_GEMINI: get_gemini_models(),
        constants.API_TYPE_CLAUDE: get_claude_models(),
        constants.API_TYPE_GPT: get_gpt_models()
    }
    return models

# --- 프롬프트 생성 (수정된 버전) ---
def generate_prompt(novel_settings, chapter_arc_notes, scene_plot, length_option, previous_scene_content=None):
    """소설 설정, 챕터 노트, 장면 플롯, 이전 장면 내용을 기반으로 사용자 프롬프트를 생성합니다."""
    length_request = f"({length_option})"

    # 소설 전체 설정 블록
    novel_setting_key = constants.NOVEL_MAIN_SETTINGS_KEY
    novel_setting_content = novel_settings.get(novel_setting_key, "").strip()
    novel_block = ""
    if novel_setting_content:
        novel_block = f"**[소설 전체 설정: {novel_setting_key}]**\n{novel_setting_content}\n---"

    # 챕터 아크 노트 블록
    chapter_notes_key = constants.CHAPTER_ARC_NOTES_KEY
    chapter_notes_content = chapter_arc_notes.get(chapter_notes_key, "").strip()
    chapter_block = ""
    if chapter_notes_content:
        chapter_block = f"**[이번 챕터 아크 노트: {chapter_notes_key}]**\n{chapter_notes_content}\n---"

    # 작성 가이드라인
    guidelines = f"""
**[작성 가이드라인]**
*   요청 분량({length_request})에 맞춰 웹소설 형식으로 작성해주세요.
*   다음 장면이 궁금해지도록 흥미로운 사건이나 복선을 포함해주세요."""

    # 장면 플롯 블록
    plot_key = constants.SCENE_PLOT_KEY
    plot_content = scene_plot.strip() if scene_plot else '자유롭게 진행해주세요.'
    plot_block = f"**[이번 장면 플롯 ({plot_key})]**\n{plot_content}"

    # --- 이전 장면 내용 블록 (수정) ---
    prev_content_block = ""
    # previous_scene_content가 이제 여러 장면의 결합된 내용일 수 있음
    if previous_scene_content and previous_scene_content.strip():
        # 레이블 수정: 이전 장면 하나가 아님을 명시
        prev_content_block = f"**[이번 챕터 이전 내용]**\n{previous_scene_content}\n---"
        # instruction 수정: '위 내용' -> '이전 내용' 또는 '지금까지의 내용'
        prompt_instruction = "지금까지의 내용에 이어서, 아래 설정과 요청에 따라 **다음 장면**을 작성해 주세요."
        final_section_header = "**[다음 장면 시작]**"
    else:
        # 첫 장면일 경우
        prompt_instruction = "다음 주어진 소설 설정, 챕터 노트, 첫 장면의 플롯을 바탕으로 흥미진진한 웹소설의 **첫 장면**을 작성해주세요."
        final_section_header = "**[웹소설 첫 장면 시작]**"

    # 프롬프트 조합
    prompt_parts = [
        prev_content_block, # 이전 내용이 맨 앞에 오도록 순서 유지
        prompt_instruction,
        novel_block,
        chapter_block,
        plot_block,
        guidelines,
        # 첫 장면이 아닐 때의 가이드라인 수정
        '*   이전 내용과 자연스럽게 이어지도록 작성해주세요.' if prev_content_block else '*   등장인물의 매력과 세계관의 특징이 잘 드러나도록 묘사해주세요.',
        final_section_header
    ]
    prompt = "\n\n".join(part for part in prompt_parts if part)

    # print("--- 생성된 프롬프트 ---")
    # print(prompt[:500] + "...")
    # print("----------------------")
    return prompt


# --- API 호출 (공통 진입점 및 분기) ---

def generate_webnovel_scene_api_call(api_type, model_name, prompt, system_prompt, temperature=constants.DEFAULT_TEMPERATURE):
    """API 타입에 따라 적절한 생성 함수 호출"""
    print(f"API HANDLER: Scene generation request received for API='{api_type}', Model='{model_name}'") # DEBUG
    if api_type == constants.API_TYPE_GEMINI:
        return _generate_with_gemini(model_name, prompt, system_prompt, temperature)
    elif api_type == constants.API_TYPE_CLAUDE:
        return _generate_with_claude(model_name, prompt, system_prompt, temperature)
    elif api_type == constants.API_TYPE_GPT:
        return _generate_with_gpt(model_name, prompt, system_prompt, temperature)
    else:
        msg = f"오류: 지원되지 않는 API 타입: {api_type}"
        print(f"❌ API HANDLER: {msg}")
        return msg, None # Return error message and None for token_info

def generate_summary_api_call(api_type, model_name, text_to_summarize):
    """API 타입에 따라 적절한 요약 함수 호출"""
    print(f"API HANDLER: Summary generation request received for API='{api_type}', Model='{model_name}'") # DEBUG
    if not text_to_summarize or not text_to_summarize.strip():
        print("ℹ️ API HANDLER: 요약할 내용 없음. 빈 요약 반환.")
        return "", {constants.INPUT_TOKEN_KEY: 0, constants.OUTPUT_TOKEN_KEY: 0} # Return empty string and zero tokens

    summary_system_prompt = "당신은 주어진 웹소설 내용을 바탕으로 이전 줄거리를 간결하고 명확하게 요약하는 AI입니다. 핵심 사건과 인물 관계 변화를 중심으로 요약해주세요."
    summary_user_prompt = f"""다음 웹소설 내용을 바탕으로 이전 줄거리를 요약해주세요:

{text_to_summarize}

---
**[요약 결과]**"""

    # Ensure a valid model name is provided for the given API type
    if not model_name:
        msg = f"오류: '{api_type}' API에 대한 요약 모델 이름이 제공되지 않았습니다."
        print(f"❌ API HANDLER: {msg}")
        return msg, None

    if api_type == constants.API_TYPE_GEMINI:
        return _generate_with_gemini(model_name, summary_user_prompt, summary_system_prompt, constants.SUMMARY_TEMPERATURE)
    elif api_type == constants.API_TYPE_CLAUDE:
        return _generate_with_claude(model_name, summary_user_prompt, summary_system_prompt, constants.SUMMARY_TEMPERATURE)
    elif api_type == constants.API_TYPE_GPT:
        return _generate_with_gpt(model_name, summary_user_prompt, summary_system_prompt, constants.SUMMARY_TEMPERATURE)
    else:
        msg = f"오류: 지원되지 않는 API 타입 (요약): {api_type}"
        print(f"❌ API HANDLER: {msg}")
        return msg, None # Return error message and None for token_info


# --- API별 실제 호출 함수 ---

def _generate_with_gemini(model_name, prompt, system_prompt, temperature):
    """Gemini API를 사용하여 텍스트 생성"""
    print(f"API HANDLER (Gemini): Calling model '{model_name}'...") # DEBUG
    token_info = {constants.INPUT_TOKEN_KEY: 0, constants.OUTPUT_TOKEN_KEY: 0}
    error_message = None
    response = None

    try:
        # Gemini API 설정 확인 및 재설정 (Ensure configure is called if needed)
        if not os.getenv(constants.GOOGLE_API_KEY_ENV):
             return "오류: Gemini API 키가 설정되지 않았습니다.", token_info # Return error, token_info
        # Consider calling configure_gemini_api() here if needed, but it might be redundant if checked at startup
        # genai.configure(api_key=os.getenv(constants.GOOGLE_API_KEY_ENV)) # Safer to reconfigure if unsure

        model_kwargs = {"model_name": model_name}
        # Gemini supports system_instruction directly in GenerativeModel constructor
        if system_prompt and system_prompt.strip():
            model_kwargs["system_instruction"] = system_prompt.strip()

        try:
            temp_value = float(temperature); temp_value = max(0.0, min(2.0, temp_value))
        except (ValueError, TypeError): temp_value = constants.DEFAULT_TEMPERATURE

        model = genai.GenerativeModel(**model_kwargs)
        generation_config = genai.types.GenerationConfig(temperature=temp_value)
        # Define request_timeout (consider making it configurable)
        request_timeout = 720 # Example: 12 minutes

        start_time = time.time()
        response = model.generate_content(
            prompt,
            generation_config=generation_config,
            safety_settings=constants.SAFETY_SETTINGS, # Define SAFETY_SETTINGS in constants if needed, otherwise remove
            request_options={'timeout': request_timeout}
        )
        end_time = time.time()
        print(f"✅ API HANDLER (Gemini): Response received ({end_time - start_time:.2f}s)")

        # --- Gemini Token Extraction ---
        try:
            if response and hasattr(response, 'usage_metadata'):
                usage_meta = response.usage_metadata
                token_info = {
                    constants.INPUT_TOKEN_KEY: getattr(usage_meta, 'prompt_token_count', 0),
                    constants.OUTPUT_TOKEN_KEY: getattr(usage_meta, 'candidates_token_count', 0) # Note: Gemini uses candidates_token_count
                }
                print(f"📊 Gemini Tokens: Input={token_info[constants.INPUT_TOKEN_KEY]}, Output={token_info[constants.OUTPUT_TOKEN_KEY]}")
            elif response and hasattr(response, 'usage'): # Fallback for potential older API versions or different response structures
                 token_info = {
                     constants.INPUT_TOKEN_KEY: getattr(response.usage, 'prompt_tokens', 0),
                     constants.OUTPUT_TOKEN_KEY: getattr(response.usage, 'completion_tokens', 0) # Check if this key exists
                 }
                 print(f"📊 Gemini Tokens (Fallback): Input={token_info[constants.INPUT_TOKEN_KEY]}, Output={token_info[constants.OUTPUT_TOKEN_KEY]}")
            else:
                print("⚠️ Gemini Tokens: No usage metadata found in response.")
        except Exception as token_err:
            print(f"⚠️ Gemini Tokens: Error extracting token info: {token_err}")

        # --- Gemini Response Handling ---
        generated_text = None
        finish_reason_val = "UNKNOWN"
        block_reason = None

        if response and response.prompt_feedback:
             block_reason_enum = getattr(response.prompt_feedback, 'block_reason', None)
             if block_reason_enum:
                  block_reason = block_reason_enum.name if hasattr(block_reason_enum, 'name') else str(block_reason_enum)
                  print(f"❌ Gemini prompt blocked: {block_reason}")
                  error_message = f"오류 발생: 입력 내용이 안전 정책에 의해 차단되었습니다 (사유: {block_reason}).\n프롬프트나 설정을 수정해보세요."
                  return error_message, token_info # Return error early

        if response and response.candidates:
            # Check for safety ratings within candidates as well
            candidate = response.candidates[0]
            finish_reason_enum = getattr(candidate, 'finish_reason', None)
            finish_reason_val = finish_reason_enum.name if hasattr(finish_reason_enum, 'name') else str(finish_reason_enum)
            print(f"ℹ️ Gemini Finish Reason: {finish_reason_val}")

            safety_ratings = getattr(candidate, 'safety_ratings', [])
            for rating in safety_ratings:
                 if getattr(rating, 'blocked', False):
                     block_reason = f"Candidate blocked (Category: {getattr(rating, 'category', 'N/A').name})"
                     print(f"❌ Gemini {block_reason}")
                     error_message = f"오류 발생: 생성된 내용이 안전 정책에 의해 차단되었습니다 (사유: {block_reason})."
                     return error_message, token_info # Return error early

            # Extract text content
            try:
                if candidate.content and candidate.content.parts:
                    generated_text = "".join(part.text for part in candidate.content.parts if hasattr(part, 'text'))
                # Sometimes the text might be directly in candidate.text
                elif hasattr(candidate, 'text') and isinstance(candidate.text, str):
                     generated_text = candidate.text

            except (AttributeError, IndexError, TypeError) as text_extract_err:
                print(f"⚠️ Gemini response text extraction error: {text_extract_err}")
                generated_text = None

        # Return logic
        if generated_text is not None:
            if finish_reason_val not in ['STOP', '1', 'FINISH_REASON_STOP']:
                print(f"⚠️ Gemini generation finished with non-STOP reason: {finish_reason_val}")
                # Append warning only if reason indicates potential truncation/issue
                if finish_reason_val in ['MAX_TOKENS', 'SAFETY', 'RECITATION', 'OTHER']:
                     generated_text += f"\n\n[!] 생성 중단됨 (사유: {finish_reason_val})"
            return generated_text, token_info
        else:
            if block_reason: # If already blocked, return that message
                 error_message = f"오류 발생: 입력 또는 생성 내용 차단됨 (사유: {block_reason})."
            else: # No text and not explicitly blocked
                 error_message = f"오류 발생: API 응답에서 생성된 내용을 찾을 수 없습니다 (종료 사유: {finish_reason_val})."
                 print(f"❌ {error_message}. Full Response: {response}")
            return error_message, token_info

    except google.api_core.exceptions.GoogleAPIError as e:
        # ... (keep existing detailed Gemini error handling) ...
        error_message = f"오류: Gemini API 호출 실패: {e.__class__.__name__}: {e}"
        print(f"❌ API HANDLER (Gemini): {error_message}")
        # Detailed error messages based on exception type
        if isinstance(e, google.api_core.exceptions.InvalidArgument): error_message = f"오류: 잘못된 요청 인수 (모델명, API키 등 확인).\n{e}"
        elif isinstance(e, google.api_core.exceptions.ResourceExhausted): error_message = f"오류: API 할당량 초과 또는 리소스 부족.\n{e}"
        elif isinstance(e, google.api_core.exceptions.DeadlineExceeded): error_message = f"오류: API 요청 시간 초과 (현재 {request_timeout}초).\n{e}"
        elif isinstance(e, google.api_core.exceptions.PermissionDenied): error_message = f"오류: API 키 권한 부족 또는 유효하지 않음.\n{e}"
        elif hasattr(e, 'message') and "API key not valid" in e.message: error_message = f"오류: Gemini API 키가 유효하지 않습니다. 키를 확인하세요.\n{e}"
        return error_message, token_info # Return error and token_info (might be 0)
    except Exception as e:
        error_message = f"오류: Gemini 생성 중 예상치 못한 문제 발생: {e.__class__.__name__}: {e}"
        print(f"❌ API HANDLER (Gemini): {error_message}")
        traceback.print_exc()
        return error_message, token_info # Return error and token_info (might be 0)


def _generate_with_claude(model_name, prompt, system_prompt, temperature):
    """Claude API를 사용하여 텍스트 생성"""
    print(f"API HANDLER (Claude): Calling model '{model_name}'...") # DEBUG
    token_info = {constants.INPUT_TOKEN_KEY: 0, constants.OUTPUT_TOKEN_KEY: 0}
    api_key = os.getenv(constants.ANTHROPIC_API_KEY_ENV)

    if not api_key: return "오류: Claude API 키가 없습니다.", token_info
    if anthropic is None: return "오류: Anthropic 라이브러리가 설치되지 않았습니다. (`pip install anthropic`)", token_info

    try:
        client = anthropic.Anthropic(api_key=api_key) # Client can be created here
        try:
            temp_value = float(temperature); temp_value = max(0.0, min(1.0, temp_value)) # Claude temp range: 0.0 to 1.0
        except (ValueError, TypeError): temp_value = constants.DEFAULT_TEMPERATURE # Use default if invalid

        # Define max_tokens (important for Claude)
        # Consider making this dynamic based on 'length_option' if passed, or use a generous default
        max_tokens_to_generate = 4096 # Claude 3.5 default max output is high

        print(f"🤖 API HANDLER (Claude): Calling model '{model_name}' (Temp: {temp_value:.2f}, MaxTokens: {max_tokens_to_generate})...")
        start_time = time.time()

        # Construct the message list
        messages = [{"role": "user", "content": prompt}]
        # Claude uses 'system' parameter for system prompt
        system_param = system_prompt if system_prompt and system_prompt.strip() else None

        response = client.messages.create(
            model=model_name,
            max_tokens=max_tokens_to_generate,
            temperature=temp_value,
            system=system_param,
            messages=messages
        )

        end_time = time.time()
        print(f"✅ API HANDLER (Claude): Response received ({end_time - start_time:.2f}s)")

        # --- Claude Token Extraction ---
        if hasattr(response, 'usage'):
            token_info = {
                constants.INPUT_TOKEN_KEY: getattr(response.usage, 'input_tokens', 0),
                constants.OUTPUT_TOKEN_KEY: getattr(response.usage, 'output_tokens', 0)
            }
            print(f"📊 Claude Tokens: Input={token_info[constants.INPUT_TOKEN_KEY]}, Output={token_info[constants.OUTPUT_TOKEN_KEY]}")
        else:
             print("⚠️ Claude Tokens: No usage info found in response.")

        # --- Claude Response Handling ---
        generated_text = ""
        finish_reason = "UNKNOWN"
        if hasattr(response, 'content') and response.content:
            # Content is a list, usually with one text block
            for block in response.content:
                if getattr(block, 'type', '') == 'text':
                    generated_text += getattr(block, 'text', '')
        if hasattr(response, 'stop_reason'):
            finish_reason = response.stop_reason
            print(f"ℹ️ Claude Finish Reason: {finish_reason}")

        if generated_text:
            if finish_reason not in ['end_turn', 'stop_sequence']: # Not a normal completion
                print(f"⚠️ Claude generation finished with non-standard reason: {finish_reason}")
                # Append warning if truncated
                if finish_reason == 'max_tokens':
                     generated_text += f"\n\n[!] 생성 중단됨 (사유: 최대 토큰 도달)"
            return generated_text, token_info
        else:
            error_message = f"오류 발생: Claude API 응답에서 생성된 내용을 찾을 수 없습니다 (종료 사유: {finish_reason})."
            print(f"❌ {error_message}. Full Response: {response}")
            return error_message, token_info # Return error and token_info

    except anthropic.APIError as e:
        # ... (keep existing detailed Claude error handling) ...
        error_message = f"오류: Claude API 호출 실패: {e.__class__.__name__}: {e}"
        print(f"❌ API HANDLER (Claude): {error_message}")
        if isinstance(e, anthropic.AuthenticationError): error_message = f"오류: Claude API 인증 실패 (API 키 확인).\n{e}"
        elif isinstance(e, anthropic.PermissionDeniedError): error_message = f"오류: Claude API 권한 부족.\n{e}"
        elif isinstance(e, anthropic.RateLimitError): error_message = f"오류: Claude API 호출 제한 초과.\n{e}"
        elif isinstance(e, anthropic.NotFoundError) and hasattr(e, 'message') and 'model' in e.message: error_message = f"오류: Claude 모델 '{model_name}'을(를) 찾을 수 없습니다.\n{e}"
        elif isinstance(e, anthropic.BadRequestError) and hasattr(e, 'message') and 'invalid system prompt' in e.message: error_message = f"오류: Claude 시스템 프롬프트 형식이 잘못되었습니다.\n{e}"
        return error_message, token_info # Return error and token_info
    except Exception as e:
        error_message = f"오류: Claude 생성 중 예상치 못한 문제 발생: {e.__class__.__name__}: {e}"
        print(f"❌ API HANDLER (Claude): {error_message}")
        traceback.print_exc()
        return error_message, token_info # Return error and token_info


def _generate_with_gpt(model_name, prompt, system_prompt, temperature):
    """OpenAI GPT API를 사용하여 텍스트 생성"""
    print(f"API HANDLER (GPT): Calling model '{model_name}'...") # DEBUG
    token_info = {constants.INPUT_TOKEN_KEY: 0, constants.OUTPUT_TOKEN_KEY: 0}
    api_key = os.getenv(constants.OPENAI_API_KEY_ENV)

    if not api_key: return "오류: OpenAI API 키가 없습니다.", token_info
    if openai is None: return "오류: OpenAI 라이브러리가 설치되지 않았습니다. (`pip install openai`)", token_info

    try:
        client = openai.OpenAI(api_key=api_key) # Client created here
        try:
            temp_value = float(temperature); temp_value = max(0.0, min(2.0, temp_value)) # OpenAI temp range: 0.0 to 2.0
        except (ValueError, TypeError): temp_value = constants.DEFAULT_TEMPERATURE

        # Construct message list including system prompt
        messages = []
        if system_prompt and system_prompt.strip():
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        # Consider adding max_tokens if needed, otherwise relies on model defaults
        # max_tokens_to_generate = 4096 # Example if needed

        print(f"🤖 API HANDLER (GPT): Calling model '{model_name}' (Temp: {temp_value:.2f})...")
        start_time = time.time()

        response = client.chat.completions.create(
            model=model_name,
            temperature=temp_value,
            messages=messages
            # max_tokens=max_tokens_to_generate # Uncomment if needed
        )

        end_time = time.time()
        print(f"✅ API HANDLER (GPT): Response received ({end_time - start_time:.2f}s)")

        # --- GPT Token Extraction ---
        if hasattr(response, 'usage'):
            token_info = {
                constants.INPUT_TOKEN_KEY: getattr(response.usage, 'prompt_tokens', 0),
                constants.OUTPUT_TOKEN_KEY: getattr(response.usage, 'completion_tokens', 0) # OpenAI uses completion_tokens
            }
            print(f"📊 GPT Tokens: Input={token_info[constants.INPUT_TOKEN_KEY]}, Output={token_info[constants.OUTPUT_TOKEN_KEY]}")
        else:
             print("⚠️ GPT Tokens: No usage info found in response.")

        # --- GPT Response Handling ---
        generated_text = None
        finish_reason = "UNKNOWN"
        if response.choices:
             choice = response.choices[0]
             if choice.message:
                 generated_text = choice.message.content
             finish_reason = choice.finish_reason
             print(f"ℹ️ GPT Finish Reason: {finish_reason}")

        if generated_text is not None: # Check for None, empty string is valid
            if finish_reason != 'stop': # Not a normal completion
                print(f"⚠️ GPT generation finished with non-stop reason: {finish_reason}")
                # Append warning if truncated by length
                if finish_reason == 'length':
                     generated_text += f"\n\n[!] 생성 중단됨 (사유: 최대 길이 도달)"
                elif finish_reason == 'content_filter':
                     # GPT usually errors out for content filter, but check anyway
                     generated_text += f"\n\n[!] 생성 중단됨 (사유: 콘텐츠 필터)"
            return generated_text, token_info
        else:
            # Check for content filter block in the response structure if available
            # (This might be in response.prompt_annotations or similar, depends on API version)
            # Example placeholder:
            # if finish_reason == 'content_filter' or _check_gpt_content_filter(response):
            #    error_message = "오류 발생: 입력 또는 생성 내용이 콘텐츠 필터에 의해 차단되었습니다."
            # else:
            error_message = f"오류 발생: GPT API 응답에서 생성된 내용을 찾을 수 없습니다 (종료 사유: {finish_reason})."
            print(f"❌ {error_message}. Full Response: {response}")
            return error_message, token_info # Return error and token_info

    except openai.APIError as e:
        # ... (keep existing detailed GPT error handling) ...
        error_message = f"오류: GPT API 호출 실패: {e.__class__.__name__}: {e}"
        print(f"❌ API HANDLER (GPT): {error_message}")
        if isinstance(e, openai.AuthenticationError): error_message = f"오류: GPT API 인증 실패 (API 키 확인).\n{e}"
        elif isinstance(e, openai.PermissionDeniedError): error_message = f"오류: GPT API 권한 부족.\n{e}"
        elif isinstance(e, openai.RateLimitError): error_message = f"오류: GPT API 호출 제한 초과.\n{e}"
        elif isinstance(e, openai.NotFoundError) and hasattr(e, 'message') and 'model' in e.message: error_message = f"오류: GPT 모델 '{model_name}'을(를) 찾을 수 없습니다.\n{e}"
        elif isinstance(e, openai.BadRequestError): error_message = f"오류: GPT 요청 형식이 잘못되었습니다 (프롬프트 확인).\n{e}"
        elif isinstance(e, openai.APIConnectionError): error_message = f"오류: GPT API 연결 실패 (네트워크 확인).\n{e}"
        # Check for content policy violation specifically if possible
        if hasattr(e, 'code') and e.code == 'content_policy_violation':
             error_message = f"오류: GPT 콘텐츠 정책 위반으로 요청이 차단되었습니다.\n{e}"

        return error_message, token_info # Return error and token_info
    except Exception as e:
        error_message = f"오류: GPT 생성 중 예상치 못한 문제 발생: {e.__class__.__name__}: {e}"
        print(f"❌ API HANDLER (GPT): {error_message}")
        traceback.print_exc()
        return error_message, token_info # Return error and token_info

# 호환성을 위해 이전 함수명도 유지 (Gemini 호출로 연결)
def generate_webnovel_api_call(model_name, prompt, system_prompt, temperature=constants.DEFAULT_TEMPERATURE):
     print("WARN: generate_webnovel_api_call() is deprecated. Use generate_webnovel_scene_api_call() with API type.")
     return _generate_with_gemini(model_name, prompt, system_prompt, temperature)