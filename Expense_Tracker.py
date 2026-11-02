import sqlite3
import customtkinter as ctk
from tkinter import ttk, messagebox
import tkinter.simpledialog as sd
from datetime import datetime
import matplotlib.pyplot as plt

#-----------------configuration-----------------
# This makes the app follow the computer's appearance settings.
ctk.set_appearance_mode("System")  # "System", "Dark", "Light"
ctk.set_default_color_theme("blue")  # "blue", "green", "dark-blue"

DB_NAME = "expenses.db"

#-----------------Database Setup-----------------
# The app stores expenses and budgets in a SQLite database.
connector = sqlite3.connect(DB_NAME)
cursor = connector.cursor()

cursor.execute(
    'CREATE TABLE IF NOT EXISTS expenses (ID INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, category TEXT, amount REAL, description TEXT)'
) # Creates a unique ID for every expense and stores its date, category, amount, and description.
cursor.execute(
    'CREATE TABLE IF NOT EXISTS budgets (category TEXT PRIMARY KEY, Budget_limit REAL)'
)# Creates a table for category budgets, with one limit per category.

connector.commit() # Saves the database setup so the tables exist for future use.

#-----------------Helper Functions-----------------
# This function saves a new expense from the form into the database.
def add_expense():
    if not amount_var.get().strip() or not category_var.get().strip():
        messagebox.showerror("Error", "Please fill in all required fields.")
        return

    try:
        amount = float(amount_var.get())
    except ValueError:
        messagebox.showerror("Error", "Please enter a valid amount.")
        return

    date_value = date_var.get().strip() if date_var.get().strip() else datetime.now().strftime("%Y-%m-%d")

    cursor.execute(
        'INSERT INTO expenses (DATE, CATEGORY, DESCRIPTION, AMOUNT) VALUES (?, ?, ?, ?)',
        (date_value, category_var.get().strip(), desc_var.get().strip(), amount)
    )
    connector.commit()

    check_budget_warning(category_var.get().strip())
    clear_fields()
    load_records()
    messagebox.showinfo("Success", "Expense added successfully!")

# This function checks whether the user has spent more than a saved budget for the chosen category.
def check_budget_warning(category: str):
    cursor.execute('SELECT Budget_limit FROM budgets WHERE category = ?', (category,))
    row = cursor.fetchone()
    if not row:
        return

    limit = row[0]

    cursor.execute('SELECT SUM(amount) FROM expenses WHERE category = ?', (category,))
    spent =cursor.fetchone()[0] or 0

    if spent > limit:
        messagebox.showwarning("Budget Warning", f"You have exceeded your budget limit for {category}!\nLimit: {limit}\nSpent: {spent}")

# Clears the input boxes after a save or when the user wants to start fresh.
def clear_fields():
    date_var.set("")
    category_var.set("")
    amount_var.set("")
    desc_var.set("")
    try:
        tree.selection_remove(tree.selection()[0])
    except Exception:
        pass

# Loads all records from the database into the table.
def load_records(search_query=""):
    for row in tree.get_children():
        tree.delete(row)

    if search_query:
        cursor.execute('SELECT * FROM expenses WHERE category LIKE ? OR description LIKE ? ORDER BY date DESC', (f'%{search_query}%', f'%{search_query}%'))
    else:
        cursor.execute('SELECT * FROM expenses ORDER BY date DESC')

    for row in cursor.fetchall():
        tree.insert("", "end", values=row)

# Deletes the selected expense after confirmation.
def delete_record():
    sel = tree.selection()
    if not sel:
        messagebox.showerror("Error", "Please select a record to delete.")
        return

    item = sel[0]
    values = tree.item(item)['values']
    if messagebox.askyesno('Confirm Delete',  f'Delete expense ID {values[0]}?'):
        cursor.execute('DELETE FROM expenses WHERE ID = ?', (values[0],))
        connector.commit()
        tree.delete(item)
        messagebox.showinfo("Success", "Expense deleted successfully!")

# Opens a small popup window so the user can edit one selected expense.
def update_record():
    sel = tree.selection()
    if not sel:
        messagebox.showerror("Error", "Please select a record to update.")
        return

    values = tree.item(sel[0])['values']

    edit_win = ctk.CTkToplevel(app)
    edit_win.title("Update Expense")
    edit_win.geometry("380x300")

    up_date = ctk.StringVar(value=values[1])
    up_category = ctk.StringVar(value=values[2])
    up_amount = ctk.StringVar(value=values[3])
    up_desc = ctk.StringVar(value=values[4])

    ctk.CTkLabel(edit_win, text="Date (YYYY-MM-DD):").pack(pady=(12, 2))
    ctk.CTkEntry(edit_win, textvariable=up_date).pack(fill='x', padx=(12))

    ctk.CTkLabel(edit_win, text="Category:").pack(pady=(8, 2))
    ctk.CTkEntry(edit_win, textvariable=up_category).pack(fill='x', padx=(12))

    ctk.CTkLabel(edit_win, text="Amount:").pack(pady=(8, 2))
    ctk.CTkEntry(edit_win, textvariable=up_amount).pack(fill='x', padx=(12))

    ctk.CTkLabel(edit_win, text="Description:").pack(pady=(8, 2))
    ctk.CTkEntry(edit_win, textvariable=up_desc).pack(fill='x', padx=(12))

    def save_update():
        try:
            new_amt = float(up_amount.get())
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid amount.")
            return

        cursor.execute(
            'UPDATE expenses SET date = ?, category = ?, amount = ?, description = ? WHERE ID = ?',
            (up_date.get().strip(), up_category.get().strip(), new_amt, up_desc.get().strip(), values[0])
        )
        connector.commit()
        load_records()
        edit_win.destroy()

    ctk.CTkButton(edit_win, text="Save Changes", command=save_update).pack(pady=12)

#------------------Report and Visualization------------------
# Shows the total amount spent each month.
def show_monthly_report():
    cursor.execute('SELECT substr(date, 1, 7) AS month, SUM(amount) FROM expenses GROUP BY Month ORDER BY Month DESC')
    data = cursor.fetchall()

    report_lines = ["Monthly Expense Report", "----------------------"]
    for month, total in data:
        report_lines.append(f"{month} : KES{total}")

    messagebox.showinfo("Monthly Report", "\n".join(report_lines))

# Draws a bar chart so the user can compare spending by category.
def show_expense_graph():
    cursor.execute('SELECT category, SUM(amount) FROM expenses GROUP BY category')
    data = cursor.fetchall()
    if not data:
        messagebox.showinfo("No Data", "No expenses to display.")
        return

    categories = [d[0] for d in data]
    amounts = [d[1] for d in data]

    plt.figure(figsize = (7, 4))
    plt.bar(categories, amounts)
    plt.title("Expenses by Category")
    plt.xlabel("Categories")
    plt.ylabel("Total Amount (KES)")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()

#------------------Budgets and Search------------------
# Lets the user set a spending limit for a category.
def set_budget():
    cat = sd.askstring("Budget Category", "Enter category name:")
    if not cat:
        return
    limit = sd.askfloat("Budget Limit", f"Enter budget limit for {cat}:")
    if limit is None:
        return

    cursor.execute('INSERT OR REPLACE INTO budgets (category, Budget_limit) VALUES (?, ?)', (cat.strip(), limit))
    connector.commit()
    messagebox.showinfo("Budget Set", f"Budget for {cat} has been set to {limit}.")

# Shows all budget limits that have been saved.
def view_budgets():
    cursor.execute('SELECT category, Budget_limit FROM budgets ORDER BY category ASC')
    budgets = cursor.fetchall()

    if not budgets:
        messagebox.showinfo("Budgets", "No budgets have been set yet.")
        return

    budget_lines = ["Saved Budgets", "----------------"]
    for category, limit in budgets:
        budget_lines.append(f"{category}: KES{limit}")

    messagebox.showinfo("Budgets", "\n".join(budget_lines), parent=app)

# Removes a saved budget for a specific category.
def remove_budget():
    cat = sd.askstring("Remove Budget", "Enter category name to remove:")
    if not cat:
        return

    cursor.execute('DELETE FROM budgets WHERE category = ?', (cat.strip(),))
    connector.commit()

    if cursor.rowcount == 0:
        messagebox.showinfo("Budget Removed", f"No budget found for {cat.strip()}.")
    else:
        messagebox.showinfo("Budget Removed", f"Budget for {cat.strip()} has been removed.")

# Lets the user search expenses by category or description.
def search_expenses():
    query = sd.askstring("Search Expenses", "Enter category or description ")
    if query is not None:
        load_records(query.strip())

#------------------Aplication GUI------------------
# Create the main application window.
app = ctk.CTk()
app.title("Expense Tracker")
app.geometry("1100x750")

# Make the two columns in the app resize properly when the window size changes.
app.grid_columnconfigure(0, weight=1)
app.grid_columnconfigure(1, weight=3)
app.grid_rowconfigure(0, weight=1)

# Left panel for input fields and buttons.
left_panel = ctk.CTkFrame(master = app, corner_radius = 8)
left_panel.grid(row = 0, column = 0, sticky = "nsew", padx = 12, pady = 12)

ctk.CTkLabel(left_panel, text = "Expense Manager", font = ctk.CTkFont(size = 20, weight = "bold")).pack(pady = (12, 8))

# Variables for the form fields.
date_var = ctk.StringVar()
category_var = ctk.StringVar()
amount_var = ctk.StringVar()
desc_var = ctk.StringVar()

# Input fields for date, category, amount, and description.
ctk.CTkLabel(left_panel, text = "Date (YYYY-MM-DD):").pack(anchor = "w", padx = 12, pady = (6, 0))
ctk.CTkEntry(left_panel, textvariable = date_var).pack(fill = "x", padx = 12, pady = 4)

ctk.CTkLabel(left_panel, text = "Category:").pack(anchor = "w", padx = 12, pady = (6, 0))
ctk.CTkEntry(left_panel, textvariable = category_var).pack(fill = "x", padx = 12, pady = 4)

ctk.CTkLabel(left_panel, text = "Amount:").pack(anchor = "w", padx = 12, pady = (6, 0))
ctk.CTkEntry(left_panel, textvariable = amount_var).pack(fill = "x", padx = 12, pady = 4)

ctk.CTkLabel(left_panel, text = "Description:").pack(anchor = "w", padx = 12, pady = (6, 0))
ctk.CTkEntry(left_panel, textvariable = desc_var).pack(fill = "x", padx = 12, pady = 4) 

# Buttons for the main actions.
btn_frame = ctk.CTkFrame(left_panel, fg_color = "transparent")
btn_frame.pack(pady = 12, fill = 'x', padx = 8)

ctk.CTkButton(btn_frame, text = 'Add Expense', command = add_expense).pack(fill = 'x', padx = 8, pady = (4, 6))
ctk.CTkButton(btn_frame, text = 'Clear Fields', command = clear_fields).pack(fill = 'x', padx = 8, pady = 6)
ctk.CTkButton(btn_frame, text = 'Search', command = search_expenses).pack(fill = 'x', padx = 8, pady = 6)
ctk.CTkButton(btn_frame, text = 'Set Budget', command = set_budget).pack(fill = 'x', padx = 8, pady = 6)
ctk.CTkButton(btn_frame, text = 'View Budgets', command = view_budgets).pack(fill = 'x', padx = 8, pady = 6)
ctk.CTkButton(btn_frame, text = 'Remove Budget', command = remove_budget).pack(fill = 'x', padx = 8, pady = 6)
ctk.CTkButton(btn_frame, text = 'Monthly Report', command = show_monthly_report).pack(fill = 'x', padx = 8, pady = 6)
ctk.CTkButton(btn_frame, text = 'Expense Graph', command = show_expense_graph).pack(fill = 'x', padx = 8, pady = (6, 12))

# Right panel (records)
# This area displays the saved expenses in a table.
right_panel = ctk.CTkFrame(master = app, corner_radius = 8)
right_panel.grid(row = 0, column = 1, sticky = 'nsew', padx = 12, pady = 12)
right_panel.grid_columnconfigure(0, weight = 1)
right_panel.grid_rowconfigure(1, weight = 1)

ctk.CTkLabel(right_panel, text = 'Expense Records', font = ctk.CTkFont(size = 18, weight = 'bold')).grid(row = 0, column = 0, sticky = 'w', padx = 12, pady = 8)

# Treeview inside a frame so it expands when the window is resized.
tree_frame = ctk.CTkFrame(right_panel, fg_color = 'transparent')
tree_frame.grid(row = 1, column = 0, sticky = 'nsew', padx = 12, pady = (0, 12))

columns = ('ID', 'Date', 'Category', 'Amount', 'Description')

def resize_tree_columns(event = None):
    if not tree.winfo_exists():
        return

    available_width = max(right_panel.winfo_width() - 44, 300)
    ratios = {'ID': 0.10, 'Date': 0.18, 'Category': 0.22, 'Amount': 0.18, 'Description': 0.32}

    for column in columns:
        width = max(70, int(available_width * ratios[column]))
        tree.column(column, width = width, minwidth = 60, stretch = True)

tree = ttk.Treeview(tree_frame, columns = columns, show = 'headings', selectmode = 'browse')
for col in columns:
    tree.heading(col, text = col)
    tree.column(col, minwidth = 60, anchor = 'center', stretch = True)

# Scrollbars allow the table to scroll when it gets too long.
vsb = ttk.Scrollbar(tree_frame, orient = 'vertical', command = tree.yview)
hsb = ttk.Scrollbar(tree_frame, orient = 'horizontal', command = tree.xview)

tree.configure(yscrollcommand = vsb.set, xscrollcommand = hsb.set)

tree.grid(row = 0, column = 0, sticky = 'nsew')
vsb.grid(row = 0, column = 1, sticky = 'ns')
hsb.grid(row = 1, column = 0, sticky = 'ew')

tree_frame.grid_rowconfigure(0, weight = 1)
tree_frame.grid_columnconfigure(0, weight = 1)
right_panel.bind('<Configure>', resize_tree_columns)
app.bind('<Configure>', resize_tree_columns)
app.after(100, resize_tree_columns)

# Action buttons under the expense table.
action_frame = ctk.CTkFrame(right_panel, fg_color = 'transparent')
action_frame.grid(row = 2, column = 0, sticky = 'ew', padx = 12, pady = (0, 12))

ctk.CTkButton(action_frame, text = 'Delete Expense', fg_color = '#ff6b6b', command = delete_record).pack(side = 'left', padx = 8, pady = 6)
ctk.CTkButton(action_frame, text = 'Update Record', fg_color = '#4da6ff', command = update_record).pack(side = 'left', padx = 8, pady = 6)

# Load the saved records when the app starts.
load_records()

# Run the app.
app.mainloop() 