"""
Student Academic Task & Deadline Manager (version 2, simpler)

Run with:  python student_manager_v2.py

It uses the same database file as version 1 (student_manager.db),
so your old data still shows up.
"""

import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date, datetime, timedelta


DB_FILE = "student_manager.db"

# All the widgets and small pieces of state are kept in this one dictionary.
# This way we don't need lots of global variables.
ui = {"editing_id": None}


# ---------------------------------------------------------------
# DATABASE HELPERS
# ---------------------------------------------------------------

def create_tables():
    # Make the tables if they don't exist yet
    run_query("""CREATE TABLE IF NOT EXISTS assignments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    subject TEXT,
                    description TEXT,
                    due_date TEXT NOT NULL,
                    priority TEXT,
                    completed INTEGER DEFAULT 0)""")
    run_query("""CREATE TABLE IF NOT EXISTS daily_tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    due_date TEXT NOT NULL,
                    completed INTEGER DEFAULT 0)""")
    run_query("""CREATE TABLE IF NOT EXISTS subjects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE)""")
    run_query("""CREATE TABLE IF NOT EXISTS chapters (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    subject_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    completed INTEGER DEFAULT 0)""")


def run_query(sql, params=()):
    # Used for INSERT, UPDATE, DELETE and CREATE
    conn = sqlite3.connect(DB_FILE)
    conn.execute(sql, params)
    conn.commit()
    conn.close()


def get_rows(sql, params=()):
    # Used for SELECT. Returns a list of rows.
    conn = sqlite3.connect(DB_FILE)
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return rows


def get_progress(subject_id=None):
    # Returns (done, total, percent) for one subject, or for everything if no id is given
    sql = "SELECT COUNT(*), SUM(completed) FROM chapters"
    params = ()
    if subject_id is not None:
        sql += " WHERE subject_id = ?"
        params = (subject_id,)
    total, done = get_rows(sql, params)[0]
    done = done or 0
    percent = round(done * 100 / total) if total else 0
    return done, total, percent


# ---------------------------------------------------------------
# DATE HELPERS
# ---------------------------------------------------------------

def today_text():
    return date.today().strftime("%Y-%m-%d")


def parse_date(text):
    # Returns a date object, or None if the text is not YYYY-MM-DD
    try:
        return datetime.strptime(text.strip(), "%Y-%m-%d").date()
    except ValueError:
        return None


def days_left_text(due_text, completed):
    if completed:
        return "-"
    due = parse_date(due_text)
    if due is None:
        return "?"
    days = (due - date.today()).days
    if days < 0:
        return "Overdue by " + str(-days) + " day(s)"
    if days == 0:
        return "Due today"
    return str(days) + " day(s)"


def is_overdue(due_text, completed):
    due = parse_date(due_text)
    return due is not None and not completed and due < date.today()


# ---------------------------------------------------------------
# SMALL GUI HELPERS
# ---------------------------------------------------------------

def make_entry(parent, label, row, col, width=25):
    # A label with a text box next to it. Returns the text box.
    ttk.Label(parent, text=label).grid(row=row, column=col, sticky="w", padx=3, pady=3)
    entry = ttk.Entry(parent, width=width)
    entry.grid(row=row, column=col + 1, padx=3, pady=3)
    return entry


def make_tree(parent, columns):
    # columns is a list of (column_id, heading_text, width) entries
    tree = ttk.Treeview(parent, columns=[c[0] for c in columns], show="headings", height=12)
    for col_id, heading, width in columns:
        tree.heading(col_id, text=heading)
        tree.column(col_id, width=width)
    tree.tag_configure("overdue", background="#ffd6d6")  # red
    tree.tag_configure("done", foreground="gray")        # grey
    return tree


def get_selected_id(tree):
    # The database id is stored as the row's id, so we just read it back
    selected = tree.selection()
    if not selected:
        messagebox.showwarning("Nothing selected", "Please click a row first.")
        return None
    return int(selected[0])


def toggle_done(table, tree):
    # Switch an item between done and not done
    item_id = get_selected_id(tree)
    if item_id is None:
        return
    completed = get_rows("SELECT completed FROM " + table + " WHERE id = ?", (item_id,))[0][0]
    new_value = 0 if completed else 1
    run_query("UPDATE " + table + " SET completed = ? WHERE id = ?", (new_value, item_id))
    refresh_all()


def delete_row(table, tree):
    item_id = get_selected_id(tree)
    if item_id is None:
        return
    if messagebox.askyesno("Delete", "Are you sure you want to delete this?"):
        run_query("DELETE FROM " + table + " WHERE id = ?", (item_id,))
        if table == "assignments" and ui["editing_id"] == item_id:
            clear_assignment_form()
        refresh_all()


# ---------------------------------------------------------------
# ASSIGNMENTS
# ---------------------------------------------------------------

def save_assignment():
    name = ui["a_name"].get().strip()
    subject = ui["a_subject"].get().strip()
    desc = ui["a_desc"].get().strip()
    due_text = ui["a_due"].get().strip()
    priority = ui["a_priority"].get()

    if name == "":
        messagebox.showwarning("Missing info", "Please enter an assignment name.")
        return
    if parse_date(due_text) is None:
        messagebox.showwarning("Wrong date", "Use the format YYYY-MM-DD, for example 2026-11-20.")
        return

    if ui["editing_id"] is None:
        # New assignment
        run_query("""INSERT INTO assignments
                     (name, subject, description, due_date, priority, completed)
                     VALUES (?, ?, ?, ?, ?, 0)""",
                  (name, subject, desc, due_text, priority))
    else:
        # Changing an existing assignment
        run_query("""UPDATE assignments
                     SET name = ?, subject = ?, description = ?, due_date = ?, priority = ?
                     WHERE id = ?""",
                  (name, subject, desc, due_text, priority, ui["editing_id"]))

    clear_assignment_form()
    refresh_all()


def clear_assignment_form():
    ui["editing_id"] = None
    for key in ["a_name", "a_subject", "a_desc", "a_due"]:
        ui[key].delete(0, tk.END)
    ui["a_priority"].set("Medium")


def edit_assignment():
    # Copy the selected assignment into the form
    item_id = get_selected_id(ui["assign_tree"])
    if item_id is None:
        return
    name, subject, desc, due_text, priority = get_rows(
        "SELECT name, subject, description, due_date, priority FROM assignments WHERE id = ?",
        (item_id,))[0]
    clear_assignment_form()
    ui["editing_id"] = item_id
    ui["a_name"].insert(0, name)
    ui["a_subject"].insert(0, subject or "")
    ui["a_desc"].insert(0, desc or "")
    ui["a_due"].insert(0, due_text)
    ui["a_priority"].set(priority or "Medium")


def refresh_assignments():
    tree = ui["assign_tree"]
    tree.delete(*tree.get_children())

    sql = "SELECT id, name, subject, due_date, priority, completed FROM assignments"
    choice = ui["a_filter"].get()
    if choice == "Pending":
        sql += " WHERE completed = 0"
    elif choice == "Completed":
        sql += " WHERE completed = 1"
    sql += " ORDER BY due_date"

    for item_id, name, subject, due_text, priority, completed in get_rows(sql):
        if is_overdue(due_text, completed):
            tag = "overdue"
        elif completed:
            tag = "done"
        else:
            tag = "normal"
        tree.insert("", tk.END, iid=str(item_id),
                    values=(item_id, name, subject or "", due_text,
                            days_left_text(due_text, completed), priority,
                            "Completed" if completed else "Pending"),
                    tags=(tag,))


def build_assignments_tab(parent):
    frame = ttk.Frame(parent, padding=10)
    frame.pack(fill="both", expand=True)

    form = ttk.LabelFrame(frame, text="Add or edit assignment", padding=10)
    form.pack(fill="x")
    ui["a_name"] = make_entry(form, "Name:", 0, 0)
    ui["a_subject"] = make_entry(form, "Subject:", 0, 2, width=20)
    ui["a_desc"] = make_entry(form, "Description:", 1, 0)
    ui["a_due"] = make_entry(form, "Due (YYYY-MM-DD):", 1, 2, width=20)

    ttk.Label(form, text="Priority:").grid(row=2, column=0, sticky="w", padx=3)
    ui["a_priority"] = ttk.Combobox(form, values=["High", "Medium", "Low"],
                                    state="readonly", width=23)
    ui["a_priority"].set("Medium")
    ui["a_priority"].grid(row=2, column=1, padx=3)

    buttons = ttk.Frame(form)
    buttons.grid(row=2, column=2, columnspan=2, sticky="e")
    ttk.Button(buttons, text="Save", command=save_assignment).pack(side="left", padx=3)
    ttk.Button(buttons, text="Clear", command=clear_assignment_form).pack(side="left", padx=3)

    bar = ttk.Frame(frame)
    bar.pack(fill="x", pady=8)
    ttk.Label(bar, text="Show:").pack(side="left")
    ui["a_filter"] = ttk.Combobox(bar, values=["All", "Pending", "Completed"],
                                  state="readonly", width=12)
    ui["a_filter"].set("All")
    ui["a_filter"].pack(side="left", padx=5)
    ui["a_filter"].bind("<<ComboboxSelected>>", lambda event: refresh_all())

    ttk.Button(bar, text="Delete",
               command=lambda: delete_row("assignments", ui["assign_tree"])).pack(side="right", padx=3)
    ttk.Button(bar, text="Mark done / not done",
               command=lambda: toggle_done("assignments", ui["assign_tree"])).pack(side="right", padx=3)
    ttk.Button(bar, text="Edit selected", command=edit_assignment).pack(side="right", padx=3)

    ui["assign_tree"] = make_tree(frame, [
        ("id", "ID", 40), ("name", "Assignment", 200), ("subject", "Subject", 120),
        ("due", "Due date", 90), ("left", "Days left", 150),
        ("priority", "Priority", 80), ("status", "Status", 90)])
    ui["assign_tree"].pack(fill="both", expand=True)


# ---------------------------------------------------------------
# DAILY TASKS
# ---------------------------------------------------------------

def add_task():
    title = ui["t_title"].get().strip()
    due_text = ui["t_due"].get().strip()
    if title == "":
        messagebox.showwarning("Missing info", "Please enter a task name.")
        return
    if parse_date(due_text) is None:
        messagebox.showwarning("Wrong date", "Use the format YYYY-MM-DD, for example 2026-11-20.")
        return
    run_query("INSERT INTO daily_tasks (title, due_date, completed) VALUES (?, ?, 0)",
              (title, due_text))
    ui["t_title"].delete(0, tk.END)
    ui["t_due"].delete(0, tk.END)
    refresh_all()


def refresh_tasks():
    tree = ui["task_tree"]
    tree.delete(*tree.get_children())

    sql = "SELECT id, title, due_date, completed FROM daily_tasks"
    if ui["t_filter"].get() == "Pending":
        sql += " WHERE completed = 0"
    sql += " ORDER BY due_date"

    for item_id, title, due_text, completed in get_rows(sql):
        tree.insert("", tk.END, iid=str(item_id),
                    values=(item_id, title, due_text, "Done" if completed else "Pending"),
                    tags=("done" if completed else "normal",))


def build_tasks_tab(parent):
    frame = ttk.Frame(parent, padding=10)
    frame.pack(fill="both", expand=True)

    form = ttk.LabelFrame(frame, text="Add daily task", padding=10)
    form.pack(fill="x")
    ui["t_title"] = make_entry(form, "Task:", 0, 0, width=35)
    ui["t_due"] = make_entry(form, "Due (YYYY-MM-DD):", 0, 2, width=15)
    ttk.Button(form, text="Add task", command=add_task).grid(row=0, column=4, padx=5)

    bar = ttk.Frame(frame)
    bar.pack(fill="x", pady=8)
    ttk.Label(bar, text="Show:").pack(side="left")
    ui["t_filter"] = ttk.Combobox(bar, values=["All", "Pending"], state="readonly", width=12)
    ui["t_filter"].set("Pending")
    ui["t_filter"].pack(side="left", padx=5)
    ui["t_filter"].bind("<<ComboboxSelected>>", lambda event: refresh_all())

    ttk.Button(bar, text="Delete",
               command=lambda: delete_row("daily_tasks", ui["task_tree"])).pack(side="right", padx=3)
    ttk.Button(bar, text="Mark done / not done",
               command=lambda: toggle_done("daily_tasks", ui["task_tree"])).pack(side="right", padx=3)

    ui["task_tree"] = make_tree(frame, [
        ("id", "ID", 50), ("task", "Task", 350), ("due", "Due date", 120), ("status", "Status", 100)])
    ui["task_tree"].pack(fill="both", expand=True)


# ---------------------------------------------------------------
# SYLLABUS
# ---------------------------------------------------------------

def add_subject():
    name = ui["s_name"].get().strip()
    if name == "":
        messagebox.showwarning("Missing info", "Please enter a subject name.")
        return
    try:
        run_query("INSERT INTO subjects (name) VALUES (?)", (name,))
    except sqlite3.IntegrityError:
        messagebox.showwarning("Duplicate", "That subject already exists.")
        return
    ui["s_name"].delete(0, tk.END)
    refresh_all()


def get_chosen_subject_id():
    rows = get_rows("SELECT id FROM subjects WHERE name = ?", (ui["subject_box"].get(),))
    return rows[0][0] if rows else None


def add_chapter():
    subject_id = get_chosen_subject_id()
    name = ui["c_name"].get().strip()
    if subject_id is None:
        messagebox.showwarning("No subject", "Please add and choose a subject first.")
        return
    if name == "":
        messagebox.showwarning("Missing info", "Please enter a chapter name.")
        return
    run_query("INSERT INTO chapters (subject_id, name, completed) VALUES (?, ?, 0)",
              (subject_id, name))
    ui["c_name"].delete(0, tk.END)
    refresh_all()


def refresh_syllabus():
    # Subject dropdown
    names = [row[0] for row in get_rows("SELECT name FROM subjects ORDER BY name")]
    ui["subject_box"]["values"] = names
    if ui["subject_box"].get() not in names:
        ui["subject_box"].set(names[0] if names else "")

    # Progress table for every subject
    summary = ui["subject_tree"]
    summary.delete(*summary.get_children())
    for subject_id, name in get_rows("SELECT id, name FROM subjects ORDER BY name"):
        done, total, percent = get_progress(subject_id)
        summary.insert("", tk.END, values=(name, done, total, str(percent) + "%"))

    # Chapters for the chosen subject
    chapters = ui["chapter_tree"]
    chapters.delete(*chapters.get_children())
    subject_id = get_chosen_subject_id()
    if subject_id is None:
        ui["progress_label"].config(text="Add a subject to start.")
    else:
        rows = get_rows("SELECT id, name, completed FROM chapters WHERE subject_id = ? ORDER BY id",
                        (subject_id,))
        for chapter_id, name, completed in rows:
            chapters.insert("", tk.END, iid=str(chapter_id),
                            values=(chapter_id, name, "Done" if completed else "Not done"),
                            tags=("done" if completed else "normal",))
        done, total, percent = get_progress(subject_id)
        ui["progress_label"].config(
            text=ui["subject_box"].get() + ": " + str(done) + "/" + str(total) +
                 " chapters (" + str(percent) + "%)")

    done, total, percent = get_progress()
    ui["overall_label"].config(
        text="Overall syllabus progress: " + str(percent) + "% (" + str(done) + "/" +
             str(total) + " chapters)")


def build_syllabus_tab(parent):
    frame = ttk.Frame(parent, padding=10)
    frame.pack(fill="both", expand=True)

    top = ttk.LabelFrame(frame, text="Subjects and chapters", padding=10)
    top.pack(fill="x")

    ui["s_name"] = make_entry(top, "New subject:", 0, 0)
    ttk.Button(top, text="Add subject", command=add_subject).grid(row=0, column=2, padx=5)

    ttk.Label(top, text="Choose subject:").grid(row=1, column=0, sticky="w", padx=3)
    ui["subject_box"] = ttk.Combobox(top, state="readonly", width=23)
    ui["subject_box"].grid(row=1, column=1, padx=3, pady=3)
    ui["subject_box"].bind("<<ComboboxSelected>>", lambda event: refresh_all())

    ui["c_name"] = make_entry(top, "New chapter:", 2, 0)
    ttk.Button(top, text="Add chapter", command=add_chapter).grid(row=2, column=2, padx=5)

    middle = ttk.Frame(frame)
    middle.pack(fill="both", expand=True, pady=10)

    left = ttk.LabelFrame(middle, text="Chapters for chosen subject", padding=10)
    left.pack(side="left", fill="both", expand=True)
    ui["chapter_tree"] = make_tree(left, [("id", "ID", 40), ("chapter", "Chapter", 220),
                                          ("status", "Status", 90)])
    ui["chapter_tree"].pack(fill="both", expand=True)
    ttk.Button(left, text="Mark done / not done",
               command=lambda: toggle_done("chapters", ui["chapter_tree"])).pack(pady=5)
    ui["progress_label"] = ttk.Label(left, text="")
    ui["progress_label"].pack()

    right = ttk.LabelFrame(middle, text="Progress by subject", padding=10)
    right.pack(side="left", fill="both", expand=True, padx=(10, 0))
    ui["subject_tree"] = make_tree(right, [("subject", "Subject", 160), ("done", "Done", 60),
                                           ("total", "Total", 60), ("percent", "Progress", 90)])
    ui["subject_tree"].pack(fill="both", expand=True)

    ui["overall_label"] = ttk.Label(frame, text="", font=("Arial", 11, "bold"))
    ui["overall_label"].pack(anchor="w")


# ---------------------------------------------------------------
# DASHBOARD
# ---------------------------------------------------------------

def refresh_dashboard():
    today = today_text()
    total = get_rows("SELECT COUNT(*) FROM assignments")[0][0]
    completed = get_rows("SELECT COUNT(*) FROM assignments WHERE completed = 1")[0][0]
    overdue = get_rows("SELECT COUNT(*) FROM assignments WHERE completed = 0 AND due_date < ?",
                       (today,))[0][0]
    _, _, syllabus_percent = get_progress()

    stats = ui["stats"]
    stats["total"].config(text=str(total))
    stats["completed"].config(text=str(completed))
    stats["pending"].config(text=str(total - completed))
    stats["overdue"].config(text=str(overdue))
    stats["syllabus"].config(text=str(syllabus_percent) + "%")

    # Deadlines in the next 7 days
    upcoming = ui["upcoming_list"]
    upcoming.delete(0, tk.END)
    week_end = (date.today() + timedelta(days=7)).strftime("%Y-%m-%d")
    rows = get_rows("""SELECT name, subject, due_date FROM assignments
                       WHERE completed = 0 AND due_date >= ? AND due_date <= ?
                       ORDER BY due_date""", (today, week_end))
    if not rows:
        upcoming.insert(tk.END, "No deadlines in the next 7 days.")
    for name, subject, due_text in rows:
        upcoming.insert(tk.END, due_text + "  " + name + " (" + (subject or "no subject") +
                        ") - " + days_left_text(due_text, 0))

    # Today's pending tasks
    todays = ui["today_list"]
    todays.delete(0, tk.END)
    rows = get_rows("SELECT title FROM daily_tasks WHERE completed = 0 AND due_date = ?", (today,))
    if not rows:
        todays.insert(tk.END, "No tasks for today.")
    for (title,) in rows:
        todays.insert(tk.END, "[ ] " + title)


def build_dashboard_tab(parent):
    frame = ttk.Frame(parent, padding=15)
    frame.pack(fill="both", expand=True)
    ttk.Label(frame, text="Dashboard", font=("Arial", 16, "bold")).pack(anchor="w")

    stats_row = ttk.Frame(frame)
    stats_row.pack(fill="x", pady=10)
    ui["stats"] = {}
    for col, (key, title) in enumerate([("total", "Total assignments"),
                                        ("completed", "Completed"),
                                        ("pending", "Pending"),
                                        ("overdue", "Overdue"),
                                        ("syllabus", "Syllabus progress")]):
        box = ttk.LabelFrame(stats_row, text=title, padding=10)
        box.grid(row=0, column=col, padx=5, sticky="nsew")
        label = ttk.Label(box, text="0", font=("Arial", 14, "bold"))
        label.pack()
        ui["stats"][key] = label
        stats_row.columnconfigure(col, weight=1)

    lists_row = ttk.Frame(frame)
    lists_row.pack(fill="both", expand=True)

    up_box = ttk.LabelFrame(lists_row, text="Upcoming deadlines (next 7 days)", padding=10)
    up_box.pack(side="left", fill="both", expand=True, padx=5)
    ui["upcoming_list"] = tk.Listbox(up_box, height=10)
    ui["upcoming_list"].pack(fill="both", expand=True)

    today_box = ttk.LabelFrame(lists_row, text="Today's tasks", padding=10)
    today_box.pack(side="left", fill="both", expand=True, padx=5)
    ui["today_list"] = tk.Listbox(today_box, height=10)
    ui["today_list"].pack(fill="both", expand=True)


# ---------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------

def refresh_all():
    # Call this after any change so every tab shows the latest data
    refresh_assignments()
    refresh_tasks()
    refresh_syllabus()
    refresh_dashboard()


def build_gui():
    root = tk.Tk()
    root.title("Student Academic Task & Deadline Manager")
    root.geometry("1000x620")

    notebook = ttk.Notebook(root)
    notebook.pack(fill="both", expand=True)

    tabs = [("Dashboard", build_dashboard_tab),
            ("Assignments", build_assignments_tab),
            ("Daily Tasks", build_tasks_tab),
            ("Syllabus", build_syllabus_tab)]
    for title, builder in tabs:
        tab = ttk.Frame(notebook)
        notebook.add(tab, text=title)
        builder(tab)

    refresh_all()
    root.mainloop()


if __name__ == "__main__":
    create_tables()
    build_gui()