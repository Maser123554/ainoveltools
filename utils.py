# utils.py
import tkinter.font as tkFont
import tkinter as tk
from tkinter import ttk
import platform
import re
import constants # BASE_FONT_SIZE 등 사용

def get_platform_font():
    """시스템에 맞는 기본 폰트 이름과 크기 반환"""
    base_family = constants.BASE_FONT_FAMILY # 기본값
    base_size = constants.BASE_FONT_SIZE

    try:
        temp_root = None
        try:
             tk._default_root
        except AttributeError:
             temp_root = tk.Tk()
             temp_root.withdraw()

        available_tk_fonts = tkFont.families(temp_root if temp_root else None)
        system = platform.system()
        preferred_font = None

        if system == "Windows":
            win_prefs = ["Malgun Gothic", "맑은 고딕", "Segoe UI", "Tahoma", "Verdana"]
            for font in win_prefs:
                if font in available_tk_fonts: preferred_font = font; break
        elif system == "Darwin": # macOS
            mac_prefs = ["Apple SD Gothic Neo", "AppleGothic", "Helvetica Neue", "Lucida Grande"]
            for font in mac_prefs:
                if font in available_tk_fonts: preferred_font = font; break
        else: # Linux etc.
            linux_prefs = ["NanumGothic", "Noto Sans CJK KR", "UnDotum", "Droid Sans Fallback", "DejaVu Sans", "Ubuntu", "Cantarell"]
            for font in linux_prefs:
                 if font in available_tk_fonts: preferred_font = font; break

        if preferred_font:
             base_family = preferred_font
             print(f"UTILS: 시스템 폰트 감지: {base_family}")
        else:
             print(f"UTILS: 시스템 폰트 감지 실패. 기본 Tk 폰트({base_family}) 사용.")

        if temp_root:
             try: temp_root.destroy()
             except Exception: pass

    except Exception as e:
        print(f"UTILS WARN: 시스템 폰트 감지 중 오류: {e}. 기본 설정 사용.")

    return base_family, base_size


def configure_ttk_styles(style_obj, base_font_family, base_font_size):
    """ttk 위젯 스타일 및 폰트 설정 적용"""
    try:
        current_os = platform.system()
        theme_to_use = 'default'
        available_themes = style_obj.theme_names()
        print(f"UTILS DEBUG: Available themes: {available_themes}")
        if current_os == "Windows":
            win_prefs = ['win11', 'vista', 'xpnative', 'clam'] # ttkthemes 필요할 수 있음
            for theme in win_prefs:
                if theme in available_themes: theme_to_use = theme; break
        elif current_os == "Darwin":
             if 'aqua' in available_themes: theme_to_use = 'aqua'
        else: # Linux/Other
            linux_prefs = ['clam', 'alt', 'default']
            for theme in linux_prefs:
                 if theme in available_themes: theme_to_use = theme; break

        style_obj.theme_use(theme_to_use)
        print(f"UTILS: 적용된 ttk 테마: {theme_to_use}")
    except tk.TclError as e:
        print(f"UTILS WARN: 테마 설정 중 오류 ({e}). 기본 테마 사용.")
        try: style_obj.theme_use('default')
        except tk.TclError: print("UTILS ERROR: 기본 테마('default') 설정도 실패.")

    # 폰트 객체 생성
    text_font = (base_font_family, base_font_size)
    label_font = (base_font_family, base_font_size, "bold")
    status_font = (base_font_family, base_font_size - 1)
    treeview_font = (base_font_family, base_font_size)

    # 스타일 설정
    try:
        style_obj.configure("Treeview", font=treeview_font, rowheight=int(base_font_size * 2.0))
        style_obj.configure("Treeview.Heading", font=label_font)
        style_obj.configure('.', font=text_font) # 기본 ttk 위젯 폰트
        style_obj.configure('TLabel', font=text_font)
        style_obj.configure('Bold.TLabel', font=label_font) # 볼드 라벨용 스타일
        style_obj.configure('Status.TLabel', font=status_font) # 상태 라벨용
        style_obj.configure('Token.TLabel', font=status_font) # 토큰 라벨용
        style_obj.configure('Value.TLabel', font=text_font) # 값 표시 라벨 (온도 등)
        style_obj.configure('TButton', font=text_font, padding=(constants.PAD_X, constants.PAD_Y // 2))
        style_obj.configure('Toolbutton', font=text_font, padding=(constants.PAD_X // 2, constants.PAD_Y // 2)) # 작은 버튼용
        style_obj.map('Toolbutton', background=[('active', '#E0E0E0')])
        style_obj.configure('TEntry', font=text_font, padding=(constants.PAD_X // 2, constants.PAD_Y // 2))
        style_obj.configure('TCombobox', font=text_font, padding=(constants.PAD_X // 2, constants.PAD_Y // 2))
        style_obj.map('TCombobox', fieldbackground=[('readonly', 'white')], selectbackground=[('readonly', '#BDE6FD')], selectforeground=[('readonly', 'black')])
        style_obj.configure('TLabelframe', font=label_font, padding=(constants.PAD_X, constants.PAD_Y // 2))
        style_obj.configure('TLabelframe.Label', font=label_font)
        print("UTILS: ttk 스타일 설정 적용 완료.")
    except tk.TclError as e:
         print(f"UTILS ERROR: ttk 스타일 설정 중 오류: {e}")


def format_chapter_display_name(folder_name):
    """챕터 폴더명을 Treeview 표시용 문자열로 변환 (폴더 아이콘 포함)"""
    match = re.match(r"^Chapter_(\d+)", folder_name, re.IGNORECASE)
    if match and match.group(1).isdigit():
        num = int(match.group(1))
        # 접두사(Chapter_XXX_) 제거 후 나머지 부분을 제목으로 사용
        # 001 -> Chapter_001_
        # 010 -> Chapter_010_
        prefix_to_remove = f"Chapter_{num:03d}_"
        title = folder_name[len(prefix_to_remove):].strip() if folder_name.startswith(prefix_to_remove) else folder_name[len(match.group(0)):].lstrip('_')

        # 밑줄을 공백으로 바꾸고 양 끝 공백 제거
        title = title.replace("_", " ").strip()
        # 폴더 아이콘 + 번호 + 제목
        return f"📁 {num:03d}화{f': {title}' if title else ''}"
    else:
        # 패턴 매칭 실패 시 폴더명 그대로 반환 (아이콘만 추가)
        return f"📁 {folder_name}"

def format_scene_display_name(scene_filename):
    """장면 파일명(XXX.txt)을 Treeview 표시용 문자열로 변환 (장면 아이콘 포함)"""
    match = re.match(r"^(\d+)\.txt$", scene_filename, re.IGNORECASE)
    if match and match.group(1).isdigit():
        num = int(match.group(1))
        # 장면 아이콘 + 번호
        return f"  🎬 {num:03d} 장면" # 들여쓰기 추가
    else:
        # 패턴 매칭 실패 시 파일명 그대로 반환 (아이콘만 추가)
        return f"  📄 {scene_filename}" # 들여쓰기 추가 및 다른 아이콘