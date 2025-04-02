# gui_panels/output_panel.py
import tkinter as tk
from tkinter import ttk, scrolledtext
import constants

class OutputPanel(ttk.Frame):
    """출력 영역 GUI (좌측 하단)"""
    def __init__(self, parent, app_core, text_font, **kwargs):
        super().__init__(parent, padding=(constants.PAD_X, 0), **kwargs) # 상단 패딩은 0
        self.app_core = app_core
        self.text_font = text_font

        self.widgets = {}
        self._create_widgets()
        # 초기 상태 설정 시 app_core 객체가 완전히 초기화되었는지 확인 필요
        # 생성자에서는 아직 app_core의 모든 속성이 준비되지 않았을 수 있음
        # self.update_ui_state(False, False, False) # 생성자 호출 시점 문제 가능성 -> GuiManager에서 초기화 후 호출하도록 변경 고려
        # GuiManager 생성자에서 패널 인스턴스화 후 update_ui_state 호출하는 것이 안전

    def _create_widgets(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1) # 내용 영역이 확장되도록

        # 내용 프레임 (LabelFrame)
        output_frame = ttk.LabelFrame(self, text="📖 내용 (편집 가능)", padding=(constants.PAD_X, constants.PAD_Y))
        output_frame.grid(row=0, column=0, sticky="nsew")
        output_frame.rowconfigure(0, weight=1)
        output_frame.columnconfigure(0, weight=1)

        # ScrolledText 위젯
        text_container = ttk.Frame(output_frame)
        text_container.grid(row=0, column=0, sticky="nsew")
        text_container.rowconfigure(0, weight=1)
        text_container.columnconfigure(0, weight=1)

        # 줄 간격 설정
        base_size = constants.BASE_FONT_SIZE
        spacing_after = int(base_size * constants.OUTPUT_LINE_SPACING_FACTOR)
        spacing_within = int(base_size * constants.OUTPUT_LINE_SPACING_WITHIN_FACTOR)

        output_text = scrolledtext.ScrolledText(text_container, wrap=tk.WORD, state=tk.NORMAL, font=self.text_font,
                                                 padx=constants.PAD_X, pady=constants.PAD_Y,
                                                 relief=tk.SOLID, borderwidth=1, undo=True,
                                                 spacing1=0, spacing2=spacing_within, spacing3=spacing_after,
                                                 bg=self.app_core.output_bg, fg=self.app_core.output_fg)
        output_text.grid(row=0, column=0, sticky="nsew")
        output_text.bind("<<Modified>>", self._on_output_modified) # 수정 감지 연결
        self.widgets['output_text'] = output_text

        # 하단 정보 프레임 (버튼, 토큰, 글자수)
        bottom_info = ttk.Frame(output_frame)
        bottom_info.grid(row=1, column=0, sticky="ew", pady=(constants.PAD_Y, 0))
        # *** 수정: columnconfigure 변경 (버튼 추가로 인한 인덱스 변경) ***
        bottom_info.columnconfigure(3, weight=1) # 확장 공백 (기존 2에서 3으로 변경)

        # 버튼
        save_btn = ttk.Button(bottom_info, text="💾 변경 저장", command=self.app_core.handle_save_changes_request, state=tk.DISABLED)
        save_btn.grid(row=0, column=0, padx=(0, constants.PAD_X // 2))
        copy_btn = ttk.Button(bottom_info, text="📋 본문 복사", command=self.app_core.handle_copy_request, state=tk.DISABLED)
        copy_btn.grid(row=0, column=1, padx=(0, constants.PAD_X // 2)) # 간격 조정

        # *** 추가: '이미지로 저장' 버튼 ***
        capture_btn = ttk.Button(bottom_info, text="🖼️ 이미지로 저장", command=self.app_core.handle_capture_output_as_png, state=tk.DISABLED)
        capture_btn.grid(row=0, column=2, padx=(0, constants.PAD_X)) # 버튼 추가 및 간격 조정 (column 2에 추가)
        self.widgets['capture_button'] = capture_btn # 위젯 딕셔너리에 추가
        # *** --- ***

        self.widgets['save_button'] = save_btn
        self.widgets['copy_button'] = copy_btn

        # 토큰 라벨 (Grid column 인덱스 변경)
        token_in_lbl = ttk.Label(bottom_info, text="입력: ---", style='Token.TLabel', anchor='e')
        token_in_lbl.grid(row=0, column=4, sticky='e', padx=(0, constants.PAD_X // 2)) # 인덱스 변경 (3 -> 4)
        token_out_lbl = ttk.Label(bottom_info, text="출력: ---", style='Token.TLabel', anchor='e')
        token_out_lbl.grid(row=0, column=5, sticky='e', padx=(0, constants.PAD_X // 2)) # 인덱스 변경 (4 -> 5)
        self.widgets['token_input_label'] = token_in_lbl
        self.widgets['token_output_label'] = token_out_lbl

        # 글자수 라벨 (Grid column 인덱스 변경)
        char_lbl = ttk.Label(bottom_info, text="글자 수: 0", style='Status.TLabel', anchor='e')
        char_lbl.grid(row=0, column=6, sticky='e', padx=(constants.PAD_X // 2, 0)) # 인덱스 변경 (5 -> 6)
        self.widgets['char_count_label'] = char_lbl

    def _on_output_modified(self, event=None):
        """출력 텍스트 수정 감지 시 AppCore에 알림"""
        widget = self.widgets.get('output_text')
        # Check if the modification was not programmatic and the flag is not already set
        if widget and widget.winfo_exists() and widget.edit_modified() and not self.app_core.output_text_modified:
            # Ensure widget is enabled (ignore modifications when disabled)
            if widget.cget('state') == tk.NORMAL:
                 self.app_core.handle_output_modified()
            else:
                 # If modified while disabled (shouldn't happen ideally), reset the Tk flag
                 widget.edit_modified(False)


    # --- AppCore에서 호출하는 메소드 ---

    def display_content(self, text):
        """텍스트 내용을 위젯에 표시"""
        widget = self.widgets.get('output_text')
        if widget and widget.winfo_exists():
            try:
                scroll_pos_before = widget.yview()
                current_state = widget.cget('state') # Remember current state

                widget.config(state=tk.NORMAL) # Enable for modification
                widget.delete("1.0", tk.END)
                widget.insert(tk.END, text if text else "")

                widget.edit_reset() # Clear undo stack
                widget.edit_modified(False) # Reset Tk's internal modified flag

                # Restore original state (might be disabled if no scene is loaded)
                widget.config(state=current_state)

                if scroll_pos_before[0] > 0.0:
                    widget.yview_moveto(scroll_pos_before[0])
                else:
                    widget.yview_moveto(0)

                self.update_char_count_display(text)
            except tk.TclError: pass

    def clear_content(self):
        """텍스트 내용 비우기"""
        self.display_content("")
        self.update_token_display(None)

    def get_content(self):
        """현재 텍스트 위젯 내용 반환"""
        widget = self.widgets.get('output_text')
        if widget and widget.winfo_exists():
            try: return widget.get("1.0", "end-1c")
            except tk.TclError: return ""
        return ""

    def update_token_display(self, token_info):
        """토큰 정보 라벨 업데이트"""
        in_lbl = self.widgets.get('token_input_label')
        out_lbl = self.widgets.get('token_output_label')
        if not (in_lbl and in_lbl.winfo_exists() and out_lbl and out_lbl.winfo_exists()): return

        input_text = "입력: ---"; output_text = "출력: ---"
        if isinstance(token_info, dict):
            try: input_text = f"입력: {int(token_info.get(constants.INPUT_TOKEN_KEY, 0)):,}"
            except (ValueError, TypeError): pass
            try: output_text = f"출력: {int(token_info.get(constants.OUTPUT_TOKEN_KEY, 0)):,}"
            except (ValueError, TypeError): pass

        try:
            in_lbl.config(text=input_text)
            out_lbl.config(text=output_text)
        except tk.TclError: pass

    def update_char_count_display(self, text_content):
        """글자 수 라벨 업데이트"""
        lbl = self.widgets.get('char_count_label')
        if lbl and lbl.winfo_exists():
            try:
                count = len(text_content) if text_content else 0
                lbl.config(text=f"글자 수: {count:,}")
            except tk.TclError: pass

    def set_colors(self, bg_color, fg_color):
        """출력 영역 배경색/글자색 설정"""
        widget = self.widgets.get('output_text')
        if widget and widget.winfo_exists():
            try:
                widget.config(bg=bg_color, fg=fg_color)
            except tk.TclError: pass

    def update_ui_state(self, is_busy: bool, scene_loaded: bool, output_modified: bool):
        """AppCore 상태에 따라 버튼 활성화/비활성화"""
        save_btn = self.widgets.get('save_button')
        if save_btn and save_btn.winfo_exists():
            # Check combined settings modification flag from SettingsPanel
            chapter_settings_mod = False
            if self.app_core.gui_manager and self.app_core.gui_manager.settings_panel:
                chapter_settings_mod = self.app_core.gui_manager.settings_panel.chapter_settings_modified_flag

            # Check novel and arc settings modification flags from AppCore
            novel_settings_mod = self.app_core.novel_settings_modified_flag
            arc_settings_mod = self.app_core.arc_settings_modified_flag

            # Determine what is currently loaded to decide which flags matter
            can_save_scene_related = scene_loaded and (output_modified or chapter_settings_mod)
            # Save chapter arc notes if chapter is loaded but no scene, AND arc notes modified
            can_save_chapter_arc_only = not scene_loaded and self.app_core.current_chapter_arc_dir and arc_settings_mod
             # Save novel settings if novel is loaded but no chapter/scene, AND novel settings modified
            can_save_novel_only = not scene_loaded and not self.app_core.current_chapter_arc_dir and self.app_core.current_novel_dir and novel_settings_mod

            # Save is enabled if not busy AND any relevant modification exists
            can_save = not is_busy and (can_save_scene_related or can_save_chapter_arc_only or can_save_novel_only)

            save_btn.config(state=tk.NORMAL if can_save else tk.DISABLED)

        copy_btn = self.widgets.get('copy_button')
        if copy_btn and copy_btn.winfo_exists():
            has_content = bool(self.get_content())
            # Copy is possible if not busy and there is content (regardless of scene loaded)
            can_copy = not is_busy and has_content
            copy_btn.config(state=tk.NORMAL if can_copy else tk.DISABLED)

        # *** 추가: 이미지 캡처 버튼 상태 업데이트 ***
        capture_btn = self.widgets.get('capture_button')
        if capture_btn and capture_btn.winfo_exists():
            has_content = bool(self.get_content())
            # 캡처는 바쁘지 않고 내용이 있을 때 가능 (씬 로드 여부는 상관 없음)
            can_capture = not is_busy and has_content
            capture_btn.config(state=tk.NORMAL if can_capture else tk.DISABLED)
        # *** --- ***

        # Text widget editability
        output_widget = self.widgets.get('output_text')
        if output_widget and output_widget.winfo_exists():
             # Enable editing only if a scene is loaded and not busy
             output_widget.config(state=tk.NORMAL if (scene_loaded and not is_busy) else tk.DISABLED)


    def reset_modified_flag(self):
        """텍스트 위젯의 내부 수정 플래그 리셋 (저장 후 호출)"""
        widget = self.widgets.get('output_text')
        if widget and widget.winfo_exists():
            try:
                widget.edit_modified(False)
            except tk.TclError: pass
        # Note: AppCore's output_text_modified flag is reset separately in AppCore