# gui_manager.py
import tkinter as tk
from tkinter import ttk, messagebox
import platform
import os

# 프로젝트 모듈 임포트
import constants
from gui_panels.settings_panel import SettingsPanel
from gui_panels.output_panel import OutputPanel
from gui_panels.treeview_panel import TreeviewPanel
import utils # 유틸리티 함수 사용

class GuiManager:
    """메인 GUI 창 생성, 레이아웃 관리, 패널 인스턴스화 담당 클래스"""

    def __init__(self, root, app_core):
        print("GUI: GuiManager 초기화 시작...")
        self.root = root
        self.app_core = app_core # AppCore 참조 저장

        # 기본 폰트 설정 (utils 사용)
        self.base_font_family, self.base_font_size = utils.get_platform_font()
        self.text_font = (self.base_font_family, self.base_font_size)
        self.label_font = (self.base_font_family, self.base_font_size, "bold")
        self.status_font = (self.base_font_family, self.base_font_size - 1)
        self.treeview_font = (self.base_font_family, self.base_font_size)
        print(f"GUI: 적용된 기본 폰트: {self.base_font_family}, 크기: {self.base_font_size}")

        # 스타일 설정
        self.style = ttk.Style(self.root)
        self._setup_styles()

        # 메인 윈도우 설정
        self.root.title(constants.APP_NAME) # 초기 제목
        self.root.geometry("1150x820") # 초기 크기
        self.root.protocol("WM_DELETE_WINDOW", self.app_core.handle_quit_request) # 종료 버튼 연결

        # 메인 메뉴 설정
        self._setup_menu()

        # 메인 레이아웃 (PanedWindow)
        self.main_pane = ttk.PanedWindow(root, orient=tk.HORIZONTAL)
        self.main_pane.pack(fill=tk.BOTH, expand=True, padx=constants.PAD_X, pady=constants.PAD_Y)

        # 왼쪽 프레임 (설정 + 출력)
        self.left_frame = ttk.Frame(self.main_pane, padding=(0, 0)) # 패딩은 내부 패널에서 관리
        self.main_pane.add(self.left_frame, weight=3) # 초기 너비 비율
        self.left_frame.rowconfigure(1, weight=1) # 출력 패널이 확장되도록 설정
        self.left_frame.columnconfigure(0, weight=1)

        # 오른쪽 프레임 (트리뷰)
        self.right_frame = ttk.Frame(self.main_pane, padding=(0, 0))
        self.main_pane.add(self.right_frame, weight=1)
        self.right_frame.rowconfigure(0, weight=1)
        self.right_frame.columnconfigure(0, weight=1)

        # --- 패널 인스턴스화 및 배치 ---
        # SettingsPanel (Left Top)
        self.settings_panel = SettingsPanel(self.left_frame, self.app_core, self.text_font, self.label_font)
        self.settings_panel.grid(row=0, column=0, sticky="new")

        # OutputPanel (Left Bottom)
        self.output_panel = OutputPanel(self.left_frame, self.app_core, self.text_font)
        self.output_panel.grid(row=1, column=0, sticky="nsew", pady=(constants.PAD_Y*2, 0))

        # TreeviewPanel (Right)
        self.treeview_panel = TreeviewPanel(self.right_frame, self.app_core, self.treeview_font, self.label_font)
        self.treeview_panel.pack(fill=tk.BOTH, expand=True) # pack 사용 (Frame이므로)

        # 상태 표시줄 (SettingsPanel 내부에 포함됨)
        self.status_label_widget = self.settings_panel.status_label # 직접 참조 저장

        print("GUI: GuiManager 초기화 완료.")


    def _setup_styles(self):
        """ttk 스타일 및 기본 폰트 설정"""
        utils.configure_ttk_styles(self.style, self.base_font_family, self.base_font_size)


    def _setup_menu(self):
        """메인 메뉴바 생성"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        settings_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="⚙️ 설정", menu=settings_menu)
        # 메뉴 항목 클릭 시 AppCore의 핸들러 호출
        settings_menu.add_command(label="API 키 관리...", command=self.app_core.handle_api_key_dialog) # *** MODIFIED: ADDED ***
        settings_menu.add_separator() # *** MODIFIED: ADDED ***
        settings_menu.add_command(label="기본 시스템 프롬프트 설정...", command=self.app_core.handle_system_prompt_dialog)
        settings_menu.add_command(label="출력 영역 색상 설정...", command=self.app_core.handle_color_dialog)
        settings_menu.add_separator()
        settings_menu.add_command(label="요약 모델 설정...", command=self.app_core.handle_summary_model_dialog)
        settings_menu.add_separator()
        settings_menu.add_command(label="소설 저장 폴더 열기", command=self.app_core.handle_open_save_directory)

    # --- AppCore에서 호출하는 GUI 업데이트 메소드 ---

    def set_window_title(self, title):
        if self.root and self.root.winfo_exists():
            self.root.title(title)

    def update_status_bar(self, message):
        """상태 표시줄 텍스트 업데이트"""
        if self.status_label_widget and self.status_label_widget.winfo_exists():
            try:
                self.status_label_widget.config(text=message)
            except tk.TclError: pass # 위젯 파괴 시 무시

    def update_status_bar_conditional(self, message):
        """중요 메시지가 아닐 때만 상태 표시줄 업데이트"""
        if self.status_label_widget and self.status_label_widget.winfo_exists():
            try:
                current_text = self.status_label_widget.cget("text")
                # 중요 접두사가 포함되어 있지 않으면 업데이트
                if not any(prefix in current_text for prefix in ["✅", "❌", "⚠️", "⏳", "🔄", "✨", "📄", "🗑️"]):
                    self.status_label_widget.config(text=message)
            except tk.TclError: pass

    def get_status_bar_text(self):
        """현재 상태 표시줄 텍스트 반환"""
        if self.status_label_widget and self.status_label_widget.winfo_exists():
            try:
                return self.status_label_widget.cget("text")
            except tk.TclError: return ""
        return ""

    def schedule_status_clear(self, expected_message, delay_ms):
        """특정 시간 후 상태 표시줄 클리어 예약 (메시지 일치 시)"""
        if self.root and self.root.winfo_exists():
             self.root.after(delay_ms, self._clear_status_if_equals, expected_message)

    def _clear_status_if_equals(self, expected_message):
        """예약된 상태 표시줄 클리어 실행"""
        try:
            # Ensure AppCore reference exists before accessing its attributes
            if not hasattr(self, 'app_core') or self.app_core is None:
                print("GUI WARN: _clear_status_if_equals - AppCore not available.")
                return

            if self.status_label_widget and self.status_label_widget.winfo_exists():
                # 현재 상태 메시지가 지우기로 예약된 메시지와 일치하는 경우에만 처리
                if self.get_status_bar_text() == expected_message:
                    # 기본 상태 메시지 결정 로직 (is_busy() 호출 제거)
                    default_status = "상태 메시지 초기화됨." # 기본값
                    # Use self.app_core consistently
                    if self.app_core.current_scene_path:
                        scene_num = self.app_core._get_scene_number_from_path(self.app_core.current_scene_path)
                        current_chapter_path = os.path.dirname(self.app_core.current_scene_path) if self.app_core.current_scene_path else None
                        ch_str = self.app_core._get_chapter_number_str_from_folder(current_chapter_path) if current_chapter_path else "?"
                        # Check if novel name exists
                        novel_name = self.app_core.current_novel_name if self.app_core.current_novel_name else "소설"
                        default_status = f"[{novel_name}] {ch_str} - {scene_num:03d} 장면 로드됨."
                    elif self.app_core.current_chapter_arc_dir:
                        ch_str = self.app_core._get_chapter_number_str_from_folder(self.app_core.current_chapter_arc_dir)
                        novel_name = self.app_core.current_novel_name if self.app_core.current_novel_name else "소설"
                        default_status = f"[{novel_name}] {ch_str} 폴더 로드됨."
                    elif self.app_core.current_novel_dir:
                        novel_name = self.app_core.current_novel_name if self.app_core.current_novel_name else "소설"
                        default_status = f"[{novel_name}] 소설 로드됨."
                    else:
                        default_status = "새 소설을 시작하거나 기존 항목을 선택하세요."

                    # 결정된 기본 상태 메시지로 업데이트
                    self.update_status_bar(default_status)
        except tk.TclError: pass # 위젯 파괴 시 무시
        except Exception as e: print(f"GUI WARN: 상태 클리어 중 오류: {e}")


    def set_ui_state(self, is_busy: bool, novel_loaded: bool, chapter_loaded: bool, scene_loaded: bool):
        """
        모든 패널의 UI 상태 업데이트 요청.
        이제 novel, chapter, scene 로드 상태를 모두 받습니다.
        """
        print(f"GUI: UI 상태 업데이트 요청: Busy={is_busy}, Novel={novel_loaded}, Chapter={chapter_loaded}, Scene={scene_loaded}")

        # SettingsPanel에는 모든 상태 전달
        if self.settings_panel:
            self.settings_panel.update_ui_state(is_busy, novel_loaded, chapter_loaded, scene_loaded)

        # OutputPanel에는 is_busy, scene_loaded 및 output_modified 상태 전달
        if self.output_panel:
            # OutputPanel은 AppCore에서 직접 output_modified 상태를 가져올 수 있음
            output_mod = self.app_core.output_text_modified
            self.output_panel.update_ui_state(is_busy, scene_loaded, output_mod)

        # TreeviewPanel에는 is_busy만 전달 (트리뷰 자체는 항상 활성)
        if self.treeview_panel:
            self.treeview_panel.update_ui_state(is_busy)

        # 저장 버튼 활성화 로직은 각 패널(주로 OutputPanel) 내부 또는 AppCore에서 관리됨.
        # GuiManager는 상태만 전달하고 각 패널이 그에 맞게 버튼 상태를 조정.

    def show_message(self, msg_type, title, message):
        """메시지 박스 표시 래퍼"""
        if self.root and self.root.winfo_exists(): # 루트 윈도우가 있을 때만
            if msg_type == "info":
                messagebox.showinfo(title, message, parent=self.root)
            elif msg_type == "warning":
                messagebox.showwarning(title, message, parent=self.root)
            elif msg_type == "error":
                messagebox.showerror(title, message, parent=self.root)
            else:
                messagebox.showinfo(title, message, parent=self.root) # 기본값

    def ask_yes_no(self, title, message, icon='question'):
        """Yes/No 질문 메시지 박스"""
        if self.root and self.root.winfo_exists():
             return messagebox.askyesno(title, message, icon=icon, parent=self.root)
        return False # GUI 없으면 False 반환

    def ask_yes_no_cancel(self, title, message, icon='question'):
        """Yes/No/Cancel 질문 메시지 박스"""
        if self.root and self.root.winfo_exists():
            # askyesnocancel 반환값: True(Yes), False(No), None(Cancel)
            return messagebox.askyesnocancel(title, message, icon=icon, parent=self.root)
        return None # GUI 없으면 None 반환