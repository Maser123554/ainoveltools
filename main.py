# main.py
import tkinter as tk
from tkinter import simpledialog, messagebox
import os
import sys
import traceback
# import google.generativeai as genai # 직접 사용 안 함

# 프로젝트 모듈 임포트
import constants
import file_handler
import api_handler # 이제 여러 API 함수 포함
import app_core
import gui_manager
# gui_panels, gui_dialogs, utils 는 필요시 app_core나 gui_manager 에서 임포트

def select_startup_api_and_model(parent_root, last_saved_config, available_models_by_type):
    """
    프로그램 시작 시 사용할 API 유형 및 모델 결정.
    - last_saved_config 를 참조하여 마지막 사용값 제안.
    - 사용 가능한 모델이 없거나 저장된 값이 유효하지 않으면 기본값/첫번째 값 사용.
    - 현재는 사용자에게 직접 묻지 않고 결정된 값을 반환.
    """
    print("CORE: 시작 API 타입 및 모델 결정 중...")

    valid_api_types = [api for api, models in available_models_by_type.items() if models]
    if not valid_api_types:
        messagebox.showerror("모델 오류", "사용 가능한 API 모델이 없습니다.", parent=parent_root)
        return None, None

    # 1. API 타입 결정
    last_api_type = last_saved_config.get(constants.CONFIG_API_TYPE_KEY, constants.API_TYPE_GEMINI)
    startup_api_type = None
    if last_api_type in valid_api_types:
        startup_api_type = last_api_type
    else:
        startup_api_type = valid_api_types[0] # 첫 번째 유효한 API 사용
        print(f"INFO: 마지막 저장 API 타입 '{last_api_type}' 사용 불가. '{startup_api_type}'(으)로 시작.")

    # 2. 모델 결정 (선택된 API 타입 기준)
    api_models = available_models_by_type.get(startup_api_type, [])
    last_model = last_saved_config.get(constants.CONFIG_MODEL_KEY, "")
    startup_model = None

    if last_model and last_model in api_models:
        startup_model = last_model
    else:
        # 해당 API의 기본 모델 시도
        default_model = None
        if startup_api_type == constants.API_TYPE_GEMINI: default_model = constants.DEFAULT_GEMINI_MODEL
        elif startup_api_type == constants.API_TYPE_CLAUDE: default_model = constants.DEFAULT_CLAUDE_MODEL
        elif startup_api_type == constants.API_TYPE_GPT: default_model = constants.DEFAULT_GPT_MODEL

        if default_model and default_model in api_models:
            startup_model = default_model
        elif api_models: # 기본 모델도 없으면 목록의 첫 번째 모델
            startup_model = api_models[0]

        if startup_model: # Check if a model was actually assigned
            print(f"INFO: 마지막 저장 모델 '{last_model}' 사용 불가 또는 없음. '{startup_model}'(으)로 시작.")
        # Removed the print statement if startup_model is still None after checks

    if not startup_model:
        messagebox.showerror("모델 오류", f"'{startup_api_type}' API에 사용할 수 있는 모델이 없습니다.", parent=parent_root)
        return None, None

    print(f"CORE: 시작 API={startup_api_type}, 모델={startup_model}")
    return startup_api_type, startup_model


if __name__ == "__main__":
    print("--- AI 소설 생성기 시작 ---")

    # 0. 초기화 단계용 임시 루트 생성
    root_temp = tk.Tk()
    root_temp.withdraw()

    # 초기화 변수
    api_keys_ok = False
    apis_configured = {api: False for api in constants.SUPPORTED_API_TYPES}
    available_models = {api: [] for api in constants.SUPPORTED_API_TYPES}
    startup_api_type = constants.API_TYPE_GEMINI # 기본값
    startup_model = None
    last_config = {} # Initialize last_config

    try:
        # 0.5 Load config BEFORE checking keys to get the 'ask' preference
        print("0.5. 마지막 설정 로드 중 (키 확인 전)...")
        last_config = file_handler.load_config()
        print("✅ 마지막 설정 로드 완료.")

        # 1. API 키 확인 (이제 config 객체를 전달)
        print("1. API 키 확인 중...")
        api_keys_ok = file_handler.check_and_get_all_api_keys(last_config) # Pass config
        if not api_keys_ok:
            # API 키 확인 실패 시 메시지는 check_and_get_all_api_keys 내부에서 표시
            print("❌ API 키 설정 실패 (필수 키 없음 또는 사용자 취소). 프로그램을 종료합니다.")
            sys.exit(1)
        print("✅ API 키 확인 완료.")

        # 2. 모든 API 클라이언트 설정 시도
        print("2. API 설정 중...")
        gemini_ok, claude_ok, gpt_ok = api_handler.configure_apis()
        apis_configured[constants.API_TYPE_GEMINI] = gemini_ok
        apis_configured[constants.API_TYPE_CLAUDE] = claude_ok
        apis_configured[constants.API_TYPE_GPT] = gpt_ok

        if not any(apis_configured.values()):
            messagebox.showerror("API 설정 오류", "모든 API 설정에 실패했습니다.\nAPI 키 또는 라이브러리 설치를 확인하세요.")
            print("❌ 모든 API 설정 실패. 프로그램을 종료합니다.")
            sys.exit(1)
        print("✅ API 설정 시도 완료.")

        # 3. 사용 가능한 모델 목록 동적 로드 (설정된 API에 대해서만)
        print("3. 사용 가능한 모델 목록 로드 중...")
        try:
            available_models = api_handler.get_available_models()

            num_total_models = sum(len(m) for m in available_models.values())
            if num_total_models == 0:
                 raise ValueError("사용 가능한 모델을 찾을 수 없습니다 (모든 API 확인).")

            for api_type, models in available_models.items():
                if models: print(f"✅ {api_type.capitalize()} 모델 로드 완료 ({len(models)}개)")
                else: print(f"ℹ️ {api_type.capitalize()} 모델 없음 또는 로드 실패 (API 키/설정 확인)")

        except Exception as e:
            print(f"❌ 사용 가능한 모델 목록 로드 실패: {e}")
            traceback.print_exc()
            messagebox.showerror("API 오류", f"사용 가능한 모델 목록 로드 실패:\n{e}\nAPI 키, 네트워크 연결, 라이브러리 설치를 확인하세요.")
            sys.exit(1)
        print("✅ 모델 목록 로드 완료.")

        # 4. 마지막 설정 로드 (이미 위에서 로드함, 여기서는 재확인/사용)
        print("4. 마지막 설정 재확인...")
        # last_config = file_handler.load_config() # No need to load again

        # 5. 시작 API 타입 및 모델 결정 (사용자 선택 없이)
        print("5. 시작 API 타입 및 모델 결정...")
        startup_api_type, startup_model = select_startup_api_and_model(root_temp, last_config, available_models)
        if not startup_api_type or not startup_model:
            # 오류 메시지는 select_startup_api_and_model 내부에서 표시
            print("❌ 시작 API/모델 결정 실패. 프로그램을 종료합니다.")
            sys.exit(1)
        print(f"✅ 시작 API 타입 및 모델 결정됨: {startup_api_type} - {startup_model}")

    except Exception as init_err:
        print(f"❌ 초기화 중 심각한 오류 발생: {init_err}")
        traceback.print_exc()
        try: messagebox.showerror("초기화 오류", f"프로그램 시작 중 오류 발생:\n{init_err}")
        except tk.TclError: pass
        sys.exit(1)
    finally:
        # 6. 임시 루트 파괴
        if root_temp:
            try: root_temp.destroy(); print("ℹ️ 임시 루트 파괴됨.")
            except tk.TclError as e: print(f"WARN: 임시 루트 파괴 중 오류 (무시): {e}")

    # --- 메인 애플리케이션 실행 ---
    print("🚀 메인 GUI 애플리케이션 시작...")
    # 7. 메인 Tkinter 루트 생성
    root = tk.Tk()

    # 8. 아이콘 설정 (수정된 로직)
    try:
        if getattr(sys, 'frozen', False): # PyInstaller 등 번들 환경
            application_path = os.path.dirname(sys.executable)
        else: # 스크립트 실행 환경
            application_path = os.path.dirname(os.path.abspath(__file__))
        icon_path = os.path.join(application_path, constants.ICON_FILE)

        if os.path.exists(icon_path):
            if os.name == 'nt': # Windows
                 root.iconbitmap(default=icon_path)
                 print(f"✅ Windows 아이콘 설정됨: {icon_path}")
            else: # macOS, Linux 등 (PhotoImage 사용 시도)
                try:
                    img = tk.PhotoImage(file=icon_path)
                    root.iconphoto(True, img)
                    print(f"✅ PhotoImage 아이콘 설정됨: {icon_path}")
                except tk.TclError as e:
                    print(f"⚠️ PhotoImage 형식 아이콘 로드 실패 ({icon_path}): {e}")
        else:
             print(f"⚠️ 아이콘 파일 없음: {icon_path}")
    except Exception as e:
        print(f"⚠️ 아이콘 로드 중 오류 발생 ({constants.ICON_FILE}): {e}")
        traceback.print_exc()


    # 9. AppCore 및 GuiManager 인스턴스화 (수정된 인자 전달)
    core = app_core.AppCore(
        available_models_by_type=available_models,
        startup_api_type=startup_api_type,
        startup_model=startup_model
    )
    gui = gui_manager.GuiManager(root, core)
    core.set_gui_manager(gui) # AppCore에 GuiManager 참조 설정

    # 10. Tkinter 메인 루프 시작
    print("⏳ GUI 메인 루프 시작.")
    root.mainloop()

    print("--- AI 소설 생성기 종료 ---")