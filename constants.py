# constants.py
import os
import platform

# --- 경로 및 파일명 ---
BASE_SAVE_DIR = "novels_data"  # 최상위 저장 폴더 이름

CONFIG_FILE = "config.json"  # 전역 설정 파일
ENV_FILE = ".env"  # 환경 변수 파일

# --- 소설 레벨 ---
NOVEL_SETTINGS_FILENAME = "novel_settings.json"  # 소설 레벨 설정 파일 이름

# --- 챕터 (Arc/폴더) 레벨 ---
CHAPTER_SETTINGS_FILENAME = "chapter_settings.json" # 챕터 아크 전체 설정 파일 이름 (챕터 폴더 내)

# --- 장면 (Scene/파일) 레벨 ---
SCENE_FILENAME_FORMAT = "{:03d}.txt"
SCENE_SETTINGS_FILENAME_FORMAT = "{:03d}_settings.json"

ICON_FILE = "novel_icon.ico"  # 아이콘 파일 이름

# --- API 및 모델 설정 ---
# API 타입 정의 (소문자 사용 권장)
API_TYPE_GEMINI = "gemini"
API_TYPE_CLAUDE = "claude"
API_TYPE_GPT = "gpt"
SUPPORTED_API_TYPES = [API_TYPE_GEMINI, API_TYPE_CLAUDE, API_TYPE_GPT]

# API 키 환경 변수 이름
GOOGLE_API_KEY_ENV = "GOOGLE_API_KEY"
ANTHROPIC_API_KEY_ENV = "ANTHROPIC_API_KEY"
OPENAI_API_KEY_ENV = "OPENAI_API_KEY"

# 기본 창작 모델 (각 API별 - 사용 가능한 모델 중 선호도)
# 실제 사용 가능 여부는 main.py에서 확인 후 조정될 수 있음
DEFAULT_GEMINI_MODEL = "gemini-2.5-pro-exp-03-25" # 기존 DEFAULT_MODEL
DEFAULT_CLAUDE_MODEL = "claude-3-5-sonnet-20240620" # Claude 3.5 Sonnet 예시
DEFAULT_GPT_MODEL = "gpt-4" # GPT-4 예시

# 기본 요약 모델 (각 API별)
DEFAULT_SUMMARY_MODEL_GEMINI = "gemini-2.0-flash-exp" # 기존 DEFAULT_SUMMARY_MODEL
DEFAULT_SUMMARY_MODEL_CLAUDE = "claude-3-haiku-20240307" # Haiku 예시
DEFAULT_SUMMARY_MODEL_GPT = "gpt-3.5-turbo" # GPT 3.5 Turbo 예시

# Config 키 (요약 모델 - API 타입별 저장)
SUMMARY_MODEL_KEY_PREFIX = "summary_model_" # 예: summary_model_gemini

# --- 생성 파라미터 ---
DEFAULT_TEMPERATURE = 1.0
SUMMARY_TEMPERATURE = 0.5
LENGTH_OPTIONS = ["5000자 내외", "3000자 내외", "2000자 내외", "1000자 내외"]

# --- 기본값 및 마커 ---
DEFAULT_SYSTEM_PROMPT = "다음화를 예고하는 느낌의 문장을 매 화의 마지막 문장으로 쓰지마. 마지막 문장은 주로 평이한 문장으로 쓸 것. 전개할 때 설명이 많이 필요한 파트는 설명한 뒤 주인공의 혼잣말으로 요약해서 알려줄 것. [소설 설정], [챕터 아크 설정], [장면 설정] 같은 경우에는 참고하되 생성하는 본문에는 넣지 말것. **강조** 이런 표현 사용하지 말 것."
DEFAULT_OUTPUT_BG = "#E3EFEE"
DEFAULT_OUTPUT_FG = "black"
SUMMARY_HEADER = "[이전 줄거리 요약]"

# --- 설정 키 정의 ---
# 설정 키는 이전과 동일하게 유지 (NOVEL_MAIN_SETTINGS_KEY 등)
# 다만 config.json 저장 시 API 타입 관련 키 추가 가능성 있음
CONFIG_API_TYPE_KEY = 'selected_api_type' # config.json 에 저장될 마지막 사용 API 타입 키
CONFIG_MODEL_KEY = 'selected_model' # config.json 에 저장될 마지막 사용 모델 키
# --- New Key ---
CONFIG_ASK_KEYS_KEY = 'ask_for_missing_keys_on_startup' # 시작 시 누락된 키 확인 여부

# 1. 소설 전체 레벨 (novel_settings.json 에 저장)
NOVEL_MAIN_SETTINGS_KEY = 'novel_settings'
NOVEL_LEVEL_SETTINGS = [NOVEL_MAIN_SETTINGS_KEY]
NOVEL_SETTING_KEYS_TO_SAVE = NOVEL_LEVEL_SETTINGS

# 2. 챕터 (Arc/폴더) 레벨 (chapter_settings.json 에 저장)
CHAPTER_ARC_NOTES_KEY = 'chapter_arc_notes'
CHAPTER_LEVEL_SETTINGS = [CHAPTER_ARC_NOTES_KEY]
CHAPTER_SETTING_KEYS_TO_SAVE = CHAPTER_LEVEL_SETTINGS

# 3. 장면 (Scene/파일) 레벨 (XXX_settings.json 에 저장)
SCENE_PLOT_KEY = 'scene_plot'
SCENE_SPECIFIC_SETTINGS = [SCENE_PLOT_KEY]

# 4. GUI 입력/표시용 설정 (Scene 생성 시 스냅샷으로 저장)
GUI_OTHER_SETTINGS = ['temperature', 'length', 'selected_model']

# 5. 토큰 정보 키 (Scene 설정 파일에 저장)
TOKEN_INFO_KEY = 'token_info'
INPUT_TOKEN_KEY = 'input_tokens'
OUTPUT_TOKEN_KEY = 'output_tokens'

# XXX_settings.json 에 저장될 키 목록 (장면 플롯 + GUI 옵션 + 토큰 정보)
SCENE_SETTING_KEYS_TO_SAVE = SCENE_SPECIFIC_SETTINGS + GUI_OTHER_SETTINGS + [TOKEN_INFO_KEY]

# GUI에 표시되고 상호작용하는 모든 설정 관련 키 (소설 + 챕터 아크 + 장면 플롯 + GUI 기타)
ALL_SETTING_KEYS_IN_GUI = NOVEL_LEVEL_SETTINGS + CHAPTER_LEVEL_SETTINGS + SCENE_SPECIFIC_SETTINGS + GUI_OTHER_SETTINGS


# --- GUI 관련 ---
APP_NAME = "AI소설 생성기 ver1.1"
BASE_FONT_FAMILY = "TkDefaultFont"
BASE_FONT_SIZE = 11

PAD_X = 6
PAD_Y = 3
TEXT_FONT = (BASE_FONT_FAMILY, BASE_FONT_SIZE)
LABEL_FONT = (BASE_FONT_FAMILY, BASE_FONT_SIZE, "bold")
STATUS_FONT = (BASE_FONT_FAMILY, BASE_FONT_SIZE - 1)
TREEVIEW_FONT = (BASE_FONT_FAMILY, BASE_FONT_SIZE)

OUTPUT_LINE_SPACING_FACTOR = 0.7
OUTPUT_LINE_SPACING_WITHIN_FACTOR = 0.5

# --- API 관련 ---
SAFETY_SETTINGS = None # Gemini 기본값 사용