import sys
import psycopg2
import customtkinter as ctk
from tkinter import ttk, messagebox
from datetime import datetime, date
from tkcalendar import DateEntry

# --- ОБЩИЕ НАСТРОЙКИ ---
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


# --- КЛАССЫ ПРИЛОЖЕНИЯ ---

class DatabaseManager:
    """Управляет подключением и всеми взаимодействиями с базой данных PostgreSQL."""

    def __init__(self):
        self.connection = None
        self.connect()

    def connect(self):
        try:
            self.connection = psycopg2.connect(
                host="localhost",
                database="kpo",
                user="postgres",
                password="admin"
            )
        except Exception as e:
            messagebox.showerror("Ошибка подключения", f"Не удалось подключиться к базе данных: {str(e)}")
            sys.exit()

    def execute_query(self, query, params=None):
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(query, params)
                if query.strip().upper().startswith('SELECT'):
                    return cursor.fetchall()
                else:
                    self.connection.commit()
                    return True
        except psycopg2.Error as e:
            print(f"Ошибка выполнения запроса: {e}")
            self.connection.rollback()
            # Возвращаем конкретный код ошибки для обработки в интерфейсе
            return e.pgcode
        except Exception as e:
            print(f"Неизвестная ошибка: {e}")
            self.connection.rollback()
            return None


class RoleSelectionWindow(ctk.CTk):
    """Стартовое окно для выбора роли (Администратор или Пользователь)."""

    def __init__(self):
        super().__init__()
        self.title("Выбор роли")
        self.geometry("400x200")
        self.resizable(False, False)
        self.role = None
        self.grid_columnconfigure(0, weight=1)

        label = ctk.CTkLabel(self, text="Выберите роль для входа:", font=("Arial", 16))
        label.pack(pady=20, padx=20)

        admin_btn = ctk.CTkButton(self, text="Администратор", command=lambda: self.select_role("admin"), width=200,
                                  height=40)
        admin_btn.pack(pady=10)

        user_btn = ctk.CTkButton(self, text="Пользователь", command=lambda: self.select_role("user"), width=200,
                                 height=40, fg_color="gray")
        user_btn.pack(pady=10)

    def select_role(self, role):
        self.role = role
        self.destroy()


class UserInputWindow(ctk.CTkToplevel):
    """Окно для пользователя, где он вводит свои ФИО и подает заявление на курс."""

    def __init__(self, db_manager):
        super().__init__()
        self.db = db_manager
        self.title("Подача заявления")
        self.geometry("500x400")
        self.resizable(False, False)

        label = ctk.CTkLabel(self, text="Введите свои данные:", font=("Arial", 16))
        label.pack(pady=20)

        form_frame = ctk.CTkFrame(self)
        form_frame.pack(fill="x", padx=20, pady=10)
        form_frame.columnconfigure(1, weight=1)

        ctk.CTkLabel(form_frame, text="Фамилия:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.surname = ctk.CTkEntry(form_frame, placeholder_text="Фамилия")
        self.surname.grid(row=0, column=1, sticky="ew", padx=5, pady=5)

        ctk.CTkLabel(form_frame, text="Имя:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.firstname = ctk.CTkEntry(form_frame, placeholder_text="Имя")
        self.firstname.grid(row=1, column=1, sticky="ew", padx=5, pady=5)

        ctk.CTkLabel(form_frame, text="Отчество:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        self.father = ctk.CTkEntry(form_frame, placeholder_text="Отчество (если есть)")
        self.father.grid(row=2, column=1, sticky="ew", padx=5, pady=5)

        button_frame = ctk.CTkFrame(self)
        button_frame.pack(fill="x", padx=20, pady=10)

        submit_btn = ctk.CTkButton(button_frame, text="Продолжить", command=self.check_student)
        submit_btn.pack(pady=10)

    def check_student(self):
        surname = self.surname.get().strip()
        firstname = self.firstname.get().strip()
        father = self.father.get().strip() or None  # Используем None, если отчество не введено

        if not surname or not firstname:
            messagebox.showwarning("Ошибка", "Фамилия и имя обязательны для заполнения!")
            return

        student = self.db.execute_query(
            "SELECT student_id FROM student WHERE surname = %s AND firstname = %s AND (father = %s OR father IS NULL)",
            (surname, firstname, father))
        if student:
            stmt = self.db.execute_query(
                "SELECT c.name FROM statement s JOIN course c ON s.course_id = c.course_id WHERE s.student_id = %s ORDER BY s.statement_id DESC LIMIT 1",
                (student[0][0],))
            if stmt:
                messagebox.showinfo("Статус", f"Вы уже подали заявление на курс: {stmt[0][0]}.")
            else:
                messagebox.showinfo("Статус", "У вас нет активных заявлений.")
        else:
            self.ask_course_and_date(surname, firstname, father)

    def ask_course_and_date(self, surname, firstname, father):
        self.withdraw()
        course_window = ctk.CTkToplevel(self)
        course_window.title("Выбор курса и даты")
        course_window.geometry("500x300")
        course_window.resizable(False, False)

        label = ctk.CTkLabel(course_window, text="Выберите курс и дату начала:", font=("Arial", 16))
        label.pack(pady=20)

        form_frame = ctk.CTkFrame(course_window)
        form_frame.pack(fill="x", padx=20, pady=10)
        form_frame.columnconfigure(1, weight=1)

        ctk.CTkLabel(form_frame, text="Курс:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        course_combo = ctk.CTkComboBox(form_frame)
        course_combo.grid(row=0, column=1, sticky="ew", padx=5, pady=5)

        ctk.CTkLabel(form_frame, text="Дата начала:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        date_combo = ctk.CTkComboBox(form_frame, state="disabled")
        date_combo.grid(row=1, column=1, sticky="ew", padx=5, pady=5)

        all_courses = self.db.execute_query(
            "SELECT course_id, name, start_date, max_students FROM course ORDER BY name, start_date")

        def update_available_dates(selected_course_name):
            dates = [c[2].strftime('%Y-%m-%d') for c in all_courses if c[1] == selected_course_name]
            if dates:
                date_combo.configure(values=dates, state="readonly")
                date_combo.set(dates[0])
            else:
                date_combo.configure(values=[], state="disabled")
                date_combo.set("Нет доступных дат")

        if all_courses:
            names = sorted(list(set([c[1] for c in all_courses])))
            course_combo.configure(values=names, command=update_available_dates)
            course_combo.set(names[0])
            update_available_dates(names[0])
        else:
            course_combo.configure(state="disabled", values=["Нет доступных курсов"])
            course_combo.set("Нет доступных курсов")
            date_combo.set("Нет доступных дат")

        def submit():
            course_name, start_date_str = course_combo.get(), date_combo.get()
            if "Нет" in course_name or "Нет" in start_date_str:
                messagebox.showwarning("Ошибка", "Пожалуйста, выберите курс и доступную дату.")
                return

            course_id, max_students = None, 0
            for course in all_courses:
                if course[1] == course_name and course[2].strftime('%Y-%m-%d') == start_date_str:
                    course_id, max_students = course[0], course[3]
                    break

            if not course_id:
                messagebox.showerror("Ошибка", "Выбранный курс не найден. Возможно, данные устарели.")
                return

            count = self.db.execute_query("SELECT COUNT(*) FROM statement WHERE course_id = %s", (course_id,))
            if count and count[0][0] >= max_students:
                messagebox.showwarning("Запись невозможна", "К сожалению, на выбранную дату все места заняты.")
                return

            self.db.execute_query("INSERT INTO student (surname, firstname, father) VALUES (%s, %s, %s)",
                                  (surname, firstname, father))
            student = self.db.execute_query(
                "SELECT student_id FROM student WHERE surname = %s AND firstname = %s AND (father = %s OR father IS NULL)",
                (surname, firstname, father))

            if not student:
                messagebox.showerror("Критическая ошибка", "Не удалось создать запись слушателя.")
                return

            if self.db.execute_query("INSERT INTO statement (student_id, course_id, start_date) VALUES (%s, %s, %s)",
                                     (student[0][0], course_id, start_date_str)):
                messagebox.showinfo("Успех", "Заявление успешно подано!")
                course_window.destroy()
                self.destroy()
            else:
                messagebox.showerror("Ошибка", "Не удалось подать заявление.")

        button_frame = ctk.CTkFrame(course_window)
        button_frame.pack(fill="x", padx=20, pady=10)
        submit_btn = ctk.CTkButton(button_frame, text="Подать заявление", command=submit)
        submit_btn.pack(pady=10)


class CoursesApp(ctk.CTk):
    """Основное окно приложения для администратора с полным функционалом."""

    def __init__(self, role="admin"):
        super().__init__()
        self.role = role
        self.db = DatabaseManager()
        self.all_courses_data = []
        if self.role == "user":
            self.withdraw()
            user_window = UserInputWindow(self.db)
            user_window.protocol("WM_DELETE_WINDOW", self.quit)
        else:
            self.init_ui()

    def init_ui(self):
        self.title("Система автоматизации курсов (Панель администратора)")
        self.geometry("1400x800")

        style = ttk.Style()
        style.configure("Treeview", font=("Arial", 14), rowheight=28)
        style.configure("Treeview.Heading", font=("Arial", 16, "bold"))

        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=20, pady=20)

        tabs = ["Преподаватели", "Курсы", "Слушатели", "Заявления", "Договоры", "Отчеты"]
        for name in tabs: self.tabview.add(name)

        self.setup_tabs()
        self.load_all_data()

    def setup_tabs(self):
        self.setup_teachers_tab()
        self.setup_courses_tab()
        self.setup_students_tab()
        self.setup_statements_tab()
        self.setup_contracts_tab()
        self.setup_reports_tab()

    def setup_teachers_tab(self):
        tab = self.tabview.tab("Преподаватели")
        main_frame = ctk.CTkFrame(tab)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        form_frame = ctk.CTkFrame(main_frame)
        form_frame.pack(fill="x", padx=10, pady=10)
        form_frame.columnconfigure(1, weight=1)

        ctk.CTkLabel(form_frame, text="Фамилия:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.teacher_surname = ctk.CTkEntry(form_frame)
        self.teacher_surname.grid(row=0, column=1, sticky="ew", padx=5, pady=5)

        ctk.CTkLabel(form_frame, text="Имя:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.teacher_firstname = ctk.CTkEntry(form_frame)
        self.teacher_firstname.grid(row=1, column=1, sticky="ew", padx=5, pady=5)

        ctk.CTkLabel(form_frame, text="Отчество:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        self.teacher_father = ctk.CTkEntry(form_frame)
        self.teacher_father.grid(row=2, column=1, sticky="ew", padx=5, pady=5)

        ctk.CTkLabel(form_frame, text="Образование:").grid(row=3, column=0, sticky="w", padx=5, pady=5)
        self.teacher_education = ctk.CTkEntry(form_frame)
        self.teacher_education.grid(row=3, column=1, sticky="ew", padx=5, pady=5)

        ctk.CTkLabel(form_frame, text="Категория:").grid(row=4, column=0, sticky="w", padx=5, pady=5)
        self.teacher_category = ctk.CTkComboBox(form_frame, values=["первая", "вторая", "высшая"])
        self.teacher_category.grid(row=4, column=1, sticky="ew", padx=5, pady=5)

        button_frame = ctk.CTkFrame(form_frame)
        button_frame.grid(row=5, column=0, columnspan=2, sticky="ew", padx=5, pady=10)
        ctk.CTkButton(button_frame, text="Добавить", command=self.add_teacher).pack(side="left", padx=5)
        ctk.CTkButton(button_frame, text="Очистить", command=self.clear_teacher_form, fg_color="gray").pack(side="left",
                                                                                                            padx=5)
        ctk.CTkButton(button_frame, text="Удалить выбранное", command=self.delete_teacher, fg_color="red").pack(
            side="left", padx=5)

        table_frame = ctk.CTkFrame(main_frame)
        table_frame.pack(fill="both", expand=True, padx=10, pady=10)
        self.teachers_table = ttk.Treeview(table_frame,
                                           columns=("ID", "Фамилия", "Имя", "Отчество", "Образование", "Категория"),
                                           show="headings")
        for col in self.teachers_table["columns"]: self.teachers_table.heading(col, text=col)
        self.teachers_table.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.teachers_table.yview)
        self.teachers_table.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

    def setup_courses_tab(self):
        tab = self.tabview.tab("Курсы")
        main_frame = ctk.CTkFrame(tab)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        form_frame = ctk.CTkFrame(main_frame)
        form_frame.pack(fill="x", padx=10, pady=10)

        labels = ["Название:", "Часы:", "Цена:", "Макс. студентов:", "Преподаватель:"]
        self.course_widgets = {}
        for i, label in enumerate(labels):
            row, col = i // 2, (i % 2) * 2
            ctk.CTkLabel(form_frame, text=label).grid(row=row, column=col, sticky="w", padx=5, pady=5)
            widget = ctk.CTkComboBox(form_frame) if "Преподаватель" in label else ctk.CTkEntry(form_frame)
            widget.grid(row=row, column=col + 1, sticky="ew", padx=5, pady=5)
            self.course_widgets[label] = widget

        ctk.CTkLabel(form_frame, text="Дата начала:").grid(row=3, column=0, sticky="w", padx=5, pady=5)
        self.course_start_date = DateEntry(form_frame, date_pattern='yyyy-mm-dd', locale='ru_RU')
        self.course_start_date.grid(row=3, column=1, sticky="ew", padx=5, pady=5)

        ctk.CTkLabel(form_frame, text="Дата окончания:").grid(row=3, column=2, sticky="w", padx=5, pady=5)
        self.course_end_date = DateEntry(form_frame, date_pattern='yyyy-mm-dd', locale='ru_RU')
        self.course_end_date.grid(row=3, column=3, sticky="ew", padx=5, pady=5)

        button_frame = ctk.CTkFrame(form_frame)
        button_frame.grid(row=4, column=0, columnspan=4, sticky="ew", padx=5, pady=10)
        ctk.CTkButton(button_frame, text="Добавить", command=self.add_course).pack(side="left", padx=5)
        ctk.CTkButton(button_frame, text="Очистить", command=self.clear_course_form, fg_color="gray").pack(side="left",
                                                                                                           padx=5)
        ctk.CTkButton(button_frame, text="Удалить выбранное", command=self.delete_course, fg_color="red").pack(
            side="left", padx=5)

        table_frame = ctk.CTkFrame(main_frame)
        table_frame.pack(fill="both", expand=True, padx=10, pady=10)
        self.courses_table = ttk.Treeview(table_frame, columns=(
        "ID", "Название", "Часы", "Цена", "Макс", "Начало", "Окончание", "Преподаватель"), show="headings")
        for col in self.courses_table["columns"]: self.courses_table.heading(col, text=col)
        self.courses_table.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.courses_table.yview)
        self.courses_table.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

    def setup_students_tab(self):
        tab = self.tabview.tab("Слушатели")
        main_frame = ctk.CTkFrame(tab)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        form_frame = ctk.CTkFrame(main_frame)
        form_frame.pack(fill="x", padx=10, pady=10)
        form_frame.columnconfigure(1, weight=1)

        ctk.CTkLabel(form_frame, text="Фамилия:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.student_surname = ctk.CTkEntry(form_frame)
        self.student_surname.grid(row=0, column=1, sticky="ew", padx=5, pady=5)

        ctk.CTkLabel(form_frame, text="Имя:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.student_firstname = ctk.CTkEntry(form_frame)
        self.student_firstname.grid(row=1, column=1, sticky="ew", padx=5, pady=5)

        ctk.CTkLabel(form_frame, text="Отчество:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        self.student_father = ctk.CTkEntry(form_frame)
        self.student_father.grid(row=2, column=1, sticky="ew", padx=5, pady=5)

        button_frame = ctk.CTkFrame(form_frame)
        button_frame.grid(row=3, column=0, columnspan=2, sticky="ew", padx=5, pady=10)
        ctk.CTkButton(button_frame, text="Добавить", command=self.add_student).pack(side="left", padx=5)
        ctk.CTkButton(button_frame, text="Очистить", command=self.clear_student_form, fg_color="gray").pack(side="left",
                                                                                                            padx=5)
        ctk.CTkButton(button_frame, text="Удалить выбранное", command=self.delete_student, fg_color="red").pack(
            side="left", padx=5)

        table_frame = ctk.CTkFrame(main_frame)
        table_frame.pack(fill="both", expand=True, padx=10, pady=10)
        self.students_table = ttk.Treeview(table_frame, columns=("ID", "Фамилия", "Имя", "Отчество"), show="headings")
        for col in self.students_table["columns"]: self.students_table.heading(col, text=col)
        self.students_table.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.students_table.yview)
        self.students_table.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

    def setup_statements_tab(self):
        tab = self.tabview.tab("Заявления")
        main_frame = ctk.CTkFrame(tab)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        form_frame = ctk.CTkFrame(main_frame)
        form_frame.pack(fill="x", padx=10, pady=10)
        form_frame.columnconfigure(1, weight=1)

        ctk.CTkLabel(form_frame, text="Слушатель:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.statement_student = ctk.CTkComboBox(form_frame)
        self.statement_student.grid(row=0, column=1, sticky="ew", padx=5, pady=5)

        ctk.CTkLabel(form_frame, text="Курс:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.statement_course = ctk.CTkComboBox(form_frame, command=self.update_statement_dates)
        self.statement_course.grid(row=1, column=1, sticky="ew", padx=5, pady=5)

        ctk.CTkLabel(form_frame, text="Дата начала:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        self.statement_start_date_combo = ctk.CTkComboBox(form_frame, state="disabled")
        self.statement_start_date_combo.grid(row=2, column=1, sticky="ew", padx=5, pady=5)

        button_frame = ctk.CTkFrame(form_frame)
        button_frame.grid(row=3, column=0, columnspan=2, sticky="ew", padx=5, pady=10)
        ctk.CTkButton(button_frame, text="Подать заявление", command=self.add_statement).pack(side="left", padx=5)

        table_frame = ctk.CTkFrame(main_frame)
        table_frame.pack(fill="both", expand=True, padx=10, pady=10)
        self.statements_table = ttk.Treeview(table_frame, columns=("ID", "Слушатель", "Курс", "Дата"), show="headings")
        for col in self.statements_table["columns"]: self.statements_table.heading(col, text=col)
        self.statements_table.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.statements_table.yview)
        self.statements_table.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

    def setup_contracts_tab(self):
        tab = self.tabview.tab("Договоры")
        main_frame = ctk.CTkFrame(tab)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        button_frame = ctk.CTkFrame(main_frame)
        button_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkButton(button_frame, text="Сформировать договор по последнему заявлению",
                      command=self.create_contract).pack(side="left", padx=5)

        table_frame = ctk.CTkFrame(main_frame)
        table_frame.pack(fill="both", expand=True, padx=10, pady=10)
        self.contracts_table = ttk.Treeview(table_frame, columns=("ID", "ID заявления", "Слушатель", "Курс", "Дата"),
                                            show="headings")
        for col in self.contracts_table["columns"]: self.contracts_table.heading(col, text=col)
        self.contracts_table.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.contracts_table.yview)
        self.contracts_table.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

    def setup_reports_tab(self):
        tab = self.tabview.tab("Отчеты")
        main_frame = ctk.CTkFrame(tab)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        reports_frame = ctk.CTkFrame(main_frame)
        reports_frame.pack(fill="x", padx=10, pady=10)

        price_frame = ctk.CTkFrame(reports_frame)
        price_frame.pack(fill="x", padx=5, pady=5)
        ctk.CTkLabel(price_frame, text="Прайс-лист за период:").pack(side="left", padx=5)
        self.price_start_date = DateEntry(price_frame, date_pattern='yyyy-mm-dd', locale='ru_RU')
        self.price_start_date.pack(side="left", padx=5)
        self.price_end_date = DateEntry(price_frame, date_pattern='yyyy-mm-dd', locale='ru_RU')
        self.price_end_date.pack(side="left", padx=5)
        ctk.CTkButton(price_frame, text="Сформировать", command=self.generate_price_list).pack(side="left", padx=5)
        ctk.CTkButton(price_frame, text="Изменить цены", command=self.open_change_price_window).pack(side="left",
                                                                                                     padx=5)

        other_reports_frame = ctk.CTkFrame(reports_frame)
        other_reports_frame.pack(fill="x", padx=5, pady=5)
        ctk.CTkButton(other_reports_frame, text="Состав слушателей по курсам",
                      command=self.generate_students_report).pack(side="left", padx=5)
        ctk.CTkButton(other_reports_frame, text="Часы преподавателей",
                      command=self.generate_teachers_hours_report).pack(side="left", padx=5)

        table_frame = ctk.CTkFrame(main_frame)
        table_frame.pack(fill="both", expand=True, padx=10, pady=10)
        self.reports_table = ttk.Treeview(table_frame, show="headings")
        self.reports_table.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.reports_table.yview)
        self.reports_table.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

    # --- ЗАГРУЗКА ДАННЫХ ---
    def load_all_data(self):
        self.load_teachers()
        self.load_courses()
        self.load_students()
        self.load_statements()
        self.load_contracts()

    def load_teachers(self):
        teachers = self.db.execute_query("SELECT * FROM teacher ORDER BY surname")
        self.teachers_table.delete(*self.teachers_table.get_children())
        teacher_names = []
        if teachers and isinstance(teachers, list):
            for teacher in teachers:
                self.teachers_table.insert("", "end", values=teacher)
                teacher_names.append(f"{teacher[1]} {teacher[2]}")
        self.course_widgets["Преподаватель:"].configure(values=teacher_names)
        if teacher_names: self.course_widgets["Преподаватель:"].set(teacher_names[0])

    def load_courses(self):
        self.all_courses_data = self.db.execute_query("""
            SELECT c.course_id, c.name, c.hours, c.price, c.max_students, 
                   c.start_date, c.end_date, t.surname || ' ' || t.firstname 
            FROM course c JOIN teacher t ON c.teacher_id = t.teacher_id 
            ORDER BY c.name, c.start_date
        """)
        if not self.all_courses_data or not isinstance(self.all_courses_data, list):
            self.all_courses_data = []

        self.courses_table.delete(*self.courses_table.get_children())
        for row in self.all_courses_data: self.courses_table.insert("", "end", values=row)

        names = sorted(list(set([c[1] for c in self.all_courses_data])))
        if names:
            self.statement_course.configure(values=names)
            self.statement_course.set(names[0])
            self.update_statement_dates(names[0])
        else:
            self.statement_course.configure(values=[], state="disabled")
            self.statement_course.set("")
            self.update_statement_dates(None)

    def load_students(self):
        students = self.db.execute_query("SELECT * FROM student ORDER BY surname")
        self.students_table.delete(*self.students_table.get_children())
        student_names = []
        if students and isinstance(students, list):
            for student in students:
                self.students_table.insert("", "end", values=student)
                student_names.append(f"{student[1]} {student[2]}")
        self.statement_student.configure(values=student_names)
        if student_names: self.statement_student.set(student_names[0])

    def load_statements(self):
        statements = self.db.execute_query("""
            SELECT s.statement_id, st.surname || ' ' || st.firstname, c.name, s.start_date
            FROM statement s
            JOIN student st ON s.student_id = st.student_id
            JOIN course c ON s.course_id = c.course_id
            ORDER BY s.statement_id DESC
        """)
        self.statements_table.delete(*self.statements_table.get_children())
        if statements and isinstance(statements, list):
            for stmt in statements: self.statements_table.insert("", "end", values=stmt)

    def load_contracts(self):
        contracts = self.db.execute_query("""
            SELECT co.contract_id, co.statement_id, st.surname || ' ' || st.firstname, 
                   c.name, co.contract_date
            FROM contract co JOIN statement s ON co.statement_id = s.statement_id
            JOIN student st ON s.student_id = st.student_id
            JOIN course c ON s.course_id = c.course_id
            ORDER BY co.contract_id DESC
        """)
        self.contracts_table.delete(*self.contracts_table.get_children())
        if contracts and isinstance(contracts, list):
            for contract in contracts: self.contracts_table.insert("", "end", values=contract)

    # --- ДОБАВЛЕНИЕ И СОЗДАНИЕ ---
    def add_teacher(self):
        surname = self.teacher_surname.get().strip()
        firstname = self.teacher_firstname.get().strip()
        father = self.teacher_father.get().strip() or None
        education = self.teacher_education.get().strip()
        category = self.teacher_category.get()

        if not all([surname, firstname, education]):
            messagebox.showwarning("Ошибка", "Заполните обязательные поля: Фамилия, Имя, Образование.")
            return

        if self.db.execute_query(
                "INSERT INTO teacher (surname, firstname, father, education, category) VALUES (%s, %s, %s, %s, %s)",
                (surname, firstname, father, education, category)):
            self.load_teachers()
            self.clear_teacher_form()
            messagebox.showinfo("Успех", "Преподаватель добавлен.")
        else:
            messagebox.showerror("Ошибка", "Не удалось добавить преподавателя.")

    def add_course(self):
        try:
            name = self.course_widgets["Название:"].get().strip()
            hours = int(self.course_widgets["Часы:"].get())
            price = float(self.course_widgets["Цена:"].get())
            max_students = int(self.course_widgets["Макс. студентов:"].get())
            teacher_name = self.course_widgets["Преподаватель:"].get()
            start_date = self.course_start_date.get_date().strftime("%Y-%m-%d")
            end_date = self.course_end_date.get_date().strftime("%Y-%m-%d")

            if not all([name, teacher_name]):
                messagebox.showwarning("Ошибка", "Название и преподаватель обязательны.");
                return

            teacher = self.db.execute_query("SELECT teacher_id FROM teacher WHERE surname = %s AND firstname = %s",
                                            tuple(teacher_name.split()))
            if not teacher:
                messagebox.showerror("Ошибка", "Преподаватель не найден.");
                return

            if self.db.execute_query(
                    """INSERT INTO course (name, hours, price, max_students, start_date, end_date, teacher_id) VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    (name, hours, price, max_students, start_date, end_date, teacher[0][0])):
                self.load_courses()
                self.clear_course_form()
                messagebox.showinfo("Успех", "Курс добавлен.")
            else:
                messagebox.showerror("Ошибка", "Не удалось добавить курс.")
        except ValueError:
            messagebox.showerror("Ошибка", "Проверьте правильность числовых полей (часы, цена, макс. студентов).")
        except Exception as e:
            messagebox.showerror("Неизвестная ошибка", f"Произошла ошибка: {e}")

    def add_student(self):
        surname = self.student_surname.get().strip()
        firstname = self.student_firstname.get().strip()
        father = self.student_father.get().strip() or None

        if not surname or not firstname:
            messagebox.showwarning("Ошибка", "Заполните Фамилию и Имя.");
            return

        if self.db.execute_query("INSERT INTO student (surname, firstname, father) VALUES (%s, %s, %s)",
                                 (surname, firstname, father)):
            self.load_students()
            self.clear_student_form()
            messagebox.showinfo("Успех", "Слушатель добавлен.")
        else:
            messagebox.showerror("Ошибка", "Не удалось добавить слушателя.")

    def add_statement(self):
        student_name = self.statement_student.get()
        course_name = self.statement_course.get()
        start_date_str = self.statement_start_date_combo.get()

        if not student_name or not course_name or "Нет" in start_date_str:
            messagebox.showwarning("Ошибка", "Заполните все поля и выберите доступную дату.");
            return

        student = self.db.execute_query("SELECT student_id FROM student WHERE surname = %s AND firstname = %s",
                                        tuple(student_name.split()))
        if not student:
            messagebox.showerror("Ошибка", "Слушатель не найден.");
            return

        course_id, max_students = None, 0
        for c in self.all_courses_data:
            if c[1] == course_name and c[5].strftime('%Y-%m-%d') == start_date_str:
                course_id, max_students = c[0], c[4]
                break

        if not course_id:
            messagebox.showerror("Ошибка", "Выбранный курс с указанной датой не найден.");
            return

        count = self.db.execute_query("SELECT COUNT(*) FROM statement WHERE course_id = %s", (course_id,))
        if count and count[0][0] >= max_students:
            messagebox.showwarning("Запись невозможна", f"Группа набрана. Максимум: {max_students} слушателей.");
            return

        if self.db.execute_query("INSERT INTO statement (student_id, course_id, start_date) VALUES (%s, %s, %s)",
                                 (student[0][0], course_id, start_date_str)):
            self.load_statements()
            messagebox.showinfo("Успех", "Заявление подано.")
        else:
            messagebox.showerror("Ошибка", "Не удалось подать заявление.")

    def create_contract(self):
        last_stmt = self.db.execute_query("SELECT statement_id FROM statement ORDER BY statement_id DESC LIMIT 1")
        if not last_stmt:
            messagebox.showwarning("Ошибка", "Нет заявлений для формирования договора.");
            return

        statement_id = last_stmt[0][0]
        if self.db.execute_query("SELECT 1 FROM contract WHERE statement_id = %s", (statement_id,)):
            messagebox.showinfo("Информация", "Договор для последнего заявления уже существует.");
            return

        if self.db.execute_query("INSERT INTO contract (statement_id) VALUES (%s)", (statement_id,)):
            self.load_contracts()
            messagebox.showinfo("Успех", "Договор сформирован.")
        else:
            messagebox.showerror("Ошибка", "Не удалось сформировать договор.")

    # --- УДАЛЕНИЕ ---
    def delete_teacher(self):
        selected_item = self.teachers_table.focus()
        if not selected_item:
            messagebox.showwarning("Внимание", "Выберите преподавателя для удаления.");
            return

        teacher_id = self.teachers_table.item(selected_item)['values'][0]
        if messagebox.askyesno("Подтверждение", f"Вы уверены, что хотите удалить преподавателя (ID: {teacher_id})?"):
            result = self.db.execute_query("DELETE FROM teacher WHERE teacher_id = %s", (teacher_id,))
            if result is True:
                messagebox.showinfo("Успех", "Преподаватель удален.")
                self.load_all_data()  # Обновляем все данные, т.к. могли измениться курсы
            elif result == '23503':  # Код ошибки Foreign Key Violation
                messagebox.showerror("Ошибка удаления",
                                     "Невозможно удалить преподавателя, так как он назначен на один или несколько курсов.")
            else:
                messagebox.showerror("Ошибка", "Произошла неизвестная ошибка при удалении.")

    def delete_course(self):
        selected_item = self.courses_table.focus()
        if not selected_item:
            messagebox.showwarning("Внимание", "Выберите курс для удаления.");
            return

        course_id = self.courses_table.item(selected_item)['values'][0]
        if messagebox.askyesno("Подтверждение", f"Вы уверены, что хотите удалить курс (ID: {course_id})?"):
            result = self.db.execute_query("DELETE FROM course WHERE course_id = %s", (course_id,))
            if result is True:
                messagebox.showinfo("Успех", "Курс удален.")
                self.load_courses()
            elif result == '23503':
                messagebox.showerror("Ошибка удаления", "Невозможно удалить курс, так как на него поданы заявления.")
            else:
                messagebox.showerror("Ошибка", "Произошла неизвестная ошибка при удалении.")

    def delete_student(self):
        selected_item = self.students_table.focus()
        if not selected_item:
            messagebox.showwarning("Внимание", "Выберите слушателя для удаления.");
            return

        student_id = self.students_table.item(selected_item)['values'][0]
        if messagebox.askyesno("Подтверждение", f"Вы уверены, что хотите удалить слушателя (ID: {student_id})?"):
            result = self.db.execute_query("DELETE FROM student WHERE student_id = %s", (student_id,))
            if result is True:
                messagebox.showinfo("Успех", "Слушатель удален.")
                self.load_all_data()
            elif result == '23503':
                messagebox.showerror("Ошибка удаления",
                                     "Невозможно удалить слушателя, так как у него есть поданные заявления.")
            else:
                messagebox.showerror("Ошибка", "Произошла неизвестная ошибка при удалении.")

    # --- ОТЧЕТЫ И УТИЛИТЫ ---
    def generate_price_list(self):
        start_date = self.price_start_date.get_date().strftime("%Y-%m-%d")
        end_date = self.price_end_date.get_date().strftime("%Y-%m-%d")
        prices = self.db.execute_query(
            "SELECT name, hours, price FROM course WHERE start_date BETWEEN %s AND %s ORDER BY name",
            (start_date, end_date))
        self.reports_table.delete(*self.reports_table.get_children())
        self.reports_table["columns"] = ("Название курса", "Часы", "Цена")
        for col in self.reports_table["columns"]: self.reports_table.heading(col, text=col)
        if prices and isinstance(prices, list):
            for price in prices: self.reports_table.insert("", "end", values=price)

    def generate_students_report(self):
        year = datetime.now().year
        students = self.db.execute_query("""
            SELECT c.name, st.surname || ' ' || st.firstname
            FROM course c JOIN statement s ON c.course_id = s.course_id AND EXTRACT(YEAR FROM s.start_date) = %s
            JOIN student st ON s.student_id = st.student_id ORDER BY c.name, st.surname
        """, (year,))
        self.reports_table.delete(*self.reports_table.get_children())
        self.reports_table["columns"] = ("Курс", "Слушатель")
        for col in self.reports_table["columns"]: self.reports_table.heading(col, text=col)
        if students and isinstance(students, list):
            for student in students: self.reports_table.insert("", "end", values=student)

    def generate_teachers_hours_report(self):
        year = datetime.now().year
        hours = self.db.execute_query("""
            SELECT t.surname || ' ' || t.firstname, c.name, c.hours
            FROM teacher t JOIN course c ON t.teacher_id = c.teacher_id
            WHERE EXTRACT(YEAR FROM c.start_date) = %s ORDER BY t.surname, c.name
        """, (year,))
        self.reports_table.delete(*self.reports_table.get_children())
        self.reports_table["columns"] = ("Преподаватель", "Курс", "Часы")
        for col in self.reports_table["columns"]: self.reports_table.heading(col, text=col)
        if hours and isinstance(hours, list):
            for hour in hours: self.reports_table.insert("", "end", values=hour)

    def update_statement_dates(self, selected_course_name):
        if not selected_course_name:
            self.statement_start_date_combo.configure(values=[], state="disabled")
            self.statement_start_date_combo.set("")
            return
        dates = [c[5].strftime('%Y-%m-%d') for c in self.all_courses_data if c[1] == selected_course_name]
        if dates:
            self.statement_start_date_combo.configure(values=dates, state="readonly")
            self.statement_start_date_combo.set(dates[0])
        else:
            self.statement_start_date_combo.configure(values=[], state="disabled")
            self.statement_start_date_combo.set("Нет дат")

    def open_change_price_window(self):
        change_window = ctk.CTkToplevel(self)
        change_window.title("Изменить цены")
        change_window.geometry("400x200")
        change_window.resizable(False, False)
        label = ctk.CTkLabel(change_window, text="Введите новую цену для ВСЕХ курсов:", font=("Arial", 14))
        label.pack(pady=20)
        entry = ctk.CTkEntry(change_window, placeholder_text="Новая цена")
        entry.pack(pady=10)

        def apply_change():
            try:
                new_price = float(entry.get().strip())
            except ValueError:
                messagebox.showerror("Ошибка", "Введите корректное число."); return
            if new_price <= 0: messagebox.showerror("Ошибка", "Цена должна быть положительным числом."); return
            if self.db.execute_query("UPDATE course SET price = %s", (new_price,)):
                messagebox.showinfo("Успех", f"Цены обновлены.")
                self.load_courses()
                change_window.destroy()
            else:
                messagebox.showerror("Ошибка", "Не удалось обновить цены.")

        ctk.CTkButton(change_window, text="Применить", command=apply_change).pack(pady=10)

    def clear_teacher_form(self):
        self.teacher_surname.delete(0, 'end')
        self.teacher_firstname.delete(0, 'end')
        self.teacher_father.delete(0, 'end')
        self.teacher_education.delete(0, 'end')
        self.teacher_category.set("первая")

    def clear_course_form(self):
        for widget in self.course_widgets.values():
            if isinstance(widget, ctk.CTkEntry): widget.delete(0, 'end')
        self.course_start_date.set_date(date.today())
        self.course_end_date.set_date(date.today())

    def clear_student_form(self):
        self.student_surname.delete(0, 'end')
        self.student_firstname.delete(0, 'end')
        self.student_father.delete(0, 'end')


# --- ЗАПУСК ПРИЛОЖЕНИЯ ---
def main():
    """Главная функция для запуска приложения."""
    role_window = RoleSelectionWindow()
    role_window.mainloop()
    if role_window.role:
        app = CoursesApp(role=role_window.role)
        app.mainloop()


if __name__ == '__main__':
    main()