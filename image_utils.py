# --- START OF FILE image_utils.py ---

# image_utils.py (Pillow Direct Rendering - Upscaling with Font Factor)
import tkinter as tk
from tkinter import filedialog, font as tkFont
import os
import traceback
import platform
import time
import math
try:
    from PIL import Image, ImageDraw, ImageFont, ImageOps # ImageOps 추가 (선택적)
    Image.MAX_IMAGE_PIXELS = 250000000
except ImportError:
    print("ERROR: Pillow 라이브러리가 필요합니다. 'pip install Pillow'")
    Image = None
    ImageDraw = None
    ImageFont = None
    ImageOps = None # Also set to None if import fails

# --- Helper Functions (get_widget_bg_color, _font_cache, get_pillow_font) ---
def get_widget_bg_color(widget):
    """ 위젯의 배경색을 RGB 튜플로 반환 """
    try:
        # Try getting color directly from widget
        bg_color_str = widget.cget('bg')
        root = widget.winfo_toplevel()
        rgb = root.winfo_rgb(bg_color_str)
        return tuple(c // 256 for c in rgb)
    except Exception as e1:
        # Fallback: Try getting default background from a temporary label
        print(f"UTILS WARN: Failed to get widget BG color directly ({e1}). Trying fallback.")
        try:
            # Ensure a root window exists for the temp label
            temp_root = widget.winfo_toplevel() if widget.winfo_exists() else tk.Tk()
            temp_label = tk.Label(temp_root)
            bg_color_str = temp_label.cget('bg')
            rgb = temp_root.winfo_rgb(bg_color_str)
            temp_label.destroy()
            # If the temp root was created here, destroy it
            if not widget.winfo_exists(): temp_root.destroy()
            return tuple(c // 256 for c in rgb)
        except Exception as e2:
             print(f"UTILS ERROR: Failed to get default BG color ({e2}). Returning white.")
             return (255, 255, 255) # Final fallback: white

_font_cache = {}

# *** 수정된 get_pillow_font 함수 시그니처 및 내부 로직 변경 ***
def get_pillow_font(tk_font_spec, font_size_increase=0, user_font_path=None, upscale_factor=1.0):
    """
    Tkinter 폰트 스펙, 사용자 경로, 업스케일링 팩터를 기반으로 Pillow 폰트 객체를 로드합니다.
    """
    # 캐시 키에 upscale_factor 추가
    cache_key = (tk_font_spec, font_size_increase, user_font_path if user_font_path else "", upscale_factor)
    if cache_key in _font_cache:
        # print(f"UTILS FONT DEBUG: Cache hit for {cache_key}")
        return _font_cache[cache_key]
    # print(f"UTILS FONT DEBUG: Cache miss for {cache_key}")

    try:
        tk_font = tkFont.Font(font=tk_font_spec)
        actual_font = tk_font.actual()
        family = actual_font.get('family', 'Arial')
        # --- 수정: 최종 폰트 크기 계산 시 upscale_factor 적용 ---
        base_size_points = actual_font.get('size', 10) # Tkinter size (usually points)
        # Convert base points to pixels, add increase, then apply upscale factor
        base_size_pixels = int(base_size_points * 96 / 72) # Approximate pixels
        target_size = int((base_size_pixels + font_size_increase) * upscale_factor)
        target_size = max(1, target_size) # 최소 1 이상 보장
        # --- 수정 끝 ---
        weight = actual_font.get('weight', 'normal')
        slant = actual_font.get('slant', 'roman')
        # print(f"UTILS FONT DEBUG: Requested Tk Font: {actual_font}, Base Px: {base_size_pixels}, Increase: {font_size_increase}, Factor: {upscale_factor}, Target Pillow Size: {target_size}")

        pillow_font = None

        # 1. 사용자 지정 경로 우선 확인 (target_size 사용)
        if user_font_path and isinstance(user_font_path, str) and os.path.isfile(user_font_path):
            try:
                pillow_font = ImageFont.truetype(user_font_path, target_size) # target_size 사용
                print(f"UTILS FONT INFO: 사용자 지정 폰트 로드 성공: {user_font_path} (Target Size: {target_size})")
            except Exception as e:
                print(f"UTILS FONT WARN: 사용자 지정 폰트 '{user_font_path}' 로드 실패: {e}. Fallback 시도.")
                pillow_font = None

        # 2. Fallback 로직 (target_size 사용)
        if pillow_font is None:
            # --- Fallback 폰트 파일 경로 찾는 로직 ---
            found_path = None; system = platform.system();
            base_filename = None; family_lower = family.lower().replace(" ", "")
            if "malgungothic" in family_lower or "맑은고딕" in family_lower: base_filename = "malgun"
            elif "nanumgothic" in family_lower: base_filename = "NanumGothic"
            elif "dotum" in family_lower or "돋움" in family_lower: base_filename = "dotum"
            elif "gulim" in family_lower or "굴림" in family_lower: base_filename = "gulim"
            elif "batang" in family_lower or "바탕" in family_lower: base_filename = "batang"
            elif "gungsuh" in family_lower or "궁서" in family_lower: base_filename = "gungsuh"
            elif "applesdgothicneo" in family_lower: base_filename = "AppleSDGothicNeo"
            elif "arial" in family_lower: base_filename = "arial"
            elif "timesnewroman" in family_lower: base_filename = "times"

            potential_filenames = []
            if base_filename:
                style_suffix = ""
                if weight == 'bold': style_suffix += "bd" # Common suffixes
                if slant == 'italic': style_suffix += "i"
                # Generate potential filenames (.ttf and .otf)
                potential_filenames.append(f"{base_filename}{style_suffix}.ttf")
                potential_filenames.append(f"{base_filename}{style_suffix}.otf")
                if style_suffix: # Also try base name if style wasn't found
                     potential_filenames.append(f"{base_filename}.ttf")
                     potential_filenames.append(f"{base_filename}.otf")

            # Font directories based on OS
            font_dirs = []
            if system == "Windows": font_dirs = [os.path.join(os.environ.get("SystemRoot", "C:\\Windows"), "Fonts")]
            elif system == "Darwin": font_dirs = ["/System/Library/Fonts", "/Library/Fonts", os.path.expanduser("~/Library/Fonts")]
            else: font_dirs = ["/usr/share/fonts", "/usr/local/share/fonts", os.path.expanduser("~/.fonts")]

            # Search for the font file
            for fname in potential_filenames:
                for dir_path in font_dirs:
                    full_dir_path = os.path.expanduser(dir_path)
                    if not os.path.isdir(full_dir_path): continue
                    try_path = os.path.join(full_dir_path, fname)
                    if os.path.exists(try_path): found_path = try_path; break
                    # Search one level deeper (optional)
                    try:
                        for item in os.listdir(full_dir_path):
                            item_path = os.path.join(full_dir_path, item)
                            if os.path.isdir(item_path):
                                sub_try_path = os.path.join(item_path, fname)
                                if os.path.exists(sub_try_path): found_path = sub_try_path; break
                        if found_path: break
                    except OSError: pass
                if found_path: break
            # --- Fallback 경로 탐색 로직 끝 ---

            if found_path:
                try:
                    pillow_font = ImageFont.truetype(found_path, target_size) # target_size 사용
                    print(f"UTILS FONT INFO: Fallback 폰트 로드 성공: {found_path} (Target Size: {target_size})")
                except Exception as e:
                    print(f"UTILS FONT WARN: Fallback 폰트 '{found_path}' 로드 실패: {e}. Pillow 기본 폰트 사용.")
                    pillow_font = None
            else:
                 # Log only if potential filenames were generated
                 if potential_filenames:
                     print(f"UTILS FONT WARN: Fallback 폰트 파일 못 찾음 ('{potential_filenames[0]}' or similar). Pillow 기본 폰트 사용.")
                 else:
                     print(f"UTILS FONT WARN: Fallback 폰트 추측 불가 (Family: '{family}'). Pillow 기본 폰트 사용.")
                 pillow_font = None

        # 3. Pillow 기본 폰트 (target_size 사용, 단 load_default는 크기 조절 불가)
        if pillow_font is None:
            try:
                # Try common system fonts first with target_size
                try:
                    pillow_font = ImageFont.truetype("arial.ttf", target_size) # target_size 사용
                    print(f"UTILS FONT INFO: 시스템 폰트(Arial) 로드 성공 (Target Size: {target_size})")
                except IOError:
                     try:
                        pillow_font = ImageFont.truetype("DejaVuSans.ttf", target_size) # target_size 사용
                        print(f"UTILS FONT INFO: 시스템 폰트(DejaVuSans) 로드 성공 (Target Size: {target_size})")
                     except IOError:
                         # If truetype fails, use load_default (size cannot be specified)
                         pillow_font = ImageFont.load_default()
                         print(f"UTILS FONT INFO: Pillow 내장 기본 폰트 사용 (크기 조절 불가).")
            except Exception as e:
                print(f"UTILS FONT WARN: 기본 폰트 로드 중 예외 발생: {e}")
                pillow_font = ImageFont.load_default()


        _font_cache[cache_key] = pillow_font
        return pillow_font

    except Exception as e:
        print(f"UTILS FONT ERROR: 폰트 로드 중 심각한 오류 (Spec: '{tk_font_spec}', UserPath: '{user_font_path}', Factor: {upscale_factor}): {e}")
        traceback.print_exc()
        fallback_font = ImageFont.load_default()
        _font_cache[cache_key] = fallback_font
        return fallback_font


# --- 메인 렌더링 함수 ---
def render_text_widget_to_image(text_widget: tk.Text, root_window: tk.Tk, render_font_path: str = None):
    """ tk.Text 위젯 내용을 분석하여 Pillow 이미지로 직접 렌더링 (업스케일링 적용) """
    if Image is None or ImageDraw is None or ImageFont is None:
         return False, "Pillow 라이브러리가 설치되지 않았습니다."

    print(f"IMAGE_UTILS: 위젯 내용 직접 렌더링 시작 (사용자 폰트: '{render_font_path or '미지정'}')...")
    start_time = time.time()

    # --- 사용자 정의 설정값 (조정) ---
    UPSCALE_FACTOR = 7.0       # 렌더링 해상도 배율 (1.0 = 원본, 2.0 = 2배)
    FONT_SIZE_INCREASE = 12     # 업스케일링 후 추가 폰트 증가량 (미세조정)
    # 간격도 업스케일링에 맞춰 조정
    EXTRA_LINE_SPACING = int(3 * UPSCALE_FACTOR)
    EXTRA_PARAGRAPH_SPACING = int(7 * UPSCALE_FACTOR)
    WRAP_MODE = 'word'
    MIN_RENDER_WIDTH = int(300 * UPSCALE_FACTOR) # 업스케일링된 최소 너비
    MAX_RENDER_WIDTH = int(1200 * UPSCALE_FACTOR) # 업스케일링된 최대 너비
    BOTTOM_MARGIN = int(10 * UPSCALE_FACTOR) # 하단 여백 추가
    # ------------------------

    try:
        # 1. 위젯 정보 수집
        root_window.update_idletasks() # 정확한 위젯 크기 얻기
        bg_color = get_widget_bg_color(text_widget)
        widget_width = text_widget.winfo_width()
        try: padx = int(text_widget.cget('padx'))
        except: padx = 5
        try: pady = int(text_widget.cget('pady'))
        except: pady = 5

        original_content_width = widget_width - 2 * padx
        if original_content_width <= 0:
            print("WARN: 위젯 콘텐츠 너비 계산 불가. widget_width 사용.")
            original_content_width = widget_width
            padx = 0

        # *** 수정: 렌더링 너비를 업스케일링 ***
        render_width = max(MIN_RENDER_WIDTH, min(MAX_RENDER_WIDTH, int(original_content_width * UPSCALE_FACTOR)))
        print(f"Original content width: {original_content_width}, UPSCALE_FACTOR: {UPSCALE_FACTOR}, Target render width: {render_width}")

        default_font_spec = text_widget.cget('font')
        # *** 수정: get_pillow_font 호출 시 upscale_factor 전달 ***
        default_pillow_font = get_pillow_font(default_font_spec, FONT_SIZE_INCREASE, user_font_path=render_font_path, upscale_factor=UPSCALE_FACTOR)
        default_fg_color = text_widget.cget('fg')

        # 2. 초기 이미지 생성 (업스케일링된 너비 사용)
        initial_height = 40000 # 필요 시 더 늘릴 수 있음
        image = Image.new('RGB', (render_width, initial_height), color=bg_color)
        draw = ImageDraw.Draw(image)

        # 3. 텍스트 분석 및 렌더링 (업스케일링된 너비 기준)
        scaled_pady = int(pady * UPSCALE_FACTOR) # 패딩도 스케일링
        current_y = float(scaled_pady)
        max_drawn_y = current_y
        line_start_index = "1.0"
        prev_line_had_content = False

        while text_widget.compare(line_start_index, "<", "end"):
            line_end_index = text_widget.index(f"{line_start_index} lineend")
            is_empty_line = text_widget.compare(line_start_index, "==", line_end_index)

            if prev_line_had_content:
                 current_y += EXTRA_PARAGRAPH_SPACING # 스케일링된 값 사용
                 max_drawn_y = max(max_drawn_y, current_y)

            if is_empty_line:
                # *** 수정: get_pillow_font 호출 시 upscale_factor 전달 ***
                default_font_for_height = get_pillow_font(default_font_spec, FONT_SIZE_INCREASE, user_font_path=render_font_path, upscale_factor=UPSCALE_FACTOR)
                try: bbox = default_font_for_height.getbbox("X")
                except AttributeError: bbox = (0, 0, int(10*UPSCALE_FACTOR), int(12*UPSCALE_FACTOR)) # Fallback bbox
                line_height = bbox[3] - bbox[1] if bbox else int(15 * UPSCALE_FACTOR) # 스케일링된 기본 높이
                current_y += line_height + EXTRA_LINE_SPACING # 스케일링된 값 사용
                max_drawn_y = max(max_drawn_y, current_y)
                line_start_index = text_widget.index(f"{line_start_index}+1line")
                prev_line_had_content = False
                continue

            # --- 내용 있는 줄 처리 ---
            current_x = float(0)
            max_line_height_in_visual_line = 0
            line_processed_height = 0

            segment_start_index = line_start_index
            while text_widget.compare(segment_start_index, "<", line_end_index):
                tags = text_widget.tag_names(segment_start_index)
                effective_font_spec = default_font_spec; effective_fg_color = default_fg_color
                tag_font = None; tag_fg = None
                for tag in reversed(tags): 
                    current_tag_font = text_widget.tag_cget(tag, 'font')
                    if current_tag_font: tag_font = current_tag_font
                    break
                if tag_font: effective_font_spec = tag_font
                for tag in reversed(tags): 
                    current_tag_fg = text_widget.tag_cget(tag, 'foreground')
                    if current_tag_fg: tag_fg = current_tag_fg
                    break
                if tag_fg: effective_fg_color = tag_fg

                # *** 수정: get_pillow_font 호출 시 upscale_factor 전달 ***
                current_pillow_font = get_pillow_font(effective_font_spec, FONT_SIZE_INCREASE, user_font_path=render_font_path, upscale_factor=UPSCALE_FACTOR)
                try: bbox_ay = current_pillow_font.getbbox("Ay")
                except AttributeError: bbox_ay = (0,0, int(10*UPSCALE_FACTOR), int(15*UPSCALE_FACTOR)) # Fallback
                current_segment_font_height = bbox_ay[3] - bbox_ay[1] if bbox_ay else int(15 * UPSCALE_FACTOR)
                max_line_height_in_visual_line = max(max_line_height_in_visual_line, current_segment_font_height)

                # 세그먼트 끝 찾기
                next_change = line_end_index; current_effective_tags = set(tags); check_index = text_widget.index(f"{segment_start_index}+1c")
                while text_widget.compare(check_index, "<", line_end_index): 
                    check_tags = set(text_widget.tag_names(check_index))
                    if check_tags != current_effective_tags: next_change = check_index
                    break
                check_index = text_widget.index(f"{check_index}+1c")
                segment_end_index = next_change; segment_text = text_widget.get(segment_start_index, segment_end_index)

                # --- Word/Char Wrap 및 그리기 (render_width 사용) ---
                remaining_text = segment_text
                while remaining_text:
                    drawable_text = ""; drawable_width = 0; last_space_index = -1; last_space_width = 0; consumed_chars = 0
                    for i, char in enumerate(remaining_text):
                        try: char_width = draw.textlength(char, font=current_pillow_font)
                        except AttributeError: char_width = int(10 * UPSCALE_FACTOR) # Fallback width
                        if current_x + drawable_width + char_width <= render_width:
                             drawable_text += char; drawable_width += char_width; consumed_chars += 1
                             if char.isspace(): last_space_index = i; last_space_width = drawable_width
                        else: # Width exceeded
                            if WRAP_MODE == 'word' and last_space_index >= 0:
                                consumed_chars = last_space_index + 1; drawable_text = remaining_text[:last_space_index]; drawable_width = last_space_width
                            else: drawable_text = remaining_text[:consumed_chars]
                            break
                    else: consumed_chars = len(remaining_text)

                    if drawable_text:
                         try: draw.text((current_x, current_y + line_processed_height), drawable_text, fill=effective_fg_color, font=current_pillow_font)
                         except Exception as draw_e: print(f"ERROR: draw.text 실패: {draw_e}")
                         current_x += drawable_width
                         max_line_height_in_visual_line = max(max_line_height_in_visual_line, current_segment_font_height)

                    remaining_text = remaining_text[consumed_chars:]
                    if remaining_text: # 줄바꿈 발생
                         line_processed_height += max_line_height_in_visual_line + EXTRA_LINE_SPACING
                         current_x = float(0); max_line_height_in_visual_line = 0

                segment_start_index = segment_end_index

            # Tkinter 라인 처리 완료
            current_y += line_processed_height
            prev_line_had_content = True
            current_y += max_line_height_in_visual_line + EXTRA_LINE_SPACING
            max_drawn_y = max(max_drawn_y, current_y)
            line_start_index = text_widget.index(f"{line_start_index}+1line")

        # 4. 실제 콘텐츠 영역 크롭 (하단 여백 추가된 버전)
        # 최종 높이 계산 (하단 여백 추가, 스케일링된 최소 높이 보장)
        BOTTOM_MARGIN = int(40 * UPSCALE_FACTOR) # 예: 10 픽셀 상당의 여백
        # 마지막으로 그려진 Y 좌표(max_drawn_y)에 상단 패딩(scaled_pady)과 하단 여백(BOTTOM_MARGIN)을 더함
        final_drawn_height = math.ceil(max_drawn_y + scaled_pady + BOTTOM_MARGIN)
        final_drawn_height = max(scaled_pady * 2 + int(20 * UPSCALE_FACTOR), final_drawn_height) # 스케일링된 최소 높이
        final_drawn_height = min(initial_height, final_drawn_height) # 초기 높이 초과 방지

        print(f"DEBUG: Max drawn Y = {max_drawn_y}, Final drawn height = {final_drawn_height}")
        final_image_scaled = image.crop((0, 0, render_width, final_drawn_height))

        # --- 최종 이미지 생성 및 리사이즈 ---
        resampling_filter = Image.Resampling.LANCZOS if hasattr(Image, 'Resampling') and hasattr(Image.Resampling, 'LANCZOS') else Image.LANCZOS

        if UPSCALE_FACTOR > 1.0:
            target_width = original_content_width # 원본 콘텐츠 너비로 복원
            target_height = int(final_image_scaled.height / UPSCALE_FACTOR)
            print(f"Resizing final image from {final_image_scaled.size} to ({target_width}, {target_height}) using {resampling_filter}")
            try:
                final_image_resized = final_image_scaled.resize((target_width, target_height), resample=resampling_filter)
            except Exception as resize_err:
                print(f"WARN: Final image resize failed: {resize_err}. Using upscaled image.")
                final_image_resized = final_image_scaled
        else:
            final_image_resized = final_image_scaled

        # 최종 캔버스 생성 (원본 패딩 적용)
        final_canvas_width = final_image_resized.width + 2 * padx
        final_canvas_height = final_image_resized.height + 2 * pady # 상하 패딩도 적용
        final_canvas = Image.new('RGB', (final_canvas_width, final_canvas_height), color=bg_color)
        final_canvas.paste(final_image_resized, (padx, pady)) # 패딩 위치에 붙여넣기

        print(f"최종 렌더링 완료. 저장될 이미지 크기: {final_canvas.size}")
        end_time = time.time(); print(f"렌더링 소요 시간: {end_time - start_time:.2f} 초")

        # 6. 파일 저장 경로 묻기
        save_path = filedialog.asksaveasfilename(
            title="이미지 파일로 저장 (렌더링)",
            defaultextension=".png",
            filetypes=[("PNG 파일", "*.png"), ("모든 파일", "*.*")],
            parent=root_window
        )
        if not save_path:
            print("INFO: 이미지 저장 취소됨.")
            return False, "사용자가 저장을 취소했습니다."

        # 7. 이미지 파일 저장 (PNG 옵션 추가)
        try:
            final_canvas.save(save_path, "PNG", optimize=True, compress_level=6)
            print(f"이미지가 저장되었습니다: {save_path}")
            return True, None
        except Exception as save_err:
             msg = f"이미지 파일 저장 중 오류 발생: {save_err}"
             print(f"ERROR: {msg}")
             traceback.print_exc()
             return False, msg

    except ImportError:
        return False, "Pillow 라이브러리가 필요합니다. `pip install Pillow`"
    except Exception as e:
        msg = f"이미지 직접 렌더링 중 오류: {e.__class__.__name__}: {e}"
        print(f"ERROR: {msg}")
        traceback.print_exc()
        return False, msg

# --- END OF FILE image_utils.py ---