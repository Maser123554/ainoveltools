# gui_panels/treeview_panel.py
import tkinter as tk
from tkinter import ttk
import os
import re # 폴더/파일명 파싱용
import platform
import constants
import utils # format_chapter_display_name 등 사용

class TreeviewPanel(ttk.Frame):
    """트리뷰 영역 GUI (우측)"""
    def __init__(self, parent, app_core, tree_font, heading_font, **kwargs):
        super().__init__(parent, padding=(constants.PAD_X, constants.PAD_Y), **kwargs)
        self.app_core = app_core
        self.tree_font = tree_font
        self.heading_font = heading_font

        self.widgets = {}
        self._create_widgets()
        self.treeview = self.widgets['treeview']

    def _create_widgets(self):
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        tree_frame = ttk.LabelFrame(self, text="📚 소설 / 챕터 / 장면", padding=(constants.PAD_X, constants.PAD_Y))
        tree_frame.grid(row=0, column=0, sticky='nsew')
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)

        # Treeview 생성
        tree = ttk.Treeview(tree_frame, selectmode='browse', style="Treeview")
        tree.grid(row=0, column=0, sticky='nsew')
        # 스크롤바
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree.yview)
        scrollbar.grid(row=0, column=1, sticky='ns')
        tree.config(yscrollcommand=scrollbar.set)
        tree.heading('#0', text='소설/챕터/장면', anchor='w')
        self.widgets['treeview'] = tree
        self.widgets['scrollbar'] = scrollbar

        # --- 이벤트 바인딩 ---
        tree.bind("<<TreeviewSelect>>", self._on_tree_select) # 선택 변경
        tree.bind("<Double-1>", self._on_tree_double_click) # 더블클릭 (로드)
        # 우클릭 메뉴 바인딩 (플랫폼별)
        if platform.system() == 'Darwin': # macOS
             tree.bind("<Button-2>", self._show_context_menu)
             tree.bind("<Control-Button-1>", self._show_context_menu)
        else: # Windows and Linux
             tree.bind("<Button-3>", self._show_context_menu)

        # --- 컨텍스트 메뉴 생성 ---
        # 소설 폴더용
        self.tree_novel_context_menu = tk.Menu(tree, tearoff=0)
        self.tree_novel_context_menu.add_command(label="✏️ 소설 이름 변경", command=self._request_rename_novel)
        self.tree_novel_context_menu.add_separator()
        self.tree_novel_context_menu.add_command(label="🗑️ 소설 삭제", command=self._request_delete_novel)

        # 챕터(Arc) 폴더용
        self.tree_chapter_context_menu = tk.Menu(tree, tearoff=0)
        self.tree_chapter_context_menu.add_command(label="✏️ 챕터 제목 변경", command=self._request_rename_chapter)
        # self.tree_chapter_context_menu.add_command(label="➕ 새 장면 추가", command=self._request_new_scene) # 필요 시 추가
        self.tree_chapter_context_menu.add_separator()
        self.tree_chapter_context_menu.add_command(label="🗑️ 챕터 폴더 삭제", command=self._request_delete_chapter)

        # 장면(Scene) 파일용
        self.tree_scene_context_menu = tk.Menu(tree, tearoff=0)
        # self.tree_scene_context_menu.add_command(label="✏️ 장면 번호 변경", command=self._request_rename_scene) # 구현 복잡성 높음
        self.tree_scene_context_menu.add_command(label="🗑️ 장면 삭제", command=self._request_delete_scene)


    # --- Treeview 이벤트 핸들러 ---

    def _on_tree_select(self, event=None):
        """트리뷰 선택 변경 시 AppCore에 알림"""
        selected_id = self.treeview.focus() # iid는 경로 (소설명, 챕터경로, 장면경로)
        if selected_id:
            tags = self.treeview.item(selected_id, 'tags')
            self.app_core.handle_tree_selection(selected_id, tags)
        else: # 선택 해제 시
             self.app_core.handle_tree_selection(None, [])

    def _on_tree_double_click(self, event=None):
        """더블클릭 시 AppCore에 로드 요청"""
        selected_id = self.treeview.focus() # iid는 경로
        if selected_id:
            tags = self.treeview.item(selected_id, 'tags')
            # 소설, 챕터, 장면 모두 로드 요청 가능하도록 AppCore에 전달
            self.app_core.handle_tree_load_request(selected_id, tags)

    def _show_context_menu(self, event):
        """우클릭 시 컨텍스트 메뉴 표시"""
        item_id = self.treeview.identify_row(event.y)
        if item_id:
            # 클릭한 아이템 선택 및 포커스
            if item_id not in self.treeview.selection():
                self.treeview.selection_set(item_id)
                self.treeview.focus(item_id)

            tags = self.treeview.item(item_id, 'tags')
            if 'scene' in tags:
                self.tree_scene_context_menu.tk_popup(event.x_root, event.y_root)
            elif 'chapter' in tags:
                self.tree_chapter_context_menu.tk_popup(event.x_root, event.y_root)
            elif 'novel' in tags:
                self.tree_novel_context_menu.tk_popup(event.x_root, event.y_root)

    # --- 컨텍스트 메뉴 액션 요청 ---

    def _request_rename_novel(self):
        """소설 이름 변경 AppCore 요청"""
        selected_id = self.treeview.focus() # 소설 이름
        if selected_id and 'novel' in self.treeview.item(selected_id, 'tags'):
            self.app_core.handle_rename_novel_request(selected_id)

    def _request_delete_novel(self):
        """소설 삭제 AppCore 요청"""
        selected_id = self.treeview.focus() # 소설 이름
        if selected_id and 'novel' in self.treeview.item(selected_id, 'tags'):
            self.app_core.handle_delete_novel_request(selected_id)

    def _request_rename_chapter(self):
        """챕터 폴더 이름 변경 AppCore 요청"""
        selected_id = self.treeview.focus() # 챕터 폴더 경로
        if selected_id and 'chapter' in self.treeview.item(selected_id, 'tags'):
            self.app_core.handle_rename_chapter_request(selected_id)

    def _request_delete_chapter(self):
        """챕터 폴더 삭제 AppCore 요청"""
        selected_id = self.treeview.focus() # 챕터 폴더 경로
        if selected_id and 'chapter' in self.treeview.item(selected_id, 'tags'):
            self.app_core.handle_delete_chapter_request(selected_id)

    def _request_delete_scene(self):
        """장면 파일 삭제 AppCore 요청"""
        selected_id = self.treeview.focus() # 장면 파일(.txt) 경로
        if selected_id and 'scene' in self.treeview.item(selected_id, 'tags'):
            self.app_core.handle_delete_scene_request(selected_id)

    # def _request_new_scene(self): # 새 장면 추가 (컨텍스트 메뉴용, 필요 시 구현)
    #     selected_id = self.treeview.focus() # 챕터 폴더 경로
    #     if selected_id and 'chapter' in self.treeview.item(selected_id, 'tags'):
    #         # AppCore에 챕터 폴더 내 새 장면 생성 요청
    #         self.app_core.handle_new_scene_request_from_chapter(selected_id)
    #     else: # 소설 노드에서 호출될 경우 현재 소설의 마지막 챕터에 추가?
    #         print("DEBUG: 새 장면 추가는 챕터 폴더에서만 가능합니다.")


    # --- AppCore에서 호출하는 메소드 ---

    def refresh_tree(self):
        """트리뷰 내용 새로고침 (파일 시스템 기반 - 챕터 폴더 및 장면 파일 스캔)"""
        print("GUI Treeview: 새로고침 시작...")
        selected_id = self.treeview.focus()
        open_nodes = {item for item in self.treeview.get_children('')} # 모든 최상위 노드 ID
        open_nodes.update({item for item in self.treeview.tag_has('chapter') if self.treeview.item(item, 'open')}) # 열린 챕터 노드 ID 추가

        for item in self.treeview.get_children(''):
            self.treeview.delete(item)

        base_dir = constants.BASE_SAVE_DIR
        if not os.path.exists(base_dir):
            try: os.makedirs(base_dir)
            except OSError: print("GUI ERROR: Treeview 새로고침 중 기본 폴더 생성 실패."); return

        try:
            # Scan for novel folders (directories in base_dir)
            novel_folders = sorted([d for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d)) and not d.startswith('.')])
        except OSError as e:
            print(f"GUI ERROR: 소설 폴더 목록 읽기 실패: {e}")
            return

        # 패턴 정의
        chapter_pattern = re.compile(r"^Chapter_(\d+)", re.IGNORECASE)
        scene_pattern = re.compile(r"^(\d+)\.txt$", re.IGNORECASE) # 장면 텍스트 파일

        for novel_name in novel_folders:
            novel_dir = os.path.join(base_dir, novel_name)
            try:
                # Novel node iid is the novel name (simple string)
                novel_node_id_tree = self.treeview.insert('', 'end', iid=novel_name, text=f"📁 {novel_name}", open=(novel_name in open_nodes), tags=('novel',))
            except tk.TclError as e:
                print(f"GUI WARN: 소설 노드({novel_name}) 삽입 실패: {e}. 건너<0xEB><0x9C><0x84.")
                continue

            # Scan for chapter FOLDERS and sort them
            chapters = [] # (chap_num, chapter_dir_path, chapter_folder_name)
            try:
                with os.scandir(novel_dir) as chap_entries:
                     for entry in chap_entries:
                         if entry.is_dir():
                             match = chapter_pattern.match(entry.name)
                             if match and match.group(1).isdigit():
                                 try: chapters.append((int(match.group(1)), entry.path, entry.name))
                                 except ValueError: pass
            except OSError as e: print(f"GUI WARN: '{novel_name}' 챕터 스캔 실패: {e}")

            chapters.sort(key=lambda x: x[0]) # Sort by chapter number

            # Insert chapter nodes
            for chap_num, chapter_path, chapter_folder_name in chapters:
                 # Chapter node iid is the chapter FOLDER path
                 chapter_display_name = utils.format_chapter_display_name(chapter_folder_name)
                 try:
                     chapter_node_id_tree = self.treeview.insert(novel_node_id_tree, 'end', iid=chapter_path, text=chapter_display_name, open=(chapter_path in open_nodes), tags=('chapter',))
                 except tk.TclError as e:
                     print(f"GUI WARN: 챕터 노드({chapter_folder_name}) 삽입 실패: {e}. 이 소설의 나머지 챕터 건너<0xEB><0x9C><0x84.")
                     break # 다음 소설로

                 # Scan for scene FILES within the chapter folder and sort them
                 scenes = [] # (scene_num, scene_file_path)
                 try:
                     with os.scandir(chapter_path) as scene_entries:
                         for entry in scene_entries:
                             if entry.is_file():
                                 match = scene_pattern.match(entry.name)
                                 if match and match.group(1).isdigit():
                                     try: scenes.append((int(match.group(1)), entry.path))
                                     except ValueError: pass
                 except OSError as e: print(f"GUI WARN: '{chapter_folder_name}' 장면 스캔 실패: {e}")

                 scenes.sort(key=lambda x: x[0]) # Sort by scene number

                 # Insert scene nodes
                 for scene_num, scene_path in scenes:
                     scene_display_name = f"🎬 {scene_num:03d} 장면" # Simple display name
                     try:
                         # Scene node iid is the scene text FILE path
                         self.treeview.insert(chapter_node_id_tree, 'end', iid=scene_path, text=scene_display_name, tags=('scene',))
                     except tk.TclError as e:
                         print(f"GUI WARN: 장면 노드({os.path.basename(scene_path)}) 삽입 실패: {e}. 이 챕터의 나머지 장면 건너<0xEB><0x9C><0x84.")
                         break # 다음 챕터로

        # Restore selection if it still exists
        if selected_id and self.treeview.exists(selected_id):
             self.select_item(selected_id)
        # If selection doesn't exist, try selecting the parent chapter or novel
        elif selected_id:
             parent_chapter = os.path.dirname(selected_id) # Try parent chapter path
             if self.treeview.exists(parent_chapter):
                  self.select_item(parent_chapter)
             else:
                  parent_novel = os.path.basename(parent_chapter) # Try parent novel name
                  if self.treeview.exists(parent_novel):
                      self.select_item(parent_novel)

        print("GUI Treeview: 새로고침 완료.")


    def select_item(self, item_id):
        """특정 ID의 아이템 선택 및 포커스"""
        if self.treeview.exists(item_id):
            try:
                # 부모 노드 펼치기 (소설 -> 챕터 폴더 펼치기)
                parent_id = self.treeview.parent(item_id)
                if parent_id and not self.treeview.item(parent_id, 'open'):
                    self.treeview.item(parent_id, open=True)
                    # 소설 노드도 펼치기 (만약 챕터의 부모가 소설이라면)
                    grandparent_id = self.treeview.parent(parent_id)
                    if grandparent_id and not self.treeview.item(grandparent_id, 'open'):
                         self.treeview.item(grandparent_id, open=True)

                self.treeview.selection_set(item_id)
                self.treeview.focus(item_id)
                # 화면에 보이도록 스크롤 (after_idle 사용 권장)
                self.treeview.after_idle(lambda iid=item_id: self._safe_tree_see(iid))
            except tk.TclError as e: print(f"GUI WARN: 트리뷰 아이템 선택 오류 ({item_id}): {e}")
            except Exception as e: print(f"GUI ERROR: 트리뷰 아이템 선택 중 오류 ({item_id}): {e}")

    def _safe_tree_see(self, item_id):
        """treeview.see() 안전 호출"""
        try:
            if self.treeview.exists(item_id):
                self.treeview.see(item_id)
        except tk.TclError: pass
        except Exception as e: print(f"GUI WARN: 트리뷰 see 오류 ({item_id}): {e}")


    def deselect_all(self):
        """트리뷰 선택 해제"""
        try:
             selection = self.treeview.selection()
             if selection: self.treeview.selection_remove(selection)
             focused = self.treeview.focus()
             if focused: self.treeview.focus("")
        except tk.TclError: pass

    def update_ui_state(self, is_busy: bool):
        """트리뷰 자체의 활성화/비활성화 (선택적)"""
        # 트리뷰 자체 비활성화는 보통 불필요
        pass

    def get_item_text(self, item_id):
        """주어진 ID의 트리뷰 아이템 표시 텍스트 반환"""
        if self.treeview.exists(item_id):
             try: return self.treeview.item(item_id, 'text')
             except tk.TclError: return ""
        return ""