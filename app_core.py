# app_core.py
import os
import sys
import threading
import time
import traceback
import copy
import shutil
import re
import tkinter.messagebox as messagebox
import tkinter as tk

# 프로젝트 모듈 임포트
import constants
import file_handler
import api_handler # 이제 여러 API 함수 포함
import gui_dialogs

class AppCore:
    """애플리케이션 핵심 로직, 상태 관리, 백엔드 연동 클래스"""

    def __init__(self, available_models_by_type=None, startup_api_type=constants.API_TYPE_GEMINI, startup_model=None):
        print("CORE: AppCore 초기화 시작...")
        self.gui_manager = None

        # --- 상태 변수 ---
        self.config = file_handler.load_config()
        self.system_prompt = self.config.get('system_prompt', constants.DEFAULT_SYSTEM_PROMPT)
        self.output_bg = self.config.get('output_bg_color', constants.DEFAULT_OUTPUT_BG)
        self.output_fg = self.config.get('output_fg_color', constants.DEFAULT_OUTPUT_FG)

        # === API 및 모델 관리 (다중 API 지원) ===
        if available_models_by_type is None or not isinstance(available_models_by_type, dict):
            print("CORE WARN: 유효한 모델 목록 수신 실패. 빈 목록 사용.")
            self.available_models_by_type = {api: [] for api in constants.SUPPORTED_API_TYPES}
        else:
            self.available_models_by_type = available_models_by_type

        # API 타입 설정 (startup_api_type 유효성 검사)
        if startup_api_type in self.available_models_by_type and self.available_models_by_type[startup_api_type]:
            self.current_api_type = startup_api_type
        else:
            found_valid_api = False
            for api_type in constants.SUPPORTED_API_TYPES:
                if self.available_models_by_type.get(api_type):
                    self.current_api_type = api_type
                    found_valid_api = True
                    break
            if not found_valid_api:
                 print("CORE FATAL: 사용 가능한 API 모델이 하나도 없습니다!")
                 self.current_api_type = constants.API_TYPE_GEMINI # 임시 fallback
                 # messagebox.showerror("초기화 오류", "사용 가능한 API 모델이 없습니다.\n프로그램을 종료합니다.")
                 # sys.exit(1)
            print(f"CORE WARN: 시작 API 타입 '{startup_api_type}' 사용 불가. '{self.current_api_type}'(으)로 변경됨.")

        # 현재 API 타입에 해당하는 모델 목록 설정
        self.available_models = self.available_models_by_type.get(self.current_api_type, [])

        # 모델 선택 (startup_model 유효성 검사)
        if startup_model and startup_model in self.available_models:
            self.selected_model = startup_model
        elif self.available_models:
             # API 타입별 기본 모델 사용 시도
             default_model = None
             if self.current_api_type == constants.API_TYPE_GEMINI: default_model = constants.DEFAULT_GEMINI_MODEL
             elif self.current_api_type == constants.API_TYPE_CLAUDE: default_model = constants.DEFAULT_CLAUDE_MODEL
             elif self.current_api_type == constants.API_TYPE_GPT: default_model = constants.DEFAULT_GPT_MODEL

             if default_model and default_model in self.available_models:
                  self.selected_model = default_model
             else:
                  self.selected_model = self.available_models[0] # 목록의 첫 번째 모델 사용
             print(f"CORE INFO: 시작 모델 '{startup_model}' 사용 불가 또는 지정 안됨. '{self.selected_model}'(으)로 설정됨.")
        else:
            # 현재 API 타입에 모델이 없는 경우
            self.selected_model = None
            print(f"CORE WARN: 현재 API 타입 '{self.current_api_type}'에 사용 가능한 모델이 없습니다.")

        # --- API 타입별 요약 모델 관리 (수정됨) ---
        self.summary_models = {} # API 타입별 선택된 요약 모델 저장
        print("CORE INFO: API 타입별 요약 모델 초기화...")
        for api_type in constants.SUPPORTED_API_TYPES:
            api_models = self.available_models_by_type.get(api_type, [])
            config_key = f"{constants.SUMMARY_MODEL_KEY_PREFIX}{api_type}"
            # 각 API 타입별 기본 요약 모델 결정
            default_summary_model = None
            if api_type == constants.API_TYPE_GEMINI: default_summary_model = constants.DEFAULT_SUMMARY_MODEL_GEMINI
            elif api_type == constants.API_TYPE_CLAUDE: default_summary_model = constants.DEFAULT_SUMMARY_MODEL_CLAUDE
            elif api_type == constants.API_TYPE_GPT: default_summary_model = constants.DEFAULT_SUMMARY_MODEL_GPT
            # 저장된 값 로드, 없으면 해당 API 기본값 사용
            saved_model = self.config.get(config_key, default_summary_model)

            chosen_model = None
            if api_models: # 해당 API에 모델이 있는 경우에만 유효성 검사
                if saved_model and saved_model in api_models:
                    chosen_model = saved_model
                elif default_summary_model and default_summary_model in api_models:
                    chosen_model = default_summary_model
                    print(f"CORE INFO: ({api_type.capitalize()}) 저장된 요약 모델 '{saved_model}' 유효하지 않음. 기본값 '{chosen_model}' 사용.")
                else:
                    chosen_model = api_models[0] # 모델 목록의 첫 번째 모델 사용
                    print(f"CORE INFO: ({api_type.capitalize()}) 저장/기본 요약 모델 유효하지 않음. 첫 번째 모델 '{chosen_model}' 사용.")
            else: # 해당 API에 모델 자체가 없음
                chosen_model = None
                print(f"CORE INFO: ({api_type.capitalize()}) 사용 가능한 모델 없음. 요약 모델 비활성화.")

            self.summary_models[api_type] = chosen_model
            print(f"  - {api_type.capitalize()}: {self.summary_models[api_type]}")
        # --- 요약 모델 관리 끝 ---


        # 현재 활성 API 타입의 요약 모델 설정
        self.summary_model = self.summary_models.get(self.current_api_type)

        print(f"CORE INFO: 세션 API 타입: {self.current_api_type}")
        print(f"CORE INFO: 세션 창작 모델: {self.selected_model}")
        print(f"CORE INFO: 세션 요약 모델: {self.summary_model}") # 활성 요약 모델 출력
        # === API 및 모델 관리 끝 ===

        # 소설/챕터/장면 상태 (기존 코드 유지)
        self.current_novel_name = None
        self.current_novel_dir = None
        self.current_novel_settings = {}
        self.current_chapter_arc_dir = None
        self.current_loaded_chapter_arc_settings = {}
        self.current_scene_path = None
        self.current_loaded_scene_settings = {}

        # 편집 상태 및 작업 상태 플래그 (기존 코드 유지)
        self.output_text_modified = False
        self.novel_settings_modified_flag = False
        self.arc_settings_modified_flag = False
        self._novel_settings_after_id = None
        self._arc_settings_after_id = None

        self.is_generating = False # *** 이 플래그 사용 ***
        self.is_summarizing = False # *** 이 플래그 사용 ***
        self.start_time = 0
        self.timer_after_id = None

        # 재생성 컨텍스트 (기존 코드 유지)
        self.last_generation_settings_snapshot = None
        self.last_generation_previous_content = None

        # Check if self can be printed here
        try:
            print(f"CORE: AppCore __init__ 완료. 객체 ID: {id(self)}")
        except Exception as e:
            print(f"CORE: Error printing self ID in __init__: {e}")

        print("CORE: AppCore 초기화 완료.")

    def set_gui_manager(self, gui_manager):
        """GuiManager 참조 설정 및 초기 UI 상태 업데이트"""
        self.gui_manager = gui_manager
        print("CORE: GuiManager 참조 설정됨.")
        # 초기 데이터 로딩 및 UI 업데이트
        self.update_window_title()
        # 초기 상태 업데이트 (아무것도 로드되지 않음)
        self.update_ui_status_and_state("애플리케이션 준비 완료. 새 소설을 시작하거나 기존 항목을 선택하세요.",
                                        generating=False, novel_loaded=False, chapter_loaded=False, scene_loaded=False)
        # 설정 패널에 초기 모델 정보 채우기
        if self.gui_manager and self.gui_manager.settings_panel:
             self.gui_manager.settings_panel.populate_widgets({}, {}, {}) # 초기 빈 데이터로 호출

        # 트리뷰 새로고침
        self.refresh_treeview_data()

    # --- API 및 모델 관련 핸들러 ---
    def handle_api_type_change(self, new_api_type):
        """GUI에서 API 타입 변경 시 호출됨"""
        if self.check_busy_and_warn(): return # 작업 중이면 변경 불가
        if new_api_type == self.current_api_type: return # 변경 없음
        if new_api_type not in constants.SUPPORTED_API_TYPES:
            print(f"CORE WARN: 지원되지 않는 API 타입 변경 시도: {new_api_type}")
            return
        if not self.available_models_by_type.get(new_api_type):
             print(f"CORE WARN: '{new_api_type}' 타입에 사용 가능한 모델이 없어 변경 불가.")
             # GUI 콤보박스를 원래대로 되돌리는 로직 필요 (SettingsPanel에서 처리?)
             if self.gui_manager and self.gui_manager.settings_panel:
                  api_combo = self.gui_manager.settings_panel.widgets.get('api_type_combobox')
                  if api_combo: api_combo.set(self.current_api_type.capitalize())
             return

        print(f"CORE: API 타입 변경: {self.current_api_type} -> {new_api_type}")
        self.current_api_type = new_api_type
        self.available_models = self.available_models_by_type.get(new_api_type, [])

        # --- 활성 요약 모델 업데이트 (추가된 부분) ---
        self.summary_model = self.summary_models.get(new_api_type)
        print(f"CORE INFO: 활성 요약 모델 변경됨 -> {self.summary_model} (for {new_api_type})")
        # --- 요약 모델 업데이트 끝 ---

        # 현재 선택된 창작 모델이 새 API 타입에 유효한지 확인, 아니면 기본값/첫번째로 변경
        if not self.selected_model or self.selected_model not in self.available_models:
            old_model = self.selected_model
            # 새 API 타입의 기본 모델 시도
            new_default_model = None
            if new_api_type == constants.API_TYPE_GEMINI: new_default_model = constants.DEFAULT_GEMINI_MODEL
            elif new_api_type == constants.API_TYPE_CLAUDE: new_default_model = constants.DEFAULT_CLAUDE_MODEL
            elif new_api_type == constants.API_TYPE_GPT: new_default_model = constants.DEFAULT_GPT_MODEL

            if new_default_model and new_default_model in self.available_models:
                 self.selected_model = new_default_model
            elif self.available_models:
                 self.selected_model = self.available_models[0] # 첫 번째 모델
            else:
                 self.selected_model = None # 모델 없음

            print(f"CORE: API 타입 변경으로 창작 모델 자동 변경됨: {old_model} -> {self.selected_model}")

        # 설정 저장
        self.config[constants.CONFIG_API_TYPE_KEY] = self.current_api_type
        if self.selected_model: self.config[constants.CONFIG_MODEL_KEY] = self.selected_model
        file_handler.save_config(self.config)

        # UI 업데이트 (창 제목, 모델 콤보 등)
        self.update_window_title()
        self.update_ui_state() # 버튼 등 상태 업데이트
        # SettingsPanel의 모델 콤보박스는 _update_models_for_api_type에서 업데이트됨 (handle_api_type_change 호출 후 실행됨)


    def handle_model_change(self, new_model):
        """GUI에서 창작 모델 변경 시 호출됨"""
        if self.check_busy_and_warn(): return # 작업 중이면 변경 불가
        if new_model == self.selected_model: return
        # 선택된 모델이 현재 API 타입의 사용 가능 목록에 있는지 확인
        if new_model and new_model in self.available_models:
            print(f"CORE: 창작 모델 변경됨: {self.selected_model} -> {new_model}")
            self.selected_model = new_model
            self.config[constants.CONFIG_MODEL_KEY] = new_model
            if not file_handler.save_config(self.config):
                 self.gui_manager.show_message("warning", "저장 경고", "창작 모델 설정을 config.json에 저장 실패.")
            self.update_window_title()
            # 모델 변경도 저장 대상 변경으로 간주 (현재 장면에 스냅샷 저장 필요)
            if self.current_scene_path:
                 self._trigger_chapter_settings_modified_in_gui() # GUI 통해 플래그 설정 요청
        elif new_model is None: # 모델 목록이 비어서 None으로 설정될 때
             print(f"CORE: 창작 모델 없음으로 설정됨.")
             self.selected_model = None
             self.config[constants.CONFIG_MODEL_KEY] = None
             file_handler.save_config(self.config)
             self.update_window_title()
        else:
            print(f"CORE WARN: 변경 시도된 모델 '{new_model}'은(는) 현재 API 타입 '{self.current_api_type}'에서 사용 불가.")
            # GUI 콤보박스를 현재 선택된 모델로 되돌림 (SettingsPanel에서 처리)
            if self.gui_manager and self.gui_manager.settings_panel:
                 model_combo = self.gui_manager.settings_panel.widgets.get('model_combobox')
                 if model_combo: model_combo.set(self.selected_model)


    def get_models_by_api_type(self, api_type):
        """특정 API 타입의 모델 목록 반환"""
        return self.available_models_by_type.get(api_type, [])

    # --- GUI 업데이트 요청 메소드 ---
    def update_window_title(self):
        if self.gui_manager:
            # API 타입 표시 추가
            api_display = self.current_api_type.capitalize()
            model_display = self.selected_model or "모델 없음"
            title = f"{constants.APP_NAME} ({api_display}: {model_display})" # API 타입과 모델 표시

            if self.current_novel_name:
                title += f" - [{self.current_novel_name}]"
                if self.current_chapter_arc_dir:
                    ch_str = self._get_chapter_number_str_from_folder(self.current_chapter_arc_dir)
                    title += f" - {ch_str}"
                    if self.current_scene_path:
                        scene_num = self._get_scene_number_from_path(self.current_scene_path)
                        if scene_num >= 0: title += f" - {scene_num:03d} 장면"
            self.gui_manager.set_window_title(title)

    def update_status_bar(self, message):
        if self.gui_manager:
            self.gui_manager.update_status_bar(message)

    def update_ui_state(self, generating=None, novel_loaded=None, chapter_loaded=None, scene_loaded=None):
         if self.gui_manager:
            is_gen = generating if generating is not None else self.is_generating
            is_sum = self.is_summarizing
            is_novel = novel_loaded if novel_loaded is not None else bool(self.current_novel_dir)
            is_chap = chapter_loaded if chapter_loaded is not None else bool(self.current_chapter_arc_dir)
            is_scene = scene_loaded if scene_loaded is not None else bool(self.current_scene_path)
            is_busy = is_gen or is_sum # 생성 또는 요약 중이면 Busy

            # GuiManager에 모든 상태 전달
            self.gui_manager.set_ui_state(is_busy, is_novel, is_chap, is_scene)

    def update_ui_status_and_state(self, status_msg, generating, novel_loaded, chapter_loaded, scene_loaded):
        """상태 표시줄과 UI 상태 동시 업데이트"""
        self.update_status_bar(status_msg)
        self.update_ui_state(generating, novel_loaded, chapter_loaded, scene_loaded)

    def clear_output_panel(self):
        if self.gui_manager and self.gui_manager.output_panel:
            self.gui_manager.output_panel.clear_content()
        self.output_text_modified = False
        self.update_ui_state() # 상태 업데이트 필요

    def clear_chapter_arc_and_scene_fields(self):
        if self.gui_manager and self.gui_manager.settings_panel:
            self.gui_manager.settings_panel.clear_chapter_arc_notes_field()
            self.gui_manager.settings_panel.clear_scene_settings_fields()
        self.arc_settings_modified_flag = False
        if self._arc_settings_after_id and self.gui_manager and self.gui_manager.root:
            try: self.gui_manager.root.after_cancel(self._arc_settings_after_id)
            except Exception: pass
            self._arc_settings_after_id = None
        # SettingsPanel의 chapter_settings_modified_flag는 clear_* 에서 리셋됨

    def clear_settings_panel_novel_fields(self):
        if self.gui_manager and self.gui_manager.settings_panel:
            self.gui_manager.settings_panel.clear_novel_settings()
        self.current_novel_settings = {}
        self.novel_settings_modified_flag = False
        if self._novel_settings_after_id and self.gui_manager and self.gui_manager.root:
            try: self.gui_manager.root.after_cancel(self._novel_settings_after_id)
            except Exception: pass
            self._novel_settings_after_id = None

    def populate_settings_panel(self, novel_settings=None, chapter_arc_settings=None, scene_settings=None):
        if self.gui_manager and self.gui_manager.settings_panel:
            # None 대신 빈 딕셔너리 전달하여 get() 오류 방지
            self.gui_manager.settings_panel.populate_widgets(
                novel_settings if novel_settings is not None else {},
                chapter_arc_settings if chapter_arc_settings is not None else {},
                scene_settings if scene_settings is not None else {}
            )
        # Update AppCore's internal state copies
        if novel_settings is not None: self.current_novel_settings = novel_settings.copy()
        if chapter_arc_settings is not None: self.current_loaded_chapter_arc_settings = chapter_arc_settings.copy()
        if scene_settings is not None: self.current_loaded_scene_settings = scene_settings.copy()

        # Reset modification flags after populating
        self.novel_settings_modified_flag = False
        self.arc_settings_modified_flag = False
        self.output_text_modified = False
        if self.gui_manager and self.gui_manager.settings_panel:
             self.gui_manager.settings_panel.reset_novel_modified_flag()
             self.gui_manager.settings_panel.reset_chapter_modified_flag()
        if self.gui_manager and self.gui_manager.output_panel:
             self.gui_manager.output_panel.reset_modified_flag()
        # UI 상태 업데이트 필요
        self.update_ui_state()

    def display_output_content(self, text, token_info=None):
        if self.gui_manager and self.gui_manager.output_panel:
            self.gui_manager.output_panel.display_content(text)
            self.gui_manager.output_panel.update_token_display(token_info)
        self.output_text_modified = False
        if self.gui_manager and self.gui_manager.output_panel:
            self.gui_manager.output_panel.reset_modified_flag()
        self.update_ui_state() # 상태 업데이트 필요

    def refresh_treeview_data(self):
        if self.gui_manager and self.gui_manager.treeview_panel:
            self.gui_manager.treeview_panel.refresh_tree()
            print("CORE: 트리뷰 새로고침 요청됨.")

    def select_treeview_item(self, item_id):
        if self.gui_manager and self.gui_manager.treeview_panel:
            self.gui_manager.treeview_panel.select_item(item_id)

    # --- 핵심 로직 및 이벤트 핸들러 ---
    def handle_quit_request(self):
        """애플리케이션 종료 요청 처리"""
        print("CORE: 종료 요청 수신.")
        if self.check_busy_and_warn(): return # Check before proceeding
        if self._check_and_handle_unsaved_changes("프로그램 종료"):
            print("CORE: 변경사항 처리 완료. 프로그램 종료.")
            if self.gui_manager and self.gui_manager.root:
                self.gui_manager.root.destroy()
            else:
                sys.exit(0)
        else:
            print("CORE: 사용자가 종료 취소.")

    def handle_new_novel_request(self):
        """'새 소설' 버튼 클릭 처리"""
        print("CORE: 새 소설 요청 처리 시작...")
        action_name = "새 소설 시작"
        if self.check_busy_and_warn(): return # Check before proceeding
        if not self._check_and_handle_unsaved_changes(action_name): return

        dialog_result = gui_dialogs.show_new_novel_dialog(self.gui_manager.root)
        if dialog_result is None: print(f"CORE: {action_name} 취소됨 (Dialog)."); return

        name_raw = dialog_result["name"]
        initial_settings_text = dialog_result["settings"]
        novel_setting_key = constants.NOVEL_MAIN_SETTINGS_KEY

        novel_name = file_handler.sanitize_filename(name_raw)
        if not novel_name:
             self.gui_manager.show_message("error", "입력 오류", f"유효하지 않은 소설 이름입니다: '{name_raw}'")
             return
        novel_dir = os.path.join(constants.BASE_SAVE_DIR, novel_name)
        if os.path.exists(novel_dir):
             self.gui_manager.show_message("error", "생성 오류", f"같은 이름의 소설 ('{novel_name}')이 이미 존재합니다.")
             return

        initial_novel_settings = {novel_setting_key: initial_settings_text}
        self.clear_all_ui_state() # UI 초기화

        try:
            os.makedirs(novel_dir)
            print(f"CORE: 새 소설 폴더 생성 성공: {novel_dir}")
        except OSError as e:
            self.gui_manager.show_message("error", "폴더 생성 오류", f"소설 폴더 생성 중 오류 발생:\n{e}")
            return

        if not file_handler.save_novel_settings(novel_dir, initial_novel_settings):
            self.gui_manager.show_message("error", "설정 저장 오류", "초기 소설 설정 저장에 실패했습니다.")
            try: shutil.rmtree(novel_dir) # 생성된 폴더 정리 시도
            except Exception as rm_err: print(f"CORE WARN: 폴더 정리 실패: {rm_err}")
            self.clear_all_ui_state() # 실패 시 UI 완전 초기화
            return

        # 상태 업데이트
        self.current_novel_name = novel_name
        self.current_novel_dir = novel_dir
        self.current_novel_settings = initial_novel_settings.copy()
        self.current_chapter_arc_dir = None
        self.current_scene_path = None

        self.refresh_treeview_data()
        self.select_treeview_item(novel_name) # 트리뷰에서 새 소설 선택
        self.populate_settings_panel(initial_novel_settings, None, None) # 설정 패널 업데이트
        self.update_window_title()
        self.update_ui_status_and_state(f"✨ 새 소설 '{novel_name}' 생성됨. '새 챕터 폴더'로 시작하세요.",
                                        generating=False, novel_loaded=True, chapter_loaded=False, scene_loaded=False)
        print(f"CORE: 새 소설 '{novel_name}' 생성 완료.")

    def handle_new_chapter_folder_request(self):
        """'새 챕터 폴더' 버튼 클릭 처리"""
        print("CORE: 새 챕터 폴더 요청 처리 시작...")
        action = "새 챕터 폴더 생성"
        if self.check_busy_and_warn(): return # Check before proceeding
        if not self.current_novel_dir or not self.current_novel_name:
            self.gui_manager.show_message("error", "오류", f"{action}을 진행할 소설이 로드되지 않았습니다.")
            return
        if not self._check_and_handle_unsaved_changes(action): return

        dialog_result = gui_dialogs.show_new_chapter_folder_dialog(self.gui_manager.root, self.current_novel_name)
        if dialog_result is None: print(f"CORE: {action} 취소됨 (Dialog)."); return

        chapter_title_from_dialog = dialog_result["title"]
        arc_notes_from_dialog = dialog_result["arc_notes"]
        arc_notes_key = constants.CHAPTER_ARC_NOTES_KEY

        # --- 폴더 생성 준비 ---
        try:
            next_chapter_num = file_handler.get_next_chapter_number(self.current_novel_dir)
            sanitized_title = file_handler.sanitize_filename(chapter_title_from_dialog)
            chapter_folder_name = f"Chapter_{next_chapter_num:03d}"
            if sanitized_title: chapter_folder_name += f"_{sanitized_title}"

            new_chapter_arc_dir = os.path.join(self.current_novel_dir, chapter_folder_name)

            if os.path.exists(new_chapter_arc_dir):
                self.gui_manager.show_message("error", "오류", f"챕터 폴더 '{chapter_folder_name}'가 이미 존재합니다.")
                return
        except Exception as e:
            self.gui_manager.show_message("error", "오류", f"다음 챕터 번호/이름 확인 중 오류 발생:\n{e}")
            return

        # --- 생성 진행 ---
        # 현재 로드된 챕터/장면 정보 클리어 (폴더만 생성)
        self.clear_output_panel()
        self.clear_chapter_arc_and_scene_fields()
        self.current_chapter_arc_dir = None
        self.current_scene_path = None
        self.current_loaded_chapter_arc_settings = {}
        self.current_loaded_scene_settings = {}

        try:
            os.makedirs(new_chapter_arc_dir)
            print(f"CORE: 새 챕터 폴더 생성 성공: {new_chapter_arc_dir}")
        except OSError as e:
            self.gui_manager.show_message("error", "폴더 생성 오류", f"챕터 폴더 생성에 실패했습니다:\n{e}")
            return

        # chapter_settings.json 저장
        initial_arc_settings = {arc_notes_key: arc_notes_from_dialog}
        if not file_handler.save_chapter_settings(new_chapter_arc_dir, initial_arc_settings):
             self.gui_manager.show_message("error", "설정 저장 오류", "초기 챕터 아크 노트 저장 실패.")
             # 폴더는 유지하고 사용자에게 알림

        # 상태 업데이트 (소설은 유지, 챕터/장면은 없음)
        self.current_chapter_arc_dir = new_chapter_arc_dir # 폴더 경로만 저장
        self.current_loaded_chapter_arc_settings = initial_arc_settings.copy() # 로드된 상태로 설정
        self.current_scene_path = None

        self.refresh_treeview_data()
        self.select_treeview_item(new_chapter_arc_dir) # 트리뷰에서 새 챕터 폴더 선택
        # Populate settings panel with novel and newly created arc settings
        self.populate_settings_panel(self.current_novel_settings, initial_arc_settings, None)
        self.update_window_title()
        ch_str = self._get_chapter_number_str_from_folder(new_chapter_arc_dir)
        self.update_ui_status_and_state(f"📁 [{self.current_novel_name}] {ch_str} 폴더 생성됨. '새 장면'으로 1장면 생성을 시작하세요.",
                                        generating=False, novel_loaded=True, chapter_loaded=True, scene_loaded=False)
        print(f"CORE: 새 챕터 폴더 '{chapter_folder_name}' 생성 완료.")

    def handle_new_scene_request(self):
        """'새 장면' 버튼 클릭 처리 (이어쓰기 역할)"""
        print("CORE: 새 장면 요청 처리 시작...")
        action = "새 장면 생성"
        if self.check_busy_and_warn(): return
        if not self.current_chapter_arc_dir:
            self.gui_manager.show_message("error", "오류", f"{action}을 진행할 챕터 폴더가 로드되지 않았습니다.")
            return
        if not os.path.isdir(self.current_chapter_arc_dir):
             self.gui_manager.show_message("error", "오류", f"현재 로드된 챕터 폴더를 찾을 수 없습니다:\n{self.current_chapter_arc_dir}")
             self.clear_all_ui_state(); self.refresh_treeview_data(); return
        if not self._check_and_handle_unsaved_changes(action): return

        if not self.selected_model:
             self.gui_manager.show_message("error", "모델 오류", f"현재 API 타입({self.current_api_type.capitalize()})에 사용할 창작 모델이 선택되지 않았습니다.")
             return

        current_gui_plot = self.gui_manager.settings_panel.get_scene_plot() if self.gui_manager.settings_panel else ""
        scene_plot_from_dialog = gui_dialogs.show_scene_plot_dialog(self.gui_manager.root, current_plot=current_gui_plot, title="🎬 새 장면에 사용할 플롯 입력")
        if scene_plot_from_dialog is None: print(f"CORE: {action} 취소됨 (Dialog)."); return
        if self.gui_manager.settings_panel: self.gui_manager.settings_panel.set_scene_plot(scene_plot_from_dialog)

        try:
            target_chapter_dir = self.current_chapter_arc_dir
            next_scene_num = file_handler.get_next_scene_number(target_chapter_dir)
        except Exception as e:
            self.gui_manager.show_message("error", "오류", f"다음 장면 번호 확인 중 오류 발생:\n{e}")
            return

        # --- 이전 장면 내용 로드 (수정된 부분) ---
        # 이전 장면(들) 내용을 새로 만든 함수로 로드 (next_scene_num 미만까지)
        print(f"CORE: 이전 내용 로드 중 (챕터: '{os.path.basename(target_chapter_dir)}', 기준: {next_scene_num}화)")
        previous_content_str = file_handler.load_previous_scenes_in_chapter(target_chapter_dir, next_scene_num)
        # load_previous_scenes_in_chapter는 오류 시 빈 문자열("") 반환하므로 None 체크 불필요
        # if previous_content_str is None:
        #      self.gui_manager.show_message("error", "오류", "이전 장면 내용을 로드하는 데 실패했습니다.\n새 장면 생성을 중단합니다.")
        #      return

        self.clear_output_panel()
        self.current_scene_path = None
        self.current_loaded_scene_settings = {}

        novel_settings_for_gen = self.current_novel_settings
        arc_notes_for_gen = self.current_loaded_chapter_arc_settings
        gui_scene_gen_settings = self._get_settings_from_gui(read_novel_settings=False, read_chapter_arc_settings=False, read_scene_settings=True)
        gui_scene_gen_settings[constants.SCENE_PLOT_KEY] = scene_plot_from_dialog

        self._start_generation_thread_internal(
            api_type=self.current_api_type,
            novel_settings=novel_settings_for_gen,
            chapter_arc_notes=arc_notes_for_gen,
            scene_specific_settings=gui_scene_gen_settings,
            previous_scene_content=previous_content_str, # 결합된 내용 전달
            target_chapter_arc_dir=target_chapter_dir,
            target_scene_number=next_scene_num,
            is_new_scene=True
        )

    def handle_regenerate_request(self):
        """'장면 재생성' 버튼 클릭 처리"""
        print("CORE: 장면 재생성 요청 처리 시작...")
        action = "장면 재생성"
        if self.check_busy_and_warn(): return
        target_scene_path = self.current_scene_path
        if not target_scene_path or not os.path.isfile(target_scene_path):
            self.gui_manager.show_message("error", "오류", f"{action}할 장면이 로드되지 않았거나 파일을 찾을 수 없습니다.")
            self.clear_all_ui_state(); self.refresh_treeview_data(); return
        target_chapter_dir = os.path.dirname(target_scene_path)
        target_scene_num = self._get_scene_number_from_path(target_scene_path)
        if target_scene_num < 0:
             self.gui_manager.show_message("error", "오류", f"재생성할 장면 번호 확인 실패: {target_scene_path}")
             return

        if not self._check_and_handle_unsaved_changes(action): return

        if not self.selected_model:
             self.gui_manager.show_message("error", "모델 오류", f"현재 API 타입({self.current_api_type.capitalize()})에 사용할 창작 모델이 선택되지 않았습니다.")
             return

        current_gui_plot = self.gui_manager.settings_panel.get_scene_plot() if self.gui_manager.settings_panel else ""
        loaded_plot = self.current_loaded_scene_settings.get(constants.SCENE_PLOT_KEY, "")
        initial_plot_for_dialog = loaded_plot if loaded_plot else current_gui_plot

        scene_plot_from_dialog = gui_dialogs.show_scene_plot_dialog(self.gui_manager.root, current_plot=initial_plot_for_dialog, title="🔄 재생성할 장면 플롯 확인/수정")
        if scene_plot_from_dialog is None: print(f"CORE: {action} 취소됨 (Dialog)."); return
        if self.gui_manager.settings_panel: self.gui_manager.settings_panel.set_scene_plot(scene_plot_from_dialog)

        scene_display = os.path.basename(target_scene_path)
        ch_str = self._get_chapter_number_str_from_folder(target_chapter_dir)
        if not self.gui_manager.ask_yes_no("재생성 확인", f"현재 장면 '{ch_str} - {scene_display}' 내용을 덮어씁니다.\n기존 내용과 설정 스냅샷이 변경됩니다. 계속하시겠습니까?"):
            print("CORE: 재생성 취소됨 (확인 창).")
            return

        # --- 이전 장면 내용 로드 (수정된 부분) ---
        # 재생성할 장면 '이전'까지의 모든 내용을 로드 (target_scene_num 미만까지)
        print(f"CORE: 이전 내용 로드 중 (챕터: '{os.path.basename(target_chapter_dir)}', 기준: {target_scene_num}화)")
        prev_content_for_regen = file_handler.load_previous_scenes_in_chapter(target_chapter_dir, target_scene_num)
        # if prev_content_for_regen is None: # 오류 시 빈 문자열 반환되므로 None 체크 불필요
        #      self.gui_manager.show_message("error", "오류", f"'{scene_display}'의 이전 장면 내용 로드 실패. 재생성 불가.")
        #      return

        novel_settings = self.current_novel_settings
        arc_notes = self.current_loaded_chapter_arc_settings
        gui_scene_gen_settings = self._get_settings_from_gui(read_novel_settings=False, read_chapter_arc_settings=False, read_scene_settings=True)
        gui_scene_gen_settings[constants.SCENE_PLOT_KEY] = scene_plot_from_dialog

        self._start_generation_thread_internal(
            api_type=self.current_api_type,
            novel_settings=novel_settings,
            chapter_arc_notes=arc_notes,
            scene_specific_settings=gui_scene_gen_settings,
            previous_scene_content=prev_content_for_regen, # 결합된 내용 전달
            target_chapter_arc_dir=target_chapter_dir,
            target_scene_number=target_scene_num,
            is_new_scene=False
        )

    def handle_save_changes_request(self):
        """'변경 저장' 버튼 클릭 처리"""
        print("CORE: 변경 저장 요청 처리 시작...")
        if self.check_busy_and_warn(): return # Check before proceeding

        # Check modification flags
        unsaved_output = self.output_text_modified
        unsaved_novel = self.novel_settings_modified_flag
        unsaved_arc = self.arc_settings_modified_flag
        # Get combined chapter/scene settings flag from SettingsPanel
        unsaved_chapter_scene_opts = self.gui_manager.settings_panel.chapter_settings_modified_flag if self.gui_manager.settings_panel else False

        if not unsaved_output and not unsaved_novel and not unsaved_arc and not unsaved_chapter_scene_opts:
            print("CORE INFO: 저장할 변경 사항 없음.")
            self.update_status_bar("저장할 변경 사항이 없습니다.")
            # 상태 업데이트를 통해 버튼 비활성화
            self.update_ui_state()
            return

        print(f"CORE: 변경 내용 저장 시도...")
        saved_something = False
        error_occurred = False

        # 1. 소설 설정 저장 (필요 시)
        if unsaved_novel and self.current_novel_dir:
            print("CORE: 소설 설정 변경 감지됨. 저장 시도...")
            if self._save_current_novel_settings():
                 saved_something = True
            else:
                 error_occurred = True

        # 2. 챕터 아크 노트 저장 (필요 시)
        # unsaved_arc 플래그 사용
        if not error_occurred and unsaved_arc and self.current_chapter_arc_dir:
             print("CORE: 챕터 아크 노트 변경 감지됨. 저장 시도...")
             # _save_current_chapter_arc_settings가 arc_settings_modified_flag 사용
             if self._save_current_chapter_arc_settings():
                 saved_something = True
             else:
                 error_occurred = True


        # 3. 장면 내용 저장 (필요 시)
        if not error_occurred and unsaved_output and self.current_scene_path:
            print(f"CORE: 장면 내용 변경 감지됨 ({os.path.basename(self.current_scene_path)}). 저장 시도...")
            output_content = self.gui_manager.output_panel.get_content() if self.gui_manager.output_panel else None
            if output_content is None:
                print("CORE ERROR: 출력 내용 가져오기 실패.")
                self.update_status_bar("⚠️ 출력 내용 가져오기 실패.")
                error_occurred = True
            else:
                scene_num = self._get_scene_number_from_path(self.current_scene_path)
                chapter_dir = os.path.dirname(self.current_scene_path)
                if scene_num >= 0:
                    if file_handler.save_scene_content(chapter_dir, scene_num, output_content):
                        print("CORE: 장면 내용 저장 성공.")
                        self.output_text_modified = False
                        if self.gui_manager.output_panel: self.gui_manager.output_panel.reset_modified_flag()
                        saved_something = True
                    else:
                        self.update_status_bar("⚠️ 장면 내용 저장 실패.")
                        error_occurred = True
                else:
                    print(f"CORE ERROR: 장면 번호 가져오기 실패 ({self.current_scene_path}). 내용 저장 불가.")
                    error_occurred = True

        # 4. 장면 설정 스냅샷 저장 (옵션/플롯 변경 시)
        # chapter_settings_modified_flag 사용
        if not error_occurred and unsaved_chapter_scene_opts and self.current_scene_path:
            print(f"CORE: 장면 관련 설정(플롯/옵션) 변경 감지됨 ({os.path.basename(self.current_scene_path)}). 스냅샷 저장 시도...")
            scene_num = self._get_scene_number_from_path(self.current_scene_path)
            chapter_dir = os.path.dirname(self.current_scene_path)
            if scene_num >= 0:
                 try:
                     # Get current settings from GUI to save as snapshot
                     # API 타입, 모델, 온도, 길이, 플롯 가져오기
                     settings_for_snapshot = self._get_settings_from_gui(read_novel_settings=False, read_chapter_arc_settings=False, read_scene_settings=True)
                     # API 타입은 저장할 필요 없음 (모델명으로 추론 가능하거나, 로드 시 현재 API 기준 검증)
                     if 'selected_api_type' in settings_for_snapshot: del settings_for_snapshot['selected_api_type']

                     # Add existing token info if available
                     token_info = self.current_loaded_scene_settings.get(constants.TOKEN_INFO_KEY, {constants.INPUT_TOKEN_KEY: 0, constants.OUTPUT_TOKEN_KEY: 0})
                     settings_for_snapshot[constants.TOKEN_INFO_KEY] = token_info

                     if file_handler.save_scene_settings(chapter_dir, scene_num, settings_for_snapshot):
                         print("CORE: 장면 설정(플롯/옵션+토큰) 스냅샷 저장 성공.")
                         self.current_loaded_scene_settings.update(settings_for_snapshot) # Update loaded state only for saved keys
                         if self.gui_manager.settings_panel: self.gui_manager.settings_panel.reset_chapter_modified_flag() # Reset combined flag
                         saved_something = True
                     else:
                         self.update_status_bar("⚠️ 장면 설정 스냅샷 저장 실패.")
                         error_occurred = True
                 except Exception as e:
                     self.gui_manager.show_message("error", "저장 오류", f"장면 설정 저장 중 오류 발생:\n{e}")
                     print(f"CORE ERROR: 장면 설정 저장 중 오류: {e}")
                     traceback.print_exc()
                     error_occurred = True
            else:
                 print(f"CORE ERROR: 장면 번호 가져오기 실패 ({self.current_scene_path}). 설정 저장 불가.")
                 error_occurred = True

        # --- 최종 처리 ---
        if saved_something and not error_occurred:
             context_name = "[?]"
             if self.current_scene_path:
                 scene_num = self._get_scene_number_from_path(self.current_scene_path)
                 ch_str = self._get_chapter_number_str_from_folder(os.path.dirname(self.current_scene_path))
                 context_name = f"[{self.current_novel_name}] {ch_str} - {scene_num:03d} 장면" if scene_num >= 0 else f"[{self.current_novel_name}] {ch_str}"
             elif self.current_chapter_arc_dir:
                 ch_str = self._get_chapter_number_str_from_folder(self.current_chapter_arc_dir)
                 context_name = f"[{self.current_novel_name}] {ch_str}"
             elif self.current_novel_dir:
                 context_name = f"[{self.current_novel_name}]"

             status_msg = f"✅ {context_name} 변경사항 저장 완료."
             if self.gui_manager: self.gui_manager.schedule_status_clear(status_msg, 3000)
             self.update_status_bar(status_msg)
        elif error_occurred:
             self.update_status_bar(f"❌ 일부 항목 저장 실패.")
        else: # 저장할 것이 있었으나 아무것도 저장되지 않음 (오류는 없었음?) - 이 경우는 거의 없음
             print("CORE WARN: 저장 요청 처리 완료, 저장된 항목 없음.")

        # UI 상태 업데이트 (버튼 비활성화 등)
        self.update_ui_state()

    def handle_copy_request(self):
        """'본문 복사' 버튼 클릭 처리"""
        print("CORE: 본문 복사 요청 처리...")
        if self.check_busy_and_warn(): return # Check before proceeding

        content = ""
        if self.gui_manager and self.gui_manager.output_panel:
            content = self.gui_manager.output_panel.get_content()

        if content:
            try:
                if self.gui_manager and self.gui_manager.root:
                    self.gui_manager.root.clipboard_clear()
                    self.gui_manager.root.clipboard_append(content)
                    status_msg = "✅ 본문 클립보드 복사됨."
                    self.update_status_bar(status_msg)
                    if self.gui_manager: self.gui_manager.schedule_status_clear(status_msg, 2000)
                else:
                     print("CORE ERROR: 클립보드 복사 실패 - GUI Manager 또는 Root 없음.")
                     self.update_status_bar("⚠️ 클립보드 복사 실패 (GUI 오류)")
            except Exception as e:
                 print(f"CORE ERROR: 클립보드 복사 오류: {e}")
                 traceback.print_exc()
                 if self.gui_manager: self.gui_manager.show_message("error", "복사 오류", f"클립보드 작업 중 오류 발생:\n{e}")
                 else: messagebox.showerror("복사 오류", f"클립보드 작업 중 오류 발생:\n{e}")
        else:
             status_msg = "⚠️ 복사할 내용이 없습니다."
             self.update_status_bar(status_msg)
             if self.gui_manager: self.gui_manager.schedule_status_clear(status_msg, 2000)

    def handle_tree_selection(self, item_id, tags):
        """트리뷰 아이템 선택 변경 처리"""
        busy_now = self._check_if_busy_status() # 경고 없이 상태 확인

        print(f"CORE: 트리뷰 선택 변경: ID='{item_id}', Tags={tags}")
        is_novel = 'novel' in tags
        is_chapter = 'chapter' in tags
        is_scene = 'scene' in tags

        # Update UI state based on selection type, passing the determined busy state
        if self.gui_manager:
            self.gui_manager.set_ui_state(
                is_busy=busy_now, # 확인된 상태 전달
                novel_loaded=(is_novel or is_chapter or is_scene),
                chapter_loaded=(is_chapter or is_scene), # Chapter is considered loaded if a scene within it is selected
                scene_loaded=is_scene
            )

        # Update status bar message conditionally (only if not busy)
        if not busy_now:
            current_status = self.gui_manager.get_status_bar_text() if self.gui_manager else ""
            # Only update if not showing an important message
            if not any(prefix in current_status for prefix in ["✅", "❌", "⚠️", "⏳", "🔄", "✨", "📄", "🗑️"]):
                status_msg = ""
                if is_scene and item_id: # Scene selected
                    scene_num = self._get_scene_number_from_path(item_id)
                    chap_dir = os.path.dirname(item_id)
                    ch_str = self._get_chapter_number_str_from_folder(chap_dir)
                    novel_name = os.path.basename(os.path.dirname(chap_dir))
                    if item_id != self.current_scene_path:
                         status_msg = f"[{novel_name}] {ch_str} - {scene_num:03d} 장면 선택됨 (더블클릭으로 로드)."
                    else: # Currently loaded scene re-selected
                         status_msg = f"[{self.current_novel_name}] {ch_str} - {scene_num:03d} 장면 로드됨."
                elif is_chapter and item_id: # Chapter folder selected
                     ch_str = self._get_chapter_number_str_from_folder(item_id)
                     novel_name = os.path.basename(os.path.dirname(item_id))
                     if item_id != self.current_chapter_arc_dir:
                         status_msg = f"[{novel_name}] {ch_str} 폴더 선택됨 (더블클릭으로 로드)."
                     else: # Currently loaded chapter folder re-selected
                         status_msg = f"[{self.current_novel_name}] {ch_str} 폴더 로드됨."
                elif is_novel and item_id: # Novel selected
                    if item_id != self.current_novel_name:
                        status_msg = f"소설 '{item_id}' 선택됨 (더블클릭으로 로드)."
                    else: # Currently loaded novel re-selected
                        status_msg = f"[{item_id}] 소설 로드됨."
                else: # Selection cleared or invalid
                    if not self.current_novel_dir:
                        status_msg = "새 소설을 시작하거나 기존 항목을 선택하세요."
                    # If something was loaded before, don't clear status just because selection moved to blank space

                if status_msg: self.update_status_bar(status_msg)
        else:
            print(f"DEBUG: handle_tree_selection - Skipping status bar update because AppCore is busy.")


    def handle_tree_load_request(self, item_id, tags):
        """트리뷰 아이템 더블클릭 (로드) 처리"""
        print(f"CORE: 트리뷰 로드 요청: ID='{item_id}', Tags={tags}")
        if self.check_busy_and_warn(): return # Check before proceeding
        if not self._check_and_handle_unsaved_changes("다른 항목 로드"): return

        is_novel = 'novel' in tags
        is_chapter = 'chapter' in tags
        is_scene = 'scene' in tags

        try:
            if is_scene:
                scene_path = item_id # Path to XXX.txt
                if not scene_path or not isinstance(scene_path, str) or not os.path.isfile(scene_path):
                     self.gui_manager.show_message("error", "로드 오류", f"선택된 장면 파일 경로가 유효하지 않습니다:\n{scene_path}\n목록을 새로고침합니다.")
                     self.clear_all_ui_state(); self.refresh_treeview_data(); return

                chapter_dir = os.path.dirname(scene_path)
                novel_dir = os.path.dirname(chapter_dir)
                novel_name = os.path.basename(novel_dir)
                scene_num = self._get_scene_number_from_path(scene_path)

                if scene_num < 0:
                     self.gui_manager.show_message("error", "로드 오류", f"장면 번호 확인 실패:\n{scene_path}")
                     self.clear_all_ui_state(); self.refresh_treeview_data(); return

                print(f"CORE: 장면 로드 시도: '{os.path.basename(scene_path)}' (챕터: '{os.path.basename(chapter_dir)}', 소설: '{novel_name}')")

                if not os.path.isdir(chapter_dir) or not os.path.isdir(novel_dir):
                     self.gui_manager.show_message("error", "로드 오류", f"장면의 상위 폴더 경로가 유효하지 않습니다.\n목록을 새로고침합니다.")
                     self.clear_all_ui_state(); self.refresh_treeview_data(); return

                # --- Scene Load ---
                preserve_novel = (self.current_novel_dir and os.path.normpath(self.current_novel_dir) == os.path.normpath(novel_dir))
                preserve_chapter = (self.current_chapter_arc_dir and os.path.normpath(self.current_chapter_arc_dir) == os.path.normpath(chapter_dir))

                self.clear_output_panel()
                if not preserve_chapter: self.clear_chapter_arc_and_scene_fields()
                if not preserve_novel: self.clear_settings_panel_novel_fields()

                # Load Novel Settings
                loaded_novel_settings = self.current_novel_settings if preserve_novel else file_handler.load_novel_settings(novel_dir)
                if not preserve_novel:
                     self.current_novel_name = novel_name
                     self.current_novel_dir = novel_dir
                     print(f"CORE: 새 소설 설정 로드: {novel_name}")

                # Load Chapter Arc Settings
                loaded_chapter_arc_settings = self.current_loaded_chapter_arc_settings if preserve_chapter else file_handler.load_chapter_settings(chapter_dir)
                if not preserve_chapter:
                     self.current_chapter_arc_dir = chapter_dir
                     print(f"CORE: 새 챕터 아크 설정 로드: {os.path.basename(chapter_dir)}")

                # Load Scene Settings and Content
                print(f"CORE: 장면 설정 및 내용 로드: {os.path.basename(scene_path)}")
                loaded_scene_settings = file_handler.load_scene_settings(chapter_dir, scene_num)
                scene_content = file_handler.load_scene_content(chapter_dir, scene_num)

                # === 모델 유효성 검사 및 조정 ===
                saved_model = loaded_scene_settings.get('selected_model')
                if saved_model and saved_model in self.available_models:
                    # 저장된 모델이 현재 API에서 유효하면 사용
                    if saved_model != self.selected_model:
                         print(f"CORE INFO: 로드된 장면 설정에서 모델 변경: {self.selected_model} -> {saved_model}")
                         self.handle_model_change(saved_model) # AppCore 상태 업데이트
                else:
                    # 저장된 모델이 없거나 현재 API에서 유효하지 않으면 현재 세션 모델 유지
                    print(f"CORE INFO: 로드된 장면 모델('{saved_model}') 사용 불가 또는 없음. 현재 세션 모델('{self.selected_model}') 유지.")
                    loaded_scene_settings['selected_model'] = self.selected_model # 로드된 설정에 현재 모델 반영
                # === 모델 유효성 검사 끝 ===

                # Update state
                self.current_scene_path = scene_path

                # Populate UI (로드된/조정된 데이터 사용)
                self.populate_settings_panel(loaded_novel_settings, loaded_chapter_arc_settings, loaded_scene_settings)
                self.display_output_content(scene_content, loaded_scene_settings.get(constants.TOKEN_INFO_KEY))
                self.update_window_title()

                # 로드 시에는 재생성 컨텍스트 업데이트 필요: 해당 장면 이전까지의 내용 로드
                print(f"CORE: 재생성 컨텍스트 업데이트용 이전 내용 로드 중 (챕터: '{os.path.basename(chapter_dir)}', 기준: {scene_num}화)")
                prev_content_for_regen_context = file_handler.load_previous_scenes_in_chapter(chapter_dir, scene_num)
                self.last_generation_previous_content = prev_content_for_regen_context if prev_content_for_regen_context is not None else ""
                # self.last_generation_settings_snapshot 은 로드 시에는 초기화하는 것이 나을 수 있음.
                # 또는 로드된 설정으로 업데이트. 여기서는 일단 None으로.
                self.last_generation_settings_snapshot = None


                ch_str = self._get_chapter_number_str_from_folder(chapter_dir)
                status_suffix = " (설정 로드됨)" # 설정 파일은 항상 존재하거나 생성되므로
                self.update_ui_status_and_state(f"✅ [{self.current_novel_name}] {ch_str} - {scene_num:03d} 장면 불러옴{status_suffix}.",
                                                generating=False, novel_loaded=True, chapter_loaded=True, scene_loaded=True)

            elif is_chapter:
                chapter_dir = item_id
                if not chapter_dir or not isinstance(chapter_dir, str) or not os.path.isdir(chapter_dir):
                     self.gui_manager.show_message("error", "로드 오류", f"선택된 챕터 폴더 경로가 유효하지 않습니다:\n{chapter_dir}\n목록을 새로고침합니다.")
                     self.clear_all_ui_state(); self.refresh_treeview_data(); return

                novel_dir = os.path.dirname(chapter_dir)
                novel_name = os.path.basename(novel_dir)
                print(f"CORE: 챕터 폴더 로드 시도: '{os.path.basename(chapter_dir)}' (소설: '{novel_name}')")

                if not os.path.isdir(novel_dir):
                     self.gui_manager.show_message("error", "로드 오류", f"챕터 폴더의 상위 소설 폴더를 찾을 수 없습니다:\n{novel_dir}\n목록을 새로고침합니다.")
                     self.clear_all_ui_state(); self.refresh_treeview_data(); return

                preserve_novel = (self.current_novel_dir and os.path.normpath(self.current_novel_dir) == os.path.normpath(novel_dir))

                self.clear_output_panel()
                self.clear_chapter_arc_and_scene_fields()
                self.current_scene_path = None
                self.current_loaded_scene_settings = {}
                self.last_generation_previous_content = None
                self.last_generation_settings_snapshot = None
                if not preserve_novel: self.clear_settings_panel_novel_fields()

                loaded_novel_settings = self.current_novel_settings if preserve_novel else file_handler.load_novel_settings(novel_dir)
                if not preserve_novel:
                     self.current_novel_name = novel_name
                     self.current_novel_dir = novel_dir
                     print(f"CORE: 새 소설 설정 로드: {novel_name}")

                print(f"CORE: 챕터 아크 설정 로드: {os.path.basename(chapter_dir)}")
                loaded_chapter_arc_settings = file_handler.load_chapter_settings(chapter_dir)

                self.current_chapter_arc_dir = chapter_dir

                self.populate_settings_panel(loaded_novel_settings, loaded_chapter_arc_settings, None)
                self.update_window_title()

                ch_str = self._get_chapter_number_str_from_folder(chapter_dir)
                status_suffix = " (아크 노트 로드됨)" # 설정 파일은 항상 존재하거나 생성됨
                self.update_ui_status_and_state(f"✅ [{self.current_novel_name}] {ch_str} 폴더 로드됨{status_suffix}. '새 장면' 가능.",
                                                generating=False, novel_loaded=True, chapter_loaded=True, scene_loaded=False)

            elif is_novel:
                novel_name = item_id
                novel_dir = os.path.join(constants.BASE_SAVE_DIR, novel_name)
                print(f"CORE: 소설 로드 시도: {novel_name}")

                if not os.path.isdir(novel_dir):
                     self.gui_manager.show_message("error", "로드 오류", f"소설 폴더를 찾을 수 없습니다:\n{novel_dir}")
                     self.clear_all_ui_state(); self.refresh_treeview_data(); return

                self.clear_all_ui_state()

                loaded_novel_settings = file_handler.load_novel_settings(novel_dir)

                self.current_novel_name = novel_name
                self.current_novel_dir = novel_dir
                self.current_chapter_arc_dir = None
                self.current_scene_path = None
                self.current_loaded_chapter_arc_settings = {}
                self.current_loaded_scene_settings = {}
                self.last_generation_previous_content = None
                self.last_generation_settings_snapshot = None

                self.populate_settings_panel(loaded_novel_settings, None, None)
                self.update_window_title()
                self.update_ui_status_and_state(f"✅ 소설 '{novel_name}' 로드됨. '새 챕터 폴더' 또는 트리뷰에서 챕터/장면 선택 가능.",
                                                generating=False, novel_loaded=True, chapter_loaded=False, scene_loaded=False)

            else:
                print(f"CORE WARN: 알 수 없는 타입의 트리 아이템 로드 시도: {item_id}")
                self.clear_all_ui_state()
                self.update_status_bar("알 수 없는 항목입니다.")

            self.select_treeview_item(item_id)

        except Exception as e:
            print(f"CORE ERROR: 항목 로드 중 오류: {e}")
            traceback.print_exc()
            self.gui_manager.show_message("error", "로드 오류", f"항목 로드 중 오류 발생:\n{e}")
            self.clear_all_ui_state()

    def handle_rename_chapter_request(self, chapter_path):
        """챕터 폴더 이름 변경 요청 처리"""
        print(f"CORE: 챕터 폴더 이름 변경 요청: {chapter_path}")
        if self.check_busy_and_warn(): return # Check before proceeding
        if not chapter_path or not isinstance(chapter_path, str) or not os.path.isdir(chapter_path):
            self.gui_manager.show_message("error", "오류", f"변경할 챕터 폴더 경로가 유효하지 않습니다:\n{chapter_path}")
            self.refresh_treeview_data(); return

        if chapter_path == self.current_chapter_arc_dir:
             if not self._check_and_handle_unsaved_changes("챕터 폴더 이름 변경"): return

        old_folder_name = os.path.basename(chapter_path)
        prefix_match = re.match(r"^(Chapter_\d+)", old_folder_name, re.IGNORECASE)
        current_title = ""
        prefix = "UnknownPrefix"
        if prefix_match:
             prefix = prefix_match.group(1)
             # Prefix 뒤의 내용을 가져옴
             title_part = old_folder_name[len(prefix):]
             # 맨 앞의 '_' 제거
             current_title = title_part.lstrip('_')

        new_title_input = gui_dialogs.show_rename_dialog(self.gui_manager.root, "챕터 제목 변경",
                                                    f"새로운 챕터 제목 입력 (접두사 '{prefix}_' 유지):", current_title)

        if new_title_input is None: print("CORE: 챕터 폴더 이름 변경 취소."); return

        success, message, new_path = file_handler.rename_chapter_folder(chapter_path, new_title_input)

        if success:
            print(f"CORE: 챕터 폴더 이름 변경 성공: {message}")
            if self.current_chapter_arc_dir == chapter_path:
                # Update current chapter path if it was renamed
                self.current_chapter_arc_dir = new_path
                # Scene path might also need update if a scene was loaded from the renamed chapter
                if self.current_scene_path and os.path.dirname(self.current_scene_path) == chapter_path:
                     self.current_scene_path = os.path.join(new_path, os.path.basename(self.current_scene_path))

                status_prefix = f"✅ [{self.current_novel_name}] {self._get_chapter_number_str_from_folder(new_path)} 이름 변경 및 로드됨."
                self.update_status_bar(status_prefix)
                # Update window title reflecting new chapter name
                self.update_window_title()
            else:
                 self.update_status_bar(f"✅ {message}")

            self.refresh_treeview_data()
            # Select the renamed folder
            self.select_treeview_item(new_path)
        else:
            self.gui_manager.show_message("error", "이름 변경 실패", message)

    def handle_delete_chapter_request(self, chapter_path):
        """챕터 폴더 삭제 요청 처리"""
        print(f"CORE: 챕터 폴더 삭제 요청: {chapter_path}")
        if self.check_busy_and_warn(): return # Check before proceeding
        if not chapter_path or not isinstance(chapter_path, str):
            self.gui_manager.show_message("error", "오류", f"삭제할 챕터 폴더 경로 정보가 유효하지 않습니다:\n{chapter_path}")
            self.refresh_treeview_data(); return

        chapter_name_display = self.gui_manager.treeview_panel.get_item_text(chapter_path) if self.gui_manager.treeview_panel else os.path.basename(chapter_path)
        chapter_folder_name = os.path.basename(chapter_path)
        try: novel_name_of_deleted = os.path.basename(os.path.dirname(chapter_path))
        except Exception: novel_name_of_deleted = "?"

        del_msg = f"챕터 폴더 '{chapter_name_display}' ({chapter_folder_name})을(를) 삭제하시겠습니까?\n\n⚠️ 경고: 폴더 내 모든 장면과 설정이 영구 삭제되며 복구할 수 없습니다!"
        was_current_chapter_or_scene = False
        if self.current_chapter_arc_dir and os.path.normpath(chapter_path) == os.path.normpath(self.current_chapter_arc_dir):
             was_current_chapter_or_scene = True
             del_msg += "\n\n(현재 로드된 챕터 폴더입니다. 삭제 시 관련 내용이 초기화됩니다.)"
             # Check unsaved changes within this chapter
             # Check flags for output, arc notes, and scene options
             output_mod = self.output_text_modified and self.current_scene_path and os.path.dirname(self.current_scene_path) == chapter_path
             arc_mod = self.arc_settings_modified_flag
             scene_opts_mod = self.gui_manager.settings_panel.chapter_settings_modified_flag if self.gui_manager.settings_panel else False
             if output_mod or arc_mod or scene_opts_mod:
                 del_msg += "\n(저장되지 않은 변경사항도 유실됩니다.)"
        elif self.current_scene_path and os.path.dirname(self.current_scene_path) == chapter_path:
             # A scene within the chapter to be deleted is loaded
             was_current_chapter_or_scene = True
             del_msg += "\n\n(현재 로드된 장면이 이 챕터 폴더 안에 있습니다. 삭제 시 관련 내용이 초기화됩니다.)"
             if self.output_text_modified:
                  del_msg += "\n(저장되지 않은 내용 변경사항도 유실됩니다.)"


        if not self.gui_manager.ask_yes_no("챕터 폴더 삭제 확인", del_msg, icon='warning'):
            print("CORE: 챕터 폴더 삭제 취소됨."); return

        success, message = file_handler.delete_chapter_folder(chapter_path)

        if success:
            print(f"CORE: 챕터 폴더 삭제 성공: {message}")
            if was_current_chapter_or_scene:
                print("CORE: 현재 로드된 챕터 폴더 또는 그 안의 장면 삭제됨. UI 초기화 (소설 유지).")
                self.clear_output_panel()
                self.clear_chapter_arc_and_scene_fields()
                self.current_chapter_arc_dir = None
                self.current_scene_path = None
                self.current_loaded_chapter_arc_settings = {}
                self.current_loaded_scene_settings = {}
                # 소설 정보는 유지
                novel_name_to_select = self.current_novel_name
                self.update_ui_status_and_state(f"🗑️ [{novel_name_to_select}] '{chapter_folder_name}' 챕터 폴더 삭제됨. (로드 상태 초기화)",
                                                generating=False, novel_loaded=True, chapter_loaded=False, scene_loaded=False)
                if novel_name_to_select: self.select_treeview_item(novel_name_to_select) # Select parent novel
            else:
                 self.update_status_bar(f"🗑️ [{novel_name_of_deleted}] '{chapter_folder_name}' 챕터 폴더 삭제 완료.")

            self.refresh_treeview_data()
            # Trigger summary if the deleted chapter was part of the currently loaded novel
            if self.current_novel_dir and novel_name_of_deleted != "?" and os.path.normpath(self.current_novel_dir) == os.path.normpath(os.path.join(constants.BASE_SAVE_DIR, novel_name_of_deleted)):
                 self._trigger_summary_generation(self.current_novel_dir)

        else:
            self.gui_manager.show_message("error", "삭제 오류", f"챕터 폴더 삭제 중 오류 발생:\n{message}")
            self.refresh_treeview_data()

    def handle_delete_scene_request(self, scene_path):
        """장면 파일 삭제 요청 처리"""
        print(f"CORE: 장면 삭제 요청: {scene_path}")
        if self.check_busy_and_warn(): return # Check before proceeding
        if not scene_path or not isinstance(scene_path, str):
             self.gui_manager.show_message("error", "오류", "삭제할 장면 경로 정보가 유효하지 않습니다.")
             self.refresh_treeview_data(); return

        # 파일 존재 여부는 file_handler.delete_scene_files 에서 처리하도록 변경
        # if not os.path.exists(scene_path):
        #     self.gui_manager.show_message("error", "오류", f"삭제할 장면 파일 경로가 유효하지 않거나 파일이 없습니다:\n{scene_path}")
        #     self.refresh_treeview_data(); return

        scene_name_display = self.gui_manager.treeview_panel.get_item_text(scene_path) if self.gui_manager.treeview_panel else os.path.basename(scene_path)
        scene_filename = os.path.basename(scene_path)
        chapter_dir = os.path.dirname(scene_path)
        chapter_name = os.path.basename(chapter_dir)
        scene_num = self._get_scene_number_from_path(scene_path)
        if scene_num < 0:
             self.gui_manager.show_message("error", "오류", f"장면 번호 확인 실패: {scene_path}")
             return

        del_msg = f"장면 '{scene_name_display}' ({scene_filename})을(를) 삭제하시겠습니까?\n(in {chapter_name})\n\n⚠️ 경고: 이 작업은 복구할 수 없습니다!"
        was_current_scene = False
        if scene_path == self.current_scene_path:
             was_current_scene = True
             del_msg += "\n\n(현재 로드된 장면입니다. 삭제 시 로드 상태가 초기화됩니다.)"
             if self.output_text_modified:
                  del_msg += "\n(저장되지 않은 내용 변경사항도 유실됩니다.)"
             # Scene settings modifications are less critical to warn about before deletion

        if not self.gui_manager.ask_yes_no("장면 삭제 확인", del_msg, icon='warning'):
            print("CORE: 장면 삭제 취소됨."); return

        success = file_handler.delete_scene_files(chapter_dir, scene_num)

        if success:
            print(f"CORE: 장면 파일 삭제 성공: {scene_filename}")
            if was_current_scene:
                print("CORE: 현재 로드된 장면 삭제됨. UI 초기화 (챕터 폴더 유지).")
                self.clear_output_panel()
                # Clear only scene-specific fields in settings panel
                if self.gui_manager.settings_panel:
                    self.gui_manager.settings_panel.clear_scene_settings_fields()
                self.current_scene_path = None
                self.current_loaded_scene_settings = {}
                # 챕터 폴더는 로드된 상태 유지
                chapter_to_select = self.current_chapter_arc_dir
                self.update_ui_status_and_state(f"🗑️ '{scene_filename}' 장면 삭제됨. (로드 상태 초기화)",
                                                generating=False, novel_loaded=True, chapter_loaded=True, scene_loaded=False)
                if chapter_to_select: self.select_treeview_item(chapter_to_select) # Select parent chapter
            else:
                 self.update_status_bar(f"🗑️ '{scene_filename}' 장면 삭제 완료.")

            self.refresh_treeview_data()
            # Trigger summary if the deleted scene was part of the currently loaded novel
            if self.current_novel_dir and os.path.dirname(os.path.dirname(scene_path)) == self.current_novel_dir:
                 self._trigger_summary_generation(self.current_novel_dir)

        else:
            # Error message already shown by file_handler
            print(f"CORE: 장면 파일 삭제 실패: {scene_filename}")
            self.refresh_treeview_data()

    def handle_rename_novel_request(self, novel_name):
        """소설 이름 변경 요청 처리"""
        print(f"CORE: 소설 이름 변경 요청: {novel_name}")
        if self.check_busy_and_warn(): return # Check before proceeding
        if not novel_name or not isinstance(novel_name, str):
            self.gui_manager.show_message("error", "오류", f"변경할 소설 이름 정보가 유효하지 않습니다: '{novel_name}'")
            self.refresh_treeview_data(); return

        old_path = os.path.join(constants.BASE_SAVE_DIR, novel_name)
        if not os.path.isdir(old_path):
            self.gui_manager.show_message("error", "오류", f"변경할 소설 폴더를 찾을 수 없습니다:\n{old_path}")
            self.refresh_treeview_data(); return

        was_loaded = (self.current_novel_dir and os.path.normpath(old_path) == os.path.normpath(self.current_novel_dir))

        if was_loaded:
             warn_msg = f"현재 로드된 소설 '{novel_name}' 이름을 변경합니다.\n이름 변경 후 작업 상태(로드된 챕터/장면 등)가 초기화됩니다.\n계속하시겠습니까?"
             if not self.gui_manager.ask_yes_no("이름 변경 확인", warn_msg, icon='warning'):
                 print("CORE: 로드된 소설 이름 변경 취소됨."); return
             if not self._check_and_handle_unsaved_changes("로드된 소설 이름 변경"): return

        new_name_input = gui_dialogs.show_rename_dialog(self.gui_manager.root, "소설 이름 변경",
                                                       f"소설 '{novel_name}'의 새 이름 입력:", novel_name)

        if new_name_input is None: print("CORE: 소설 이름 변경 취소됨."); return

        success, message, new_path = file_handler.rename_novel_folder(old_path, new_name_input)

        if success:
            new_name = os.path.basename(new_path)
            print(f"CORE: 소설 이름 변경 성공: {message}")

            if was_loaded:
                print("CORE: 로드된 소설 이름 변경됨. UI 초기화 및 상태 업데이트.")
                self.clear_all_ui_state()
                # Re-load the renamed novel
                self.current_novel_name = new_name
                self.current_novel_dir = new_path
                self.current_novel_settings = file_handler.load_novel_settings(self.current_novel_dir) or {}
                self.populate_settings_panel(self.current_novel_settings, None, None)
                self.update_window_title()
                self.update_ui_status_and_state(f"✅ '{new_name}' 이름 변경됨 (UI 초기화됨).",
                                                generating=False, novel_loaded=True, chapter_loaded=False, scene_loaded=False)
            else:
                 self.update_status_bar(f"✅ {message}")

            self.refresh_treeview_data()
            self.select_treeview_item(new_name) # Select the renamed novel

        else:
            self.gui_manager.show_message("error", "이름 변경 실패", message)

    def handle_delete_novel_request(self, novel_name):
        """소설 삭제 요청 처리"""
        print(f"CORE: 소설 삭제 요청: {novel_name}")
        if self.check_busy_and_warn(): return # Check before proceeding
        if not novel_name or not isinstance(novel_name, str):
            self.gui_manager.show_message("error", "오류", f"삭제할 소설 이름 정보가 유효하지 않습니다: '{novel_name}'")
            self.refresh_treeview_data(); return

        novel_path = os.path.join(constants.BASE_SAVE_DIR, novel_name)
        # 파일 존재 여부는 delete_novel_folder 내부에서 처리하도록 변경
        # path_exists_before_delete = os.path.isdir(novel_path)

        was_loaded = (self.current_novel_dir and os.path.normpath(novel_path) == os.path.normpath(self.current_novel_dir))

        del_msg = f"소설 '{novel_name}'을(를) 삭제하시겠습니까?\n\n⚠️ 경고: 소설 폴더 내 모든 챕터 폴더와 파일이 영구 삭제되며 복구할 수 없습니다!"
        if was_loaded:
            del_msg += "\n\n(현재 로드된 소설입니다. 삭제 시 작업 내용이 초기화됩니다.)"
            # Check all potentially unsaved changes if deleting loaded novel
            output_mod = self.output_text_modified
            arc_mod = self.arc_settings_modified_flag
            scene_opts_mod = self.gui_manager.settings_panel.chapter_settings_modified_flag if self.gui_manager.settings_panel else False
            novel_mod = self.novel_settings_modified_flag
            if output_mod or arc_mod or scene_opts_mod or novel_mod:
                 del_msg += "\n(저장되지 않은 변경사항도 유실됩니다.)"

        # if not path_exists_before_delete:
        #      self.gui_manager.show_message("info", "삭제 정보", f"소설 폴더 '{novel_name}'이(가) 이미 존재하지 않습니다.\n목록을 새로고침합니다.")
        #      self.refresh_treeview_data()
        #      if was_loaded: self.clear_all_ui_state()
        #      return

        if not self.gui_manager.ask_yes_no("소설 삭제 확인", del_msg, icon='warning'):
            print("CORE: 소설 삭제 취소됨."); return

        if was_loaded:
            print("CORE: 로드된 소설 삭제 전 UI 초기화...")
            self.clear_all_ui_state()

        success, message = file_handler.delete_novel_folder(novel_path)

        if success:
            print(f"CORE: 소설 삭제 성공: {message}")
            self.update_status_bar(f"🗑️ {message}")
            self.refresh_treeview_data()
        else:
            # 오류 메시지는 file_handler에서 이미 표시했을 수 있음
            # self.gui_manager.show_message("error", "삭제 실패", message)
            self.refresh_treeview_data()

    def handle_novel_settings_modified(self):
        """소설 설정 텍스트 위젯 수정 감지 시 호출됨 (자동 저장 스케줄)"""
        if self.check_busy_and_warn(): return # Check before scheduling save
        if not self.current_novel_dir: return

        print("CORE DEBUG: 소설 설정 변경 감지됨. 저장 예약.")
        self.novel_settings_modified_flag = True
        self.update_ui_state() # Update save button state etc.

        if self._novel_settings_after_id and self.gui_manager and self.gui_manager.root:
            try: self.gui_manager.root.after_cancel(self._novel_settings_after_id)
            except Exception: pass
            self._novel_settings_after_id = None

        if self.gui_manager and self.gui_manager.root:
            save_delay_ms = 1500
            self._novel_settings_after_id = self.gui_manager.root.after(save_delay_ms, self._save_current_novel_settings)
            print(f"CORE DEBUG: {save_delay_ms}ms 후 소설 설정 저장 예약됨.")

    def handle_arc_settings_modified(self):
        """챕터 아크 노트 텍스트 위젯 수정 감지 시 호출됨 (자동 저장 스케줄)"""
        if self.check_busy_and_warn(): return # Check before scheduling save
        if not self.current_chapter_arc_dir: return

        print("CORE DEBUG: 챕터 아크 노트 변경 감지됨. 저장 예약.")
        self.arc_settings_modified_flag = True
        # Also trigger combined flag in SettingsPanel
        self._trigger_chapter_settings_modified_in_gui()
        # self.update_ui_state() is called within _trigger...

        if self._arc_settings_after_id and self.gui_manager and self.gui_manager.root:
            try: self.gui_manager.root.after_cancel(self._arc_settings_after_id)
            except Exception: pass
            self._arc_settings_after_id = None

        if self.gui_manager and self.gui_manager.root:
            save_delay_ms = 1500
            self._arc_settings_after_id = self.gui_manager.root.after(save_delay_ms, self._save_current_chapter_arc_settings)
            print(f"CORE DEBUG: {save_delay_ms}ms 후 챕터 아크 노트 저장 예약됨.")


    def handle_output_modified(self):
        """출력 텍스트 위젯 수정 감지 시 호출됨"""
        if self._check_if_busy_status(): return # Only check status, don't warn for typing
        # Only set flag if a scene is actually loaded
        if self.current_scene_path:
             # Check internal Tk modified flag as well
             output_widget = self.gui_manager.output_panel.widgets.get('output_text') if self.gui_manager and self.gui_manager.output_panel else None
             if output_widget and output_widget.edit_modified():
                 self.output_text_modified = True
                 self.update_ui_state()
                 if self.gui_manager and self.gui_manager.output_panel:
                     content = self.gui_manager.output_panel.get_content()
                     self.gui_manager.output_panel.update_char_count_display(content)
                 # Reset Tk flag after handling
                 output_widget.edit_modified(False)

    # --- 설정 메뉴 핸들러들 ---
    def handle_api_key_dialog(self):
        """API 키 관리 대화상자 표시 및 결과 처리"""
        print("CORE: API 키 관리 요청...")
        if self.check_busy_and_warn(): return
        if not self.gui_manager: return

        current_ask_pref = self.config.get(constants.CONFIG_ASK_KEYS_KEY, True)

        dialog_result = gui_dialogs.show_api_key_dialog(self.gui_manager.root, current_ask_pref)

        if dialog_result is None:
            print("CORE: API 키 관리 취소됨.")
            return

        # --- Process Results ---
        keys_changed = dialog_result.get("keys") # Dict of {api_type: new_key_value} or None
        new_ask_pref = dialog_result.get("ask_pref") # Boolean or None
        config_updated = False
        api_reconfigured = False
        valid_keys_to_save = {} # Initialize here

        # 1. Update Ask Preference if changed
        if new_ask_pref is not None and new_ask_pref != current_ask_pref:
            print(f"CORE: 시작 시 키 확인 설정 변경됨: {current_ask_pref} -> {new_ask_pref}")
            self.config[constants.CONFIG_ASK_KEYS_KEY] = new_ask_pref
            config_updated = True

        # 2. Update API Keys if changed
        if keys_changed: # Should be a dict if not cancelled
            valid_keys_to_save = {api: key for api, key in keys_changed.items() if key}
            if valid_keys_to_save:
                print(f"CORE: 변경된 API 키 저장 시도: {list(valid_keys_to_save.keys())}")
                if file_handler.save_api_keys(valid_keys_to_save):
                    print("CORE: API 키 .env 파일 저장 성공.")
                    # Reconfigure APIs and reload models if keys were successfully saved
                    print("CORE: API 설정 및 모델 목록 새로고침 시도...")
                    try:
                        # Re-run configuration for affected APIs or all
                        gemini_ok, claude_ok, gpt_ok = api_handler.configure_apis()
                        # Update internal state if needed (though configure_apis might not return anything useful here)

                        # --- Reload available models ---
                        self.available_models_by_type = api_handler.get_available_models()
                        api_reconfigured = True # Mark that reconfiguration happened

                        # Update the current API's model list in AppCore state
                        self.available_models = self.available_models_by_type.get(self.current_api_type, [])

                        # Re-validate selected model and summary models
                        # (Could potentially switch API type if current one becomes invalid)
                        self._validate_and_update_models_after_reconfig() # New helper needed

                        self.gui_manager.show_message("info", "저장 완료", "API 키가 저장되었습니다.\n모델 목록이 업데이트되었을 수 있습니다.")
                    except Exception as e:
                         print(f"CORE ERROR: 키 저장 후 API 재설정/모델 로드 실패: {e}")
                         traceback.print_exc()
                         self.gui_manager.show_message("error", "오류", f"API 키는 저장되었으나, API 재설정 또는 모델 목록 로드 중 오류 발생:\n{e}")
                else:
                    self.gui_manager.show_message("error", "저장 실패", "API 키를 .env 파일에 저장하는 데 실패했습니다.")
            else:
                 print("CORE INFO: API 키 관리 대화상자에서 변경된 키 없음.")


        # 3. Save config if preference changed
        if config_updated:
            if file_handler.save_config(self.config):
                print("CORE: 키 확인 설정 config.json 저장 완료.")
                # Show message only if keys weren't *also* updated, to avoid double messages
                if not valid_keys_to_save:
                     self.gui_manager.show_message("info", "저장 완료", "시작 시 키 확인 설정이 저장되었습니다.")
            else:
                 self.gui_manager.show_message("error", "저장 실패", "키 확인 설정을 config.json에 저장 실패.")

        # 4. Update UI if APIs were reconfigured
        if api_reconfigured:
             print("CORE: API 재설정으로 인한 UI 업데이트 중...")
             # Update SettingsPanel comboboxes (API type and Model)
             if self.gui_manager.settings_panel:
                 # Update API types combobox values (if needed, though unlikely to change)
                 # Re-populate model combobox based on potentially new model lists
                 self.gui_manager.settings_panel.populate_widgets(
                     self.current_novel_settings,
                     self.current_loaded_chapter_arc_settings,
                     self.current_loaded_scene_settings
                 ) # This calls _update_models_for_api_type internally
             self.update_window_title()
             self.update_ui_state()


    def handle_system_prompt_dialog(self):
        if self.check_busy_and_warn(): return # Check before proceeding
        if not self.gui_manager: return
        new_prompt = gui_dialogs.show_system_prompt_dialog(self.gui_manager.root, self.system_prompt)
        if new_prompt is not None:
            if new_prompt != self.system_prompt:
                self.system_prompt = new_prompt
                self.config['system_prompt'] = new_prompt
                if file_handler.save_config(self.config):
                    self.gui_manager.show_message("info", "저장 완료", "기본 시스템 프롬프트가 저장되었습니다.")
                else:
                    self.gui_manager.show_message("error", "저장 실패", "시스템 프롬프트를 config.json에 저장 실패.")

    def handle_color_dialog(self):
        if self.check_busy_and_warn(): return # Check before proceeding
        if not self.gui_manager: return
        new_colors = gui_dialogs.show_color_dialog(self.gui_manager.root, self.output_bg, self.output_fg)
        if new_colors:
            changed = False
            if new_colors['bg'] != self.output_bg:
                self.output_bg = new_colors['bg']
                changed = True
            if new_colors['fg'] != self.output_fg:
                self.output_fg = new_colors['fg']
                changed = True

            if changed:
                if self.gui_manager and self.gui_manager.output_panel:
                    self.gui_manager.output_panel.set_colors(self.output_bg, self.output_fg)
                self.config['output_bg_color'] = self.output_bg
                self.config['output_fg_color'] = self.output_fg
                if file_handler.save_config(self.config):
                    print("CORE: 출력 색상 설정 저장 완료.")
                else:
                     self.gui_manager.show_message("error", "저장 실패", "색상 설정을 config.json에 저장 실패.")

    def handle_summary_model_dialog(self):
        """요약 모델 설정 대화상자 표시 (현재 활성 API 타입 기준)"""
        if self.check_busy_and_warn(): return
        if not self.gui_manager: return

        # --- 현재 활성 API 타입 기준으로 모델 목록 및 현재 설정 가져오기 ---
        current_api = self.current_api_type
        available_api_models = self.available_models_by_type.get(current_api, [])
        # 현재 API 타입에 설정된 요약 모델 가져오기
        current_summary_model_for_api = self.summary_models.get(current_api)

        if not available_api_models:
             self.gui_manager.show_message("info", "모델 없음", f"{current_api.capitalize()} API에서 사용 가능한 모델이 없습니다.\n요약 모델을 설정할 수 없습니다.")
             return

        # 대화상자에 전달할 모델 목록
        dialog_models = list(available_api_models)
        # 대화상자 호출 (현재 API 타입의 설정된 모델 전달)
        new_model = gui_dialogs.show_summary_model_dialog(
            self.gui_manager.root,
            current_summary_model_for_api,
            dialog_models
        )

        if new_model and new_model in available_api_models:
            # 선택된 모델이 현재 API의 설정된 모델과 다를 경우 업데이트
            if new_model != current_summary_model_for_api:
                print(f"CORE: 요약 모델 변경 ({current_api.capitalize()}): {current_summary_model_for_api} -> {new_model}")
                # 해당 API 타입의 요약 모델 업데이트
                self.summary_models[current_api] = new_model
                # 현재 활성 요약 모델도 업데이트 (current_api가 활성 API이므로)
                self.summary_model = new_model

                # 설정 저장 (API 타입별 키 사용)
                config_key = f"{constants.SUMMARY_MODEL_KEY_PREFIX}{current_api}"
                self.config[config_key] = new_model
                if file_handler.save_config(self.config):
                    self.gui_manager.show_message("info", "저장 완료", f"({current_api.capitalize()}) 요약 모델이 '{new_model}'(으)로 저장되었습니다.")
                else:
                    self.gui_manager.show_message("error", "저장 실패", "요약 모델 설정을 config.json에 저장 실패.")
            else:
                 print(f"CORE INFO: ({current_api.capitalize()}) 요약 모델 변경 없음.")
        elif new_model is not None: # Dialog 반환값이 있으나 유효 목록에 없을 때 (오류)
             print(f"CORE ERROR: Dialog에서 잘못된 요약 모델 반환: {new_model}")


    def handle_open_save_directory(self):
        if self.check_busy_and_warn(): return # Check before proceeding
        try:
            save_dir_path = os.path.realpath(constants.BASE_SAVE_DIR)
            if not os.path.exists(save_dir_path):
                 os.makedirs(save_dir_path)
                 if self.gui_manager: self.gui_manager.show_message("info", "폴더 생성됨", f"소설 저장 폴더가 생성되었습니다:\n{save_dir_path}")

            print(f"CORE INFO: 소설 저장 폴더 열기 시도: {save_dir_path}")
            if sys.platform == 'win32': os.startfile(save_dir_path)
            elif sys.platform == 'darwin': import subprocess; subprocess.run(['open', save_dir_path], check=True)
            else: import subprocess; subprocess.run(['xdg-open', save_dir_path], check=True)
        except Exception as e:
            print(f"CORE ERROR: 저장 폴더 열기 실패: {e}")
            traceback.print_exc()
            if self.gui_manager: self.gui_manager.show_message("error", "폴더 열기 오류", f"폴더를 여는 중 오류 발생:\n{e}")

    # --- 내부 헬퍼 및 스레드 관련 ---

    def _check_if_busy_status(self):
        """내부 상태 확인: 현재 생성 또는 요약 작업 중인지 순수하게 확인"""
        # Check if flags exist before accessing
        generating = getattr(self, 'is_generating', False)
        summarizing = getattr(self, 'is_summarizing', False)
        return generating or summarizing

    # --- 추가된 공개 메소드 ---
    def is_busy(self):
        """Public method to check if the core is busy generating or summarizing."""
        return self._check_if_busy_status()
    # --- 추가 끝 ---

    def check_busy_and_warn(self):
        """상태 확인 및 사용자 알림: 현재 작업 중인지 확인하고, 그렇다면 경고 메시지 표시"""
        busy = self._check_if_busy_status() # 내부 상태 확인 함수 호출
        if busy and self.gui_manager:
            # --- 디버깅 로그는 유지하거나 필요에 따라 제거 ---
            try:
                caller_frame = traceback.extract_stack()[-2]
                caller_name = caller_frame.name
                caller_lineno = caller_frame.lineno
                print(f"DEBUG: check_busy_and_warn() called by {caller_name} (line {caller_lineno}), showing Busy message (generating={getattr(self, 'is_generating', False)}, summarizing={getattr(self, 'is_summarizing', False)})")
            except Exception: # Fallback if stack extraction fails
                 print(f"DEBUG: check_busy_and_warn() called, showing Busy message (generating={getattr(self, 'is_generating', False)}, summarizing={getattr(self, 'is_summarizing', False)})")
            # --- 로그 끝 ---
            self.gui_manager.show_message("info", "작업 중", "현재 다른 AI 작업이 진행 중입니다.\n완료 후 다시 시도해주세요.")
        return busy

    def clear_all_ui_state(self):
        """UI 전체 상태 초기화 (소설/챕터/장면 로드 해제)"""
        # Note: This function clears state, it doesn't need a busy check itself,
        # but it might be called by functions that *should* check if busy first.
        print("CORE: UI 전체 상태 초기화 중...")
        self.clear_output_panel()
        self.clear_settings_panel_novel_fields()
        self.clear_chapter_arc_and_scene_fields()

        self.current_novel_name = None
        self.current_novel_dir = None
        self.current_chapter_arc_dir = None
        self.current_scene_path = None

        self.current_novel_settings = {}
        self.current_loaded_chapter_arc_settings = {}
        self.current_loaded_scene_settings = {}

        self.last_generation_previous_content = None
        self.last_generation_settings_snapshot = None

        self.output_text_modified = False
        self.novel_settings_modified_flag = False
        self.arc_settings_modified_flag = False
        # Reset combined flag in SettingsPanel too
        if self.gui_manager and self.gui_manager.settings_panel:
             self.gui_manager.settings_panel.reset_chapter_modified_flag()

        # Cancel auto-save timers
        if self._novel_settings_after_id and self.gui_manager and self.gui_manager.root:
            try: self.gui_manager.root.after_cancel(self._novel_settings_after_id)
            except Exception: pass
            self._novel_settings_after_id = None
        if self._arc_settings_after_id and self.gui_manager and self.gui_manager.root:
            try: self.gui_manager.root.after_cancel(self._arc_settings_after_id)
            except Exception: pass
            self._arc_settings_after_id = None

        if self.gui_manager and self.gui_manager.treeview_panel:
            self.gui_manager.treeview_panel.deselect_all()

        self.update_window_title()
        self.update_ui_status_and_state("새 소설을 시작하거나 기존 항목을 선택하세요.",
                                        generating=False, novel_loaded=False, chapter_loaded=False, scene_loaded=False)

    def _check_and_handle_unsaved_changes(self, action_description="작업"):
        """저장되지 않은 변경사항 확인 및 처리 (저장/무시/취소)"""
        # Note: This doesn't need a busy check itself. The caller should check.
        if not self.gui_manager: return True # Cannot check without GUI

        unsaved_output = self.output_text_modified
        unsaved_novel = self.novel_settings_modified_flag
        unsaved_arc = self.arc_settings_modified_flag
        unsaved_scene_opts = self.gui_manager.settings_panel.chapter_settings_modified_flag if self.gui_manager.settings_panel else False

        if not unsaved_output and not unsaved_novel and not unsaved_arc and not unsaved_scene_opts:
            return True

        prompt_lines = ["저장되지 않은 변경사항이 있습니다:"]
        if unsaved_output and self.current_scene_path: prompt_lines.append(f"  - 장면 내용 ({os.path.basename(self.current_scene_path)})")
        if unsaved_novel and self.current_novel_dir: prompt_lines.append(f"  - 소설 전체 설정 ({self.current_novel_name})")
        if unsaved_arc and self.current_chapter_arc_dir: prompt_lines.append(f"  - 챕터 아크 노트 ({os.path.basename(self.current_chapter_arc_dir)})")
        if unsaved_scene_opts and self.current_scene_path: prompt_lines.append(f"  - 장면 설정/옵션 ({os.path.basename(self.current_scene_path)})")

        # If no specific item is loaded but flags are true (shouldn't normally happen, but as safeguard)
        if unsaved_output and not self.current_scene_path: prompt_lines.append("  - 장면 내용 (로드되지 않음)")
        if unsaved_novel and not self.current_novel_dir: prompt_lines.append("  - 소설 전체 설정 (로드되지 않음)")
        if unsaved_arc and not self.current_chapter_arc_dir: prompt_lines.append("  - 챕터 아크 노트 (로드되지 않음)")
        if unsaved_scene_opts and not self.current_scene_path: prompt_lines.append("  - 장면 설정/옵션 (로드되지 않음)")

        prompt_lines.append(f"\n저장 후 {action_description}을(를) 진행하시겠습니까?")
        prompt_lines.append("\n('아니오' 선택 시 변경사항을 버리고 진행합니다.)")
        save_prompt_msg = "\n".join(prompt_lines)

        resp = self.gui_manager.ask_yes_no_cancel("저장 확인", save_prompt_msg, icon='warning')

        if resp is True: # 저장 (Yes)
            print(f"CORE: '{action_description}' 전 저장 선택됨.")
            self.handle_save_changes_request() # This already has a busy check inside
            # Re-check flags after save attempt
            chapter_mod_after_save = self.gui_manager.settings_panel.chapter_settings_modified_flag if self.gui_manager.settings_panel else False
            if self.output_text_modified or self.novel_settings_modified_flag or self.arc_settings_modified_flag or chapter_mod_after_save:
                 print("CORE WARN: 저장 시도 후에도 변경사항 플래그가 남아있음 (저장 실패?). 작업 취소.")
                 self.gui_manager.show_message("warning", "저장 실패", f"변경사항 저장에 실패했습니다.\n{action_description}을(를) 취소합니다.")
                 return False
            else:
                 print("CORE: 저장 성공. 작업 진행.")
                 return True
        elif resp is None: # 취소 (Cancel)
            print(f"CORE: {action_description} 작업 취소됨 (저장 확인 창).")
            return False
        else: # 저장 안 함 (No)
            print(f"CORE: 변경사항 저장 안 함 선택됨 ({action_description} 진행).")
            self.output_text_modified = False
            self.novel_settings_modified_flag = False
            self.arc_settings_modified_flag = False
            if self.gui_manager.output_panel: self.gui_manager.output_panel.reset_modified_flag()
            if self.gui_manager.settings_panel:
                 self.gui_manager.settings_panel.reset_novel_modified_flag()
                 self.gui_manager.settings_panel.reset_chapter_modified_flag() # Reset combined flag
            # Cancel auto-save timers as well
            if self._novel_settings_after_id and self.gui_manager and self.gui_manager.root:
                try: self.gui_manager.root.after_cancel(self._novel_settings_after_id)
                except Exception: pass; self._novel_settings_after_id = None
            if self._arc_settings_after_id and self.gui_manager and self.gui_manager.root:
                try: self.gui_manager.root.after_cancel(self._arc_settings_after_id)
                except Exception: pass; self._arc_settings_after_id = None

            self.update_ui_state()
            return True

    def _get_settings_from_gui(self, read_novel_settings=True, read_chapter_arc_settings=True, read_scene_settings=True):
        """GUI 패널에서 현재 설정값들을 가져옴"""
        settings = {}
        if not self.gui_manager or not self.gui_manager.settings_panel:
            print("CORE ERROR: 설정값 가져오기 실패 - SettingsPanel 없음.")
            return settings

        # Get all current values from the panel
        panel_settings = self.gui_manager.settings_panel.get_settings()

        if read_novel_settings:
             for key in constants.NOVEL_LEVEL_SETTINGS:
                 settings[key] = panel_settings.get(key, "")
        if read_chapter_arc_settings:
             for key in constants.CHAPTER_LEVEL_SETTINGS:
                 settings[key] = panel_settings.get(key, "")
        if read_scene_settings:
             # Include API type as well? Not typically saved in scene settings
             # settings['selected_api_type'] = panel_settings.get('selected_api_type', self.current_api_type)
             for key in constants.SCENE_SPECIFIC_SETTINGS: # e.g., scene_plot
                 settings[key] = panel_settings.get(key, "")
             for key in constants.GUI_OTHER_SETTINGS: # e.g., temperature, length, selected_model
                 settings[key] = panel_settings.get(key, "")

        return settings

    def _save_current_novel_settings(self):
        """현재 GUI의 소설 설정 내용을 파일에 저장 (자동 저장용)"""
        if not self.gui_manager or not self.gui_manager.settings_panel: return False
        self._novel_settings_after_id = None # Timer ID reset
        if not self.current_novel_dir: return True # Nothing to save if no novel loaded
        if not self.novel_settings_modified_flag: return True # Nothing changed

        print(f"CORE: 소설 설정 자동 저장 시도: {self.current_novel_name}")
        try:
            current_gui_novel_settings_text = self.gui_manager.settings_panel.get_novel_settings()
            if current_gui_novel_settings_text is None: return False # Failed to get text

            novel_key = constants.NOVEL_MAIN_SETTINGS_KEY
            settings_to_save = {novel_key: current_gui_novel_settings_text}

            print(f"CORE: 소설 설정 파일 저장 시도 ({self.current_novel_dir})...")
            if file_handler.save_novel_settings(self.current_novel_dir, settings_to_save):
                self.current_novel_settings[novel_key] = current_gui_novel_settings_text
                status_msg = f"✅ [{self.current_novel_name}] 소설 설정 자동 저장됨."
                self.gui_manager.update_status_bar_conditional(status_msg) # Only if not showing important msg
                self.gui_manager.schedule_status_clear(status_msg, 3000)
                self.novel_settings_modified_flag = False
                if self.gui_manager.settings_panel: self.gui_manager.settings_panel.reset_novel_modified_flag()
                self.update_ui_state()
                return True
            else:
                status_msg = f"❌ [{self.current_novel_name}] 소설 설정 자동 저장 실패."
                self.update_status_bar(status_msg)
                return False
        except Exception as e:
            print(f"CORE ERROR: 소설 설정 자동 저장 중 오류: {e}")
            traceback.print_exc()
            self.gui_manager.show_message("error", "자동 저장 오류", f"소설 설정 자동 저장 중 오류 발생:\n{e}")
            return False

    def _save_current_chapter_arc_settings(self):
        """현재 GUI의 챕터 아크 노트 내용을 파일에 저장 (자동 저장용)"""
        if not self.gui_manager or not self.gui_manager.settings_panel: return False
        self._arc_settings_after_id = None # Timer ID reset
        if not self.current_chapter_arc_dir: return True # Nothing to save if no chapter loaded
        # Check specific flag for arc notes modification
        if not self.arc_settings_modified_flag: return True

        print(f"CORE: 챕터 아크 노트 자동 저장 시도: {os.path.basename(self.current_chapter_arc_dir)}")
        try:
            # Get arc notes from settings panel widget
            arc_widget = self.gui_manager.settings_panel.widgets.get('chapter_arc_notes_text')
            if not arc_widget or not arc_widget.winfo_exists(): return False
            current_gui_arc_notes = arc_widget.get("1.0", "end-1c").strip()

            arc_key = constants.CHAPTER_ARC_NOTES_KEY
            settings_to_save = {arc_key: current_gui_arc_notes}

            print(f"CORE: 챕터 아크 설정 파일 저장 시도 ({self.current_chapter_arc_dir})...")
            if file_handler.save_chapter_settings(self.current_chapter_arc_dir, settings_to_save):
                self.current_loaded_chapter_arc_settings[arc_key] = current_gui_arc_notes
                ch_str = self._get_chapter_number_str_from_folder(self.current_chapter_arc_dir)
                status_msg = f"✅ [{self.current_novel_name}] {ch_str} 아크 노트 자동 저장됨."
                self.gui_manager.update_status_bar_conditional(status_msg)
                self.gui_manager.schedule_status_clear(status_msg, 3000)
                self.arc_settings_modified_flag = False
                # Reset Tk modified flag for the widget
                if arc_widget: arc_widget.edit_modified(False)

                # Check if *only* arc notes were modified. If so, reset combined flag.
                scene_opts_mod = self.gui_manager.settings_panel.chapter_settings_modified_flag
                if scene_opts_mod and not self.output_text_modified: # Assuming save button only cares about scene opts + output
                    # If scene options *also* changed, the combined flag remains True.
                    # If only arc notes changed, reset the combined flag.
                    # This logic is tricky. Let's reset combined flag if *only* arc flag was true.
                    # Check if scene plot or options were also modified...
                    pass # For now, let the save button logic handle the combined flag state update

                self.update_ui_state()
                return True
            else:
                ch_str = self._get_chapter_number_str_from_folder(self.current_chapter_arc_dir)
                status_msg = f"❌ [{self.current_novel_name}] {ch_str} 아크 노트 자동 저장 실패."
                self.update_status_bar(status_msg)
                return False
        except Exception as e:
            print(f"CORE ERROR: 챕터 아크 노트 자동 저장 중 오류: {e}")
            traceback.print_exc()
            self.gui_manager.show_message("error", "자동 저장 오류", f"챕터 아크 노트 자동 저장 중 오류 발생:\n{e}")
            return False

    def _start_generation_thread_internal(self, api_type, novel_settings, chapter_arc_notes, scene_specific_settings, previous_scene_content, target_chapter_arc_dir, target_scene_number, is_new_scene):
        """장면 생성 스레드 시작 및 UI 상태 관리 (API 타입 인자 추가)"""
        # Note: This internal function assumes the caller already did the busy check.
        if self._check_if_busy_status(): # Double check internally, but don't warn
             print("CORE WARN: 생성 요청 무시됨 (이미 작업 진행 중 - 내부 확인).")
             return
        if not novel_settings or not chapter_arc_notes or not scene_specific_settings or not target_chapter_arc_dir or target_scene_number < 1:
             msg = "생성 시작 실패: 필수 설정 정보 누락 (소설/챕터/장면 플롯/타겟)."
             if self.gui_manager: self.gui_manager.show_message("error", "오류", msg)
             else: print(f"CORE ERROR: {msg} (GUI 없음).")
             return
        if not api_type or api_type not in constants.SUPPORTED_API_TYPES:
             msg = f"생성 시작 실패: 유효하지 않은 API 타입 ({api_type})."
             if self.gui_manager: self.gui_manager.show_message("error", "오류", msg)
             else: print(f"CORE ERROR: {msg} (GUI 없음).")
             return

        try:
            plot_for_prompt = scene_specific_settings.get(constants.SCENE_PLOT_KEY, "")
            length_option = scene_specific_settings.get('length', constants.LENGTH_OPTIONS[0])
            temperature_val = scene_specific_settings.get('temperature', constants.DEFAULT_TEMPERATURE)
            # 모델 이름은 scene_specific_settings 또는 self.selected_model 사용
            current_api_type = self.current_api_type # Read from self
            # Use model from scene settings if valid, otherwise use current session model
            session_model = self.selected_model
            model_from_settings = scene_specific_settings.get('selected_model')
            model_name_to_use = session_model # Default to session model

            if model_from_settings and model_from_settings in self.available_models_by_type.get(current_api_type, []):
                model_name_to_use = model_from_settings
                print(f"CORE DEBUG: Using model from scene settings: {model_name_to_use}")
            elif session_model and session_model in self.available_models_by_type.get(current_api_type, []):
                model_name_to_use = session_model
                print(f"CORE DEBUG: Using current session model: {model_name_to_use}")
            else:
                # Handle case where neither is valid (should be caught earlier, but safeguard)
                valid_models = self.available_models_by_type.get(current_api_type, [])
                if valid_models:
                    model_name_to_use = valid_models[0]
                    print(f"CORE WARN: Invalid model in settings/session, falling back to first available: {model_name_to_use}")
                else:
                    raise ValueError(f"No valid models available for API type '{current_api_type}'")

            scene_specific_settings['selected_model'] = model_name_to_use # Ensure snapshot uses the final model name

            system_prompt_val = self.system_prompt # generate_prompt에는 사용 안 됨
            # --- api_handler.generate_prompt 호출 시 모든 필수 인자 전달 ---
            print("CORE DEBUG: Generating prompt with:") # 디버깅 로그 추가
            print(f"  Novel Settings Keys: {list(novel_settings.keys()) if isinstance(novel_settings, dict) else 'N/A'}")
            print(f"  Chapter Arc Notes Keys: {list(chapter_arc_notes.keys()) if isinstance(chapter_arc_notes, dict) else 'N/A'}")
            print(f"  Scene Plot Length: {len(plot_for_prompt)}")
            print(f"  Length Option: {length_option}")
            print(f"  Previous Scene Content Length: {len(previous_scene_content) if previous_scene_content else 0}")

            prompt_text = api_handler.generate_prompt(
                novel_settings,         # 이 함수로 전달된 파라미터
                chapter_arc_notes,      # 이 함수로 전달된 파라미터
                plot_for_prompt,        # 위에서 추출한 값
                length_option,          # 위에서 추출한 값
                previous_scene_content  # 이 함수로 전달된 파라미터
            )
            if not prompt_text: raise ValueError("프롬프트 생성 실패.")

            # 스냅샷 생성 (장면 관련 설정만 저장)
            scene_settings_snapshot = {}
            for key in constants.SCENE_SETTING_KEYS_TO_SAVE:
                 if key in scene_specific_settings:
                     scene_settings_snapshot[key] = scene_specific_settings[key]
            # Ensure essential keys like 'selected_model' are in the snapshot
            scene_settings_snapshot['selected_model'] = model_name_to_use
            scene_settings_snapshot['temperature'] = temperature_val
            scene_settings_snapshot['length'] = length_option
            scene_settings_snapshot[constants.SCENE_PLOT_KEY] = plot_for_prompt


            # 스레드 인자에 API 타입 추가
            thread_args = (current_api_type, prompt_text, model_name_to_use, system_prompt_val, temperature_val,
                           target_chapter_arc_dir, target_scene_number, scene_settings_snapshot,
                           is_new_scene, previous_scene_content)
            action_desc = "새 장면" if is_new_scene else "장면 재생성"
            print(f"CORE INFO: {action_desc} 스레드 시작 준비: API={current_api_type}, Model={model_name_to_use}, Temp={temperature_val:.2f}, Target={os.path.basename(target_chapter_arc_dir)}/{target_scene_number:03d}.txt")

        except Exception as e:
             msg = f"생성 준비 중 오류 발생:\n{e}"
             if self.gui_manager: self.gui_manager.show_message("error", "오류", msg)
             else: print(f"CORE ERROR: {msg} (GUI 없음).")
             print(f"CORE ERROR: 생성 준비 중 오류: {e}") # Log the specific error
             traceback.print_exc()
             self.update_ui_state(generating=False)
             # Show error message to user
             if self.gui_manager:
                self.gui_manager.show_message("error", "생성 준비 오류", f"생성을 시작하는 중 문제가 발생했습니다:\n{e}")
             return

        self.is_generating = True
        self.output_text_modified = False # Reset flags before generation
        self.arc_settings_modified_flag = False
        if self.gui_manager and self.gui_manager.settings_panel:
             self.gui_manager.settings_panel.reset_chapter_modified_flag()
        if self.gui_manager and self.gui_manager.output_panel:
             self.gui_manager.output_panel.reset_modified_flag()

        self.update_ui_state(generating=True, scene_loaded=(not is_new_scene)) # Scene is loaded if regenerating
        self.start_timer("⏳ AI 생성 준비 중...")

        thread = threading.Thread(target=self._run_generation_in_thread, args=thread_args, daemon=True)
        thread.start()

    def _run_generation_in_thread(self, api_type, prompt, model_name, system_prompt, temperature, target_chapter_dir, target_scene_number, settings_snapshot, is_new_scene, previous_content):
        """백그라운드 스레드: API 호출 수행 (API 타입 인자 추가)"""
        result_content = None; token_data = None; is_api_call_error = False; error_message_detail = ""
        thread_id = threading.get_ident()
        target_file_str = f"{os.path.basename(target_chapter_dir)}/{target_scene_number:03d}.txt"
        print(f"CORE THREAD {thread_id}: 생성 작업 시작 (API: {api_type}, Target: {target_file_str})...")

        try:
            # API 핸들러 호출 시 API 타입 전달
            api_result, token_data = api_handler.generate_webnovel_scene_api_call(
                api_type, model_name, prompt, system_prompt, temperature
            )
            if isinstance(api_result, str) and api_result.startswith("오류"):
                is_api_call_error = True; error_message_detail = api_result; result_content = api_result
                print(f"CORE THREAD {thread_id}: {api_type.upper()} API 호출 실패 - {error_message_detail}")
            else:
                result_content = api_result
                print(f"CORE THREAD {thread_id}: {api_type.upper()} API 호출 성공. 내용 길이: {len(result_content or '')}")
        except Exception as thread_exception:
            error_message_detail = f"스레드 {thread_id} 내부 오류: {thread_exception}"
            print(f"CORE THREAD {thread_id}: ❌ {error_message_detail}")
            traceback.print_exc()
            result_content = f"오류 발생: {error_message_detail}"; is_api_call_error = True; token_data = None
        finally:
            if self.gui_manager and self.gui_manager.root and self.gui_manager.root.winfo_exists():
                self.gui_manager.root.after(0, self._process_generation_result,
                                            result_content, token_data, target_chapter_dir, target_scene_number,
                                            settings_snapshot, is_new_scene, is_api_call_error,
                                            previous_content)
            else: print(f"CORE THREAD {thread_id}: GUI 루트 없음. 결과 처리 불가.")

    def _process_generation_result(self, result_data, token_data, target_chapter_dir, target_scene_number, settings_snapshot, is_new_scene, is_error, previous_content):
        """장면 생성 결과 처리 (메인 스레드에서 실행)"""
        action_desc = "재생성" if not is_new_scene else "생성"
        target_file_str = f"{os.path.basename(target_chapter_dir)}/{target_scene_number:03d}"
        print(f"CORE: 장면 {action_desc} 결과 처리 시작 (Target: {target_file_str}, IsError: {is_error})...")

        self.stop_timer()
        self.is_generating = False

        if not self.gui_manager or not self.gui_manager.root or not self.gui_manager.root.winfo_exists():
             print("CORE WARN: 결과 처리 중단 - GUI 없음.")
             return

        generated_content = result_data if isinstance(result_data, str) else "오류: 잘못된 데이터 타입 수신"
        generated_content = generated_content.strip()
        final_token_info = token_data if isinstance(token_data, dict) else {constants.INPUT_TOKEN_KEY: 0, constants.OUTPUT_TOKEN_KEY: 0}

        # Display generated content (or error message)
        self.display_output_content(generated_content, final_token_info)

        status_message = ""
        saved_scene_path = None # Store the path of the successfully saved scene file
        novel_dir_for_summary = None

        if not is_error and generated_content:
            char_count_str = f"{len(generated_content):,}자"
            elapsed_time_str = ""
            if self.start_time > 0:
                elapsed_time = time.time() - self.start_time; elapsed_time_str = f"{elapsed_time:.1f}초"
                self.start_time = 0
            time_str_display = f" ({elapsed_time_str})" if elapsed_time_str else ""

            # Check required context info again before saving
            if not target_chapter_dir or target_scene_number < 1 or not self.current_novel_dir or not self.current_novel_name:
                 status_message = f"⚠️ 생성 성공, 저장 실패 (내부 정보 부족!). ({char_count_str}{time_str_display})"
                 print("CORE ERROR: 결과 저장 실패 - 필수 컨텍스트 정보 부족.")
                 self.last_generation_settings_snapshot = None; self.last_generation_previous_content = None
                 novel_dir_for_summary = None
            else:
                 print(f"CORE: 생성된 장면 내용 저장 시도: {target_file_str}.txt")
                 saved_content_path = file_handler.save_scene_content(target_chapter_dir, target_scene_number, generated_content)

                 if saved_content_path:
                     # Add token info to the settings snapshot before saving
                     snapshot_with_tokens = settings_snapshot.copy()
                     snapshot_with_tokens[constants.TOKEN_INFO_KEY] = final_token_info

                     print(f"CORE: 장면 설정(스냅샷+토큰) 저장 시도: {target_file_str}_settings.json")
                     if file_handler.save_scene_settings(target_chapter_dir, target_scene_number, snapshot_with_tokens):
                         saved_scene_path = saved_content_path # Store path to the .txt file
                         ch_str = self._get_chapter_number_str_from_folder(target_chapter_dir)
                         status_message = f"✅ [{self.current_novel_name}] {ch_str} - {target_scene_number:03d} 장면 {action_desc} 완료! ({char_count_str}{time_str_display})"
                         print(f"CORE: 장면 {action_desc} 성공 및 저장 완료: {saved_scene_path}")

                         # Update current state to reflect the newly generated/saved scene
                         self.current_chapter_arc_dir = target_chapter_dir # Ensure chapter dir is current
                         self.current_scene_path = saved_scene_path
                         self.current_loaded_scene_settings = snapshot_with_tokens.copy() # Update loaded scene settings

                         # Update regeneration context
                         # previous_content는 이제 해당 챕터의 모든 이전 장면 내용임
                         self.last_generation_settings_snapshot = settings_snapshot.copy() # 스냅샷은 그대로
                         self.last_generation_previous_content = previous_content # 결합된 이전 내용 저장

                         # Re-populate settings panel with potentially updated scene settings
                         self.populate_settings_panel(self.current_novel_settings, self.current_loaded_chapter_arc_settings, self.current_loaded_scene_settings)

                         self.refresh_treeview_data()
                         self.select_treeview_item(saved_scene_path)

                         novel_dir_for_summary = self.current_novel_dir # Trigger summary for the novel

                     else: # Scene content saved, but settings snapshot failed
                         status_message = f"⚠️ 내용 저장됨, 장면 설정 저장 실패. ({char_count_str}{time_str_display})"
                         print(f"CORE ERROR: 장면 설정 저장 실패: {target_file_str}_settings.json")
                         # Keep scene loaded, but settings might be inconsistent
                         self.current_chapter_arc_dir = target_chapter_dir
                         self.current_scene_path = saved_content_path
                         self.current_loaded_scene_settings = {} # Clear loaded settings as save failed
                         novel_dir_for_summary = None

                 else: # Scene content save failed
                     status_message = f"⚠️ 생성 성공, 내용 저장 실패. ({char_count_str}{time_str_display})"
                     print(f"CORE ERROR: 장면 내용 저장 실패: {target_file_str}.txt")
                     # Clear scene state as content save failed
                     self.current_scene_path = None; self.current_loaded_scene_settings = {}
                     self.refresh_treeview_data()
                     novel_dir_for_summary = None

        else: # API call resulted in an error or empty content
             if not generated_content and not is_error: # Empty content but no error
                  status_message = "⚠️ AI가 빈 내용을 생성했습니다. 플롯이나 설정을 확인하세요."
                  print(f"CORE WARN: 빈 내용 생성됨 (Target: {target_file_str})")
             else: # Actual error
                  status_message = generated_content # Contains the error message
                  print(f"CORE ERROR: 장면 {action_desc} 실패 - {status_message}")

             self.last_generation_settings_snapshot = None # Clear context on error/empty
             self.last_generation_previous_content = None

             # Keep chapter loaded, clear scene state if it was a new scene attempt
             if is_new_scene:
                 self.current_scene_path = None
                 self.current_loaded_scene_settings = {}
                 self.refresh_treeview_data() # Show that new scene wasn't created
             # If regenerating, keep the current scene loaded but show error
             novel_dir_for_summary = None

        # Final UI state update
        final_scene_loaded = bool(saved_scene_path or (not is_new_scene and self.current_scene_path))
        final_novel_loaded = bool(self.current_novel_dir) # novel_loaded 상태 추가
        self.update_ui_status_and_state(status_message, generating=False, novel_loaded=final_novel_loaded, chapter_loaded=bool(self.current_chapter_arc_dir), scene_loaded=final_scene_loaded) # novel_loaded 전달
        if status_message.startswith("✅") and self.gui_manager:
             self.gui_manager.schedule_status_clear(status_message, 5000)

        # Trigger summary if appropriate
        if novel_dir_for_summary:
             self._trigger_summary_generation(novel_dir_for_summary)

        print(f"CORE: 장면 {action_desc} 결과 처리 완료.")


    def start_timer(self, initial_message="⏳ 작업 중..."):
        """타이머 시작 및 상태 표시줄 업데이트 시작"""
        if not self.gui_manager or not self.gui_manager.root: return
        if self.timer_after_id:
            try: self.gui_manager.root.after_cancel(self.timer_after_id)
            except Exception: pass
        self.start_time = time.time()
        self.update_status_bar(initial_message)
        self._update_timer_display()

    def stop_timer(self):
        """타이머 중지"""
        if not self.gui_manager or not self.gui_manager.root: return
        if self.timer_after_id:
            try: self.gui_manager.root.after_cancel(self.timer_after_id)
            except Exception: pass
            self.timer_after_id = None

    def _update_timer_display(self):
        """타이머 상태 표시줄 업데이트 (주기적 호출)"""
        if not self.gui_manager or not self.gui_manager.root: return
        if self.is_generating or self.is_summarizing:
            elapsed_time = time.time() - self.start_time if self.start_time > 0 else 0
            spinner_icons = ["◐", "◓", "◑", "◒"]
            icon = spinner_icons[int(elapsed_time * 2.5) % len(spinner_icons)]
            status_prefix = "⏳ AI 생성 중..." if self.is_generating else "⏳ 이전 줄거리 요약 중..."
            self.update_status_bar(f"{icon} {status_prefix} ({elapsed_time:.1f}초)")
            if self.gui_manager.root.winfo_exists():
                 self.timer_after_id = self.gui_manager.root.after(150, self._update_timer_display)
            else: self.timer_after_id = None


    # --- Summary Logic ---
    def _trigger_summary_generation(self, novel_dir):
        """줄거리 요약 생성 스레드 시작 (현재 활성 API 타입과 모델 사용)"""
        # Note: This internal function assumes the caller already did the busy check.
        # --- 현재 활성 API 타입과 해당 요약 모델 가져오기 ---
        current_api = self.current_api_type
        summary_model_for_current_api = self.summary_models.get(current_api)
        # --- 가져오기 끝 ---

        if not summary_model_for_current_api:
            print(f"CORE INFO: 현재 API({current_api.capitalize()})에 설정된 요약 모델 없음. 요약 건너뜀.")
            self.update_status_bar(f"⚠️ {current_api.capitalize()} 요약 모델 미설정") # 사용자에게 알림
            if self.gui_manager: self.gui_manager.schedule_status_clear(f"⚠️ {current_api.capitalize()} 요약 모델 미설정", 3000)
            return
        if not novel_dir or not os.path.isdir(novel_dir): return
        if self.is_summarizing: print("CORE INFO: 이미 요약 작업 진행 중."); return
        if self.is_generating: print("CORE INFO: 생성 작업 중. 요약 건너뜀."); return

        print(f"CORE: 소설 '{os.path.basename(novel_dir)}' 줄거리 요약 생성 시작 (API: {current_api}, Model: {summary_model_for_current_api})...")
        self.is_summarizing = True
        self.start_timer("⏳ 이전 줄거리 요약 중...")
        self.update_ui_state()

        # 스레드 인자에 API 타입과 모델 전달
        thread_args = (current_api, summary_model_for_current_api, novel_dir)
        summary_thread = threading.Thread(
            target=self._run_summary_in_thread,
            args=thread_args,
            daemon=True
        )
        summary_thread.start()

    def _run_summary_in_thread(self, api_type, model_name, novel_dir):
        """백그라운드 스레드: 전체 장면 읽고 요약 API 호출 (API 타입 인자 추가)"""
        summary_result = None; error_detail = None; token_data = None; thread_id = threading.get_ident()
        print(f"CORE THREAD {thread_id}: 요약 작업 시작 (API: {api_type}, Model: {model_name}, Novel: {os.path.basename(novel_dir)})...")

        try:
            all_content = file_handler.get_all_chapter_scene_contents(novel_dir)
            if not all_content:
                print(f"CORE THREAD {thread_id}: 요약할 내용 없음.")
                summary_result = ""
            else:
                print(f"CORE THREAD {thread_id}: 총 {len(all_content):,}자 내용 요약 {api_type.upper()} API 호출...")
                # API 핸들러 호출 시 API 타입 전달
                summary_api_result, token_data = api_handler.generate_summary_api_call(api_type, model_name, all_content)
                if isinstance(summary_api_result, str) and summary_api_result.startswith("오류"):
                    print(f"CORE THREAD {thread_id}: ❌ 요약 {api_type.upper()} API 호출 실패: {summary_api_result}")
                    error_detail = summary_api_result; summary_result = None
                else:
                    print(f"CORE THREAD {thread_id}: ✅ 요약 {api_type.upper()} API 호출 성공.")
                    summary_result = summary_api_result
        except Exception as e:
            error_detail = f"요약 스레드 {thread_id} 내부 오류: {e}"; print(f"CORE THREAD {thread_id}: ❌ {error_detail}")
            traceback.print_exc(); summary_result = None
        finally:
            if self.gui_manager and self.gui_manager.root and self.gui_manager.root.winfo_exists():
                self.gui_manager.root.after(0, self._process_summary_result, novel_dir, summary_result, error_detail)
            else: print(f"CORE THREAD {thread_id}: GUI 루트 없음. 요약 결과 처리 불가.")

    def _process_summary_result(self, novel_dir, summary_text, error_detail):
        """요약 결과 처리 (메인 스레드에서 실행)"""
        print(f"CORE: 요약 결과 처리 시작 ({os.path.basename(novel_dir)})...")
        self.is_summarizing = False
        self.stop_timer()

        if not self.gui_manager or not self.gui_manager.settings_panel:
             print("CORE WARN: 요약 결과 처리 실패 - GUI 없음"); self.update_ui_state(); return

        if error_detail:
            print(f"CORE ERROR: 요약 생성 실패: {error_detail}")
            self.update_status_bar_conditional("⚠️ 이전 줄거리 요약 실패.")
        elif summary_text is not None:
            print(f"CORE: 요약 생성 성공. 길이: {len(summary_text)}자")
            if not self.current_novel_dir or os.path.normpath(novel_dir) != os.path.normpath(self.current_novel_dir):
                print("CORE WARN: 요약 완료 시점 소설과 현재 로드된 소설 불일치. 설정 파일 업데이트 건너뜀.")
            else:
                try:
                    novel_key = constants.NOVEL_MAIN_SETTINGS_KEY
                    # Get current novel setting text from GUI to preserve non-summary parts
                    current_novel_setting_text = self.gui_manager.settings_panel.get_novel_settings() or ""
                    summary_header = constants.SUMMARY_HEADER
                    text_before_summary = current_novel_setting_text
                    existing_summary_index = text_before_summary.find(summary_header)
                    if existing_summary_index != -1:
                        text_before_summary = text_before_summary[:existing_summary_index].rstrip()

                    new_summary_part = ""
                    summary_content = summary_text.strip()
                    if summary_content: new_summary_part = f"\n\n{summary_header}\n{summary_content}"

                    final_novel_setting = text_before_summary + new_summary_part
                    new_novel_data = {novel_key: final_novel_setting}

                    print(f"CORE: 업데이트된 소설 설정 저장 시도: {novel_dir}")
                    if file_handler.save_novel_settings(novel_dir, new_novel_data):
                        print("CORE: 요약 포함된 소설 설정 저장 완료.")
                        self.current_novel_settings[novel_key] = final_novel_setting
                        if self.gui_manager.settings_panel:
                            # Update the widget and reset modification flags
                            self.gui_manager.settings_panel.set_novel_settings(final_novel_setting)
                            # set_novel_settings should handle resetting flags internally

                        status_msg = "✅ 이전 줄거리 요약 업데이트 완료."
                        self.update_status_bar_conditional(status_msg)
                        if self.gui_manager: self.gui_manager.schedule_status_clear(status_msg, 3000)
                    else:
                        print("CORE ERROR: 요약 포함된 소설 설정 저장 실패.")
                        self.update_status_bar_conditional("⚠️ 이전 줄거리 요약 저장 실패.")

                except Exception as e:
                    print(f"CORE ERROR: 요약 결과 처리/저장 중 오류: {e}")
                    traceback.print_exc()
                    self.update_status_bar_conditional("⚠️ 이전 줄거리 요약 처리 오류.")
        else:
             print("CORE ERROR: 요약 생성 실패 (결과 없음).")
             self.update_status_bar_conditional("⚠️ 이전 줄거리 요약 실패 (결과 없음).")

        self.update_ui_state()

    # --- 내부 유틸리티 함수 ---
    def _get_chapter_number_from_folder(self, folder_path_or_name):
        if not folder_path_or_name or not isinstance(folder_path_or_name, str): return -1
        folder_name = os.path.basename(folder_path_or_name)
        match = re.match(r"^Chapter_(\d+)", folder_name, re.IGNORECASE)
        try: return int(match.group(1)) if match else -1
        except ValueError: return -1

    def _get_chapter_number_str_from_folder(self, folder_path_or_name):
        num = self._get_chapter_number_from_folder(folder_path_or_name)
        return f"{num:03d}화" if num >= 0 else "챕터"

    def _get_scene_number_from_path(self, scene_file_path):
        """Extracts scene number from file path like .../XXX.txt"""
        if not scene_file_path or not isinstance(scene_file_path, str): return -1
        filename = os.path.basename(scene_file_path)
        match = re.match(r"^(\d+)\.txt$", filename, re.IGNORECASE)
        try: return int(match.group(1)) if match else -1
        except ValueError: return -1

    # _load_previous_scene_content 함수는 이제 사용되지 않음 (삭제됨)

    def _get_latest_chapter_folder_info(self, novel_dir):
        """소설 내 마지막 챕터 폴더 번호와 경로 반환"""
        latest_num = 0; latest_path = None; chapter_pattern = re.compile(r"^Chapter_(\d+)", re.IGNORECASE); found = []
        try:
            if not os.path.isdir(novel_dir): return -1, None
            with os.scandir(novel_dir) as entries:
                for entry in entries:
                    if entry.is_dir():
                        match = chapter_pattern.match(entry.name)
                        if match and match.group(1).isdigit():
                            try: found.append((int(match.group(1)), entry.path))
                            except ValueError: pass
            if found: latest_num, latest_path = max(found, key=lambda x: x[0])
        except OSError as e: print(f"CORE ERROR: 최신 챕터 검색 OSError: {e}"); return -1, None
        except Exception as e: print(f"CORE ERROR: 최신 챕터 검색 오류: {e}"); traceback.print_exc(); return -1, None
        # print(f"CORE DEBUG: Latest chapter folder found: Num={latest_num}, Path={latest_path}")
        return latest_num, latest_path

    def _get_latest_scene_info(self, chapter_dir):
        """챕터 폴더 내 마지막 장면 번호와 경로 반환"""
        latest_num = 0; latest_path = None; scene_pattern = re.compile(r"^(\d+)\.txt$", re.IGNORECASE); found = []
        try:
            if not os.path.isdir(chapter_dir): return -1, None
            with os.scandir(chapter_dir) as entries:
                for entry in entries:
                    if entry.is_file():
                         match = scene_pattern.match(entry.name)
                         if match and match.group(1).isdigit():
                             try: found.append((int(match.group(1)), entry.path))
                             except ValueError: pass
            if found: latest_num, latest_path = max(found, key=lambda x: x[0])
        except OSError as e: print(f"CORE ERROR: 최신 장면 검색 OSError: {e}"); return -1, None
        except Exception as e: print(f"CORE ERROR: 최신 장면 검색 오류: {e}"); traceback.print_exc(); return -1, None
        # print(f"CORE DEBUG: Latest scene file found: Num={latest_num}, Path={latest_path}")
        return latest_num, latest_path

    def _trigger_chapter_settings_modified_in_gui(self):
        """GUI SettingsPanel의 수정 플래그 설정 요청"""
        if self.gui_manager and self.gui_manager.settings_panel:
             # SettingsPanel의 내부 함수를 직접 호출하여 플래그 설정
             self.gui_manager.settings_panel._trigger_chapter_settings_modified()
        else:
             print("CORE WARN: GUI SettingsPanel 없음. 수정 플래그 설정 불가.")

    def update_status_bar_conditional(self, message):
        """중요 메시지가 아닐 때만 상태 표시줄 업데이트"""
        if self.gui_manager and self.gui_manager.status_label_widget and self.gui_manager.status_label_widget.winfo_exists():
            try:
                current_text = self.gui_manager.get_status_bar_text()
                # 중요 접두사가 포함되어 있지 않으면 업데이트
                if not any(prefix in current_text for prefix in ["✅", "❌", "⚠️", "⏳", "🔄", "✨", "📄", "🗑️"]):
                    self.gui_manager.update_status_bar(message)
            except tk.TclError: pass # 위젯 파괴 시 무시

    def _validate_and_update_models_after_reconfig(self):
        """Helper to re-validate selected/summary models after API keys/config change."""
        print("CORE DEBUG: Validating models after API reconfiguration...")
        # 1. Re-validate current API type and selected model
        current_api_valid = self.current_api_type in self.available_models_by_type and self.available_models_by_type[self.current_api_type]
        if not current_api_valid:
             print(f"CORE WARN: 현재 API 타입 '{self.current_api_type}'이(가) 재설정 후 유효하지 않게 됨. 다른 API로 전환 시도.")
             # Find first valid API type
             found_valid = False
             for api_type in constants.SUPPORTED_API_TYPES:
                 if self.available_models_by_type.get(api_type):
                     self.current_api_type = api_type
                     self.available_models = self.available_models_by_type[api_type]
                     found_valid = True
                     break
             if not found_valid:
                  print("CORE ERROR: 재설정 후 사용 가능한 API가 없습니다!")
                  # Handle this critical error (e.g., show message, exit?)
                  self.current_api_type = constants.API_TYPE_GEMINI # Fallback guess
                  self.available_models = []
             else:
                  print(f"CORE INFO: 새 활성 API 타입으로 전환됨: {self.current_api_type}")
             # Force model re-selection for the new API type
             self.selected_model = None

        # Re-validate selected_model within the (potentially new) current API type
        current_models = self.available_models_by_type.get(self.current_api_type, [])
        if not self.selected_model or self.selected_model not in current_models:
             old_model = self.selected_model
             if current_models:
                 # Try default for this API type
                 default_model = None
                 if self.current_api_type == constants.API_TYPE_GEMINI: default_model = constants.DEFAULT_GEMINI_MODEL
                 elif self.current_api_type == constants.API_TYPE_CLAUDE: default_model = constants.DEFAULT_CLAUDE_MODEL
                 elif self.current_api_type == constants.API_TYPE_GPT: default_model = constants.DEFAULT_GPT_MODEL

                 if default_model and default_model in current_models:
                     self.selected_model = default_model
                 else:
                     self.selected_model = current_models[0] # Fallback to first
                 print(f"CORE INFO: API 재설정 후 창작 모델 변경됨: {old_model} -> {self.selected_model}")
             else: # No models for current API
                  self.selected_model = None
                  print(f"CORE WARN: API 재설정 후 현재 API 타입 '{self.current_api_type}'에 모델 없음.")


        # 2. Re-validate summary models for ALL API types
        print("CORE DEBUG: Re-validating summary models...")
        for api_type in constants.SUPPORTED_API_TYPES:
             api_models = self.available_models_by_type.get(api_type, [])
             current_summary = self.summary_models.get(api_type)
             if not api_models: # No models for this API type
                  if current_summary is not None:
                       print(f"CORE INFO: ({api_type.capitalize()}) 모델 목록 비어있음. 요약 모델 비활성화.")
                       self.summary_models[api_type] = None
             elif current_summary is None or current_summary not in api_models:
                  # Summary model needs update
                  old_summary = current_summary
                  # Try default summary model for this API type
                  default_summary = None
                  if api_type == constants.API_TYPE_GEMINI: default_summary = constants.DEFAULT_SUMMARY_MODEL_GEMINI
                  elif api_type == constants.API_TYPE_CLAUDE: default_summary = constants.DEFAULT_SUMMARY_MODEL_CLAUDE
                  elif api_type == constants.API_TYPE_GPT: default_summary = constants.DEFAULT_SUMMARY_MODEL_GPT

                  if default_summary and default_summary in api_models:
                       self.summary_models[api_type] = default_summary
                  else:
                       self.summary_models[api_type] = api_models[0] # Fallback to first available model
                  print(f"CORE INFO: ({api_type.capitalize()}) 요약 모델 변경됨: {old_summary} -> {self.summary_models[api_type]}")

        # Update the active summary model based on the potentially changed current_api_type
        self.summary_model = self.summary_models.get(self.current_api_type)
        print(f"CORE INFO: 활성 요약 모델 업데이트됨 -> {self.summary_model}")