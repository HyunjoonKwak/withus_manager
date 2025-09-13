"""
UI 관련 유틸리티 함수들
"""
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import threading
import time
from datetime import datetime, timedelta
import json


def enable_context_menu(widget):
    """위젯에 우클릭 컨텍스트 메뉴 활성화"""
    def show_context_menu(event):
        try:
            # 컨텍스트 메뉴 생성
            context_menu = tk.Menu(widget, tearoff=0)
            
            # 복사 기능
            def copy_text():
                try:
                    if hasattr(widget, 'get') and hasattr(widget, 'selection_range'):
                        # Entry 위젯인 경우
                        if widget.selection_present():
                            widget.clipboard_clear()
                            widget.clipboard_append(widget.selection_get())
                    elif hasattr(widget, 'get') and hasattr(widget, 'index'):
                        # Text 위젯인 경우
                        if widget.tag_ranges(tk.SEL):
                            widget.clipboard_clear()
                            widget.clipboard_append(widget.get(tk.SEL_FIRST, tk.SEL_LAST))
                    elif hasattr(widget, 'get'):
                        # 전체 텍스트 복사
                        widget.clipboard_clear()
                        widget.clipboard_append(widget.get())
                except:
                    pass
            
            # 붙여넣기 기능
            def paste_text():
                try:
                    if hasattr(widget, 'insert') and hasattr(widget, 'delete'):
                        # 선택된 텍스트가 있으면 삭제
                        if hasattr(widget, 'selection_present') and widget.selection_present():
                            widget.delete(tk.SEL_FIRST, tk.SEL_LAST)
                        elif hasattr(widget, 'tag_ranges') and widget.tag_ranges(tk.SEL):
                            widget.delete(tk.SEL_FIRST, tk.SEL_LAST)
                        
                        # 클립보드 내용 붙여넣기
                        clipboard_text = widget.clipboard_get()
                        if hasattr(widget, 'insert'):
                            widget.insert(tk.INSERT, clipboard_text)
                except:
                    pass
            
            # 잘라내기 기능
            def cut_text():
                try:
                    if hasattr(widget, 'get') and hasattr(widget, 'delete'):
                        # 선택된 텍스트가 있으면 클립보드에 복사하고 삭제
                        if hasattr(widget, 'selection_present') and widget.selection_present():
                            widget.clipboard_clear()
                            widget.clipboard_append(widget.selection_get())
                            widget.delete(tk.SEL_FIRST, tk.SEL_LAST)
                        elif hasattr(widget, 'tag_ranges') and widget.tag_ranges(tk.SEL):
                            widget.clipboard_clear()
                            widget.clipboard_append(widget.get(tk.SEL_FIRST, tk.SEL_LAST))
                            widget.delete(tk.SEL_FIRST, tk.SEL_LAST)
                except:
                    pass
            
            # 전체 선택 기능
            def select_all():
                try:
                    if hasattr(widget, 'select_range'):
                        widget.select_range(0, tk.END)
                    elif hasattr(widget, 'tag_add'):
                        widget.tag_add(tk.SEL, "1.0", tk.END)
                        widget.mark_set(tk.INSERT, "1.0")
                        widget.see(tk.INSERT)
                except:
                    pass
            
            # 메뉴 항목 추가
            context_menu.add_command(label="복사", command=copy_text)
            context_menu.add_command(label="붙여넣기", command=paste_text)
            context_menu.add_command(label="잘라내기", command=cut_text)
            context_menu.add_separator()
            context_menu.add_command(label="전체 선택", command=select_all)
            
            # 메뉴 표시
            try:
                context_menu.tk_popup(event.x_root, event.y_root)
            finally:
                context_menu.grab_release()
        except Exception as e:
            print(f"컨텍스트 메뉴 오류: {e}")
    
    # 우클릭 이벤트 바인딩
    widget.bind("<Button-3>", show_context_menu)
    widget.bind("<Control-Button-1>", show_context_menu)  # macOS에서 우클릭


class BaseTab:
    """기본 탭 클래스"""
    
    def __init__(self, parent, app):
        self.parent = parent
        self.app = app
        self.frame = ttk.Frame(parent)
    
    def setup_copy_paste_bindings(self):
        """복사/붙여넣기 바인딩 설정"""
        def bind_to_widgets(widget):
            if isinstance(widget, (tk.Entry, tk.Text, ttk.Entry)):
                enable_context_menu(widget)
            for child in widget.winfo_children():
                bind_to_widgets(child)
        
        bind_to_widgets(self.frame)
    
    def copy_text(self, widget):
        """텍스트 복사"""
        try:
            if hasattr(widget, 'selection_present') and widget.selection_present():
                widget.clipboard_clear()
                widget.clipboard_append(widget.selection_get())
            elif hasattr(widget, 'tag_ranges') and widget.tag_ranges(tk.SEL):
                widget.clipboard_clear()
                widget.clipboard_append(widget.get(tk.SEL_FIRST, tk.SEL_LAST))
        except Exception as e:
            print(f"복사 오류: {e}")
    
    def paste_text(self, widget):
        """텍스트 붙여넣기"""
        try:
            if hasattr(widget, 'insert'):
                clipboard_text = widget.clipboard_get()
                if hasattr(widget, 'selection_present') and widget.selection_present():
                    widget.delete(tk.SEL_FIRST, tk.SEL_LAST)
                elif hasattr(widget, 'tag_ranges') and widget.tag_ranges(tk.SEL):
                    widget.delete(tk.SEL_FIRST, tk.SEL_LAST)
                widget.insert(tk.INSERT, clipboard_text)
        except Exception as e:
            print(f"붙여넣기 오류: {e}")
    
    def select_all(self, widget):
        """전체 선택"""
        try:
            if hasattr(widget, 'select_range'):
                widget.select_range(0, tk.END)
            elif hasattr(widget, 'tag_add'):
                widget.tag_add(tk.SEL, "1.0", tk.END)
                widget.mark_set(tk.INSERT, "1.0")
                widget.see(tk.INSERT)
        except Exception as e:
            print(f"전체 선택 오류: {e}")
    
    def show_context_menu(self, event):
        """컨텍스트 메뉴 표시"""
        try:
            context_menu = tk.Menu(self.frame, tearoff=0)
            context_menu.add_command(label="복사", command=lambda: self.copy_text(event.widget))
            context_menu.add_command(label="붙여넣기", command=lambda: self.paste_text(event.widget))
            context_menu.add_command(label="잘라내기", command=lambda: self.cut_text(event.widget))
            context_menu.add_separator()
            context_menu.add_command(label="전체 선택", command=lambda: self.select_all(event.widget))
            
            try:
                context_menu.tk_popup(event.x_root, event.y_root)
            finally:
                context_menu.grab_release()
        except Exception as e:
            print(f"컨텍스트 메뉴 오류: {e}")


def run_in_thread(func, *args, **kwargs):
    """함수를 별도 스레드에서 실행"""
    def thread_wrapper():
        try:
            func(*args, **kwargs)
        except Exception as e:
            print(f"스레드 실행 오류: {e}")
    
    thread = threading.Thread(target=thread_wrapper, daemon=True)
    thread.start()
    return thread


def format_datetime(dt, format_str="%Y-%m-%d %H:%M:%S"):
    """날짜시간 포맷팅"""
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
        except:
            return dt
    return dt.strftime(format_str)


def safe_get(data, key, default=None):
    """안전한 딕셔너리 접근"""
    if isinstance(data, dict):
        return data.get(key, default)
    return default


def safe_list_get(data, index, default=None):
    """안전한 리스트 접근"""
    if isinstance(data, list) and 0 <= index < len(data):
        return data[index]
    return default
