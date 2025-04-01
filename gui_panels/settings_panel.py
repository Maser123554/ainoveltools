# gui_panels/settings_panel.py
import tkinter as tk
from tkinter import ttk
import os # basename 사용 위해 추가
import re # 정규표현식 사용 위해 추가
import constants
import utils # format_chapter_display_name 사용 위해 추가

class SettingsPanel(ttk.Frame):
    """설정 영역 GUI (좌측 상단)"""
    def __init__(self, parent, app_core, text_font, label_font, **kwargs):
        super().__init__(parent, padding=(constants.PAD_X, constants.PAD_Y), **kwargs)
        self.app_core = app_core
        self.text_font = text_font
        self.label_font = label_font

        self.widgets = {}
        self.novel_settings_widget_visible = False
        self.chapter_arc_notes_widget_visible = False
        self.scene_plot_widget_visible = False
        self.settings_area_visible = True

        # 이 플래그는 장면 플롯, 온도, 길이 등 장면 설정 스냅샷에 영향을 주는 변경사항을 추적합니다.
        self.chapter_settings_modified_flag = False
        self._chapter_settings_after_id = None # This seems unused after the refactor, might remove later.

        self._create_widgets()
        # 초기 UI 상태 설정은 AppCore에서 set_gui_manager 호출 후 진행

    def _create_widgets(self):
        """설정 패널의 위젯들 생성"""
        self.columnconfigure(0, weight=1)

        # --- 1. 전체 설정 토글 버튼 ---
        self.widgets['toggle_settings_button'] = ttk.Button(self, text="▲ 설정 숨기기",
                                                            command=self._toggle_settings_area_visibility,
                                                            style='Toolbutton', takefocus=0)
        self.widgets['toggle_settings_button'].grid(row=0, column=0, sticky='w', pady=(0, constants.PAD_Y // 2))

        # --- 2. 설정 위젯들을 담을 프레임 ---
        self.settings_frame_outer = ttk.Frame(self)
        self.settings_frame_outer.grid(row=1, column=0, sticky="nsew")
        self.settings_frame_outer.columnconfigure(0, weight=1)
        outer_row = 0

        # === 2-1. AI 창작 모델 선택 영역 ===
        model_frame = ttk.Frame(self.settings_frame_outer)
        model_frame.grid(row=outer_row, column=0, sticky="new", pady=(0, constants.PAD_Y))
        model_frame.columnconfigure(2, weight=1)  # 모델 선택 컬럼 확장
        outer_row += 1 # row 증가
        ttk.Label(model_frame, text="1. AI 창작 모델:", style='Bold.TLabel').grid(row=0, column=0, padx=(0, constants.PAD_X//2), sticky="nw") # 라벨 간격 조정

        # API 타입 선택 콤보박스
        api_type_combo = ttk.Combobox(model_frame, values=constants.SUPPORTED_API_TYPES, width=8, state="readonly", font=self.text_font) # 폭 조정
        api_type_combo.grid(row=0, column=1, padx=(0, constants.PAD_X//2), sticky="w") # 라벨과 간격 조정
        self.widgets['api_type_combobox'] = api_type_combo

        # 모델 선택 콤보박스 (API 타입 변경 시 업데이트됨)
        model_combo = ttk.Combobox(model_frame, width=28, state="readonly", font=self.text_font) # 폭 조정
        model_combo.grid(row=0, column=2, padx=(constants.PAD_X//2, 0), sticky="ew") # 왼쪽 패딩 추가
        self.widgets['model_combobox'] = model_combo

        # 이벤트 바인딩
        api_type_combo.bind("<<ComboboxSelected>>", self._on_api_type_selected)
        model_combo.bind("<<ComboboxSelected>>", self._on_model_selected)

        # === 2-2. 소설 전체 설정 그룹 ===
        novel_group_frame = ttk.Frame(self.settings_frame_outer)
        novel_group_frame.grid(row=outer_row, column=0, sticky="new", pady=(constants.PAD_Y, constants.PAD_Y//2))
        outer_row += 1
        ttk.Label(novel_group_frame, text="[소설 전체 설정]", style='Bold.TLabel').pack(side=tk.LEFT, anchor='w')
        novel_toggle_btn = ttk.Button(novel_group_frame, text="⚙️ 보기/숨기기",
                                       command=self._toggle_novel_settings_visibility, style='Toolbutton', takefocus=0)
        novel_toggle_btn.pack(side=tk.LEFT, padx=(constants.PAD_X, 0))
        self.widgets['novel_settings_toggle_button'] = novel_toggle_btn

        self.novel_settings_wrapper = ttk.Frame(self.settings_frame_outer, padding=(0, 0))
        self.novel_settings_wrapper.grid(row=outer_row, column=0, sticky="nsew", padx=0, pady=0)
        self.novel_settings_wrapper.columnconfigure(0, weight=1)
        self.novel_settings_wrapper.rowconfigure(1, weight=1)
        outer_row += 1
        novel_label_text = f"  (소설 설정: 세계관, 주요 인물, 줄거리 등)" # 초기/기본 텍스트
        novel_label = ttk.Label(self.novel_settings_wrapper, text=novel_label_text)
        novel_label.grid(row=0, column=0, sticky='nw', padx=(constants.PAD_X // 2, 0))
        self.widgets['novel_settings_label'] = novel_label # 나중에 업데이트하기 위해 저장
        novel_text_widget, novel_scroll = self._create_text_area(self.novel_settings_wrapper, height=8)
        novel_text_widget.grid(row=1, column=0, sticky="nsew", padx=constants.PAD_X//2, pady=(0, constants.PAD_Y // 2))
        novel_scroll.grid(row=1, column=1, sticky="ns", pady=(0, constants.PAD_Y // 2))
        self.widgets['novel_settings_text'] = novel_text_widget
        novel_text_widget.bind("<<Modified>>", self._on_novel_settings_modified) # 소설 설정 수정 핸들러
        self.novel_settings_wrapper.grid_remove()
        novel_text_widget.config(state=tk.DISABLED)

        # === 2-3. 챕터 전체 설정 그룹 ===
        arc_group_frame = ttk.Frame(self.settings_frame_outer)
        arc_group_frame.grid(row=outer_row, column=0, sticky="new", pady=(constants.PAD_Y, constants.PAD_Y//2))
        outer_row += 1
        ttk.Label(arc_group_frame, text="[챕터 전체 설정]", style='Bold.TLabel').pack(side=tk.LEFT, anchor='w')
        arc_toggle_btn = ttk.Button(arc_group_frame, text="⚙️ 보기/숨기기",
                                      command=self._toggle_chapter_arc_notes_visibility, style='Toolbutton', takefocus=0)
        arc_toggle_btn.pack(side=tk.LEFT, padx=(constants.PAD_X, 0))
        self.widgets['chapter_arc_notes_toggle_button'] = arc_toggle_btn

        self.chapter_arc_notes_wrapper = ttk.Frame(self.settings_frame_outer, padding=(0,0))
        self.chapter_arc_notes_wrapper.grid(row=outer_row, column=0, sticky="nsew", padx=0, pady=0)
        self.chapter_arc_notes_wrapper.columnconfigure(0, weight=1)
        self.chapter_arc_notes_wrapper.rowconfigure(1, weight=1)
        outer_row += 1
        arc_label_text = f"  (챕터 설정: 챕터의 전반적인 플롯)" # 초기/기본 텍스트
        arc_label = ttk.Label(self.chapter_arc_notes_wrapper, text=arc_label_text)
        arc_label.grid(row=0, column=0, sticky='nw', padx=(constants.PAD_X // 2, 0))
        self.widgets['chapter_arc_notes_label'] = arc_label # 나중에 업데이트 위해 저장
        arc_text_widget, arc_scroll = self._create_text_area(self.chapter_arc_notes_wrapper, height=4, state=tk.NORMAL)
        arc_text_widget.grid(row=1, column=0, sticky="nsew", padx=constants.PAD_X//2, pady=(0, constants.PAD_Y // 2))
        arc_scroll.grid(row=1, column=1, sticky="ns", pady=(0, constants.PAD_Y // 2))
        # *** 수정: 아크 노트 전용 핸들러 바인딩 ***
        arc_text_widget.bind("<<Modified>>", self._on_arc_notes_modified)
        self.widgets['chapter_arc_notes_text'] = arc_text_widget
        self.chapter_arc_notes_wrapper.grid_remove()
        arc_text_widget.config(state=tk.DISABLED)

        # === 2-4. 장면 플롯 그룹 ===
        plot_group_frame = ttk.Frame(self.settings_frame_outer)
        plot_group_frame.grid(row=outer_row, column=0, sticky="new", pady=(constants.PAD_Y, constants.PAD_Y//2))
        outer_row += 1
        ttk.Label(plot_group_frame, text="[장면 플롯]", style='Bold.TLabel').pack(side=tk.LEFT, anchor='w')
        plot_toggle_btn = ttk.Button(plot_group_frame, text="⚙️ 보기/숨기기",
                                      command=self._toggle_scene_plot_visibility, style='Toolbutton', takefocus=0)
        plot_toggle_btn.pack(side=tk.LEFT, padx=(constants.PAD_X, 0))
        self.widgets['scene_plot_toggle_button'] = plot_toggle_btn

        self.scene_plot_wrapper = ttk.Frame(self.settings_frame_outer, padding=(0,0))
        self.scene_plot_wrapper.grid(row=outer_row, column=0, sticky="nsew", padx=0, pady=0)
        self.scene_plot_wrapper.columnconfigure(0, weight=1)
        self.scene_plot_wrapper.rowconfigure(1, weight=1)
        outer_row += 1
        ttk.Label(self.scene_plot_wrapper, text="  이번화의 상세 전개", style='Bold.TLabel').grid(row=0, column=0, sticky='nw', padx=(constants.PAD_X // 2, 0))
        plot_text_widget, plot_scroll = self._create_text_area(self.scene_plot_wrapper, height=5, state=tk.NORMAL)
        plot_text_widget.grid(row=1, column=0, sticky="nsew", padx=constants.PAD_X//2, pady=(0, constants.PAD_Y // 2))
        plot_scroll.grid(row=1, column=1, sticky="ns", pady=(0, constants.PAD_Y // 2))
        # *** 수정: 장면 플롯은 _on_chapter_settings_modified 핸들러 사용 (유지) ***
        plot_text_widget.bind("<<Modified>>", self._on_chapter_settings_modified)
        self.widgets['scene_plot_text'] = plot_text_widget
        self.scene_plot_wrapper.grid_remove()
        plot_text_widget.config(state=tk.DISABLED)

        # === 2-5. 기타 생성 옵션 ===
        options_frame = ttk.LabelFrame(self.settings_frame_outer, text="[생성 옵션]", padding=(constants.PAD_X, constants.PAD_Y//2))
        options_frame.grid(row=outer_row, column=0, sticky="ew", padx=0, pady=(constants.PAD_Y, 0))
        options_frame.grid_columnconfigure(1, weight=1)
        outer_row += 1 # row 증가
        # 온도
        ttk.Label(options_frame, text="3. 창의성(T):", style='Bold.TLabel').grid(row=0, column=0, padx=constants.PAD_X//2, pady=constants.PAD_Y//2, sticky="nw")
        temp_subframe = ttk.Frame(options_frame)
        temp_subframe.grid(row=0, column=1, padx=constants.PAD_X//2, pady=constants.PAD_Y//2, sticky="ew")
        temp_scale = ttk.Scale(temp_subframe, from_=0.0, to=2.0, orient=tk.HORIZONTAL, length=200, value=constants.DEFAULT_TEMPERATURE, command=self._update_temperature_label)
        temp_scale.pack(side=tk.LEFT, fill=tk.X, expand=True)
        temp_label = ttk.Label(temp_subframe, text="", style='Value.TLabel', width=4, anchor='w')
        temp_label.pack(side=tk.LEFT, padx=(constants.PAD_X // 2, 0))
        temp_scale.bind("<Button-1>", self._handle_scale_click)
        temp_scale.bind("<B1-Motion>", self._on_scale_drag)
        temp_scale.bind("<ButtonRelease-1>", self._on_scale_release) # 스케일 변경 완료 핸들러
        self.widgets['temperature_scale'] = temp_scale
        self.widgets['temperature_label'] = temp_label
        self._update_temperature_label()
        # 길이
        ttk.Label(options_frame, text="4. 생성 분량:", style='Bold.TLabel').grid(row=1, column=0, padx=constants.PAD_X//2, pady=constants.PAD_Y//2, sticky="nw")
        length_combo = ttk.Combobox(options_frame, values=constants.LENGTH_OPTIONS, width=45, state="readonly", font=self.text_font)
        length_combo.grid(row=1, column=1, padx=constants.PAD_X//2, pady=constants.PAD_Y//2, sticky="ew")
        length_combo.current(0) # 기본값 선택
        length_combo.bind("<<ComboboxSelected>>", self._on_chapter_settings_modified) # 길이 변경 핸들러
        self.widgets['length_combobox'] = length_combo

        # === 2-6. 액션 버튼 ===
        button_frame = ttk.Frame(self.settings_frame_outer)
        button_frame.grid(row=outer_row, column=0, pady=(constants.PAD_Y * 1.5, 0), sticky='ew')
        outer_row += 1 # row 증가
        btn_new_novel = ttk.Button(button_frame, text=" ✨ 새 소설 ", command=self.app_core.handle_new_novel_request)
        btn_new_novel.grid(row=0, column=0, padx=(0, constants.PAD_X//2), ipady=constants.PAD_Y//2)
        btn_new_chapter_folder = ttk.Button(button_frame, text=" 📁 새 챕터 폴더 ", command=self.app_core.handle_new_chapter_folder_request)
        btn_new_chapter_folder.grid(row=0, column=1, padx=constants.PAD_X//2, ipady=constants.PAD_Y//2)
        btn_new_scene = ttk.Button(button_frame, text=" 🎬 새 장면 ", command=self.app_core.handle_new_scene_request)
        btn_new_scene.grid(row=0, column=2, padx=constants.PAD_X//2, ipady=constants.PAD_Y//2)
        btn_regenerate = ttk.Button(button_frame, text=" 🔄 장면 재생성", command=self.app_core.handle_regenerate_request)
        btn_regenerate.grid(row=0, column=3, padx=constants.PAD_X//2, ipady=constants.PAD_Y//2)
        self.widgets['new_novel_button'] = btn_new_novel
        self.widgets['new_chapter_folder_button'] = btn_new_chapter_folder
        self.widgets['new_scene_button'] = btn_new_scene
        self.widgets['regenerate_button'] = btn_regenerate

        # === 2-7. 상태 표시줄 ===
        status_label = ttk.Label(self.settings_frame_outer, text="초기화 중...", style='Status.TLabel', anchor=tk.W, wraplength=450)
        status_label.grid(row=outer_row, column=0, pady=(constants.PAD_Y, 0), sticky='ew')
        outer_row += 1 # row 증가
        self.status_label = status_label


    def _create_text_area(self, parent, height, state=tk.NORMAL):
        """텍스트 위젯과 스크롤바 생성 헬퍼"""
        text_widget = tk.Text(parent, height=height, width=50, wrap=tk.WORD, font=self.text_font,
                              padx=constants.PAD_X // 2, pady=constants.PAD_Y // 2,
                              relief=tk.SOLID, borderwidth=1, undo=True, state=state)
        scroll = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=text_widget.yview)
        text_widget['yscrollcommand'] = scroll.set
        return text_widget, scroll


    # --- 위젯 이벤트 핸들러 ---

    def _on_api_type_selected(self, event=None):
        """API 타입 변경 시 호출되는 핸들러"""
        combo = self.widgets.get('api_type_combobox')
        if combo and combo.winfo_exists():
            new_api_type = combo.get().lower() # Gemini -> gemini, Claude -> claude, GPT -> gpt
            print(f"GUI: API 타입 변경 선택됨: {new_api_type}")
            # AppCore에 변경 알림 (AppCore가 상태 업데이트 후 모델 목록 반환)
            if hasattr(self.app_core, 'handle_api_type_change'):
                self.app_core.handle_api_type_change(new_api_type)
            # AppCore 변경 후, 이 패널의 모델 목록 업데이트
            self._update_models_for_api_type(new_api_type)
            # API 타입 변경도 저장 대상 변경으로 간주 -> chapter_settings_modified 트리거
            self._trigger_chapter_settings_modified()

    def _update_models_for_api_type(self, api_type):
        """선택된 API 타입에 따라 모델 콤보박스 업데이트"""
        model_combo = self.widgets.get('model_combobox')
        if not model_combo or not model_combo.winfo_exists(): return

        # AppCore에서 해당 API 타입의 업데이트된 모델 목록 가져오기
        models = []
        if hasattr(self.app_core, 'get_models_by_api_type'):
            models = self.app_core.get_models_by_api_type(api_type)
        else: # 비상시
            print("GUI WARN: AppCore에 get_models_by_api_type 없음.")
            models = self.app_core.available_models_by_type.get(api_type, [])

        print(f"GUI: '{api_type}'에 대한 모델 목록 업데이트: {models}")
        model_combo['values'] = models

        # 현재 선택된 모델 유지 또는 기본값 설정
        current_session_model = self.app_core.selected_model # AppCore가 관리하는 현재 모델
        if current_session_model and current_session_model in models:
            model_combo.set(current_session_model)
        elif models:
            model_combo.set(models[0]) # 첫 번째 항목 선택
            print(f"GUI: 모델 자동 변경됨 -> {models[0]}. AppCore 알림.")
            if models[0] != self.app_core.selected_model: # Only notify if actually changed
                 self.app_core.handle_model_change(models[0])
        else:
            model_combo.set("모델 없음")
            model_combo.config(state=tk.DISABLED)
            print(f"GUI WARN: '{api_type}'에 사용 가능한 모델 없음. AppCore 모델 비우기.")
            if self.app_core.selected_model is not None: # Only notify if actually changed
                self.app_core.handle_model_change(None)


    def _on_model_selected(self, event=None):
        """창작 모델 콤보박스 선택 시 AppCore에 알림 & 수정 플래그 설정"""
        combo = self.widgets.get('model_combobox')
        if not combo or not combo.winfo_exists(): return

        selected = combo.get()
        if selected and selected != "모델 없음":
             # AppCore 핸들러 호출 전에 비교하여 변경 시에만 플래그 설정
             if selected != self.app_core.selected_model:
                 print(f"GUI: 모델 변경 선택됨 -> {selected}")
                 self._trigger_chapter_settings_modified() # 모델 변경도 장면 설정 변경으로 간주
                 self.app_core.handle_model_change(selected)
             else:
                 print(f"GUI DEBUG: 모델 선택됨 (변경 없음): {selected}")
        else:
             print("GUI WARN: 유효하지 않은 모델 선택됨.")


    def _on_novel_settings_modified(self, event=None):
        """소설 설정 텍스트 수정 시 AppCore에 알림"""
        widget = self.widgets.get('novel_settings_text')
        # Ensure widget exists, is modified by user, and not currently disabled
        if widget and widget.winfo_exists() and widget.edit_modified() and widget.cget('state') == tk.NORMAL:
            # Check AppCore's busy state using is_busy()
            if hasattr(self.app_core, 'is_busy') and not self.app_core.is_busy():
                self.app_core.handle_novel_settings_modified()
            widget.edit_modified(False) # Reset Tk flag immediately

    # *** 추가된 메소드: 아크 노트 전용 핸들러 ***
    def _on_arc_notes_modified(self, event=None):
        """챕터 아크 노트 텍스트 수정 시 AppCore에 알림"""
        widget = self.widgets.get('chapter_arc_notes_text')
        # Ensure widget exists, is modified by user, and not currently disabled
        if widget and widget.winfo_exists() and widget.edit_modified() and widget.cget('state') == tk.NORMAL:
            # Check AppCore's busy state using is_busy()
            if hasattr(self.app_core, 'is_busy') and not self.app_core.is_busy():
                # Call the correct AppCore handler for arc notes modification
                self.app_core.handle_arc_settings_modified()
            widget.edit_modified(False) # Reset Tk flag immediately

    # *** 수정된 메소드: 장면 플롯, 길이, 온도 관련 핸들러 ***
    def _on_chapter_settings_modified(self, event=None):
        """챕터/장면 관련 설정(장면플롯, 옵션) 변경 시 플래그 설정"""
        modified = False

        # Check Text widgets (Scene Plot ONLY)
        plot_widget = self.widgets.get('scene_plot_text')
        if plot_widget and plot_widget.winfo_exists() and plot_widget.edit_modified() and plot_widget.cget('state') == tk.NORMAL:
            plot_widget.edit_modified(False) # Reset internal flag
            modified = True
            print(f"GUI DEBUG: 'scene_plot_text' 수정됨.")

        # Check Combobox (length)
        length_combo = self.widgets.get('length_combobox')
        # Check if the event was triggered by this widget specifically
        if event and event.widget == length_combo:
            # Compare with AppCore's currently loaded scene setting for length if available
            current_length = ""
            if self.app_core.current_loaded_scene_settings:
                current_length = self.app_core.current_loaded_scene_settings.get('length')
            # Only mark as modified if the value actually changed
            if length_combo.get() != current_length:
                modified = True
                print("GUI DEBUG: Length Combobox 변경됨.")

        # Scale changes are handled by _on_scale_release

        if modified:
            self._trigger_chapter_settings_modified() # This sets the panel's flag for scene snapshot save

    def _on_scale_drag(self, event=None):
         self._update_temperature_label()

    def _on_scale_release(self, event=None):
        scale = self.widgets.get('temperature_scale')
        if scale and scale.winfo_exists() and scale.cget('state') == tk.NORMAL:
            self._update_temperature_label()
            # Compare with AppCore's currently loaded scene setting for temperature
            current_temp = constants.DEFAULT_TEMPERATURE # Default value if not loaded
            if self.app_core.current_loaded_scene_settings:
                 loaded_temp_val = self.app_core.current_loaded_scene_settings.get('temperature')
                 if loaded_temp_val is not None:
                     try: current_temp = float(loaded_temp_val)
                     except (ValueError, TypeError): pass
            # Only trigger modification if the value actually changed significantly
            new_val = scale.get()
            if abs(new_val - current_temp) > 0.001: # Use a small tolerance
                print("GUI DEBUG: Temperature Scale 변경됨.")
                self._trigger_chapter_settings_modified() # 변경 완료 시 플래그 설정
            else:
                print("GUI DEBUG: Temperature Scale 값 변경 없음.")


    def _trigger_chapter_settings_modified(self):
        """장면 스냅샷 관련 설정(플롯, 옵션, 모델) 변경 시 호출되는 공통 로직"""
        # Check AppCore's busy state using is_busy()
        if hasattr(self.app_core, 'is_busy') and not self.app_core.is_busy():
            if not self.chapter_settings_modified_flag:
                print("GUI DEBUG: 장면 설정(플롯/옵션/모델) 변경 감지됨. 스냅샷 플래그 설정.")
                self.chapter_settings_modified_flag = True
            self.app_core.update_ui_state() # UI 상태 업데이트 (저장 버튼 활성화 등)


    def _update_temperature_label(self, value=None):
        """온도 스케일 값 라벨 업데이트"""
        scale = self.widgets.get('temperature_scale')
        label = self.widgets.get('temperature_label')
        if scale and scale.winfo_exists() and label and label.winfo_exists():
            try:
                val = scale.get()
                label.config(text=f"{val:.2f}")
            except tk.TclError: pass
            except Exception as e: print(f"GUI WARN: 온도 라벨 업데이트 오류: {e}")

    def _handle_scale_click(self, event):
        """온도 스케일 트러프 클릭 시 값 조정 및 수정 플래그 설정"""
        scale = event.widget
        if not isinstance(scale, ttk.Scale) or scale.cget('state') == tk.DISABLED: return
        try:
            element = scale.identify(event.x, event.y)
            if 'trough' in element:
                current_val = scale.get()
                increment = 0.1 # Adjust step
                scale_from, scale_to = scale.cget("from"), scale.cget("to")
                value_range = scale_to - scale_from
                width = scale.winfo_width()
                if width <= 0: return # Avoid division by zero if width is not yet known

                clicked_ratio = event.x / width
                estimated_value_at_click = scale_from + clicked_ratio * value_range

                new_val = current_val
                if estimated_value_at_click < current_val - 0.01: # Clicked significantly to the left
                    new_val = current_val - increment
                elif estimated_value_at_click > current_val + 0.01: # Clicked significantly to the right
                    new_val = current_val + increment

                new_val = max(scale_from, min(scale_to, new_val))

                if abs(new_val - current_val) > 0.01: # Only set if value changed noticeably
                    scale.set(new_val)
                    self._update_temperature_label()
                    # Compare with AppCore's currently loaded scene setting for temperature
                    current_temp_loaded = constants.DEFAULT_TEMPERATURE
                    if self.app_core.current_loaded_scene_settings:
                        loaded_temp_val_click = self.app_core.current_loaded_scene_settings.get('temperature')
                        if loaded_temp_val_click is not None:
                             try: current_temp_loaded = float(loaded_temp_val_click)
                             except (ValueError, TypeError): pass
                    # Only trigger if changed from original loaded value
                    if abs(new_val - current_temp_loaded) > 0.001:
                        print("GUI DEBUG: Temperature Scale 클릭으로 변경됨.")
                        self._trigger_chapter_settings_modified() # Click also triggers modification
                    else:
                        print("GUI DEBUG: Temperature Scale 클릭 (값 변경 없음).")

                return "break" # Prevent default slider jump
        except Exception as e: print(f"GUI ERROR: 온도 스케일 클릭 처리 오류: {e}")


    # --- 위젯 표시/숨김 토글 ---
    def _toggle_settings_area_visibility(self):
        btn = self.widgets['toggle_settings_button']
        if self.settings_area_visible:
            self.settings_frame_outer.grid_remove()
            self.settings_area_visible = False
            btn.config(text="▼ 설정 보이기")
            self._update_novel_settings_visibility(force_hide=True)
            self._update_chapter_arc_notes_visibility(force_hide=True)
            self._update_scene_plot_visibility(force_hide=True)
        else:
            self.settings_frame_outer.grid()
            self.settings_area_visible = True
            btn.config(text="▲ 설정 숨기기")
            self._update_novel_settings_visibility()
            self._update_chapter_arc_notes_visibility()
            self._update_scene_plot_visibility()
        self.app_core.update_ui_state()

    def _toggle_novel_settings_visibility(self):
        self.novel_settings_widget_visible = not self.novel_settings_widget_visible
        self._update_novel_settings_visibility()
        self.app_core.update_ui_state()

    def _toggle_chapter_arc_notes_visibility(self):
        self.chapter_arc_notes_widget_visible = not self.chapter_arc_notes_widget_visible
        self._update_chapter_arc_notes_visibility()
        self.app_core.update_ui_state()

    def _toggle_scene_plot_visibility(self):
        self.scene_plot_widget_visible = not self.scene_plot_widget_visible
        self._update_scene_plot_visibility()
        self.app_core.update_ui_state()

    def _update_novel_settings_visibility(self, force_hide=False):
        widget = self.widgets.get('novel_settings_text')
        wrapper = self.novel_settings_wrapper
        if not wrapper or not wrapper.winfo_exists(): return
        should_be_visible = self.settings_area_visible and self.novel_settings_widget_visible and not force_hide
        if should_be_visible:
            wrapper.grid()
            if widget and widget.winfo_exists():
                is_busy = self.app_core.is_busy() if hasattr(self.app_core, 'is_busy') else False
                widget.config(state=tk.DISABLED if (is_busy or not self.app_core.current_novel_dir) else tk.NORMAL)
        else:
            wrapper.grid_remove()
            if widget and widget.winfo_exists(): widget.config(state=tk.DISABLED)

    def _update_chapter_arc_notes_visibility(self, force_hide=False):
        widget = self.widgets.get('chapter_arc_notes_text')
        wrapper = self.chapter_arc_notes_wrapper
        if not wrapper or not wrapper.winfo_exists(): return
        should_be_visible = self.settings_area_visible and self.chapter_arc_notes_widget_visible and not force_hide
        if should_be_visible:
            wrapper.grid()
            if widget and widget.winfo_exists():
                 is_busy = self.app_core.is_busy() if hasattr(self.app_core, 'is_busy') else False
                 widget.config(state=tk.DISABLED if (is_busy or not self.app_core.current_chapter_arc_dir) else tk.NORMAL)
        else:
            wrapper.grid_remove()
            if widget and widget.winfo_exists(): widget.config(state=tk.DISABLED)

    def _update_scene_plot_visibility(self, force_hide=False):
        widget = self.widgets.get('scene_plot_text')
        wrapper = self.scene_plot_wrapper
        if not wrapper or not wrapper.winfo_exists(): return
        should_be_visible = self.settings_area_visible and self.scene_plot_widget_visible and not force_hide
        if should_be_visible:
            wrapper.grid()
            if widget and widget.winfo_exists():
                 is_busy = self.app_core.is_busy() if hasattr(self.app_core, 'is_busy') else False
                 widget.config(state=tk.DISABLED if (is_busy or not self.app_core.current_scene_path) else tk.NORMAL)
        else:
            wrapper.grid_remove()
            if widget and widget.winfo_exists(): widget.config(state=tk.DISABLED)

    def _update_dynamic_labels(self):
        """Update labels that depend on the currently loaded novel/chapter."""
        novel_label = self.widgets.get('novel_settings_label')
        if novel_label and novel_label.winfo_exists():
            novel_name = self.app_core.current_novel_name if self.app_core.current_novel_name else "소설"
            novel_label.config(text=f"  ({novel_name} 설정: 세계관, 주요 인물, 줄거리 등)")

        arc_label = self.widgets.get('chapter_arc_notes_label')
        if arc_label and arc_label.winfo_exists():
            chapter_name = "챕터" # Default
            if self.app_core.current_chapter_arc_dir:
                try:
                    folder_name = os.path.basename(self.app_core.current_chapter_arc_dir)
                    formatted_name = utils.format_chapter_display_name(folder_name)
                    match = re.match(r"^\s*📁?\s*(.*)", formatted_name) # Allow optional folder icon and leading space
                    chapter_name = match.group(1).strip() if match else folder_name
                except Exception as e:
                    print(f"GUI WARN: 챕터 이름 포맷 중 오류: {e}")
                    pass # 오류 시 기본값 "챕터" 사용
            arc_label.config(text=f"  ({chapter_name} 설정: 챕터의 전반적인 플롯)")


    # --- AppCore에서 호출하는 메소드 ---

    def update_ui_state(self, is_busy: bool, novel_loaded: bool, chapter_loaded: bool, scene_loaded: bool):
        """AppCore의 상태에 따라 위젯 활성화/비활성화"""
        gen_state = tk.DISABLED if is_busy else tk.NORMAL
        combo_state = tk.DISABLED if is_busy else 'readonly'

        # API 타입 콤보박스
        api_combo = self.widgets.get('api_type_combobox')
        if api_combo and api_combo.winfo_exists():
            num_available_apis = sum(1 for models in self.app_core.available_models_by_type.values() if models)
            api_combo.config(state=tk.DISABLED if (is_busy or num_available_apis < 2) else 'readonly')

        # 모델 콤보박스
        model_combo = self.widgets.get('model_combobox')
        if model_combo and model_combo.winfo_exists():
            current_api_models = self.app_core.available_models_by_type.get(self.app_core.current_api_type, [])
            model_combo.config(state=tk.DISABLED if (is_busy or not current_api_models) else 'readonly')

        # 온도 스케일 & 길이 콤보박스 (장면 생성 옵션)
        temp_scale = self.widgets.get('temperature_scale')
        if temp_scale and temp_scale.winfo_exists(): temp_scale.config(state=gen_state if scene_loaded else tk.DISABLED) # 장면 로드 시에만 활성
        length_combo = self.widgets.get('length_combobox')
        if length_combo and length_combo.winfo_exists(): length_combo.config(state=combo_state if scene_loaded else tk.DISABLED) # 장면 로드 시에만 활성

        # 소설 설정 텍스트 (소설 로드 시 & 토글 켜졌을 때 편집 가능)
        self._update_novel_settings_visibility() # Visibility update handles state based on loaded status

        # 챕터 아크 노트 텍스트 (챕터 로드 시 & 토글 켜졌을 때 편집 가능)
        self._update_chapter_arc_notes_visibility()

        # 장면 플롯 텍스트 (장면 로드 시 & 토글 켜졌을 때 편집 가능)
        self._update_scene_plot_visibility()

        # 토글 버튼들 (Busy 상태에만 영향받음)
        for key in ['novel_settings_toggle_button', 'chapter_arc_notes_toggle_button', 'scene_plot_toggle_button', 'toggle_settings_button']:
            btn = self.widgets.get(key)
            if btn and btn.winfo_exists(): btn.config(state=gen_state)

        # 액션 버튼들
        btn_new_novel = self.widgets.get('new_novel_button')
        if btn_new_novel and btn_new_novel.winfo_exists(): btn_new_novel.config(state=gen_state)

        btn_new_chapter_folder = self.widgets.get('new_chapter_folder_button')
        if btn_new_chapter_folder and btn_new_chapter_folder.winfo_exists():
            btn_new_chapter_folder.config(state=tk.DISABLED if (is_busy or not novel_loaded) else tk.NORMAL)

        btn_new_scene = self.widgets.get('new_scene_button')
        if btn_new_scene and btn_new_scene.winfo_exists():
            btn_new_scene.config(state=tk.DISABLED if (is_busy or not chapter_loaded) else tk.NORMAL)

        btn_regenerate = self.widgets.get('regenerate_button')
        if btn_regenerate and btn_regenerate.winfo_exists():
            btn_regenerate.config(state=tk.DISABLED if (is_busy or not scene_loaded) else tk.NORMAL)


    def populate_widgets(self, novel_settings_data, chapter_arc_settings_data, scene_settings_data):
        """AppCore에서 받은 데이터로 위젯 내용 채우기"""
        is_busy = self.app_core.is_busy() if hasattr(self.app_core, 'is_busy') else False
        novel_loaded = bool(self.app_core.current_novel_dir)
        chapter_loaded = bool(self.app_core.current_chapter_arc_dir)
        scene_loaded = bool(self.app_core.current_scene_path)

        # API 타입 콤보박스
        api_combo = self.widgets.get('api_type_combobox')
        if api_combo and api_combo.winfo_exists():
             try:
                 api_display_val = self.app_core.current_api_type.capitalize()
                 if api_display_val in api_combo['values']:
                     api_combo.set(api_display_val)
                 elif api_combo['values']: # Set to first available if current not found
                     api_combo.set(api_combo['values'][0])
             except tk.TclError: pass
             except Exception as e: print(f"GUI WARN: API 콤보박스 설정 중 오류: {e}")


        # 모델 콤보박스 (API 타입 설정 후 모델 목록 업데이트)
        self._update_models_for_api_type(self.app_core.current_api_type) # Ensure model list is correct
        model_combo = self.widgets.get('model_combobox')
        if model_combo and model_combo.winfo_exists():
             try:
                 model_val = scene_settings_data.get('selected_model', self.app_core.selected_model) if scene_settings_data else self.app_core.selected_model
                 current_api_models = self.app_core.available_models_by_type.get(self.app_core.current_api_type, [])

                 if model_val and model_val in current_api_models:
                      model_combo.set(model_val)
                      if model_val != self.app_core.selected_model:
                           self.app_core.handle_model_change(model_val) # Notify AppCore
                 elif self.app_core.selected_model in current_api_models:
                      model_combo.set(self.app_core.selected_model)
                 else: # Fallback
                      if current_api_models:
                          model_combo.set(current_api_models[0])
                          if current_api_models[0] != self.app_core.selected_model:
                              self.app_core.handle_model_change(current_api_models[0]) # Notify AppCore
                      else:
                          model_combo.set("모델 없음")
                          if self.app_core.selected_model is not None:
                              self.app_core.handle_model_change(None) # Notify AppCore

             except tk.TclError: pass
             except Exception as e: print(f"GUI WARN: 모델 콤보박스 설정 중 오류: {e}")


        # --- 소설 설정 ---
        novel_key = constants.NOVEL_MAIN_SETTINGS_KEY
        novel_widget = self.widgets.get('novel_settings_text')
        if novel_widget and novel_widget.winfo_exists():
             try:
                 novel_value = novel_settings_data.get(novel_key, "") if novel_settings_data else ""
                 is_novel_visible = self.settings_area_visible and self.novel_settings_widget_visible
                 current_novel_state = tk.DISABLED if (is_busy or not novel_loaded or not is_novel_visible) else tk.NORMAL

                 novel_widget.config(state=tk.NORMAL) # Temp enable
                 novel_widget.delete("1.0", tk.END)
                 novel_widget.insert("1.0", novel_value)
                 novel_widget.edit_reset(); novel_widget.edit_modified(False)
                 novel_widget.config(state=current_novel_state) # Restore state
             except tk.TclError: pass

        # --- 챕터 전체 설정 (아크 노트) ---
        arc_key = constants.CHAPTER_ARC_NOTES_KEY
        arc_widget = self.widgets.get('chapter_arc_notes_text')
        if arc_widget and arc_widget.winfo_exists():
            try:
                arc_value = chapter_arc_settings_data.get(arc_key, "") if chapter_arc_settings_data else ""
                is_arc_visible = self.settings_area_visible and self.chapter_arc_notes_widget_visible
                current_arc_state = tk.DISABLED if (is_busy or not chapter_loaded or not is_arc_visible) else tk.NORMAL

                arc_widget.config(state=tk.NORMAL) # Temp enable
                arc_widget.delete("1.0", tk.END)
                arc_widget.insert("1.0", arc_value)
                arc_widget.edit_reset(); arc_widget.edit_modified(False)
                arc_widget.config(state=current_arc_state) # Restore state
            except tk.TclError: pass

        # --- 장면 설정 (플롯, 온도, 길이) ---
        settings_source = scene_settings_data if scene_settings_data else {}

        plot_key = constants.SCENE_PLOT_KEY
        plot_widget = self.widgets.get('scene_plot_text')
        if plot_widget and plot_widget.winfo_exists():
            try:
                plot_value = settings_source.get(plot_key, "")
                is_plot_visible = self.settings_area_visible and self.scene_plot_widget_visible
                current_plot_state = tk.DISABLED if (is_busy or not scene_loaded or not is_plot_visible) else tk.NORMAL

                plot_widget.config(state=tk.NORMAL) # Temp enable
                plot_widget.delete("1.0", tk.END)
                plot_widget.insert("1.0", plot_value)
                plot_widget.edit_reset(); plot_widget.edit_modified(False)
                plot_widget.config(state=current_plot_state) # Restore state
            except tk.TclError: pass

        # 온도, 길이
        temp_scale = self.widgets.get('temperature_scale')
        if temp_scale and temp_scale.winfo_exists():
            try:
                temp_val = float(settings_source.get('temperature', constants.DEFAULT_TEMPERATURE))
                temp_val = max(0.0, min(2.0, temp_val)) # Clamp
                # Determine state based on whether scene is loaded and not busy
                current_scale_state = tk.DISABLED if (is_busy or not scene_loaded) else tk.NORMAL
                temp_scale.config(state=tk.NORMAL) # Enable to set value
                temp_scale.set(temp_val)
                temp_scale.config(state=current_scale_state) # Restore state
                self._update_temperature_label()
            except (ValueError, TypeError, tk.TclError): pass

        length_combo = self.widgets.get('length_combobox')
        if length_combo and length_combo.winfo_exists():
            try:
                length_val = settings_source.get('length', constants.LENGTH_OPTIONS[0])
                if length_val in constants.LENGTH_OPTIONS: length_combo.set(length_val)
                else: length_combo.current(0)
                # Determine state based on whether scene is loaded and not busy
                current_length_state = tk.DISABLED if (is_busy or not scene_loaded) else 'readonly'
                length_combo.config(state=current_length_state)
            except tk.TclError: pass

        self._update_dynamic_labels()

        # 로드 후 UI 상태 재조정 및 수정 플래그 리셋
        self.reset_chapter_modified_flag() # Scene snapshot flag reset
        self.reset_novel_modified_flag() # Reset novel flag too (handled by AppCore as well)
        # Reset Arc Notes specific Tk flag
        if arc_widget and arc_widget.winfo_exists(): arc_widget.edit_modified(False)
        self.update_ui_state(is_busy, novel_loaded, chapter_loaded, scene_loaded)


    def get_settings(self):
        """현재 패널의 설정 값들을 딕셔너리로 반환 (API 타입 포함)"""
        settings = {}
        # API 타입
        api_combo = self.widgets.get('api_type_combobox')
        if api_combo and api_combo.winfo_exists():
             try: settings['selected_api_type'] = api_combo.get().lower()
             except tk.TclError: settings['selected_api_type'] = self.app_core.current_api_type

        # 모델
        model_combo = self.widgets.get('model_combobox')
        if model_combo and model_combo.winfo_exists():
             try:
                 model_val = model_combo.get()
                 settings['selected_model'] = model_val if model_val != "모델 없음" else None
             except tk.TclError: settings['selected_model'] = self.app_core.selected_model

        # 소설 설정
        novel_widget = self.widgets.get('novel_settings_text')
        if novel_widget and novel_widget.winfo_exists():
            try: settings[constants.NOVEL_MAIN_SETTINGS_KEY] = novel_widget.get("1.0", "end-1c").strip()
            except tk.TclError: settings[constants.NOVEL_MAIN_SETTINGS_KEY] = ""

        # 챕터 전체 설정 (아크 노트)
        arc_widget = self.widgets.get('chapter_arc_notes_text')
        if arc_widget and arc_widget.winfo_exists():
            try: settings[constants.CHAPTER_ARC_NOTES_KEY] = arc_widget.get("1.0", "end-1c").strip()
            except tk.TclError: settings[constants.CHAPTER_ARC_NOTES_KEY] = ""

        # 장면 플롯
        plot_widget = self.widgets.get('scene_plot_text')
        if plot_widget and plot_widget.winfo_exists():
            try: settings[constants.SCENE_PLOT_KEY] = plot_widget.get("1.0", "end-1c").strip()
            except tk.TclError: settings[constants.SCENE_PLOT_KEY] = ""

        # 온도
        temp_scale = self.widgets.get('temperature_scale')
        if temp_scale and temp_scale.winfo_exists():
            try: settings['temperature'] = temp_scale.get()
            except tk.TclError: settings['temperature'] = constants.DEFAULT_TEMPERATURE

        # 길이
        length_combo = self.widgets.get('length_combobox')
        if length_combo and length_combo.winfo_exists():
            try: settings['length'] = length_combo.get()
            except tk.TclError: settings['length'] = constants.LENGTH_OPTIONS[0]

        return settings

    def get_scene_plot(self):
        plot_widget = self.widgets.get('scene_plot_text')
        if plot_widget and plot_widget.winfo_exists():
            try: return plot_widget.get("1.0", "end-1c").strip()
            except tk.TclError: return ""
        return ""

    def set_scene_plot(self, text):
        plot_widget = self.widgets.get('scene_plot_text')
        if plot_widget and plot_widget.winfo_exists():
             try:
                 current_plot_state = plot_widget.cget('state')
                 plot_widget.config(state=tk.NORMAL) # Temp enable
                 plot_widget.delete("1.0", tk.END)
                 plot_widget.insert("1.0", text)
                 plot_widget.edit_reset(); plot_widget.edit_modified(False)
                 plot_widget.config(state=current_plot_state) # Restore state
             except tk.TclError: pass

    def get_novel_settings(self):
         widget = self.widgets.get('novel_settings_text')
         if widget and widget.winfo_exists():
              try: return widget.get("1.0", "end-1c").strip()
              except tk.TclError: return ""
         return ""

    def set_novel_settings(self, text):
        widget = self.widgets.get('novel_settings_text')
        if widget and widget.winfo_exists():
            try:
                scroll_pos = widget.yview()
                current_novel_state = widget.cget('state')
                widget.config(state=tk.NORMAL)
                widget.delete("1.0", tk.END)
                widget.insert("1.0", text)
                widget.edit_reset(); widget.edit_modified(False)
                widget.yview_moveto(scroll_pos[0])
                widget.config(state=current_novel_state)
                # Reset novel specific modification flag in AppCore too
                if hasattr(self.app_core, 'novel_settings_modified_flag'):
                    self.app_core.novel_settings_modified_flag = False
                self.reset_novel_modified_flag() # Reset internal Tk flag
            except tk.TclError: pass

    def clear_scene_settings_fields(self):
        """Clears Scene Plot, Temperature, Length fields."""
        # 플롯
        plot_widget = self.widgets.get('scene_plot_text')
        if plot_widget and plot_widget.winfo_exists():
             try:
                 plot_widget.config(state=tk.NORMAL)
                 plot_widget.delete("1.0", tk.END)
                 plot_widget.edit_reset(); plot_widget.edit_modified(False)
                 plot_widget.config(state=tk.DISABLED) # Disable after clearing
             except tk.TclError: pass
        # 온도
        temp_scale = self.widgets.get('temperature_scale')
        if temp_scale and temp_scale.winfo_exists():
            try:
                temp_scale.config(state=tk.NORMAL) # Enable to set
                temp_scale.set(constants.DEFAULT_TEMPERATURE)
                self._update_temperature_label()
                temp_scale.config(state=tk.DISABLED) # Disable after setting default
            except tk.TclError: pass
        # 길이
        length_combo = self.widgets.get('length_combobox')
        if length_combo and length_combo.winfo_exists():
            try:
                length_combo.current(0)
                length_combo.config(state=tk.DISABLED) # Disable after setting default
            except tk.TclError: pass
        # 모델 콤보박스는 변경하지 않음

        self.reset_chapter_modified_flag() # Reset scene snapshot flag

    def clear_chapter_arc_notes_field(self):
        """Clears only the chapter settings (arc notes) field."""
        arc_widget = self.widgets.get('chapter_arc_notes_text')
        if arc_widget and arc_widget.winfo_exists():
             try:
                 arc_widget.config(state=tk.NORMAL)
                 arc_widget.delete("1.0", tk.END)
                 arc_widget.edit_reset(); arc_widget.edit_modified(False)
                 arc_widget.config(state=tk.DISABLED) # Disable after clearing
             except tk.TclError: pass
        # Arc notes modification is handled by AppCore's flag, no need to reset here
        self._update_dynamic_labels() # 라벨 업데이트 호출 추가

    def clear_novel_settings(self):
        """Clears only the novel settings field."""
        widget = self.widgets.get('novel_settings_text')
        if widget and widget.winfo_exists():
            try:
                widget.config(state=tk.NORMAL)
                widget.delete("1.0", tk.END)
                widget.edit_reset(); widget.edit_modified(False)
                widget.config(state=tk.DISABLED)
            except tk.TclError: pass
        self.reset_novel_modified_flag() # Reset internal Tk flag
        self._update_dynamic_labels() # 라벨 업데이트 호출 추가


    def reset_novel_modified_flag(self):
        """소설 설정 위젯의 내부 수정 플래그 리셋 (AppCore 호출용)"""
        widget = self.widgets.get('novel_settings_text')
        if widget and widget.winfo_exists():
            try: widget.edit_modified(False)
            except tk.TclError: pass
        # AppCore's flag (novel_settings_modified_flag) should be reset by AppCore

    def reset_chapter_modified_flag(self):
        """장면 스냅샷 관련 위젯들의 내부 수정 플래그 리셋 및 자체 플래그 리셋"""
        self.chapter_settings_modified_flag = False
        # Reset internal Tk flags for scene-related text widgets
        plot_widget = self.widgets.get('scene_plot_text')
        if plot_widget and plot_widget.winfo_exists():
            try: plot_widget.edit_modified(False)
            except tk.TclError: pass
        # Resetting flags for combo/scale is not directly needed, value comparison handles it.

        # Request UI update in AppCore (Save button state etc.)
        if hasattr(self, 'app_core') and self.app_core:
             self.app_core.update_ui_state()

    def set_status(self, message, is_error=False):
        """상태 표시줄 메시지 업데이트"""
        if self.status_label and self.status_label.winfo_exists():
            self.status_label.config(text=message)
            style = 'Error.TLabel' if is_error else 'Status.TLabel'
            self.status_label.config(style=style)
        else:
            print(f"Status ({'Error' if is_error else 'Info'}): {message}")