"""
╔══════════════════════════════════════════════╗
║          STUDY PLANNER — Python Tkinter       ║
║  Features:                                    ║
║  • Add/edit/delete study sessions             ║
║  • Subject colour tags                        ║
║  • Priority levels (High / Medium / Low)      ║
║  • Mark tasks as complete                     ║
║  • Built-in Pomodoro timer                    ║
║  • Progress dashboard                         ║
║  • Persistent JSON storage                    ║
╚══════════════════════════════════════════════╝
"""

import tkinter as tk
from tkinter import messagebox, ttk, font as tkfont
import json
import os
from datetime import datetime, date


# ─── Constants ────────────────────────────────────────────────────────────────

DATA_FILE = "study_data.json"

PRIORITY_COLORS = {
    "High":   "#e74c3c",
    "Medium": "#f39c12",
    "Low":    "#27ae60",
}

SUBJECT_PALETTE = [
    "#3498db", "#9b59b6", "#e67e22", "#1abc9c",
    "#e91e63", "#00bcd4", "#ff5722", "#607d8b",
]

BG_DARK   = "#1a1a2e"
BG_MID    = "#16213e"
BG_CARD   = "#0f3460"
ACCENT    = "#e94560"
ACCENT2   = "#533483"
TEXT_MAIN = "#eaeaea"
TEXT_DIM  = "#9e9e9e"
SUCCESS   = "#00c896"
WARNING   = "#f5a623"

POMODORO_WORK  = 25 * 60   # seconds
POMODORO_SHORT =  5 * 60
POMODORO_LONG  = 15 * 60


# ─── Data Layer ───────────────────────────────────────────────────────────────

def load_data() -> dict:
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {"tasks": [], "subjects": [], "pomodoro_count": 0}


def save_data(data: dict):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


def new_task(subject, topic, due_date, priority, notes="") -> dict:
    return {
        "id":         datetime.now().strftime("%Y%m%d%H%M%S%f"),
        "subject":    subject,
        "topic":      topic,
        "due_date":   due_date,
        "priority":   priority,
        "notes":      notes,
        "done":       False,
        "created_at": datetime.now().isoformat(),
    }


# ─── Main Application ──────────────────────────────────────────────────────────

class StudyPlanner(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Study Planner")
        self.geometry("1100x720")
        self.minsize(860, 600)
        self.configure(bg=BG_DARK)
        self.resizable(True, True)

        # State
        self.data             = load_data()
        self.filter_subject   = tk.StringVar(value="All")
        self.filter_priority  = tk.StringVar(value="All")
        self.filter_status    = tk.StringVar(value="Pending")
        self.search_var       = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self.refresh_list())

        # Pomodoro state
        self.pomo_running  = False
        self.pomo_paused   = False
        self.pomo_mode     = "Work"          # Work | Short Break | Long Break
        self.pomo_time_left = POMODORO_WORK
        self.pomo_sessions = self.data.get("pomodoro_count", 0)
        self._pomo_job     = None

        self._build_ui()
        self.refresh_list()
        self._update_dashboard()

    # ── UI Construction ──────────────────────────────────────────────────────

    def _build_ui(self):
        self._style()
        self._sidebar()
        self._main_area()

    def _style(self):
        style = ttk.Style(self)
        style.theme_use("clam")

        style.configure("TNotebook",          background=BG_MID, borderwidth=0)
        style.configure("TNotebook.Tab",      background=BG_CARD, foreground=TEXT_DIM,
                         padding=[18, 8], font=("Segoe UI", 10, "bold"))
        style.map("TNotebook.Tab",
                  background=[("selected", ACCENT)],
                  foreground=[("selected", "#ffffff")])

        style.configure("Treeview",           background=BG_CARD, foreground=TEXT_MAIN,
                         fieldbackground=BG_CARD, rowheight=36,
                         font=("Segoe UI", 10))
        style.configure("Treeview.Heading",   background=BG_MID, foreground=ACCENT,
                         font=("Segoe UI", 10, "bold"), relief="flat")
        style.map("Treeview",                 background=[("selected", ACCENT2)])

        style.configure("Vertical.TScrollbar", background=BG_MID, troughcolor=BG_DARK,
                         arrowcolor=TEXT_DIM, borderwidth=0)

        style.configure("TCombobox", fieldbackground=BG_CARD, background=BG_CARD,
                         foreground=TEXT_MAIN, selectbackground=ACCENT,
                         font=("Segoe UI", 10))
        style.map("TCombobox", fieldbackground=[("readonly", BG_CARD)])

    def _sidebar(self):
        sb = tk.Frame(self, bg=BG_MID, width=210)
        sb.pack(side="left", fill="y")
        sb.pack_propagate(False)

        # Logo
        tk.Label(sb, text="📚", font=("Segoe UI Emoji", 32), bg=BG_MID,
                 fg=ACCENT).pack(pady=(24, 4))
        tk.Label(sb, text="Study Planner", font=("Segoe UI", 14, "bold"),
                 bg=BG_MID, fg=TEXT_MAIN).pack()
        tk.Label(sb, text=date.today().strftime("%A, %d %b %Y"),
                 font=("Segoe UI", 9), bg=BG_MID, fg=TEXT_DIM).pack(pady=(2, 20))

        _divider(sb)

        # Quick stats
        self.stat_total    = _stat_label(sb, "Total Tasks",     "0")
        self.stat_done     = _stat_label(sb, "Completed",       "0")
        self.stat_today    = _stat_label(sb, "Due Today",       "0")
        self.stat_overdue  = _stat_label(sb, "Overdue",         "0", color=ACCENT)

        _divider(sb)

        # Progress ring (canvas)
        tk.Label(sb, text="Progress", font=("Segoe UI", 10, "bold"),
                 bg=BG_MID, fg=TEXT_DIM).pack(pady=(8, 4))
        self.progress_canvas = tk.Canvas(sb, width=110, height=110,
                                         bg=BG_MID, highlightthickness=0)
        self.progress_canvas.pack()
        self.progress_label = tk.Label(sb, text="0%", font=("Segoe UI", 14, "bold"),
                                       bg=BG_MID, fg=SUCCESS)
        self.progress_label.pack(pady=(2, 16))

        _divider(sb)

        # Subjects quick filter
        tk.Label(sb, text="Subjects", font=("Segoe UI", 10, "bold"),
                 bg=BG_MID, fg=TEXT_DIM).pack(pady=(10, 6))
        self.subject_frame = tk.Frame(sb, bg=BG_MID)
        self.subject_frame.pack(fill="x", padx=12)

        _divider(sb)

        # Bottom buttons
        btn_frame = tk.Frame(sb, bg=BG_MID)
        btn_frame.pack(side="bottom", fill="x", padx=12, pady=16)
        _btn(btn_frame, "⚙  Manage Subjects", self._manage_subjects,
             bg=BG_CARD, fg=TEXT_DIM).pack(fill="x", pady=3)
        _btn(btn_frame, "🗑  Clear Completed", self._clear_completed,
             bg=BG_CARD, fg=TEXT_DIM).pack(fill="x", pady=3)

    def _main_area(self):
        main = tk.Frame(self, bg=BG_DARK)
        main.pack(side="left", fill="both", expand=True)

        nb = ttk.Notebook(main)
        nb.pack(fill="both", expand=True, padx=10, pady=10)

        # Tab 1 – Task List
        tab_tasks = tk.Frame(nb, bg=BG_DARK)
        nb.add(tab_tasks, text="  📋 Tasks  ")
        self._build_tasks_tab(tab_tasks)

        # Tab 2 – Add / Edit
        tab_add = tk.Frame(nb, bg=BG_DARK)
        nb.add(tab_add, text="  ➕ Add Task  ")
        self._build_add_tab(tab_add)

        # Tab 3 – Pomodoro
        tab_pomo = tk.Frame(nb, bg=BG_DARK)
        nb.add(tab_pomo, text="  🍅 Pomodoro  ")
        self._build_pomodoro_tab(tab_pomo)

    # ── Tasks Tab ─────────────────────────────────────────────────────────────

    def _build_tasks_tab(self, parent):
        # Toolbar
        toolbar = tk.Frame(parent, bg=BG_DARK)
        toolbar.pack(fill="x", padx=8, pady=(8, 4))

        # Search
        tk.Label(toolbar, text="🔍", font=("Segoe UI Emoji", 12),
                 bg=BG_DARK, fg=TEXT_DIM).pack(side="left")
        search_entry = tk.Entry(toolbar, textvariable=self.search_var,
                                bg=BG_CARD, fg=TEXT_MAIN, insertbackground=TEXT_MAIN,
                                relief="flat", font=("Segoe UI", 11), width=20)
        search_entry.pack(side="left", padx=(4, 16), ipady=5)

        # Filters
        for label, var, opts in [
            ("Subject:", self.filter_subject,
             ["All"] + [s["name"] for s in self.data.get("subjects", [])]),
            ("Priority:", self.filter_priority,
             ["All", "High", "Medium", "Low"]),
            ("Status:",   self.filter_status,
             ["All", "Pending", "Done"]),
        ]:
            tk.Label(toolbar, text=label, bg=BG_DARK, fg=TEXT_DIM,
                     font=("Segoe UI", 9)).pack(side="left", padx=(4, 2))
            cb = ttk.Combobox(toolbar, textvariable=var, values=opts,
                               state="readonly", width=10,
                               font=("Segoe UI", 10))
            cb.pack(side="left", padx=(0, 6))
            var.trace_add("write", lambda *_: self.refresh_list())

        _btn(toolbar, "⟳ Refresh", self.refresh_list,
             bg=ACCENT2, fg="white").pack(side="right", padx=4)

        # Treeview
        cols = ("subject", "topic", "due_date", "priority", "status")
        self.tree = ttk.Treeview(parent, columns=cols, show="headings",
                                  selectmode="browse")
        self.tree.heading("subject",  text="Subject")
        self.tree.heading("topic",    text="Topic / Task")
        self.tree.heading("due_date", text="Due Date")
        self.tree.heading("priority", text="Priority")
        self.tree.heading("status",   text="Status")

        self.tree.column("subject",  width=130, anchor="center")
        self.tree.column("topic",    width=260)
        self.tree.column("due_date", width=110, anchor="center")
        self.tree.column("priority", width=90,  anchor="center")
        self.tree.column("status",   width=90,  anchor="center")

        vsb = ttk.Scrollbar(parent, orient="vertical",   command=self.tree.yview)
        self.tree.configure(yscroll=vsb.set)

        self.tree.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=4)
        vsb.pack(side="left", fill="y", pady=4)

        # Row colours
        self.tree.tag_configure("done",   foreground="#555")
        self.tree.tag_configure("high",   foreground=PRIORITY_COLORS["High"])
        self.tree.tag_configure("medium", foreground=PRIORITY_COLORS["Medium"])
        self.tree.tag_configure("low",    foreground=PRIORITY_COLORS["Low"])
        self.tree.tag_configure("overdue",foreground=ACCENT)

        # Action buttons
        act = tk.Frame(parent, bg=BG_DARK)
        act.pack(fill="x", padx=8, pady=6)
        _btn(act, "✅ Mark Done / Undo", self._toggle_done,
             bg=SUCCESS, fg="white").pack(side="left", padx=4)
        _btn(act, "✏  Edit",            self._edit_task,
             bg=WARNING, fg="white").pack(side="left", padx=4)
        _btn(act, "🗑  Delete",          self._delete_task,
             bg=ACCENT,  fg="white").pack(side="left", padx=4)
        _btn(act, "📄 View Notes",       self._view_notes,
             bg=ACCENT2, fg="white").pack(side="left", padx=4)

        self.tree.bind("<Double-1>", lambda e: self._toggle_done())

    # ── Add / Edit Tab ────────────────────────────────────────────────────────

    def _build_add_tab(self, parent):
        self._editing_id = None  # None = add mode

        card = tk.Frame(parent, bg=BG_CARD, bd=0)
        card.pack(padx=40, pady=30, fill="both", expand=True)

        tk.Label(card, text="New Study Task", font=("Segoe UI", 16, "bold"),
                 bg=BG_CARD, fg=ACCENT).pack(pady=(20, 16))

        form = tk.Frame(card, bg=BG_CARD)
        form.pack(padx=40, fill="x")

        # Subject
        self.f_subject = _form_row(form, "Subject", 0)
        self.f_subject["state"] = "readonly"
        subjects = [s["name"] for s in self.data.get("subjects", [])]
        self.f_subject["values"] = subjects if subjects else ["General"]
        if subjects: self.f_subject.current(0)

        # Topic
        self.f_topic = _form_row(form, "Topic / Task", 1, widget="entry")

        # Due Date
        self.f_due = _form_row(form, "Due Date (YYYY-MM-DD)", 2, widget="entry")
        self.f_due.insert(0, date.today().isoformat())

        # Priority
        self.f_priority = _form_row(form, "Priority", 3)
        self.f_priority["values"] = ["High", "Medium", "Low"]
        self.f_priority.current(1)

        # Notes
        tk.Label(form, text="Notes", font=("Segoe UI", 10),
                 bg=BG_CARD, fg=TEXT_DIM, anchor="w").grid(
                     row=4, column=0, sticky="nw", pady=(10, 4))
        self.f_notes = tk.Text(form, height=5, bg=BG_MID, fg=TEXT_MAIN,
                                insertbackground=TEXT_MAIN, relief="flat",
                                font=("Segoe UI", 10), bd=6)
        self.f_notes.grid(row=4, column=1, sticky="ew", pady=(10, 4), padx=(12, 0))
        form.columnconfigure(1, weight=1)

        # Buttons
        btn_row = tk.Frame(card, bg=BG_CARD)
        btn_row.pack(pady=20)
        self.save_btn = _btn(btn_row, "💾 Save Task", self._save_task,
                              bg=SUCCESS, fg="white", padx=24, pady=8)
        self.save_btn.pack(side="left", padx=8)
        _btn(btn_row, "✖ Clear", self._clear_form,
             bg=BG_MID, fg=TEXT_DIM, padx=16, pady=8).pack(side="left", padx=8)

        self._add_tab_form = form  # keep ref for edit-mode label update
        self._add_tab_card = card

    # ── Pomodoro Tab ──────────────────────────────────────────────────────────

    def _build_pomodoro_tab(self, parent):
        frame = tk.Frame(parent, bg=BG_DARK)
        frame.pack(expand=True)

        tk.Label(frame, text="🍅 Pomodoro Timer", font=("Segoe UI", 18, "bold"),
                 bg=BG_DARK, fg=ACCENT).pack(pady=(30, 6))

        # Mode selector
        mode_frame = tk.Frame(frame, bg=BG_DARK)
        mode_frame.pack(pady=8)
        self.pomo_mode_btns = {}
        for label, mode in [("Work (25m)", "Work"),
                             ("Short Break (5m)", "Short Break"),
                             ("Long Break (15m)",  "Long Break")]:
            b = _btn(mode_frame, label, lambda m=mode: self._set_pomo_mode(m),
                     bg=BG_CARD, fg=TEXT_DIM, padx=10, pady=5)
            b.pack(side="left", padx=6)
            self.pomo_mode_btns[mode] = b
        self._highlight_pomo_mode()

        # Big timer canvas
        self.pomo_canvas = tk.Canvas(frame, width=240, height=240,
                                      bg=BG_DARK, highlightthickness=0)
        self.pomo_canvas.pack(pady=16)
        self._draw_pomo_ring(1.0)

        self.pomo_time_var = tk.StringVar(value="25:00")
        tk.Label(frame, textvariable=self.pomo_time_var,
                 font=("Segoe UI", 42, "bold"), bg=BG_DARK, fg=TEXT_MAIN).pack()
        self.pomo_mode_lbl = tk.Label(frame, text="Work Session",
                                       font=("Segoe UI", 12), bg=BG_DARK, fg=TEXT_DIM)
        self.pomo_mode_lbl.pack(pady=4)

        # Controls
        ctrl = tk.Frame(frame, bg=BG_DARK)
        ctrl.pack(pady=12)
        self.pomo_start_btn = _btn(ctrl, "▶  Start", self._pomo_start,
                                    bg=SUCCESS, fg="white", padx=22, pady=8)
        self.pomo_start_btn.pack(side="left", padx=6)
        _btn(ctrl, "⏸  Pause", self._pomo_pause,
             bg=WARNING, fg="white", padx=16, pady=8).pack(side="left", padx=6)
        _btn(ctrl, "⏹  Reset", self._pomo_reset,
             bg=ACCENT,  fg="white", padx=16, pady=8).pack(side="left", padx=6)

        # Session counter
        self.pomo_count_var = tk.StringVar(
            value=f"Sessions completed: {self.pomo_sessions}")
        tk.Label(frame, textvariable=self.pomo_count_var,
                 font=("Segoe UI", 11), bg=BG_DARK, fg=TEXT_DIM).pack(pady=6)

    # ── Logic: Tasks ──────────────────────────────────────────────────────────

    def refresh_list(self, *_):
        self.tree.delete(*self.tree.get_children())
        today_str = date.today().isoformat()
        search = self.search_var.get().lower()
        subj_f = self.filter_subject.get()
        prio_f = self.filter_priority.get()
        stat_f = self.filter_status.get()

        # Sort: undone first, then by due date
        tasks = sorted(
            self.data["tasks"],
            key=lambda t: (t["done"], t["due_date"])
        )

        for t in tasks:
            if subj_f != "All" and t["subject"] != subj_f: continue
            if prio_f != "All" and t["priority"] != prio_f: continue
            if stat_f == "Pending" and t["done"]: continue
            if stat_f == "Done"    and not t["done"]: continue
            if search and search not in t["topic"].lower() \
                       and search not in t["subject"].lower(): continue

            status   = "✅ Done" if t["done"] else "⏳ Pending"
            is_over  = not t["done"] and t["due_date"] < today_str
            tags     = []

            if t["done"]:
                tags.append("done")
            elif is_over:
                tags.append("overdue")
            else:
                tags.append(t["priority"].lower())

            self.tree.insert("", "end", iid=t["id"],
                             values=(t["subject"], t["topic"],
                                     t["due_date"], t["priority"], status),
                             tags=tags)

        self._update_dashboard()
        self._refresh_subject_sidebar()
        self._refresh_subject_filter()

    def _update_dashboard(self):
        tasks     = self.data["tasks"]
        total     = len(tasks)
        done      = sum(1 for t in tasks if t["done"])
        today_str = date.today().isoformat()
        due_today = sum(1 for t in tasks if t["due_date"] == today_str and not t["done"])
        overdue   = sum(1 for t in tasks if t["due_date"] < today_str and not t["done"])
        pct       = int(done / total * 100) if total else 0

        self.stat_total.config(text=str(total))
        self.stat_done.config(text=str(done))
        self.stat_today.config(text=str(due_today))
        self.stat_overdue.config(text=str(overdue))
        self.progress_label.config(text=f"{pct}%")

        # Draw arc
        c = self.progress_canvas
        c.delete("all")
        cx, cy, r = 55, 55, 45
        # Background ring
        c.create_oval(cx-r, cy-r, cx+r, cy+r, outline=BG_DARK, width=10)
        if pct > 0:
            import math
            extent = pct / 100 * 360
            c.create_arc(cx-r, cy-r, cx+r, cy+r,
                         start=90, extent=-extent,
                         outline=SUCCESS, width=10, style="arc")

    def _refresh_subject_sidebar(self):
        for w in self.subject_frame.winfo_children():
            w.destroy()
        _btn(self.subject_frame, "All",
             lambda: self._set_subject_filter("All"),
             bg=BG_DARK if self.filter_subject.get() != "All" else ACCENT,
             fg="white").pack(fill="x", pady=2)
        for s in self.data.get("subjects", []):
            name = s["name"]
            clr  = s.get("color", ACCENT)
            bg   = clr if self.filter_subject.get() == name else BG_DARK
            _btn(self.subject_frame, name,
                 lambda n=name: self._set_subject_filter(n),
                 bg=bg, fg="white").pack(fill="x", pady=2)

    def _refresh_subject_filter(self):
        subjects = [s["name"] for s in self.data.get("subjects", [])]
        current  = self.filter_subject.get()
        opts     = ["All"] + subjects
        # find the combobox in toolbar (hacky but works)
        for w in self.tree.master.winfo_children():
            pass  # not needed; filters bind via trace

    def _set_subject_filter(self, name):
        self.filter_subject.set(name)
        self.refresh_list()

    def _toggle_done(self):
        sel = self.tree.selection()
        if not sel: return
        tid = sel[0]
        for t in self.data["tasks"]:
            if t["id"] == tid:
                t["done"] = not t["done"]
                break
        save_data(self.data)
        self.refresh_list()

    def _delete_task(self):
        sel = self.tree.selection()
        if not sel: return
        if not messagebox.askyesno("Delete", "Delete this task?", icon="warning"):
            return
        tid = sel[0]
        self.data["tasks"] = [t for t in self.data["tasks"] if t["id"] != tid]
        save_data(self.data)
        self.refresh_list()

    def _view_notes(self):
        sel = self.tree.selection()
        if not sel: return
        tid = sel[0]
        for t in self.data["tasks"]:
            if t["id"] == tid:
                win = tk.Toplevel(self)
                win.title(f"Notes — {t['topic']}")
                win.configure(bg=BG_DARK)
                win.geometry("420x280")
                tk.Label(win, text=t["topic"], font=("Segoe UI", 13, "bold"),
                         bg=BG_DARK, fg=ACCENT).pack(pady=(16, 4))
                txt = tk.Text(win, bg=BG_CARD, fg=TEXT_MAIN, relief="flat",
                              font=("Segoe UI", 11), wrap="word", bd=8)
                txt.pack(fill="both", expand=True, padx=20, pady=10)
                txt.insert("1.0", t.get("notes", "(No notes)"))
                txt.config(state="disabled")
                return

    def _edit_task(self):
        sel = self.tree.selection()
        if not sel: return
        tid = sel[0]
        for t in self.data["tasks"]:
            if t["id"] == tid:
                self._editing_id = tid
                # Switch to Add tab
                self._add_tab_card.winfo_toplevel().nametowidget(
                    self._add_tab_card.winfo_parent()
                )
                # Populate fields
                self.f_subject.set(t["subject"])
                self.f_topic.delete(0, "end")
                self.f_topic.insert(0, t["topic"])
                self.f_due.delete(0, "end")
                self.f_due.insert(0, t["due_date"])
                self.f_priority.set(t["priority"])
                self.f_notes.delete("1.0", "end")
                self.f_notes.insert("1.0", t.get("notes", ""))
                self.save_btn.config(text="💾 Update Task")
                # Switch notebook to add tab
                nb = self._find_notebook()
                if nb: nb.select(1)
                return

    def _save_task(self):
        subject  = self.f_subject.get().strip()
        topic    = self.f_topic.get().strip()
        due_date = self.f_due.get().strip()
        priority = self.f_priority.get().strip()
        notes    = self.f_notes.get("1.0", "end").strip()

        if not subject or not topic:
            messagebox.showwarning("Validation", "Subject and Topic are required.")
            return
        try:
            datetime.strptime(due_date, "%Y-%m-%d")
        except ValueError:
            messagebox.showwarning("Validation", "Date must be YYYY-MM-DD format.")
            return

        if self._editing_id:
            for t in self.data["tasks"]:
                if t["id"] == self._editing_id:
                    t["subject"]  = subject
                    t["topic"]    = topic
                    t["due_date"] = due_date
                    t["priority"] = priority
                    t["notes"]    = notes
                    break
            self._editing_id = None
            self.save_btn.config(text="💾 Save Task")
            messagebox.showinfo("Updated", "Task updated successfully!")
        else:
            self.data["tasks"].append(
                new_task(subject, topic, due_date, priority, notes))
            messagebox.showinfo("Saved", "Task added successfully!")

        # Ensure subject exists
        existing = [s["name"] for s in self.data.get("subjects", [])]
        if subject not in existing:
            colour = SUBJECT_PALETTE[len(existing) % len(SUBJECT_PALETTE)]
            self.data.setdefault("subjects", []).append(
                {"name": subject, "color": colour})

        save_data(self.data)
        self._clear_form()
        self.refresh_list()

    def _clear_form(self):
        self._editing_id = None
        self.save_btn.config(text="💾 Save Task")
        self.f_topic.delete(0, "end")
        self.f_due.delete(0, "end")
        self.f_due.insert(0, date.today().isoformat())
        self.f_priority.current(1)
        self.f_notes.delete("1.0", "end")

    def _clear_completed(self):
        n = sum(1 for t in self.data["tasks"] if t["done"])
        if not n:
            messagebox.showinfo("Nothing to clear", "No completed tasks found.")
            return
        if messagebox.askyesno("Clear Completed",
                                f"Remove {n} completed task(s)?", icon="warning"):
            self.data["tasks"] = [t for t in self.data["tasks"] if not t["done"]]
            save_data(self.data)
            self.refresh_list()

    # ── Logic: Subjects ───────────────────────────────────────────────────────

    def _manage_subjects(self):
        win = tk.Toplevel(self)
        win.title("Manage Subjects")
        win.configure(bg=BG_DARK)
        win.geometry("380x420")
        win.grab_set()

        tk.Label(win, text="Subjects", font=("Segoe UI", 14, "bold"),
                 bg=BG_DARK, fg=ACCENT).pack(pady=(16, 8))

        lb_frame = tk.Frame(win, bg=BG_DARK)
        lb_frame.pack(fill="both", expand=True, padx=20)
        lb = tk.Listbox(lb_frame, bg=BG_CARD, fg=TEXT_MAIN,
                         selectbackground=ACCENT2, relief="flat",
                         font=("Segoe UI", 11), bd=6)
        lb.pack(fill="both", expand=True)
        for s in self.data.get("subjects", []):
            lb.insert("end", s["name"])

        entry_var = tk.StringVar()
        tk.Entry(win, textvariable=entry_var, bg=BG_CARD, fg=TEXT_MAIN,
                 insertbackground=TEXT_MAIN, relief="flat",
                 font=("Segoe UI", 11)).pack(fill="x", padx=20, ipady=6, pady=8)

        def add_sub():
            name = entry_var.get().strip()
            if not name: return
            existing = [s["name"] for s in self.data.get("subjects", [])]
            if name in existing:
                messagebox.showwarning("Duplicate", "Subject already exists.", parent=win)
                return
            colour = SUBJECT_PALETTE[len(existing) % len(SUBJECT_PALETTE)]
            self.data.setdefault("subjects", []).append({"name": name, "color": colour})
            save_data(self.data)
            lb.insert("end", name)
            entry_var.set("")
            self.refresh_list()

        def del_sub():
            sel = lb.curselection()
            if not sel: return
            name = lb.get(sel[0])
            in_use = any(t["subject"] == name for t in self.data["tasks"])
            if in_use:
                messagebox.showwarning("In Use",
                    f"'{name}' is used by existing tasks.\nDelete those tasks first.",
                    parent=win)
                return
            self.data["subjects"] = [
                s for s in self.data["subjects"] if s["name"] != name]
            save_data(self.data)
            lb.delete(sel[0])
            self.refresh_list()

        btn_row = tk.Frame(win, bg=BG_DARK)
        btn_row.pack(pady=8)
        _btn(btn_row, "Add",    add_sub, bg=SUCCESS, fg="white", padx=14).pack(side="left", padx=6)
        _btn(btn_row, "Delete", del_sub, bg=ACCENT,  fg="white", padx=14).pack(side="left", padx=6)

    # ── Logic: Pomodoro ───────────────────────────────────────────────────────

    def _set_pomo_mode(self, mode):
        if self.pomo_running: return
        self.pomo_mode = mode
        durations = {"Work": POMODORO_WORK,
                     "Short Break": POMODORO_SHORT,
                     "Long Break":  POMODORO_LONG}
        self.pomo_time_left = durations[mode]
        self._update_pomo_display()
        self._highlight_pomo_mode()

    def _highlight_pomo_mode(self):
        for mode, btn in self.pomo_mode_btns.items():
            btn.config(bg=ACCENT if mode == self.pomo_mode else BG_CARD,
                       fg="white" if mode == self.pomo_mode else TEXT_DIM)

    def _pomo_start(self):
        if self.pomo_paused:
            self.pomo_paused  = False
            self.pomo_running = True
        elif not self.pomo_running:
            self.pomo_running = True
            self.pomo_paused  = False
        self.pomo_start_btn.config(text="▶  Running…", state="disabled")
        self._pomo_tick()

    def _pomo_pause(self):
        if self.pomo_running:
            self.pomo_running = False
            self.pomo_paused  = True
            if self._pomo_job:
                self.after_cancel(self._pomo_job)
            self.pomo_start_btn.config(text="▶  Resume", state="normal")

    def _pomo_reset(self):
        self.pomo_running = False
        self.pomo_paused  = False
        if self._pomo_job:
            self.after_cancel(self._pomo_job)
        durations = {"Work": POMODORO_WORK,
                     "Short Break": POMODORO_SHORT,
                     "Long Break":  POMODORO_LONG}
        self.pomo_time_left = durations[self.pomo_mode]
        self.pomo_start_btn.config(text="▶  Start", state="normal")
        self._update_pomo_display()

    def _pomo_tick(self):
        if not self.pomo_running: return
        if self.pomo_time_left <= 0:
            self.pomo_running = False
            self.pomo_start_btn.config(text="▶  Start", state="normal")
            if self.pomo_mode == "Work":
                self.pomo_sessions += 1
                self.data["pomodoro_count"] = self.pomo_sessions
                save_data(self.data)
                self.pomo_count_var.set(f"Sessions completed: {self.pomo_sessions}")
                messagebox.showinfo("🍅 Pomodoro Done!",
                    f"Great work! Session {self.pomo_sessions} complete.\n"
                    "Time for a break!")
            else:
                messagebox.showinfo("Break Over", "Break finished! Ready to work?")
            self._pomo_reset()
            return

        self.pomo_time_left -= 1
        self._update_pomo_display()
        total_secs = {"Work": POMODORO_WORK,
                      "Short Break": POMODORO_SHORT,
                      "Long Break":  POMODORO_LONG}[self.pomo_mode]
        frac = self.pomo_time_left / total_secs
        self._draw_pomo_ring(frac)
        self._pomo_job = self.after(1000, self._pomo_tick)

    def _update_pomo_display(self):
        m, s = divmod(self.pomo_time_left, 60)
        self.pomo_time_var.set(f"{m:02d}:{s:02d}")
        labels = {"Work": "Focus — Work Session",
                  "Short Break": "Short Break ☕",
                  "Long Break":  "Long Break 🌿"}
        self.pomo_mode_lbl.config(text=labels[self.pomo_mode])

    def _draw_pomo_ring(self, fraction):
        c = self.pomo_canvas
        c.delete("all")
        cx, cy, r = 120, 120, 95
        # bg
        c.create_oval(cx-r, cy-r, cx+r, cy+r, outline="#2a2a4a", width=14)
        if fraction > 0:
            extent = fraction * 360
            color  = SUCCESS if self.pomo_mode == "Work" else WARNING
            c.create_arc(cx-r, cy-r, cx+r, cy+r,
                         start=90, extent=-extent,
                         outline=color, width=14, style="arc")

    # ── Utilities ─────────────────────────────────────────────────────────────

    def _find_notebook(self):
        def _recurse(w):
            if isinstance(w, ttk.Notebook): return w
            for c in w.winfo_children():
                r = _recurse(c)
                if r: return r
        return _recurse(self)


# ─── Widget Helpers ────────────────────────────────────────────────────────────

def _btn(parent, text, command, bg=BG_CARD, fg=TEXT_MAIN,
         padx=10, pady=4, **kw) -> tk.Button:
    b = tk.Button(parent, text=text, command=command,
                  bg=bg, fg=fg, activebackground=_lighten(bg),
                  activeforeground=fg, relief="flat",
                  font=("Segoe UI", 10), cursor="hand2",
                  padx=padx, pady=pady, bd=0, **kw)
    return b


def _form_row(parent, label, row, widget="combobox") -> tk.Widget:
    tk.Label(parent, text=label, font=("Segoe UI", 10),
             bg=BG_CARD, fg=TEXT_DIM, anchor="w").grid(
                 row=row, column=0, sticky="w", pady=8)
    if widget == "entry":
        w = tk.Entry(parent, bg=BG_MID, fg=TEXT_MAIN,
                     insertbackground=TEXT_MAIN, relief="flat",
                     font=("Segoe UI", 11), bd=6)
    else:
        w = ttk.Combobox(parent, state="readonly", font=("Segoe UI", 11))
    w.grid(row=row, column=1, sticky="ew", padx=(12, 0), pady=8)
    return w


def _stat_label(parent, label, value, color=SUCCESS):
    frame = tk.Frame(parent, bg=BG_MID)
    frame.pack(fill="x", padx=16, pady=3)
    tk.Label(frame, text=label, font=("Segoe UI", 9),
             bg=BG_MID, fg=TEXT_DIM, anchor="w").pack(side="left")
    val = tk.Label(frame, text=value, font=("Segoe UI", 10, "bold"),
                   bg=BG_MID, fg=color, anchor="e")
    val.pack(side="right")
    return val


def _divider(parent):
    tk.Frame(parent, bg="#2a2a4a", height=1).pack(fill="x", padx=14, pady=6)


def _lighten(hex_color: str) -> str:
    """Return a slightly lighter shade of a hex color."""
    try:
        r = min(255, int(hex_color[1:3], 16) + 25)
        g = min(255, int(hex_color[3:5], 16) + 25)
        b = min(255, int(hex_color[5:7], 16) + 25)
        return f"#{r:02x}{g:02x}{b:02x}"
    except Exception:
        return hex_color


# ─── Entry Point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = StudyPlanner()

    # Seed demo data on first run
    if not app.data["tasks"]:
        demo_subjects = [
            {"name": "Mathematics", "color": "#3498db"},
            {"name": "Physics",     "color": "#9b59b6"},
            {"name": "History",     "color": "#e67e22"},
            {"name": "Literature",  "color": "#1abc9c"},
        ]
        app.data["subjects"] = demo_subjects
        today = date.today().isoformat()
        demo_tasks = [
            new_task("Mathematics", "Calculus – Integration by Parts",
                     today, "High", "Focus on u-substitution first."),
            new_task("Physics",     "Waves & Optics Chapter Review",
                     "2025-04-01", "Medium", "Read textbook pages 120–145."),
            new_task("History",     "Essay: Industrial Revolution Causes",
                     "2025-04-05", "High",   "Use at least 3 primary sources."),
            new_task("Literature",  "Annotate Hamlet Act III",
                     "2025-04-10", "Low",    "Note soliloquy themes."),
            new_task("Mathematics", "Practice Paper 1 – Algebra",
                     "2025-03-28", "High",   "Timed practice under exam conditions."),
        ]
        # Mark last one as overdue-demo
        app.data["tasks"] = demo_tasks
        save_data(app.data)
        # Update combobox
        subjects = [s["name"] for s in demo_subjects]
        app.f_subject["values"] = subjects
        app.f_subject.current(0)
        app.refresh_list()

    app.mainloop()
