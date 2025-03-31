# --- START OF FILE file_handler.py ---

# file_handler.py
import os
import sys
import json
import re
# find_dotenv and dotenv_values added for flexibility, though dotenv_values isn't used in the final save logic here
# Make sure find_dotenv and set_key are imported correctly
from dotenv import load_dotenv, set_key, find_dotenv
import traceback
import shutil
import tkinter as tk
from tkinter import messagebox, simpledialog

import constants # 다른 모듈의 상수 임포트

# --- API 키 확인 및 저장 함수 ---

def request_api_key(api_name, env_key):
    """
    특정 API 서비스의 키를 사용자에게 요청 (이제 시작 시에만 제한적으로 사용).
    이 함수는 키를 요청하고 반환하기만 하며, 직접 저장하지 않습니다.
    """
    root_temp = tk.Tk()
    root_temp.withdraw()
    api_key_input = None
    try:
        api_key_input = simpledialog.askstring(
            f"{api_name} API 키 입력 (시작 시)", # 제목 수정
            f"{api_name} API 키를 입력하세요.\n"
            f"입력된 키는 '{constants.ENV_FILE}' 파일에 저장됩니다.\n"
            f"이 서비스를 사용하지 않으려면 빈 값으로 두고 확인을 클릭하세요.\n\n"
            f"(나중에 '설정 > API 키 관리' 메뉴에서 추가/변경할 수 있습니다.)", # 안내 추가
            parent=root_temp
        )
    finally:
        try: root_temp.destroy()
        except tk.TclError: pass

    if api_key_input:
        api_key = api_key_input.strip()
        if api_key:
            print(f"ℹ️ {api_name} API 키 입력됨 (저장은 관리 함수에서).")
            return api_key
        else:
             print(f"ℹ️ {api_name} API 키 입력 건너뜀 (빈 값).")
             return None
    print(f"ℹ️ {api_name} API 키 입력 건너뜀 (취소).")
    return None

def save_api_keys(keys_to_save: dict):
    """주어진 API 키들을 .env 파일에 저장. 성공 시 True, 실패 시 False 반환."""
    if not isinstance(keys_to_save, dict):
        print("❌ API 키 저장 실패: 입력 데이터가 dictionary 타입이 아님.")
        return False

    try:
        # --- More Robust Path Finding ---
        # Try finding relative to the script first (assuming standard structure)
        # Get the directory where file_handler.py is located
        script_dir = os.path.dirname(os.path.abspath(__file__))
        # Assume .env should be in the parent directory (where main.py likely is)
        # Adjust this if your project structure is different
        project_root = os.path.dirname(script_dir) # Go one level up from file_handler.py's dir
        # If file_handler.py seems to be directly in the project root (not in a subdir like 'src' or 'gui')
        # Check if the script's directory name suggests it's NOT a subdirectory
        # Example: if script_dir is '/path/to/project' and not '/path/to/project/src'
        # A simple heuristic: if the parent directory name isn't something common like 'src', 'lib', 'gui', etc.
        # Or, more simply, if the script dir name itself doesn't indicate a subdir.
        # For this project structure, let's assume if it's not in a dir starting with 'gui_' it might be root.
        # Refined check: Check if parent dir exists and isn't the script dir itself. If it is, use script_dir as root.
        if not project_root or project_root == script_dir:
             project_root = script_dir
        elif not os.path.basename(script_dir).startswith("gui_"): # Heuristic: if not in 'gui_*' assume root
             project_root = script_dir

        # Define the target path explicitly
        env_path_abs = os.path.join(project_root, constants.ENV_FILE)
        print(f"DEBUG: Target .env path determined as: {env_path_abs}")

        # Use this absolute path consistently
        env_path = env_path_abs

        # --- Ensure Directory and File Exist ---
        env_dir = os.path.dirname(env_path)
        if env_dir and not os.path.exists(env_dir):
            print(f"INFO: Creating directory for .env: {env_dir}")
            os.makedirs(env_dir, exist_ok=True) # Create directory if it doesn't exist
        if not os.path.exists(env_path):
            print(f"INFO: Creating empty .env file: {env_path}")
            with open(env_path, 'w', encoding='utf-8') as f:
                 f.write("# API Keys for AI Novel Generator\n") # Add a comment
                 pass # Create empty file with a header
        else:
             print(f"INFO: Using existing .env file: {env_path}")
        # --- Path setup finished ---

    except Exception as e:
        print(f"❌ .env 파일 경로 설정 또는 생성 중 오류: {e}")
        traceback.print_exc() # Print full traceback for debugging
        messagebox.showerror("파일 오류", f".env 파일 접근/생성 중 오류 발생:\n{e}")
        return False

    all_success = True
    saved_count = 0
    failed_keys = []

    for api_type, key_value in keys_to_save.items():
        env_key = None
        api_name = api_type.capitalize()
        if api_type == constants.API_TYPE_GEMINI: env_key = constants.GOOGLE_API_KEY_ENV
        elif api_type == constants.API_TYPE_CLAUDE: env_key = constants.ANTHROPIC_API_KEY_ENV
        elif api_type == constants.API_TYPE_GPT: env_key = constants.OPENAI_API_KEY_ENV

        if env_key and key_value is not None: # Only save if key and value exist
            key_value_str = str(key_value).strip()
            if not key_value_str: # If user entered empty string, treat as removal/no change
                print(f"INFO: {api_name} 키 빈 값으로 입력됨, 저장 건너뜀.")
                continue

            try:
                # Use the determined absolute path
                print(f"DEBUG: Calling set_key for '{env_key}' in file: {env_path}")
                # Specify encoding, use calculated env_path
                success = set_key(dotenv_path=env_path, key_to_set=env_key, value_to_set=key_value_str, quote_mode='always', encoding='utf-8')
                if success:
                    print(f"✅ {api_name} API 키 ('{env_key}')가 '{env_path}' 파일에 저장/업데이트되었습니다.")
                    # Update os.environ immediately for the current session
                    os.environ[env_key] = key_value_str
                    print(f"DEBUG: os.environ['{env_key}'] updated.")
                    saved_count += 1
                else:
                    # set_key can return False for various reasons (e.g., file busy, permission issues)
                    print(f"WARN: python-dotenv set_key 함수 실패 ({api_name}, key={env_key}). 파일 권한 또는 경로 확인 필요. Path: {env_path}")
                    all_success = False
                    failed_keys.append(api_name)
            except Exception as e:
                print(f"❌ {api_name} API 키 ('{env_key}') 저장 중 오류 ({env_path}): {e}")
                traceback.print_exc()
                all_success = False
                failed_keys.append(api_name)
        elif not env_key:
             print(f"WARN: Unknown API Type '{api_type}' found in keys_to_save.")


    print(f"API 키 저장 시도 완료. 성공: {saved_count} / {len(keys_to_save)}. 전체 성공: {all_success}")
    if not all_success:
        messagebox.showwarning("API 키 저장 오류", f"다음 API 키 저장에 실패했습니다: {', '.join(failed_keys)}\n"
                                               f"'{constants.ENV_FILE}' 파일의 권한을 확인하거나 수동으로 입력해주세요.\n"
                                               f"경로: {env_path}") # Show the path in the error
    return all_success

def check_and_get_all_api_keys(config): # config 객체 받도록 수정
    """
    모든 API 키 확인 및 설정 (시작 시).
    - 최소 하나의 키가 없으면 무조건 요청.
    - 하나 이상 있고 설정에서 허용한 경우에만 누락된 키 요청.
    - 하나라도 유효한 키가 있으면 True 반환.
    """
    # Determine .env path *before* loading, using the same logic as save_api_keys
    env_path = None
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)
        if not project_root or project_root == script_dir:
             project_root = script_dir
        elif not os.path.basename(script_dir).startswith("gui_"):
             project_root = script_dir
        env_path = os.path.join(project_root, constants.ENV_FILE)
        print(f"DEBUG: Loading .env from determined path: {env_path}")
    except Exception as e:
        print(f"WARN: Error determining .env path for loading: {e}. Will use default load_dotenv behavior.")
        env_path = constants.ENV_FILE # Fallback

    try:
        # Load using the determined path if possible, otherwise let load_dotenv find it
        load_dotenv(dotenv_path=env_path, override=True, verbose=False)
    except Exception as e:
        print(f"WARN: .env 파일 로드 중 오류 (무시): {e}")

    keys = {
        constants.API_TYPE_GEMINI: os.getenv(constants.GOOGLE_API_KEY_ENV),
        constants.API_TYPE_CLAUDE: os.getenv(constants.ANTHROPIC_API_KEY_ENV),
        constants.API_TYPE_GPT: os.getenv(constants.OPENAI_API_KEY_ENV)
    }
    # Filter out None or empty values for the initial check
    found_any_key = any(k for k in keys.values() if k)
    keys_entered_now = {} # 새로 입력받은 키 임시 저장

    # --- 설정값 로드 ---
    # config 객체가 None일 경우 (예: 초기 실행 시 load_config 실패) 기본값 True 사용
    ask_for_missing_on_startup = config.get(constants.CONFIG_ASK_KEYS_KEY, True) if config else True
    print(f"DEBUG: Ask for missing keys on startup? {'Yes' if ask_for_missing_on_startup else 'No'}")

    if not found_any_key:
        print("⚠️ 사용 가능한 API 키가 하나도 없습니다. 사용자 입력 요청 (최소 1개 필수).")
        root_temp = tk.Tk()
        root_temp.withdraw()
        try:
            messagebox.showinfo(
                "API 키 필요",
                "AI 기능을 사용하려면 적어도 하나의 API 키(Gemini, Claude, GPT 중)가 필요합니다.\n"
                "다음 단계에서 각 API 키 입력을 요청합니다."
            )
            keys_entered_now.clear()
            # 각 키 요청 (이제 request_api_key는 저장 안 함)
            if not keys[constants.API_TYPE_GEMINI]:
                new_key = request_api_key("Google Gemini", constants.GOOGLE_API_KEY_ENV)
                if new_key: keys_entered_now[constants.API_TYPE_GEMINI] = new_key
            if not keys[constants.API_TYPE_CLAUDE]:
                new_key = request_api_key("Anthropic Claude", constants.ANTHROPIC_API_KEY_ENV)
                if new_key: keys_entered_now[constants.API_TYPE_CLAUDE] = new_key
            if not keys[constants.API_TYPE_GPT]:
                new_key = request_api_key("OpenAI GPT", constants.OPENAI_API_KEY_ENV)
                if new_key: keys_entered_now[constants.API_TYPE_GPT] = new_key

            # 새로 입력된 키 저장 시도
            if keys_entered_now:
                if save_api_keys(keys_entered_now):
                    print("✅ 초기 입력된 API 키 저장 완료.")
                    # Update keys dict with newly saved keys (os.environ was updated in save_api_keys)
                    keys.update(keys_entered_now)
                else:
                     # 저장은 실패했지만 키는 메모리에 있을 수 있음 (os.environ), 진행 시도
                     # Note: save_api_keys updates os.environ on success. If it failed, os.environ might not be set.
                     # Let's update the 'keys' dict anyway for the current session's logic.
                     keys.update(keys_entered_now)
                     # Attempt to update os.environ directly for current session even if file save failed
                     for api_type, key_val in keys_entered_now.items():
                         env_key_local = None
                         if api_type == constants.API_TYPE_GEMINI: env_key_local = constants.GOOGLE_API_KEY_ENV
                         elif api_type == constants.API_TYPE_CLAUDE: env_key_local = constants.ANTHROPIC_API_KEY_ENV
                         elif api_type == constants.API_TYPE_GPT: env_key_local = constants.OPENAI_API_KEY_ENV
                         if env_key_local: os.environ[env_key_local] = key_val


            # Filter out None/empty again after potential input
            found_any_key = any(k for k in keys.values() if k)

            if not found_any_key:
                messagebox.showerror(
                    "API 키 오류",
                    "유효한 API 키가 하나도 입력되지 않았습니다.\n프로그램을 종료합니다."
                )
                return False # 종료해야 함
        finally:
            try: root_temp.destroy()
            except tk.TclError: pass
    # --- 하나 이상의 키가 이미 존재하고, 설정에서 추가 확인을 허용한 경우 ---
    elif ask_for_missing_on_startup:
        print("ℹ️ 하나 이상의 API 키 발견됨. 누락된 키 확인 및 선택적 입력 요청 (설정 허용됨).")
        keys_to_ask = {}
        # Check for missing keys (None or empty string)
        if not keys.get(constants.API_TYPE_GEMINI): keys_to_ask[constants.API_TYPE_GEMINI] = ("Google Gemini", constants.GOOGLE_API_KEY_ENV)
        if not keys.get(constants.API_TYPE_CLAUDE): keys_to_ask[constants.API_TYPE_CLAUDE] = ("Anthropic Claude", constants.ANTHROPIC_API_KEY_ENV)
        if not keys.get(constants.API_TYPE_GPT): keys_to_ask[constants.API_TYPE_GPT] = ("OpenAI GPT", constants.OPENAI_API_KEY_ENV)

        if keys_to_ask:
            keys_entered_now.clear()
            root_temp = tk.Tk(); root_temp.withdraw()
            try:
                messagebox.showinfo(
                    "추가 API 키 입력 (선택)",
                    f"현재 {len(keys_to_ask)}개 API의 키가 없습니다.\n"
                    "다른 회사의 AI 모델도 사용하려면 해당 API 키를 입력하세요.\n"
                    "(나중에 '설정 > API 키 관리' 메뉴에서도 추가/변경 가능)"
                )
                for api_type, (api_name, env_key) in keys_to_ask.items():
                    if env_key:
                        new_key = request_api_key(api_name, env_key)
                        if new_key: keys_entered_now[api_type] = new_key
            finally:
                try: root_temp.destroy()
                except tk.TclError: pass

            if keys_entered_now:
                if save_api_keys(keys_entered_now):
                    print("✅ 추가 입력된 API 키 저장 완료.")
                    keys.update(keys_entered_now)
                else:
                    # 저장 실패해도 메모리 반영 시도 (os.environ updated in save_api_keys on success)
                    keys.update(keys_entered_now)
                    # Attempt to update os.environ directly for current session even if file save failed
                    for api_type, key_val in keys_entered_now.items():
                        env_key_local = None
                        if api_type == constants.API_TYPE_GEMINI: env_key_local = constants.GOOGLE_API_KEY_ENV
                        elif api_type == constants.API_TYPE_CLAUDE: env_key_local = constants.ANTHROPIC_API_KEY_ENV
                        elif api_type == constants.API_TYPE_GPT: env_key_local = constants.OPENAI_API_KEY_ENV
                        if env_key_local: os.environ[env_key_local] = key_val

    else: # ask_for_missing_on_startup is False
        print(f"ℹ️ 하나 이상의 API 키 발견됨. 설정({constants.CONFIG_ASK_KEYS_KEY}=False)에 따라 누락된 키 확인 건너뜀.")


    print("✅ API 키 확인 및 설정 완료.")
    # Ensure os.environ reflects the latest state (load_dotenv + save_api_keys should handle this)
    # Final check and update os.environ just in case save failed but key was entered/already existed
    for api_type, key_value in keys.items():
         if key_value: # Only set non-empty keys
            env_key = None
            if api_type == constants.API_TYPE_GEMINI: env_key = constants.GOOGLE_API_KEY_ENV
            elif api_type == constants.API_TYPE_CLAUDE: env_key = constants.ANTHROPIC_API_KEY_ENV
            elif api_type == constants.API_TYPE_GPT: env_key = constants.OPENAI_API_KEY_ENV
            if env_key and os.environ.get(env_key) != key_value:
                # This might happen if load_dotenv initially missed it, or save failed but we want it for the session
                print(f"DEBUG: Updating os.environ for {env_key} (maybe from failed save or initial load issue)")
                os.environ[env_key] = key_value

    # Return True only if at least one valid key exists after all checks/inputs
    return any(k for k in keys.values() if k)

# --- 전역 설정 로드/저장 ---
def load_config():
    """전역 설정(config.json) 로드. 없으면 기본값으로 생성 및 저장."""
    # 기본 설정에 ask_keys_on_startup 키 추가 (기본값 True)
    default_config = {
        'system_prompt': constants.DEFAULT_SYSTEM_PROMPT,
        constants.CONFIG_API_TYPE_KEY: constants.API_TYPE_GEMINI,
        constants.CONFIG_MODEL_KEY: constants.DEFAULT_GEMINI_MODEL,
        f"{constants.SUMMARY_MODEL_KEY_PREFIX}{constants.API_TYPE_GEMINI}": constants.DEFAULT_SUMMARY_MODEL_GEMINI,
        f"{constants.SUMMARY_MODEL_KEY_PREFIX}{constants.API_TYPE_CLAUDE}": constants.DEFAULT_SUMMARY_MODEL_CLAUDE,
        f"{constants.SUMMARY_MODEL_KEY_PREFIX}{constants.API_TYPE_GPT}": constants.DEFAULT_SUMMARY_MODEL_GPT,
        'output_bg_color': constants.DEFAULT_OUTPUT_BG,
        'output_fg_color': constants.DEFAULT_OUTPUT_FG,
        constants.CONFIG_ASK_KEYS_KEY: True # --- 추가된 설정 키 ---
    }
    config_path = constants.CONFIG_FILE
    try:
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            print(f"✅ 전역 설정 로드 완료: {config_path}")

            updated = False
            # 기본 키들 확인 (새로운 키 포함)
            for key, value in default_config.items():
                if key not in config_data:
                    config_data[key] = value
                    updated = True
                    print(f"ℹ️ 전역 설정에 '{key}' 추가됨 (기본값: {value}).")

            # --- 기존 유효성 검사 ---
            if config_data.get(constants.CONFIG_API_TYPE_KEY) not in constants.SUPPORTED_API_TYPES:
                config_data[constants.CONFIG_API_TYPE_KEY] = constants.API_TYPE_GEMINI; updated = True
            if not isinstance(config_data.get('output_bg_color'), str) or not config_data.get('output_bg_color'):
                config_data['output_bg_color'] = constants.DEFAULT_OUTPUT_BG; updated = True
            if not isinstance(config_data.get('output_fg_color'), str) or not config_data.get('output_fg_color'):
                config_data['output_fg_color'] = constants.DEFAULT_OUTPUT_FG; updated = True

            # --- ask_keys_on_startup 타입 검사 ---
            if not isinstance(config_data.get(constants.CONFIG_ASK_KEYS_KEY), bool):
                print(f"WARN: 전역 설정 '{constants.CONFIG_ASK_KEYS_KEY}' 타입 오류 수정 -> True")
                config_data[constants.CONFIG_ASK_KEYS_KEY] = True; updated = True

            if updated:
                if save_config(config_data): print("ℹ️ 기본값 추가/수정 후 전역 설정 파일 저장됨.")
                else: print("❌ 기본값 추가/수정 후 전역 설정 파일 저장 실패.")
            return config_data
        else:
            print(f"ℹ️ 전역 설정 파일({config_path}) 없음, 기본값으로 생성.")
            if save_config(default_config): print(f"✅ 기본 전역 설정 파일 생성 완료: {config_path}")
            else: print(f"❌ 기본 전역 설정 파일 생성 실패.")
            return default_config.copy()
    except json.JSONDecodeError as e:
        print(f"❌ 전역 설정 JSON 디코딩 오류 ({config_path}): {e}")
        messagebox.showerror("설정 파일 오류", f"전역 설정 파일({config_path}) 형식이 잘못되었습니다.\n기본 설정으로 시작합니다.")
        return default_config.copy()
    except Exception as e:
        print(f"❌ 전역 설정 로드 중 오류 ({config_path}): {e}")
        traceback.print_exc()
        messagebox.showerror("전역 설정 로드 오류", f"파일({config_path}) 로드 오류:\n{e}\n기본 설정으로 시작합니다.")
        return default_config.copy()


def save_config(config_data):
    """전역 설정(config.json) 저장."""
    config_path = constants.CONFIG_FILE
    try:
        # --- 저장 전 유효성 검사/정리 ---
        # API 타입, 색상, 모델 키 등 (기존 로직 유지)
        if config_data.get(constants.CONFIG_API_TYPE_KEY) not in constants.SUPPORTED_API_TYPES:
             config_data[constants.CONFIG_API_TYPE_KEY] = constants.API_TYPE_GEMINI
             print(f"WARN: 저장 전 유효하지 않은 API 타입 수정됨 -> {constants.API_TYPE_GEMINI}")
        bg_color = config_data.get('output_bg_color', constants.DEFAULT_OUTPUT_BG)
        fg_color = config_data.get('output_fg_color', constants.DEFAULT_OUTPUT_FG)
        if not isinstance(bg_color, str) or not bg_color:
             config_data['output_bg_color'] = constants.DEFAULT_OUTPUT_BG
             print(f"WARN: 저장 전 유효하지 않은 배경색 수정됨 -> {constants.DEFAULT_OUTPUT_BG}")
        if not isinstance(fg_color, str) or not fg_color:
             config_data['output_fg_color'] = constants.DEFAULT_OUTPUT_FG
             print(f"WARN: 저장 전 유효하지 않은 글자색 수정됨 -> {constants.DEFAULT_OUTPUT_FG}")
        if constants.CONFIG_MODEL_KEY not in config_data:
            config_data[constants.CONFIG_MODEL_KEY] = constants.DEFAULT_GEMINI_MODEL # Should depend on current API type? For now, Gemini default.
            print(f"WARN: 저장 전 누락된 모델 키 추가됨 -> {constants.DEFAULT_GEMINI_MODEL}")

        # --- 요약 모델 키 존재 확인 (기존 로직 유지) ---
        for api_type in constants.SUPPORTED_API_TYPES:
            key = f"{constants.SUMMARY_MODEL_KEY_PREFIX}{api_type}"
            if key not in config_data:
                default_summary = ""
                if api_type == constants.API_TYPE_GEMINI: default_summary = constants.DEFAULT_SUMMARY_MODEL_GEMINI
                elif api_type == constants.API_TYPE_CLAUDE: default_summary = constants.DEFAULT_SUMMARY_MODEL_CLAUDE
                elif api_type == constants.API_TYPE_GPT: default_summary = constants.DEFAULT_SUMMARY_MODEL_GPT
                config_data[key] = default_summary
                print(f"ℹ️ 저장 전 전역 설정에 누락된 키 '{key}' 추가됨 (기본값).")

        # --- ask_keys_on_startup 키 존재 및 타입 확인 ---
        if constants.CONFIG_ASK_KEYS_KEY not in config_data or \
           not isinstance(config_data.get(constants.CONFIG_ASK_KEYS_KEY), bool):
            config_data[constants.CONFIG_ASK_KEYS_KEY] = True # 기본값으로 설정
            print(f"ℹ️ 저장 전 전역 설정에 누락/잘못된 키 '{constants.CONFIG_ASK_KEYS_KEY}' 수정됨 (기본값 True).")

        # --- 파일 저장 ---
        config_dir = os.path.dirname(config_path)
        if config_dir and not os.path.exists(config_dir):
            os.makedirs(config_dir, exist_ok=True)

        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, ensure_ascii=False, indent=4)
        print(f"✅ 전역 설정 저장 완료: {config_path}")
        return True
    except Exception as e:
        print(f"❌ 전역 설정 저장 중 오류 ({config_path}): {e}")
        traceback.print_exc()
        messagebox.showerror("전역 설정 저장 오류", f"파일({config_path}) 저장 오류:\n{e}")
        return False

# --- 소설 설정 로드/저장 ---
def load_novel_settings(novel_dir):
    """특정 소설 폴더의 설정(novel_settings.json) 로드."""
    settings_file = os.path.join(novel_dir, constants.NOVEL_SETTINGS_FILENAME)
    default_settings = {key: "" for key in constants.NOVEL_LEVEL_SETTINGS}

    if not os.path.exists(settings_file):
        print(f"ℹ️ 소설 설정 파일 없음: {settings_file}. 기본값 반환.")
        return default_settings.copy()

    try:
        with open(settings_file, 'r', encoding='utf-8') as f:
            novel_data = json.load(f)
        print(f"✅ 소설 설정 로드: {settings_file}")

        if not isinstance(novel_data, dict):
             print(f"❌ 소설 설정 파일 내용이 JSON 객체가 아님. 기본값 반환.")
             return default_settings.copy()

        final_data = {}
        for key in constants.NOVEL_LEVEL_SETTINGS:
            final_data[key] = novel_data.get(key, default_settings[key]) # 누락 시 기본값 사용

        return final_data

    except json.JSONDecodeError as e:
        print(f"❌ 소설 설정 파일 JSON 디코딩 오류 ({settings_file}): {e}")
        messagebox.showerror("설정 파일 오류", f"소설 설정 파일({os.path.basename(settings_file)}) 형식 오류.", parent=None) # Parent can be None for background errors
        return default_settings.copy()
    except Exception as e:
        print(f"❌ 소설 설정 로드 중 오류 ({settings_file}): {e}")
        traceback.print_exc()
        messagebox.showerror("소설 설정 로드 오류", f"파일({os.path.basename(settings_file)}) 로드 오류:\n{e}", parent=None)
        return default_settings.copy()

def save_novel_settings(novel_dir, settings_data):
    """특정 소설 폴더에 소설 레벨 설정(novel_settings.json) 저장."""
    settings_file = os.path.join(novel_dir, constants.NOVEL_SETTINGS_FILENAME)
    # 저장할 데이터는 NOVEL_SETTING_KEYS_TO_SAVE 에 정의된 키만 포함
    data_to_save = {key: settings_data.get(key, "") for key in constants.NOVEL_SETTING_KEYS_TO_SAVE}

    try:
        os.makedirs(novel_dir, exist_ok=True) # 폴더 존재 확인 및 생성
        with open(settings_file, 'w', encoding='utf-8') as f:
            json.dump(data_to_save, f, ensure_ascii=False, indent=4)
        print(f"✅ 소설 설정 저장: {settings_file}")
        return True
    except Exception as e:
        print(f"❌ 소설 설정 저장 중 오류 ({settings_file}): {e}")
        traceback.print_exc()
        messagebox.showerror("소설 설정 저장 오류", f"파일({os.path.basename(settings_file)}) 저장 오류:\n{e}", parent=None)
        return False

# --- 챕터 (Arc) 설정 로드/저장 ---
def load_chapter_settings(chapter_dir):
    """특정 챕터 폴더의 설정(chapter_settings.json) 로드."""
    settings_file = os.path.join(chapter_dir, constants.CHAPTER_SETTINGS_FILENAME)
    # 챕터 아크 노트만 포함 (실제로는 CHAPTER_LEVEL_SETTINGS에 정의된 모든 키)
    default_settings = {key: "" for key in constants.CHAPTER_LEVEL_SETTINGS}

    if not os.path.exists(settings_file):
        print(f"ℹ️ 챕터 아크 설정 파일 없음: {settings_file}. 기본값 반환.")
        return default_settings.copy()

    try:
        with open(settings_file, 'r', encoding='utf-8') as f:
            chapter_data = json.load(f)
        print(f"✅ 챕터 아크 설정 로드: {settings_file}")

        if not isinstance(chapter_data, dict):
            print(f"❌ 챕터 아크 설정 파일 내용이 JSON 객체가 아님. 기본값 반환.")
            return default_settings.copy()

        final_data = {}
        for key in constants.CHAPTER_LEVEL_SETTINGS:
            final_data[key] = chapter_data.get(key, default_settings[key]) # 누락 시 기본값 사용

        return final_data

    except json.JSONDecodeError as e:
        print(f"❌ 챕터 아크 설정 파일 JSON 디코딩 오류 ({settings_file}): {e}")
        messagebox.showerror("설정 파일 오류", f"챕터 아크 설정 파일({os.path.basename(settings_file)}) 형식 오류.", parent=None)
        return default_settings.copy()
    except Exception as e:
        print(f"❌ 챕터 아크 설정 로드 중 오류 ({settings_file}): {e}")
        traceback.print_exc()
        messagebox.showerror("챕터 아크 설정 로드 오류", f"파일({os.path.basename(settings_file)}) 로드 오류:\n{e}", parent=None)
        return default_settings.copy()

def save_chapter_settings(chapter_dir, settings_data):
    """특정 챕터 폴더에 챕터 아크 레벨 설정(chapter_settings.json) 저장."""
    settings_file = os.path.join(chapter_dir, constants.CHAPTER_SETTINGS_FILENAME)
    # 저장할 데이터는 CHAPTER_SETTING_KEYS_TO_SAVE 에 정의된 키만 포함
    data_to_save = {key: settings_data.get(key, "") for key in constants.CHAPTER_SETTING_KEYS_TO_SAVE}

    try:
        os.makedirs(chapter_dir, exist_ok=True)
        with open(settings_file, 'w', encoding='utf-8') as f:
            json.dump(data_to_save, f, ensure_ascii=False, indent=4)
        print(f"✅ 챕터 아크 설정 저장: {settings_file}")
        return True
    except Exception as e:
        print(f"❌ 챕터 아크 설정 저장 중 오류 ({settings_file}): {e}")
        traceback.print_exc()
        messagebox.showerror("챕터 아크 설정 저장 오류", f"파일({os.path.basename(settings_file)}) 저장 오류:\n{e}", parent=None)
        return False

# --- 장면 (Scene) 설정 로드/저장 ---
def load_scene_settings(chapter_dir, scene_number):
    """특정 장면의 설정(XXX_settings.json) 로드."""
    settings_filename = constants.SCENE_SETTINGS_FILENAME_FORMAT.format(scene_number)
    settings_file = os.path.join(chapter_dir, settings_filename)

    # 장면 설정의 기본값 구조
    default_settings = {
        constants.SCENE_PLOT_KEY: "",
        'temperature': constants.DEFAULT_TEMPERATURE,
        'length': constants.LENGTH_OPTIONS[0] if constants.LENGTH_OPTIONS else "중간", # 안전 장치
        'selected_model': "", # 로드 시 AppCore의 현재 모델 또는 config 모델 사용
        constants.TOKEN_INFO_KEY: {constants.INPUT_TOKEN_KEY: 0, constants.OUTPUT_TOKEN_KEY: 0}
    }

    if not os.path.exists(settings_file):
        print(f"ℹ️ 장면 설정 파일 없음: {settings_file}. 기본값 반환.")
        return default_settings.copy()

    try:
        with open(settings_file, 'r', encoding='utf-8') as f:
            scene_data = json.load(f)
        print(f"✅ 장면 설정 로드: {settings_file}")

        if not isinstance(scene_data, dict):
            print(f"❌ 장면 설정 파일 내용이 JSON 객체가 아님. 기본값 반환.")
            return default_settings.copy()

        # 로드된 데이터와 기본값을 병합하여 최종 데이터 구성
        final_data = default_settings.copy()
        final_data.update(scene_data) # 로드된 값으로 덮어쓰기

        # 간단한 유효성 검사 및 조정
        try: final_data['temperature'] = max(0.0, min(2.0, float(final_data['temperature'])))
        except (ValueError, TypeError): final_data['temperature'] = constants.DEFAULT_TEMPERATURE
        # LENGTH_OPTIONS가 비어있는 경우 대비
        default_length = constants.LENGTH_OPTIONS[0] if constants.LENGTH_OPTIONS else "중간"
        if final_data.get('length') not in constants.LENGTH_OPTIONS: final_data['length'] = default_length

        # 토큰 정보 구조 및 타입 검사
        loaded_token_info = final_data.get(constants.TOKEN_INFO_KEY, {})
        if not isinstance(loaded_token_info, dict):
            final_data[constants.TOKEN_INFO_KEY] = {constants.INPUT_TOKEN_KEY: 0, constants.OUTPUT_TOKEN_KEY: 0}
        else:
            try: final_data[constants.TOKEN_INFO_KEY][constants.INPUT_TOKEN_KEY] = int(loaded_token_info.get(constants.INPUT_TOKEN_KEY, 0))
            except (ValueError, TypeError): final_data[constants.TOKEN_INFO_KEY][constants.INPUT_TOKEN_KEY] = 0
            try: final_data[constants.TOKEN_INFO_KEY][constants.OUTPUT_TOKEN_KEY] = int(loaded_token_info.get(constants.OUTPUT_TOKEN_KEY, 0))
            except (ValueError, TypeError): final_data[constants.TOKEN_INFO_KEY][constants.OUTPUT_TOKEN_KEY] = 0

        # 로드된 모델 유효성 검사는 AppCore에서 수행
        if 'selected_model' not in final_data:
            final_data['selected_model'] = "" # 모델 정보가 없으면 빈 문자열

        return final_data

    except json.JSONDecodeError as e:
        print(f"❌ 장면 설정 파일 JSON 디코딩 오류 ({settings_file}): {e}")
        messagebox.showerror("설정 파일 오류", f"장면 설정 파일({os.path.basename(settings_file)}) 형식 오류.", parent=None)
        return default_settings.copy()
    except Exception as e:
        print(f"❌ 장면 설정 로드 중 오류 ({settings_file}): {e}")
        traceback.print_exc()
        messagebox.showerror("장면 설정 로드 오류", f"파일({os.path.basename(settings_file)}) 로드 오류:\n{e}", parent=None)
        return default_settings.copy()

def save_scene_settings(chapter_dir, scene_number, settings_data):
    """특정 장면의 설정(XXX_settings.json) 저장."""
    settings_filename = constants.SCENE_SETTINGS_FILENAME_FORMAT.format(scene_number)
    settings_file = os.path.join(chapter_dir, settings_filename)
    # 저장할 데이터는 SCENE_SETTING_KEYS_TO_SAVE 에 정의된 키만 포함
    data_to_save = {}
    # LENGTH_OPTIONS가 비어있는 경우 대비
    default_length = constants.LENGTH_OPTIONS[0] if constants.LENGTH_OPTIONS else "중간"

    for key in constants.SCENE_SETTING_KEYS_TO_SAVE:
        if key == constants.TOKEN_INFO_KEY:
            token_info = settings_data.get(key, {})
            input_tokens = 0; output_tokens = 0
            if isinstance(token_info, dict):
                try: input_tokens = int(token_info.get(constants.INPUT_TOKEN_KEY, 0))
                except (ValueError, TypeError): pass
                try: output_tokens = int(token_info.get(constants.OUTPUT_TOKEN_KEY, 0))
                except (ValueError, TypeError): pass
            data_to_save[key] = {constants.INPUT_TOKEN_KEY: input_tokens, constants.OUTPUT_TOKEN_KEY: output_tokens}
        elif key in settings_data:
            # 간단한 타입/값 보정
            if key == 'temperature':
                try: data_to_save[key] = max(0.0, min(2.0, float(settings_data[key])))
                except (ValueError, TypeError): data_to_save[key] = constants.DEFAULT_TEMPERATURE
            elif key == 'length':
                data_to_save[key] = settings_data[key] if settings_data[key] in constants.LENGTH_OPTIONS else default_length
            else:
                data_to_save[key] = settings_data[key]
        else:
            # 기본값 처리 (저장 시 누락된 경우)
            if key == constants.SCENE_PLOT_KEY: data_to_save[key] = ""
            elif key == 'temperature': data_to_save[key] = constants.DEFAULT_TEMPERATURE
            elif key == 'length': data_to_save[key] = default_length
            elif key == 'selected_model': data_to_save[key] = ""
            # TOKEN_INFO_KEY는 위에서 처리되므로 else에서 제외됨
            # 정의되지 않은 다른 키는 저장 안 함 (None 대신 키 자체를 제외)

    try:
        os.makedirs(chapter_dir, exist_ok=True)
        with open(settings_file, 'w', encoding='utf-8') as f:
            json.dump(data_to_save, f, ensure_ascii=False, indent=4)
        print(f"✅ 장면 설정 저장: {settings_file}")
        return True
    except Exception as e:
        print(f"❌ 장면 설정 저장 중 오류 ({settings_file}): {e}")
        traceback.print_exc()
        messagebox.showerror("장면 설정 저장 오류", f"파일({os.path.basename(settings_file)}) 저장 오류:\n{e}", parent=None)
        return False

# --- 다음 챕터/장면 번호 계산 ---
def get_next_chapter_number(novel_dir):
    """특정 소설 폴더 내 다음 챕터 **폴더** 번호 계산."""
    max_num = 0
    if not os.path.isdir(novel_dir):
        print(f"ℹ️ 다음 챕터 번호 계산: 소설 경로 없음 '{novel_dir}'. 1번 반환.")
        return 1

    try:
        # Match 'Chapter_XXX' or 'Chapter_XXX_Title'
        pattern = re.compile(r"^Chapter_(\d+)(?:_.*)?$", re.IGNORECASE)
        with os.scandir(novel_dir) as entries:
            for entry in entries:
                if entry.is_dir(): # Check if it's a directory
                    match = pattern.match(entry.name)
                    if match and match.group(1).isdigit():
                        try:
                            num = int(match.group(1))
                            max_num = max(max_num, num)
                        except ValueError:
                             print(f"WARN: 폴더명 숫자 변환 오류 (무시): {entry.name}")
    except OSError as e:
         print(f"ERROR: 디렉토리 목록 읽기 오류 ({novel_dir}): {e}")
         # 오류 발생 시 현재 최대값 + 1 반환 시도
         return max_num + 1
    except Exception as e:
        print(f"ERROR: 다음 챕터 번호 계산 중 예상치 못한 오류 ({novel_dir}): {e}")
        traceback.print_exc()
        return max_num + 1

    return max_num + 1

def get_next_scene_number(chapter_dir):
    """특정 챕터 폴더 내 다음 장면(.txt) 번호 계산."""
    max_num = 0
    if not os.path.isdir(chapter_dir):
        print(f"ℹ️ 다음 장면 번호 계산: 챕터 경로 없음 '{chapter_dir}'. 1번 반환.")
        return 1

    try:
        pattern = re.compile(r"^(\d+)\.txt$", re.IGNORECASE) # Matches XXX.txt
        with os.scandir(chapter_dir) as entries:
            for entry in entries:
                if entry.is_file(): # Check if it's a file
                    match = pattern.match(entry.name)
                    if match and match.group(1).isdigit():
                        try:
                            num = int(match.group(1))
                            max_num = max(max_num, num)
                        except ValueError:
                             print(f"WARN: 장면 파일명 숫자 변환 오류 (무시): {entry.name}")
    except OSError as e:
         print(f"ERROR: 장면 파일 목록 읽기 오류 ({chapter_dir}): {e}")
         return max_num + 1
    except Exception as e:
        print(f"ERROR: 다음 장면 번호 계산 중 예상치 못한 오류 ({chapter_dir}): {e}")
        traceback.print_exc()
        return max_num + 1

    return max_num + 1

# --- 장면 내용 저장/로드 ---
def save_scene_content(chapter_dir, scene_number, content):
    """장면 내용(XXX.txt) 저장."""
    content_filename = constants.SCENE_FILENAME_FORMAT.format(scene_number)
    content_filepath = os.path.join(chapter_dir, content_filename)
    try:
        os.makedirs(chapter_dir, exist_ok=True)
        # content가 None일 경우 빈 문자열로 처리
        content_to_write = content if content is not None else ""
        with open(content_filepath, "w", encoding="utf-8", errors='replace') as f:
            f.write(content_to_write)
        print(f"✅ 장면 내용 저장: {content_filepath}")
        return content_filepath
    except OSError as e:
        print(f"❌ 장면 내용 저장 오류 (OSError, {content_filepath}): {e}")
        traceback.print_exc()
        messagebox.showerror("파일 저장 오류", f"장면 내용 파일 쓰기 오류:\n{e}", parent=None)
        return None
    except Exception as e:
        print(f"❌ 장면 내용 저장 중 오류 ({content_filepath}): {e}")
        traceback.print_exc()
        messagebox.showerror("파일 저장 오류", f"장면 내용 파일 쓰기 중 오류:\n{e}", parent=None)
        return None

def load_scene_content(chapter_dir, scene_number):
    """장면 내용(XXX.txt) 로드."""
    content_filename = constants.SCENE_FILENAME_FORMAT.format(scene_number)
    content_filepath = os.path.join(chapter_dir, content_filename)
    content = "" # 기본값 빈 문자열

    if not os.path.isfile(content_filepath):
         print(f"ℹ️ 장면 내용 파일 없음: {content_filepath}")
         return "" # 파일 없으면 빈 문자열 반환

    try:
        with open(content_filepath, "r", encoding="utf-8", errors='replace') as f:
            content = f.read()
        print(f"✅ 장면 내용 로드: {content_filepath}")
        return content
    except Exception as e:
        print(f"❌ 장면 내용 로드 중 오류 ({content_filepath}): {e}")
        traceback.print_exc()
        messagebox.showerror("파일 읽기 오류", f"장면 내용 파일 읽기 중 오류:\n{e}", parent=None)
        return "" # 오류 시 빈 문자열 반환

# --- 파일명 정리 ---
def sanitize_filename(name):
    """폴더/파일 이름 부적합 문자 제거/대체. 공백은 밑줄로."""
    if not isinstance(name, str): name = str(name)
    name = name.strip() # 선행/후행 공백 제거
    # 윈도우 예약어 및 잘못된 문자 처리 강화
    # Remove characters invalid for Windows filenames
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    # Replace spaces with underscores (optional, depends on preference)
    name = name.replace(" ", "_")
    # Remove characters invalid for filenames in general (broader than just Windows)
    # Keep Korean, alphanumeric, underscore, hyphen. Remove others.
    name = re.sub(r'[^\w\s가-힣\-]+', '', name, flags=re.UNICODE)
    # Windows reserved names check (case-insensitive)
    reserved = r'^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])($|\..*)'
    if re.match(reserved, name, re.IGNORECASE): name = f"_{name}_"
    # Remove trailing/leading dots, underscores, spaces that might remain or be introduced
    name = name.strip('. _')
    # Handle cases like '.', '..' or empty string after sanitization
    if not name or name == '.' or name == '..': name = "Untitled"
    # Max length (OS limits vary, 255 bytes is common, use a safer limit)
    max_len_bytes = 200 # Safer limit in bytes
    original_name = name
    while len(name.encode('utf-8', errors='ignore')) > max_len_bytes:
        # Truncate carefully to avoid breaking multi-byte characters mid-way
        encoded_name = name.encode('utf-8', errors='ignore')
        truncated_encoded_name = encoded_name[:max_len_bytes]
        # Try decoding back, ignore errors if the cut was bad
        name = truncated_encoded_name.decode('utf-8', errors='ignore')
        name = name.strip('. _') # Re-strip after truncation/decoding
        if not name: # If truncation/decode resulted in empty string
            name = "Untitled_truncated"
            break
    if name != original_name and len(original_name.encode('utf-8', errors='ignore')) > max_len_bytes:
         print(f"ℹ️ 파일/폴더 이름 최대 길이({max_len_bytes} bytes) 초과, 축약됨: {original_name} -> {name}")


    if not name: name = "Untitled" # Final fallback
    return name

# --- 폴더/파일 이름 변경 ---
def rename_chapter_folder(old_chapter_path, new_chapter_title_input):
    """챕터 폴더 이름 변경 (내부 파일명은 유지). 성공 시 (True, 메시지, 새 경로), 실패 시 (False, 메시지, None) 반환."""
    print(f"🔄 챕터 이름 변경 시도: '{os.path.basename(old_chapter_path)}' -> Title: '{new_chapter_title_input}'")
    if not isinstance(old_chapter_path, str) or not os.path.isdir(old_chapter_path):
        msg = f"오류: 원본 챕터 폴더 경로 유효하지 않음:\n'{old_chapter_path}'"
        print(f"❌ {msg}")
        return False, msg, None

    novel_dir = os.path.dirname(old_chapter_path)
    old_folder_name = os.path.basename(old_chapter_path)

    # Match 'Chapter_XXX' or 'Chapter_XXX_OldTitle'
    prefix_match = re.match(r"^(Chapter_\d+)", old_folder_name, re.IGNORECASE)
    if not prefix_match:
        msg = f"오류: 원본 폴더명 '{old_folder_name}'이 'Chapter_XXX' 구조 아님."
        print(f"❌ {msg}")
        return False, msg, None
    prefix = prefix_match.group(1) # e.g., "Chapter_001"

    sanitized_suffix = sanitize_filename(new_chapter_title_input)
    # Add underscore only if suffix exists and is not empty
    new_folder_name = f"{prefix}_{sanitized_suffix}" if sanitized_suffix else prefix
    new_chapter_path = os.path.join(novel_dir, new_folder_name)

    # Normalize paths for reliable comparison
    norm_old = os.path.normpath(old_chapter_path)
    norm_new = os.path.normpath(new_chapter_path)

    if norm_old == norm_new:
        msg = "챕터 이름 변경되지 않음 (동일 이름)."
        print(f"ℹ️ {msg}")
        return True, msg, old_chapter_path # 변경 없어도 성공으로 처리

    if os.path.exists(new_chapter_path):
        msg = f"오류: 대상 폴더 '{new_folder_name}' 이미 존재."
        print(f"❌ {msg}")
        return False, msg, None

    try:
        os.rename(old_chapter_path, new_chapter_path)
        msg = f"챕터 이름이 '{new_folder_name}'(으)로 변경됨."
        print(f"✅ {msg}")
        return True, msg, new_chapter_path
    except OSError as e:
        msg = f"오류: 챕터 폴더 이름 변경 실패 (OS 오류):\n'{old_folder_name}' -> '{new_folder_name}'\n{e}"
        print(f"❌ {msg}")
        traceback.print_exc()
        return False, msg, None
    except Exception as e:
        msg = f"오류: 챕터 폴더 이름 변경 중 예상 못한 오류:\n{e}"
        print(f"❌ {msg}")
        traceback.print_exc()
        return False, msg, None

def rename_novel_folder(old_novel_path, new_novel_name_input):
    """소설 폴더 이름 변경. 성공 시 (True, 메시지, 새 경로), 실패 시 (False, 메시지, None) 반환."""
    print(f"🔄 소설 이름 변경 시도: '{os.path.basename(old_novel_path)}' -> '{new_novel_name_input}'")
    if not isinstance(old_novel_path, str) or not os.path.isdir(old_novel_path):
        msg = f"오류: 원본 소설 폴더 경로 유효하지 않음:\n'{old_novel_path}'"
        print(f"❌ {msg}")
        return False, msg, None

    base_dir = os.path.dirname(old_novel_path)
    old_name = os.path.basename(old_novel_path)
    new_name = sanitize_filename(new_novel_name_input)

    if not new_name:
        msg = f"오류: 유효한 소설 이름 아님 (정리 후 빈 문자열, 입력: '{new_novel_name_input}')"
        print(f"❌ {msg}")
        return False, msg, None

    new_novel_path = os.path.join(base_dir, new_name)
    norm_old = os.path.normpath(old_novel_path)
    norm_new = os.path.normpath(new_novel_path)

    if norm_old == norm_new:
        msg = "소설 이름 변경되지 않음 (동일 이름)."
        print(f"ℹ️ {msg}")
        return True, msg, old_novel_path

    if os.path.exists(new_novel_path):
        msg = f"오류: 대상 소설 폴더 '{new_name}' 이미 존재."
        print(f"❌ {msg}")
        return False, msg, None

    try:
        os.rename(old_novel_path, new_novel_path)
        msg = f"소설 이름이 '{new_name}'(으)로 변경됨."
        print(f"✅ {msg}")
        return True, msg, new_novel_path
    except OSError as e:
        msg = f"오류: 소설 폴더 이름 변경 실패 (OS 오류):\n'{old_name}' -> '{new_name}'\n{e}"
        print(f"❌ {msg}")
        traceback.print_exc()
        return False, msg, None
    except Exception as e:
        msg = f"오류: 소설 이름 변경 중 예상 못한 오류:\n{e}"
        print(f"❌ {msg}")
        traceback.print_exc()
        return False, msg, None

# --- 폴더/파일 삭제 ---
def delete_chapter_folder(chapter_path):
    """챕터 폴더와 내부 모든 파일(장면, 설정 등) 삭제. 성공 시 (True, 메시지), 실패 시 (False, 메시지) 반환."""
    print(f"🗑️ 챕터 폴더 삭제 시도: '{chapter_path}'")
    if not isinstance(chapter_path, str):
        return False, f"오류: 잘못된 경로 타입: {type(chapter_path)}"

    if not os.path.exists(chapter_path):
        msg = f"정보: 삭제할 챕터 폴더 없음 (이미 삭제됨?): '{os.path.basename(chapter_path)}'"
        print(f"ℹ️ {msg}")
        return True, msg # 이미 없으면 성공으로 간주
    if not os.path.isdir(chapter_path):
        msg = f"오류: 삭제 대상이 폴더가 아님: '{os.path.basename(chapter_path)}'"
        print(f"❌ {msg}")
        return False, msg

    chapter_name = os.path.basename(chapter_path)
    try:
        shutil.rmtree(chapter_path)
        msg = f"'{chapter_name}' 챕터 폴더 삭제 완료."
        print(f"✅ {msg}")
        return True, msg
    except OSError as e:
        msg = f"오류: '{chapter_name}' 삭제 실패 (파일 사용 중/권한 문제?):\n{e}"
        print(f"❌ {msg}")
        traceback.print_exc()
        return False, msg
    except Exception as e:
        msg = f"오류: '{chapter_name}' 삭제 중 오류 발생:\n{e}"
        print(f"❌ {msg}")
        traceback.print_exc()
        return False, msg

def delete_novel_folder(novel_path):
    """소설 폴더와 하위 모든 챕터 폴더/파일 삭제. 성공 시 (True, 메시지), 실패 시 (False, 메시지) 반환."""
    print(f"🗑️ 소설 폴더 삭제 시도: '{novel_path}'")
    if not isinstance(novel_path, str):
        return False, f"오류: 잘못된 경로 타입: {type(novel_path)}"

    if not os.path.exists(novel_path):
        msg = f"정보: 삭제할 소설 폴더 없음 (이미 삭제됨?): '{os.path.basename(novel_path)}'"
        print(f"ℹ️ {msg}")
        return True, msg
    if not os.path.isdir(novel_path):
        msg = f"오류: 삭제 대상이 폴더가 아님: '{os.path.basename(novel_path)}'"
        print(f"❌ {msg}")
        return False, msg

    novel_name = os.path.basename(novel_path)
    try:
        shutil.rmtree(novel_path)
        msg = f"'{novel_name}' 소설 삭제 완료."
        print(f"✅ {msg}")
        return True, msg
    except OSError as e:
        msg = f"오류: '{novel_name}' 삭제 실패 (파일 사용 중/권한 문제?):\n{e}"
        print(f"❌ {msg}")
        traceback.print_exc()
        return False, msg
    except Exception as e:
        msg = f"오류: '{novel_name}' 삭제 중 오류 발생:\n{e}"
        print(f"❌ {msg}")
        traceback.print_exc()
        return False, msg

def delete_scene_files(chapter_dir, scene_number):
    """특정 장면의 텍스트 파일(XXX.txt)과 설정 파일(XXX_settings.json) 삭제."""
    if not isinstance(scene_number, int) or scene_number < 0: # 정수형 및 0 이상 확인
         msg = f"장면 파일 삭제 실패: 유효하지 않은 장면 번호 ({scene_number}, 타입: {type(scene_number)})."
         print(f"❌ {msg}")
         messagebox.showerror("삭제 오류", msg, parent=None)
         return False

    txt_filename = constants.SCENE_FILENAME_FORMAT.format(scene_number)
    settings_filename = constants.SCENE_SETTINGS_FILENAME_FORMAT.format(scene_number)
    txt_filepath = os.path.join(chapter_dir, txt_filename)
    settings_filepath = os.path.join(chapter_dir, settings_filename)
    deleted_txt = False
    deleted_settings = False
    error_occurred = False
    last_error_msg = ""

    print(f"🗑️ 장면 파일 삭제 시도: 챕터 '{os.path.basename(chapter_dir)}', 장면 번호 {scene_number}")

    # Delete text file
    try:
        if os.path.isfile(txt_filepath):
            os.remove(txt_filepath)
            print(f"✅ 장면 내용 파일 삭제 완료: {txt_filename}")
            deleted_txt = True
        else:
            print(f"ℹ️ 장면 내용 파일 없음 (삭제 건너뜀): {txt_filename}")
    except OSError as e:
        print(f"❌ 장면 내용 파일 삭제 실패 ({txt_filename}): {e}")
        error_occurred = True
        last_error_msg = f"장면 내용 파일({txt_filename}) 삭제 중 오류:\n{e}"
    except Exception as e:
        print(f"❌ 장면 내용 파일 삭제 중 예상 못한 오류 ({txt_filename}): {e}")
        traceback.print_exc()
        error_occurred = True
        last_error_msg = f"장면 내용 파일({txt_filename}) 삭제 중 예상 못한 오류:\n{e}"

    # Delete settings file
    try:
        if os.path.isfile(settings_filepath):
            os.remove(settings_filepath)
            print(f"✅ 장면 설정 파일 삭제 완료: {settings_filename}")
            deleted_settings = True
        else:
            print(f"ℹ️ 장면 설정 파일 없음 (삭제 건너뜀): {settings_filename}")
    except OSError as e:
        print(f"❌ 장면 설정 파일 삭제 실패 ({settings_filename}): {e}")
        error_occurred = True
        # 오류 메시지는 마지막 발생한 오류만 저장
        last_error_msg = f"장면 설정 파일({settings_filename}) 삭제 중 오류:\n{e}"
    except Exception as e:
        print(f"❌ 장면 설정 파일 삭제 중 예상 못한 오류 ({settings_filename}): {e}")
        traceback.print_exc()
        error_occurred = True
        last_error_msg = f"장면 설정 파일({settings_filename}) 삭제 중 예상 못한 오류:\n{e}"

    if error_occurred:
        # 오류 발생 시 사용자에게 알림 (마지막 오류 메시지 표시)
        messagebox.showerror("파일 삭제 오류", last_error_msg, parent=None)

    # 성공 조건: 오류가 발생하지 않았고, 최소한 하나의 파일이 삭제되었거나 원래 없었음.
    # 즉, 작업 후 두 파일이 모두 존재하지 않으면 성공으로 간주 (단, 오류가 없었어야 함).
    final_success = not error_occurred and \
                    (deleted_txt or not os.path.exists(txt_filepath)) and \
                    (deleted_settings or not os.path.exists(settings_filepath))

    if final_success and (deleted_txt or deleted_settings):
         print(f"✅ 장면 {scene_number} 파일 삭제 성공적으로 완료됨.")
    elif not error_occurred and not deleted_txt and not deleted_settings:
         print(f"ℹ️ 장면 {scene_number} 파일은 원래 존재하지 않았음 (삭제 작업 없음).")

    return final_success


# --- 모든 장면 내용 읽기 (요약용) ---
def get_all_chapter_scene_contents(novel_dir):
    """
    특정 소설 폴더 내의 모든 챕터 폴더에서 모든 장면(.txt) 파일을 읽어
    챕터 번호 및 장면 번호 순서대로 정렬된 하나의 문자열로 반환합니다.
    """
    all_contents_list = []
    # Match 'Chapter_XXX' or 'Chapter_XXX_Title'
    chapter_folder_pattern = re.compile(r"^Chapter_(\d+)(?:_.*)?$", re.IGNORECASE)
    scene_file_pattern = re.compile(r"^(\d+)\.txt$", re.IGNORECASE)
    found_chapters = [] # (chap_num, chapter_dir_path) 저장

    if not os.path.isdir(novel_dir):
        print(f"ERROR: 모든 내용 읽기 실패 - 소설 경로 없음: {novel_dir}")
        return ""

    try:
        # 1. Scan for CHAPTER DIRECTORIES
        with os.scandir(novel_dir) as novel_entries:
            for entry in novel_entries:
                if entry.is_dir():
                    match = chapter_folder_pattern.match(entry.name)
                    if match and match.group(1).isdigit():
                        try:
                            chap_num = int(match.group(1))
                            found_chapters.append((chap_num, entry.path))
                        except ValueError:
                            print(f"WARN: 챕터 폴더 숫자 변환 오류 (무시): {entry.name}")

        if not found_chapters:
            print(f"INFO: 요약을 위한 챕터 폴더 없음 ({os.path.basename(novel_dir)}).")
            return ""

        # 2. Sort chapters by chapter number
        found_chapters.sort(key=lambda x: x[0])

        # 3. Read scene content files from WITHIN each chapter directory
        total_scenes_read = 0
        for chap_num, chapter_path in found_chapters:
            found_scenes = [] # (scene_num, scene_file_path) 저장
            try:
                with os.scandir(chapter_path) as chapter_entries:
                    for entry in chapter_entries:
                        if entry.is_file():
                            match = scene_file_pattern.match(entry.name)
                            if match and match.group(1).isdigit():
                                try:
                                    scene_num = int(match.group(1))
                                    found_scenes.append((scene_num, entry.path))
                                except ValueError:
                                    print(f"WARN: 장면 파일 숫자 변환 오류 (무시): {entry.name} in {os.path.basename(chapter_path)}")
            except OSError as e:
                print(f"WARN: 챕터 {chap_num} ({os.path.basename(chapter_path)})의 장면 목록 읽기 실패: {e}")
                continue # 다음 챕터로 넘어감

            if not found_scenes:
                # 장면 파일이 없는 챕터는 건너뛰거나 표시할 수 있음
                print(f"INFO: 챕터 {chap_num} ({os.path.basename(chapter_path)})에 장면 파일 없음.")
                continue

            # Sort scenes by scene number
            found_scenes.sort(key=lambda x: x[0])

            # Append scene contents for this chapter
            chapter_combined_content = []
            scenes_read_in_chapter = 0
            for scene_num, scene_path in found_scenes:
                scene_content = ""
                try:
                    with open(scene_path, "r", encoding="utf-8", errors='replace') as f:
                        scene_content = f.read().strip()
                    # 비어있지 않은 내용만 추가하고 구분자 추가
                    if scene_content:
                         # 구분자 명확하게 추가
                         chapter_combined_content.append(f"--- 장면 {scene_num} 시작 ---\n{scene_content}\n--- 장면 {scene_num} 끝 ---")
                         scenes_read_in_chapter += 1
                    else:
                         print(f"INFO: 장면 파일 비어있음 ({os.path.basename(scene_path)}). 요약에서 제외.")
                except Exception as e:
                    print(f"WARN: 장면 파일 읽기 실패 ({os.path.basename(scene_path)}): {e}")
                    # 오류 발생 시에도 구분자 추가하여 알려줌
                    chapter_combined_content.append(f"--- 장면 {scene_num} (읽기 오류) ---")

            # Combine scenes for the current chapter and add to the main list if content exists
            if chapter_combined_content:
                 all_contents_list.append(f"### {chap_num}화 내용 시작 ###\n" + "\n\n".join(chapter_combined_content) + f"\n### {chap_num}화 내용 끝 ###")
                 total_scenes_read += scenes_read_in_chapter

        print(f"✅ 총 {len(found_chapters)}개 챕터, {total_scenes_read}개 장면의 내용 결합 완료 ({os.path.basename(novel_dir)}).")
        # 각 챕터 내용을 두 줄 개행으로 구분하여 합침
        return "\n\n".join(all_contents_list)

    except OSError as e:
        print(f"ERROR: 모든 내용 읽기 중 OSError ({novel_dir}): {e}")
        traceback.print_exc()
        return ""
    except Exception as e:
        print(f"ERROR: 모든 내용 읽기 중 예상치 못한 오류 ({novel_dir}): {e}")
        traceback.print_exc()
        return ""

# --- 이전 장면 내용 읽기 (특정 챕터 내) ---
def load_previous_scenes_in_chapter(chapter_dir, current_scene_number):
    """
    특정 챕터 폴더 내에서 주어진 current_scene_number '이전'의 모든 장면(.txt) 내용을 읽어
    장면 번호 순서대로 정렬된 하나의 문자열로 결합하여 반환합니다.
    current_scene_number = 1 이면 빈 문자열을 반환합니다.
    """
    if not isinstance(current_scene_number, int) or current_scene_number <= 1:
        print(f"ℹ️ 이전 장면 읽기 건너뜀 (현재 장면 번호: {current_scene_number}).")
        return "" # 첫 장면이거나 유효하지 않은 번호

    previous_contents_list = []
    scene_file_pattern = re.compile(r"^(\d+)\.txt$", re.IGNORECASE)
    found_scenes = [] # (scene_num, scene_file_path) 저장

    if not os.path.isdir(chapter_dir):
        print(f"ERROR: 이전 장면 읽기 실패 - 챕터 경로 없음: {chapter_dir}")
        return "" # 오류 시 빈 문자열 반환

    target_scene_num_exclusive = current_scene_number

    try:
        # 1. Scan for scene files matching the pattern
        with os.scandir(chapter_dir) as chapter_entries:
            for entry in chapter_entries:
                if entry.is_file():
                    match = scene_file_pattern.match(entry.name)
                    if match and match.group(1).isdigit():
                        try:
                            scene_num = int(match.group(1))
                            # 현재 생성할 장면 번호 '미만'인 장면만 포함
                            if 0 < scene_num < target_scene_num_exclusive:
                                found_scenes.append((scene_num, entry.path))
                        except ValueError:
                             print(f"WARN: 이전 장면 스캔 중 파일명 숫자 변환 오류 (무시): {entry.name}")

        if not found_scenes:
            print(f"INFO: 이전 장면 없음 ({os.path.basename(chapter_dir)}, 기준: {target_scene_num_exclusive}화 미만).")
            return ""

        # 2. Sort scenes by scene number
        found_scenes.sort(key=lambda x: x[0])

        # 3. Read and combine content
        scenes_read = 0
        for scene_num, scene_path in found_scenes:
            scene_content = ""
            try:
                with open(scene_path, "r", encoding="utf-8", errors='replace') as f:
                    scene_content = f.read().strip()
                # 비어있지 않은 내용만 추가하고 구분자 추가
                if scene_content:
                    # 구분자를 명확하게 추가 (예: 장면 번호 명시)
                    previous_contents_list.append(f"--- {scene_num} 장면 내용 시작 ---\n{scene_content}\n--- {scene_num} 장면 내용 끝 ---")
                    scenes_read += 1
                else:
                    print(f"INFO: 이전 장면 파일 비어있음 ({os.path.basename(scene_path)}). 내용에 포함 안 함.")
            except Exception as e:
                print(f"WARN: 이전 장면 파일 읽기 실패 ({os.path.basename(scene_path)}): {e}")
                previous_contents_list.append(f"--- {scene_num} 장면 (읽기 오류) ---") # 오류 발생 표시

        print(f"✅ 챕터 '{os.path.basename(chapter_dir)}'의 이전 {scenes_read}개 장면 내용 결합 완료.")
        # 여러 장면 내용을 명확한 구분자와 함께 하나의 문자열로 반환
        return "\n\n".join(previous_contents_list)

    except OSError as e:
        print(f"ERROR: 이전 장면 읽기 중 OSError ({chapter_dir}): {e}")
        traceback.print_exc()
        return "" # 오류 시 빈 문자열
    except Exception as e:
        print(f"ERROR: 이전 장면 읽기 중 예상치 못한 오류 ({chapter_dir}): {e}")
        traceback.print_exc()
        return "" # 오류 시 빈 문자열

# --- END OF FILE file_handler.py ---