# --- START OF FILE gui_dialogs.py ---

# gui_dialogs.py
import tkinter as tk
from tkinter import ttk, colorchooser, simpledialog, messagebox, filedialog # filedialog 추가
import constants
import os # For getenv

# --- Helper Functions ---
def _grab_and_wait(dialog_window):
    """Toplevel 대화상자를 modal로 만들고 닫힐 때까지 기다림"""
    try:
        dialog_window.wait_visibility()
        dialog_window.grab_set()
        dialog_window.focus_force()
        dialog_window.wait_window()
    except tk.TclError as e:
        print(f"GUI DIALOG WARN: grab/wait 실패 ({dialog_window.title()}): {e}")
        try: dialog_window.grab_release()
        except tk.TclError: pass # Ignore error if grab was already released

def _create_text_area(parent, height, initial_text="", state=tk.NORMAL):
    """대화상자용 텍스트 위젯 생성 헬퍼"""
    text_frame = ttk.Frame(parent)
    pad_x = getattr(constants, 'PAD_X', 10) // 2
    pad_y = getattr(constants, 'PAD_Y', 10) // 2

    text_widget = tk.Text(text_frame, height=height, width=50, wrap=tk.WORD,
                          padx=pad_x, pady=pad_y,
                          relief=tk.SOLID, borderwidth=0,
                          undo=True, state=state)
    scroll = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=text_widget.yview)
    text_widget['yscrollcommand'] = scroll.set
    scroll.pack(side=tk.RIGHT, fill=tk.Y)
    text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    if initial_text:
        original_state = text_widget.cget('state')
        try:
            if original_state == tk.DISABLED: text_widget.config(state=tk.NORMAL)
            text_widget.insert("1.0", initial_text)
        finally:
            if original_state == tk.DISABLED: text_widget.config(state=original_state)

    return text_frame, text_widget

# --- Dialog Functions ---

def show_system_prompt_dialog(parent_root, current_prompt):
    """시스템 프롬프트 설정 대화상자 표시. 저장 시 새 프롬프트, 취소 시 None 반환."""
    dialog = tk.Toplevel(parent_root)
    dialog.title("기본 시스템 프롬프트 설정")
    dialog.geometry("600x400")
    dialog.transient(parent_root)

    result = {"prompt": None}

    frame = ttk.Frame(dialog, padding=(15, 15))
    frame.pack(fill=tk.BOTH, expand=True)
    frame.rowconfigure(1, weight=1); frame.columnconfigure(0, weight=1)

    ttk.Label(frame, text="AI 역할/지침 입력 (모든 생성에 기본 적용):").grid(row=0, column=0, pady=(0, 6), sticky='w')

    text_frame, text_widget = _create_text_area(frame, height=10, initial_text=current_prompt)
    text_frame.grid(row=1, column=0, sticky='nsew', pady=(0, 10))
    text_widget.focus_set()

    btn_frame = ttk.Frame(frame)
    btn_frame.grid(row=2, column=0, pady=(10, 0), sticky='e')

    def on_save():
        result["prompt"] = text_widget.get("1.0", "end-1c").strip()
        dialog.destroy()

    def on_cancel():
        result["prompt"] = None
        dialog.destroy()

    def on_restore_default():
        if messagebox.askyesno("기본값 복원", "시스템 프롬프트를 기본값으로 되돌리시겠습니까?\n(저장 버튼을 눌러야 적용됩니다)", parent=dialog):
             original_state = text_widget.cget('state')
             if original_state == tk.DISABLED: text_widget.config(state=tk.NORMAL)
             text_widget.delete("1.0", tk.END)
             text_widget.insert("1.0", constants.DEFAULT_SYSTEM_PROMPT)
             if original_state == tk.DISABLED: text_widget.config(state=original_state)

    ttk.Button(btn_frame, text="기본값 복원", command=on_restore_default).pack(side=tk.LEFT, padx=(0, 10))
    ttk.Button(btn_frame, text="저장", command=on_save).pack(side=tk.LEFT, padx=(0, 5))
    ttk.Button(btn_frame, text="취소", command=on_cancel).pack(side=tk.LEFT)

    dialog.protocol("WM_DELETE_WINDOW", on_cancel)
    _grab_and_wait(dialog)
    return result["prompt"]


def show_color_dialog(parent_root, current_bg, current_fg):
    """출력 영역 색상 설정 대화상자. 저장 시 {'bg': ..., 'fg': ...}, 취소 시 None 반환."""
    dialog = tk.Toplevel(parent_root)
    dialog.title("출력 영역 색상 설정")
    dialog.geometry("350x200")
    dialog.transient(parent_root)

    temp_colors = {'bg': current_bg, 'fg': current_fg}
    result = None

    frame = ttk.Frame(dialog, padding=(15, 15))
    frame.pack(fill=tk.BOTH, expand=True)

    prev_frame = ttk.Frame(frame); prev_frame.pack(pady=10, anchor='center')
    prev_frame.columnconfigure(1, minsize=120)
    ttk.Label(prev_frame, text="배경색:").grid(row=0, column=0, padx=6, pady=4, sticky='w')
    bg_preview = tk.Label(prev_frame, text=" ", relief="solid", borderwidth=1, width=15, bg=temp_colors['bg'])
    bg_preview.grid(row=0, column=1, padx=6, pady=4, sticky='ew')
    ttk.Button(prev_frame, text="선택...", command=lambda: choose_color('bg')).grid(row=0, column=2, padx=6)
    ttk.Label(prev_frame, text="글자색:").grid(row=1, column=0, padx=6, pady=4, sticky='w')
    fg_preview = tk.Label(prev_frame, text=" 샘플 텍스트 ", relief="solid", borderwidth=1, width=15, bg=temp_colors['bg'], fg=temp_colors['fg'])
    fg_preview.grid(row=1, column=1, padx=6, pady=4, sticky='ew')
    ttk.Button(prev_frame, text="선택...", command=lambda: choose_color('fg')).grid(row=1, column=2, padx=6)

    btn_frame = ttk.Frame(frame); btn_frame.pack(fill=tk.X, pady=(15, 0), side=tk.BOTTOM)
    cancel_btn = ttk.Button(btn_frame, text="취소", command=lambda: on_cancel())
    cancel_btn.pack(side=tk.RIGHT)
    save_btn = ttk.Button(btn_frame, text="저장/적용", command=lambda: on_save())
    save_btn.pack(side=tk.RIGHT, padx=(0, 5))
    default_btn = ttk.Button(btn_frame, text="기본값 복원", command=lambda: on_restore_default())
    default_btn.pack(side=tk.LEFT)

    def update_previews():
        bg_preview.config(bg=temp_colors['bg'])
        fg_preview.config(bg=temp_colors['bg'], fg=temp_colors['fg'])

    def choose_color(target):
        initial_color = temp_colors[target]
        title = f"{'배경' if target == 'bg' else '글자'}색 선택"
        color_info = colorchooser.askcolor(initial_color, title=title, parent=dialog)
        if color_info and color_info[1]:
             chosen_color = color_info[1]
             temp_colors[target] = chosen_color
             update_previews()
             dialog.lift()

    def on_save():
        nonlocal result
        result = temp_colors.copy()
        dialog.destroy()

    def on_cancel():
        nonlocal result
        result = None
        dialog.destroy()

    def on_restore_default():
        if messagebox.askyesno("기본값 복원", "색상을 기본값으로 되돌리시겠습니까?\n(저장/적용 버튼을 눌러야 반영됩니다)", parent=dialog):
             temp_colors['bg'] = constants.DEFAULT_OUTPUT_BG
             temp_colors['fg'] = constants.DEFAULT_OUTPUT_FG
             update_previews()

    dialog.protocol("WM_DELETE_WINDOW", on_cancel)
    _grab_and_wait(dialog)
    return result


def show_summary_model_dialog(parent_root, current_model, available_models):
    """요약 모델 선택 대화상자. 저장 시 모델 이름, 취소 시 None 반환."""
    dialog = tk.Toplevel(parent_root)
    dialog.title("요약 모델 설정")
    dialog.geometry("450x150")
    dialog.transient(parent_root)

    result = {"model": None}

    frame = ttk.Frame(dialog, padding=(15, 15))
    frame.pack(fill=tk.BOTH, expand=True)
    frame.columnconfigure(1, weight=1)

    ttk.Label(frame, text="요약 AI 모델:").grid(row=0, column=0, padx=(0, 6), pady=10, sticky='w')
    model_values = list(available_models) if available_models else []
    model_combo = ttk.Combobox(frame, values=model_values, state="readonly")
    model_combo.grid(row=0, column=1, columnspan=2, padx=6, pady=10, sticky='ew')

    if current_model and current_model in model_values:
        model_combo.set(current_model)
    elif model_values:
        model_combo.current(0)
    else:
        model_combo.set("모델 없음")
        model_combo.config(state=tk.DISABLED)

    btn_frame = ttk.Frame(frame)
    btn_frame.grid(row=1, column=0, columnspan=3, pady=(15, 0), sticky='ew')
    cancel_btn = ttk.Button(btn_frame, text="취소", command=lambda: on_cancel())
    cancel_btn.pack(side=tk.RIGHT)
    save_btn = ttk.Button(btn_frame, text="저장", command=lambda: on_save())
    save_btn.pack(side=tk.RIGHT, padx=(0, 5))

    def on_save():
        selected = model_combo.get()
        if selected and selected != "모델 없음":
            result["model"] = selected
            dialog.destroy()
        else:
             messagebox.showwarning("선택 오류", "유효한 요약 모델을 선택해주세요.", parent=dialog)

    def on_cancel():
        result["model"] = None
        dialog.destroy()

    dialog.protocol("WM_DELETE_WINDOW", on_cancel)
    model_combo.focus_set()
    _grab_and_wait(dialog)
    return result["model"]


def show_new_novel_dialog(parent_root):
    """새 소설 생성 대화상자. 생성 시 {'name': ..., 'settings': ...}, 취소 시 None 반환."""
    dialog = tk.Toplevel(parent_root)
    dialog.title("✨ 새 소설 생성")
    dialog.geometry("550x450")
    dialog.transient(parent_root)

    result = {"name": None, "settings": None}

    frame = ttk.Frame(dialog, padding=(15, 15))
    frame.pack(fill=tk.BOTH, expand=True)
    frame.columnconfigure(1, weight=1); frame.rowconfigure(2, weight=1)

    try:
        bold_style = 'Bold.TLabel'
        ttk.Style().configure(bold_style, font=('TkDefaultFont', 10, 'bold'))
    except tk.TclError:
        bold_style = 'TLabel'

    ttk.Label(frame, text="소설 이름:", style=bold_style).grid(row=0, column=0, padx=(0, 5), pady=5, sticky='w')
    name_entry = ttk.Entry(frame, width=50)
    name_entry.grid(row=0, column=1, pady=5, sticky='ew')
    name_entry.focus_set()

    novel_key = constants.NOVEL_MAIN_SETTINGS_KEY
    ttk.Label(frame, text=f"초기 소설 설정 ({novel_key}):\n(세계관, 인물, 줄거리 등)", style=bold_style, justify=tk.LEFT).grid(row=1, column=0, columnspan=2, pady=(10, 2), sticky='w')

    text_frame, settings_text = _create_text_area(frame, height=10)
    text_frame.grid(row=2, column=0, columnspan=2, pady=(0, 10), sticky='nsew')

    btn_frame = ttk.Frame(frame); btn_frame.grid(row=3, column=0, columnspan=2, pady=(10, 0), sticky='e')

    def on_confirm():
        name = name_entry.get().strip()
        if not name:
            messagebox.showwarning("입력 오류", "소설 이름을 입력해주세요.", parent=dialog)
            name_entry.focus_set()
            return
        result["name"] = name
        result["settings"] = settings_text.get("1.0", "end-1c").strip()
        dialog.destroy()

    def on_cancel():
        result["name"] = None
        dialog.destroy()

    ttk.Button(btn_frame, text="생성", command=on_confirm).pack(side=tk.RIGHT, padx=(5, 0))
    ttk.Button(btn_frame, text="취소", command=on_cancel).pack(side=tk.RIGHT)

    dialog.bind("<Return>", lambda event: on_confirm())
    dialog.bind("<Escape>", lambda event: on_cancel())
    dialog.protocol("WM_DELETE_WINDOW", on_cancel)
    _grab_and_wait(dialog)
    return result if result["name"] is not None else None


def show_new_chapter_folder_dialog(parent_root, current_novel_name):
    """새 챕터 폴더 생성 대화상자. 생성 시 {'title': ..., 'arc_notes': ...}, 취소 시 None 반환."""
    dialog = tk.Toplevel(parent_root)
    dialog.title(f"📁 새 챕터 폴더 생성 (in '{current_novel_name}')")
    dialog.geometry("550x400")
    dialog.transient(parent_root)

    # result 초기화 변경: title은 생성 시 빈 문자열일 수 있으므로 다른 플래그 사용
    result = {"confirmed": False, "title": "", "arc_notes": ""}

    frame = ttk.Frame(dialog, padding=(15, 15))
    frame.pack(fill=tk.BOTH, expand=True)
    frame.columnconfigure(1, weight=1); frame.rowconfigure(3, weight=1)

    try:
        bold_style = 'Bold.TLabel'
        ttk.Style().configure(bold_style, font=('TkDefaultFont', 10, 'bold'))
    except tk.TclError:
        bold_style = 'TLabel'

    ttk.Label(frame, text="챕터 제목 (선택사항):", style=bold_style).grid(row=0, column=0, padx=(0, 5), pady=5, sticky='w')
    ttk.Label(frame, text="(폴더명 접미사로 사용됩니다. 예: Chapter_XXX_MyTitle)").grid(row=1, column=0, columnspan=2, padx=0, pady=(0,5), sticky='w')
    title_entry = ttk.Entry(frame, width=50)
    title_entry.grid(row=0, column=1, pady=5, sticky='ew')
    title_entry.focus_set()

    arc_key = constants.CHAPTER_ARC_NOTES_KEY
    ttk.Label(frame, text=f"초기 챕터 아크 노트 ({arc_key}):\n(이번 챕터 아크 목표, 흐름 등)", style=bold_style, justify=tk.LEFT).grid(row=2, column=0, columnspan=2, pady=(10, 2), sticky='w')

    text_frame, notes_text = _create_text_area(frame, height=8)
    text_frame.grid(row=3, column=0, columnspan=2, pady=(0, 10), sticky='nsew')

    btn_frame = ttk.Frame(frame); btn_frame.grid(row=4, column=0, columnspan=2, pady=(10, 0), sticky='e')

    def on_confirm():
        result["confirmed"] = True
        result["title"] = title_entry.get().strip()
        result["arc_notes"] = notes_text.get("1.0", "end-1c").strip()
        dialog.destroy()

    def on_cancel():
        result["confirmed"] = False # Mark as cancelled
        dialog.destroy()

    ttk.Button(btn_frame, text="폴더 생성", command=on_confirm).pack(side=tk.RIGHT, padx=(5, 0))
    ttk.Button(btn_frame, text="취소", command=on_cancel).pack(side=tk.RIGHT)

    dialog.bind("<Return>", lambda event: on_confirm())
    dialog.bind("<Escape>", lambda event: on_cancel())
    dialog.protocol("WM_DELETE_WINDOW", on_cancel)
    _grab_and_wait(dialog)
    # Return data only if confirmed
    return result if result["confirmed"] else None


def show_scene_plot_dialog(parent_root, current_plot="", title="🎬 장면 플롯 입력"):
    """장면 플롯 입력 대화상자. 확인 시 플롯 문자열, 취소 시 None 반환."""
    dialog = tk.Toplevel(parent_root)
    dialog.title(title)
    dialog.geometry("550x350")
    dialog.transient(parent_root)

    result = {"plot": None}

    frame = ttk.Frame(dialog, padding=(15, 15))
    frame.pack(fill=tk.BOTH, expand=True)
    frame.columnconfigure(0, weight=1); frame.rowconfigure(1, weight=1)

    try:
        bold_style = 'Bold.TLabel'
        ttk.Style().configure(bold_style, font=('TkDefaultFont', 10, 'bold'))
    except tk.TclError:
        bold_style = 'TLabel'

    plot_key = constants.SCENE_PLOT_KEY
    ttk.Label(frame, text=f"이번 장면 {plot_key}:", style=bold_style).grid(row=0, column=0, pady=(0, 5), sticky='w')

    text_frame, plot_text = _create_text_area(frame, height=10, initial_text=current_plot)
    text_frame.grid(row=1, column=0, pady=(0, 10), sticky='nsew')
    plot_text.focus_set()
    if current_plot:
        plot_text.tag_add(tk.SEL, "1.0", tk.END)
        plot_text.mark_set(tk.INSERT, "1.0")
        plot_text.see(tk.INSERT)

    btn_frame = ttk.Frame(frame); btn_frame.grid(row=2, column=0, pady=(10, 0), sticky='e')

    def on_confirm():
        result["plot"] = plot_text.get("1.0", "end-1c").strip()
        dialog.destroy()

    def on_cancel():
        result["plot"] = None
        dialog.destroy()

    ttk.Button(btn_frame, text="확인", command=on_confirm).pack(side=tk.RIGHT, padx=(5, 0))
    ttk.Button(btn_frame, text="취소", command=on_cancel).pack(side=tk.RIGHT)

    dialog.bind("<Escape>", lambda event: on_cancel())
    dialog.protocol("WM_DELETE_WINDOW", on_cancel)
    _grab_and_wait(dialog)
    return result["plot"]


def show_rename_dialog(parent_root, title, prompt, initial_value):
    """간단한 이름 변경 simpledialog 래퍼"""
    return simpledialog.askstring(title, prompt, initialvalue=initial_value, parent=parent_root)


def show_api_key_dialog(parent_root, current_ask_pref):
    """API 키 관리 및 '다시 묻지 않기' 설정 대화상자."""
    dialog = tk.Toplevel(parent_root)
    dialog.title("🔑 API 키 관리")
    dialog.geometry("550x350")
    dialog.transient(parent_root)

    entered_keys = {api: "" for api in constants.SUPPORTED_API_TYPES}
    ask_pref_var = tk.BooleanVar(value=current_ask_pref)
    result = {"keys": None, "ask_pref": None}

    key_statuses = {}
    for api_type in constants.SUPPORTED_API_TYPES:
        env_key = ""
        if api_type == constants.API_TYPE_GEMINI: env_key = constants.GOOGLE_API_KEY_ENV
        elif api_type == constants.API_TYPE_CLAUDE: env_key = constants.ANTHROPIC_API_KEY_ENV
        elif api_type == constants.API_TYPE_GPT: env_key = constants.OPENAI_API_KEY_ENV
        key_statuses[api_type] = bool(os.getenv(env_key))

    main_frame = ttk.Frame(dialog, padding=(15, 15))
    main_frame.pack(fill=tk.BOTH, expand=True)

    api_frames = {}
    api_entries = {}
    api_status_labels = {}
    placeholder_text = "새 키 입력 또는 비우기" # Placeholder text constant

    row_idx = 0
    for api_type in constants.SUPPORTED_API_TYPES:
        api_name = api_type.capitalize()
        env_key = ""
        if api_type == constants.API_TYPE_GEMINI: env_key = constants.GOOGLE_API_KEY_ENV
        elif api_type == constants.API_TYPE_CLAUDE: env_key = constants.ANTHROPIC_API_KEY_ENV
        elif api_type == constants.API_TYPE_GPT: env_key = constants.OPENAI_API_KEY_ENV

        frame = ttk.LabelFrame(main_frame, text=f"{api_name} ({env_key})", padding=(10, 5))
        frame.grid(row=row_idx, column=0, sticky="ew", pady=(0, 10))
        frame.columnconfigure(1, weight=1)
        api_frames[api_type] = frame

        status_text = "✅ 키 있음" if key_statuses[api_type] else "❌ 키 없음"
        status_color = "green" if key_statuses[api_type] else "red"
        status_lbl = ttk.Label(frame, text=status_text, foreground=status_color)
        status_lbl.grid(row=0, column=0, padx=(0, 10), sticky="w")
        api_status_labels[api_type] = status_lbl

        key_entry = ttk.Entry(frame, width=40, show="") # Start with mask off for placeholder
        key_entry.grid(row=0, column=1, sticky="ew", padx=(0, 5))
        api_entries[api_type] = key_entry

        def on_focus_in(event, entry=key_entry, placeholder=placeholder_text):
             # Use captured variables entry and placeholder
            if entry.cget('foreground') == 'grey': # Check if it's placeholder text
                entry.delete(0, tk.END)
                entry.config(show="*", foreground='black')

        def on_focus_out(event, entry=key_entry, placeholder=placeholder_text):
            # Use captured variables entry and placeholder
            if not entry.get():
                entry.config(show="", foreground='grey')
                entry.insert(0, placeholder)

        # Bind with default arguments captured by lambda (or use functools.partial)
        key_entry.bind("<FocusIn>", on_focus_in)
        key_entry.bind("<FocusOut>", on_focus_out)

        # Initialize placeholder state correctly
        on_focus_out(None, entry=key_entry, placeholder=placeholder_text) # Call manually for initial setup

        row_idx += 1

    pref_check = ttk.Checkbutton(main_frame,
                                 text="시작 시 누락된 API 키 입력 요청하기",
                                 variable=ask_pref_var,
                                 onvalue=True, offvalue=False)
    pref_check.grid(row=row_idx, column=0, sticky="w", pady=(10, 15))
    row_idx += 1

    btn_frame = ttk.Frame(main_frame)
    btn_frame.grid(row=row_idx, column=0, pady=(10, 0), sticky='e')

    def on_save():
        for api_t, entry_widget in api_entries.items():
            if entry_widget.cget('foreground') == 'grey': # Check if placeholder is showing
                entered_keys[api_t] = "" # Treat as empty
            else:
                entered_keys[api_t] = entry_widget.get().strip()

        result["keys"] = entered_keys
        result["ask_pref"] = ask_pref_var.get()
        dialog.destroy()

    def on_cancel():
        result["keys"] = None
        result["ask_pref"] = None
        dialog.destroy()

    ttk.Button(btn_frame, text="저장", command=on_save).pack(side=tk.RIGHT, padx=(5, 0))
    ttk.Button(btn_frame, text="취소", command=on_cancel).pack(side=tk.RIGHT)

    dialog.protocol("WM_DELETE_WINDOW", on_cancel)
    _grab_and_wait(dialog)
    return result if result["keys"] is not None else None


def show_font_config_dialog(parent_root, current_font_path):
    """이미지 렌더링용 폰트 설정 대화상자. 저장 시 폰트 경로, 취소/기본값 시 빈 문자열 반환."""
    dialog = tk.Toplevel(parent_root)
    dialog.title("✒️ 이미지 캡처 폰트 설정")
    dialog.geometry("550x180") # 크기 조정
    dialog.transient(parent_root)

    result = {"path": None} # 결과 저장 (None은 취소, ""는 기본값/미설정 의미)
    temp_path = tk.StringVar(value=current_font_path if current_font_path else "")

    frame = ttk.Frame(dialog, padding=(15, 15))
    frame.pack(fill=tk.BOTH, expand=True)
    frame.columnconfigure(1, weight=1)

    ttk.Label(frame, text="캡처 시 사용할 폰트 파일 (.ttf, .otf):").grid(row=0, column=0, columnspan=3, pady=(0, 5), sticky='w')

    font_entry = ttk.Entry(frame, textvariable=temp_path, width=50, state="readonly")
    font_entry.grid(row=1, column=0, columnspan=2, padx=(0, 5), pady=5, sticky='ew')

    def browse_font():
        # 파일 타입 지정
        filetypes = [("TrueType/OpenType Fonts", "*.ttf *.otf"), ("All Files", "*.*")]
        # 초기 디렉토리 설정 (선택 사항, 예: 시스템 폰트 폴더)
        initial_dir = "/" # 기본값
        if os.name == 'nt': initial_dir = "C:/Windows/Fonts"
        elif os.path.exists("/usr/share/fonts"): initial_dir = "/usr/share/fonts"
        elif os.path.exists("/Library/Fonts"): initial_dir = "/Library/Fonts"

        filepath = filedialog.askopenfilename(title="폰트 파일 선택",
                                             filetypes=filetypes,
                                             initialdir=initial_dir,
                                             parent=dialog)
        if filepath:
            temp_path.set(filepath)
            dialog.lift() # Bring dialog back to front

    browse_btn = ttk.Button(frame, text="찾아보기...", command=browse_font)
    browse_btn.grid(row=1, column=2, pady=5)

    ttk.Label(frame, text="(비워두면 시스템 기본 또는 추측된 폰트 사용)").grid(row=2, column=0, columnspan=3, pady=(5, 10), sticky='w')

    btn_frame = ttk.Frame(frame); btn_frame.grid(row=3, column=0, columnspan=3, pady=(10, 0), sticky='e')

    def on_save():
        result["path"] = temp_path.get().strip() # 저장 시 현재 경로 반환 (빈 문자열 가능)
        dialog.destroy()

    def on_clear():
        # Confirm before clearing
        if messagebox.askyesno("기본값 복원", "폰트 경로 설정을 지우고 시스템 기본/추측 폰트를 사용하도록 되돌리시겠습니까?\n(저장 버튼을 눌러야 적용됩니다)", parent=dialog):
            temp_path.set("") # 비우기

    def on_cancel():
        result["path"] = None # 취소 시 None 반환
        dialog.destroy()

    ttk.Button(btn_frame, text="저장", command=on_save).pack(side=tk.RIGHT, padx=(5, 0))
    ttk.Button(btn_frame, text="기본값 (비우기)", command=on_clear).pack(side=tk.RIGHT, padx=(5, 0))
    ttk.Button(btn_frame, text="취소", command=on_cancel).pack(side=tk.RIGHT)

    dialog.protocol("WM_DELETE_WINDOW", on_cancel)
    _grab_and_wait(dialog)
    return result["path"] # 경로 문자열 또는 None 반환

# --- END OF FILE gui_dialogs.py ---