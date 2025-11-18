import sys
import psycopg2
import customtkinter as ctk
from tkinter import ttk, messagebox
from datetime import datetime, date
from tkcalendar import DateEntry

# Настройка внешнего вида
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class DatabaseManager:
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
            messagebox.showerror("Database Error", f"Could not connect to database: {str(e)}")

    def execute_query(self, query, params=None):
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(query, params)
                if query.strip().upper().startswith('SELECT'):
                    return cursor.fetchall()
                else:
                    self.connection.commit()
                    return True
        except Exception as e:
            print(f"Query error: {e}")
            return None


class RoleSelectionWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Выбор роли")
        self.geometry("400x200")
        self.resizable(False, False)
        self.role = None

        label = ctk.CTkLabel(self, text="Выберите роль для входа:", font=("Arial", 16))
        label.pack(pady=20)

        admin_btn = ctk.CTkButton(
            self,
            text="Администратор",
            command=lambda: self.select_role("admin"),
            width=200,
            height=40
        )
        admin_btn.pack(pady=10)

        user_btn = ctk.CTkButton(
            self,
            text="Пользователь",
            command=lambda: self.select_role("user"),
            width=200,
            height=40,
            fg_color="gray"
        )
        user_btn.pack(pady=10)

    def select_role(self, role):
        self.role = role
        self.destroy()  # Закрываем окно выбора


class UserInputWindow(ctk.CTkToplevel):
    def __init__(self, db_manager):
        super().__init__()
        self.db = db_manager
        self.title("Ввод данных слушателя")
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
        self.father = ctk.CTkEntry(form_frame, placeholder_text="Отчество")
        self.father.grid(row=2, column=1, sticky="ew", padx=5, pady=5)

        button_frame = ctk.CTkFrame(self)
        button_frame.pack(fill="x", padx=20, pady=10)

        submit_btn = ctk.CTkButton(button_frame, text="Продолжить", command=self.check_student)
        submit_btn.pack(pady=10)

    def check_student(self):
        surname = self.surname.get().strip()
        firstname = self.firstname.get().strip()
        father = self.father.get().strip()

        if not surname or not firstname:
            messagebox.showwarning("Ошибка", "Фамилия и имя обязательны!")
            return

        # Проверяем, существует ли слушатель
        student = self.db.execute_query(
            "SELECT student_id FROM student WHERE surname = %s AND firstname = %s AND father = %s",
            (surname, firstname, father)
        )

        if student:
            # Слушатель найден — проверяем статус последнего заявления
            student_id = student[0][0]
            stmt = self.db.execute_query(
                "SELECT course_id, start_date FROM statement WHERE student_id = %s ORDER BY statement_id DESC LIMIT 1",
                (student_id,)
            )
            if stmt:
                course_id = stmt[0][0]
                course = self.db.execute_query("SELECT name FROM course WHERE course_id = %s", (course_id,))
                if course:
                    messagebox.showinfo("Статус заявления", f"Вы подали заявление на курс: {course[0][0]}")
                else:
                    messagebox.showinfo("Статус заявления", "Заявление подано, но курс не найден.")
            else:
                messagebox.showinfo("Статус заявления", "Заявление не подано.")
        else:
            # Слушатель не найден — запрашиваем курс и дату
            self.ask_course_and_date(surname, firstname, father)

    def ask_course_and_date(self, surname, firstname, father):
        self.withdraw()  # Скрываем текущее окно

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
        date_entry = DateEntry(
            form_frame,
            width=12,
            background='darkblue',
            foreground='white',
            borderwidth=2,
            date_pattern='yyyy-mm-dd',
            locale='ru_RU'
        )
        date_entry.grid(row=1, column=1, sticky="ew", padx=5, pady=5)

        # Загружаем курсы
        courses = self.db.execute_query("SELECT course_id, name FROM course")
        if courses:
            course_names = [c[1] for c in courses]
            course_combo.configure(values=course_names)
            course_combo.set(course_names[0] if course_names else "Нет курсов")
        else:
            course_combo.set("Нет доступных курсов")

        def submit():
            course_name = course_combo.get()
            start_date = date_entry.get_date().strftime("%Y-%m-%d")

            if not course_name or not start_date:
                messagebox.showwarning("Ошибка", "Выберите курс и дату.")
                return

            # Получаем ID курса
            course_id = None
            for c in courses:
                if c[1] == course_name:
                    course_id = c[0]
                    break

            if not course_id:
                messagebox.showerror("Ошибка", "Курс не найден.")
                return

            # Добавляем слушателя
            success = self.db.execute_query(
                "INSERT INTO student (surname, firstname, father) VALUES (%s, %s, %s)",
                (surname, firstname, father)
            )
            if not success:
                messagebox.showerror("Ошибка", "Не удалось добавить слушателя.")
                return

            # Получаем ID слушателя
            student = self.db.execute_query(
                "SELECT student_id FROM student WHERE surname = %s AND firstname = %s AND father = %s",
                (surname, firstname, father)
            )
            if not student:
                messagebox.showerror("Ошибка", "Не удалось получить ID слушателя.")
                return

            student_id = student[0][0]

            # Создаём заявление
            success = self.db.execute_query(
                "INSERT INTO statement (student_id, course_id, start_date) VALUES (%s, %s, %s)",
                (student_id, course_id, start_date)
            )
            if success:
                messagebox.showinfo("Успех", "Заявление подано успешно!")
                course_window.destroy()
                self.destroy()
            else:
                messagebox.showerror("Ошибка", "Не удалось подать заявление.")

        button_frame = ctk.CTkFrame(course_window)
        button_frame.pack(fill="x", padx=20, pady=10)

        submit_btn = ctk.CTkButton(button_frame, text="Подать заявление", command=submit)
        submit_btn.pack(pady=10)


class CoursesApp(ctk.CTk):
    def __init__(self, role="admin"):
        super().__init__()
        self.role = role
        self.db = DatabaseManager()
        if self.role == "user":
            # Открываем окно ввода данных для пользователя
            self.user_input_window = UserInputWindow(self.db)
        else:
            # Для администратора — обычный интерфейс
            self.init_ui()
            self.apply_role_restrictions()

    def apply_role_restrictions(self):
        """Ограничиваем доступ к вкладкам в зависимости от роли"""
        if self.role == "user":
            tabs_to_hide = ["Преподаватели", "Курсы", "Слушатели", "Заявления", "Договоры"]
            for tab in tabs_to_hide:
                self.tabview.delete(tab)
            self.tabview.set("Отчеты")

    def init_ui(self):
        self.title("Система автоматизации курсов повышения квалификации")
        self.geometry("1400x800")

        # Увеличиваем шрифт в таблицах
        style = ttk.Style()
        style.configure("Treeview", font=("Arial", 14))
        style.configure("Treeview.Heading", font=("Arial", 16, "bold"))

        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=20, pady=20)

        self.teachers_tab = self.tabview.add("Преподаватели")
        self.courses_tab = self.tabview.add("Курсы")
        self.students_tab = self.tabview.add("Слушатели")
        self.statements_tab = self.tabview.add("Заявления")
        self.contracts_tab = self.tabview.add("Договоры")
        self.reports_tab = self.tabview.add("Отчеты")

        self.setup_teachers_tab()
        self.setup_courses_tab()
        self.setup_students_tab()
        self.setup_statements_tab()
        self.setup_contracts_tab()
        self.setup_reports_tab()

        self.load_teachers()
        self.load_courses()
        self.load_students()
        self.load_statements()
        self.load_contracts()

    def setup_teachers_tab(self):
        main_frame = ctk.CTkFrame(self.teachers_tab)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        form_frame = ctk.CTkFrame(main_frame)
        form_frame.pack(fill="x", padx=10, pady=10)
        form_frame.columnconfigure(1, weight=1)

        ctk.CTkLabel(form_frame, text="Фамилия:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.teacher_surname = ctk.CTkEntry(form_frame, placeholder_text="Введите фамилию")
        self.teacher_surname.grid(row=0, column=1, sticky="ew", padx=5, pady=5)

        ctk.CTkLabel(form_frame, text="Имя:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.teacher_firstname = ctk.CTkEntry(form_frame, placeholder_text="Введите имя")
        self.teacher_firstname.grid(row=1, column=1, sticky="ew", padx=5, pady=5)

        ctk.CTkLabel(form_frame, text="Отчество:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        self.teacher_father = ctk.CTkEntry(form_frame, placeholder_text="Введите отчество")
        self.teacher_father.grid(row=2, column=1, sticky="ew", padx=5, pady=5)

        ctk.CTkLabel(form_frame, text="Образование:").grid(row=3, column=0, sticky="w", padx=5, pady=5)
        self.teacher_education = ctk.CTkEntry(form_frame, placeholder_text="Введите образование")
        self.teacher_education.grid(row=3, column=1, sticky="ew", padx=5, pady=5)

        ctk.CTkLabel(form_frame, text="Категория:").grid(row=4, column=0, sticky="w", padx=5, pady=5)
        self.teacher_category = ctk.CTkComboBox(form_frame, values=["первая", "вторая", "высшая"])
        self.teacher_category.grid(row=4, column=1, sticky="ew", padx=5, pady=5)

        button_frame = ctk.CTkFrame(form_frame)
        button_frame.grid(row=5, column=0, columnspan=2, sticky="ew", padx=5, pady=10)

        add_btn = ctk.CTkButton(button_frame, text="Добавить преподавателя", command=self.add_teacher)
        add_btn.pack(side="left", padx=5)

        clear_btn = ctk.CTkButton(button_frame, text="Очистить форму", command=self.clear_teacher_form, fg_color="gray")
        clear_btn.pack(side="left", padx=5)

        table_frame = ctk.CTkFrame(main_frame)
        table_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.teachers_table = ttk.Treeview(
            table_frame,
            columns=("ID", "Фамилия", "Имя", "Отчество", "Образование", "Категория"),
            show="headings"
        )

        for col in self.teachers_table["columns"]:
            self.teachers_table.heading(col, text=col)
            self.teachers_table.column(col, width=100)

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.teachers_table.yview)
        self.teachers_table.configure(yscrollcommand=scrollbar.set)

        self.teachers_table.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def setup_courses_tab(self):
        main_frame = ctk.CTkFrame(self.courses_tab)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        form_frame = ctk.CTkFrame(main_frame)
        form_frame.pack(fill="x", padx=10, pady=10)

        for i in range(9):
            form_frame.columnconfigure(i % 3, weight=1)

        labels = ["Название:", "Часы:", "Цена:", "Мин. студентов:", "Макс. студентов:", "Преподаватель:"]
        self.course_widgets = {}

        for i, label in enumerate(labels):
            row = i // 3
            col = (i % 3) * 2
            ctk.CTkLabel(form_frame, text=label).grid(row=row, column=col, sticky="w", padx=5, pady=5)

            if label == "Преподаватель:":
                widget = ctk.CTkComboBox(form_frame)
            else:
                widget = ctk.CTkEntry(form_frame)

            widget.grid(row=row, column=col + 1, sticky="ew", padx=5, pady=5)
            self.course_widgets[label] = widget

        ctk.CTkLabel(form_frame, text="Дата начала:").grid(row=3, column=0, sticky="w", padx=5, pady=5)
        self.course_start_date = DateEntry(
            form_frame,
            width=12,
            background='darkblue',
            foreground='white',
            borderwidth=2,
            date_pattern='yyyy-mm-dd',
            locale='ru_RU'
        )
        self.course_start_date.grid(row=3, column=1, sticky="ew", padx=5, pady=5)

        ctk.CTkLabel(form_frame, text="Дата окончания:").grid(row=3, column=2, sticky="w", padx=5, pady=5)
        self.course_end_date = DateEntry(
            form_frame,
            width=12,
            background='darkblue',
            foreground='white',
            borderwidth=2,
            date_pattern='yyyy-mm-dd',
            locale='ru_RU'
        )
        self.course_end_date.grid(row=3, column=3, sticky="ew", padx=5, pady=5)

        button_frame = ctk.CTkFrame(form_frame)
        button_frame.grid(row=4, column=0, columnspan=4, sticky="ew", padx=5, pady=10)

        add_btn = ctk.CTkButton(button_frame, text="Добавить курс", command=self.add_course)
        add_btn.pack(side="left", padx=5)

        clear_btn = ctk.CTkButton(button_frame, text="Очистить форму", command=self.clear_course_form, fg_color="gray")
        clear_btn.pack(side="left", padx=5)

        table_frame = ctk.CTkFrame(main_frame)
        table_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.courses_table = ttk.Treeview(
            table_frame,
            columns=("ID", "Название", "Часы", "Цена", "Мин", "Макс", "Начало", "Окончание", "Преподаватель"),
            show="headings"
        )

        for col in self.courses_table["columns"]:
            self.courses_table.heading(col, text=col)
            self.courses_table.column(col, width=100)

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.courses_table.yview)
        self.courses_table.configure(yscrollcommand=scrollbar.set)

        self.courses_table.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def setup_students_tab(self):
        main_frame = ctk.CTkFrame(self.students_tab)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        form_frame = ctk.CTkFrame(main_frame)
        form_frame.pack(fill="x", padx=10, pady=10)
        form_frame.columnconfigure(1, weight=1)

        ctk.CTkLabel(form_frame, text="Фамилия:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.student_surname = ctk.CTkEntry(form_frame, placeholder_text="Введите фамилию")
        self.student_surname.grid(row=0, column=1, sticky="ew", padx=5, pady=5)

        ctk.CTkLabel(form_frame, text="Имя:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.student_firstname = ctk.CTkEntry(form_frame, placeholder_text="Введите имя")
        self.student_firstname.grid(row=1, column=1, sticky="ew", padx=5, pady=5)

        ctk.CTkLabel(form_frame, text="Отчество:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        self.student_father = ctk.CTkEntry(form_frame, placeholder_text="Введите отчество")
        self.student_father.grid(row=2, column=1, sticky="ew", padx=5, pady=5)

        button_frame = ctk.CTkFrame(form_frame)
        button_frame.grid(row=3, column=0, columnspan=2, sticky="ew", padx=5, pady=10)

        add_btn = ctk.CTkButton(button_frame, text="Добавить слушателя", command=self.add_student)
        add_btn.pack(side="left", padx=5)

        clear_btn = ctk.CTkButton(button_frame, text="Очистить форму", command=self.clear_student_form, fg_color="gray")
        clear_btn.pack(side="left", padx=5)

        table_frame = ctk.CTkFrame(main_frame)
        table_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.students_table = ttk.Treeview(table_frame, columns=("ID", "Фамилия", "Имя", "Отчество"), show="headings")

        for col in self.students_table["columns"]:
            self.students_table.heading(col, text=col)
            self.students_table.column(col, width=100)

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.students_table.yview)
        self.students_table.configure(yscrollcommand=scrollbar.set)

        self.students_table.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def setup_statements_tab(self):
        main_frame = ctk.CTkFrame(self.statements_tab)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        form_frame = ctk.CTkFrame(main_frame)
        form_frame.pack(fill="x", padx=10, pady=10)
        form_frame.columnconfigure(1, weight=1)

        ctk.CTkLabel(form_frame, text="Слушатель:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.statement_student = ctk.CTkComboBox(form_frame)
        self.statement_student.grid(row=0, column=1, sticky="ew", padx=5, pady=5)

        ctk.CTkLabel(form_frame, text="Курс:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.statement_course = ctk.CTkComboBox(form_frame)
        self.statement_course.grid(row=1, column=1, sticky="ew", padx=5, pady=5)

        ctk.CTkLabel(form_frame, text="Дата начала:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        self.statement_start_date = DateEntry(
            form_frame,
            width=12,
            background='darkblue',
            foreground='white',
            borderwidth=2,
            date_pattern='yyyy-mm-dd',
            locale='ru_RU'
        )
        self.statement_start_date.grid(row=2, column=1, sticky="ew", padx=5, pady=5)

        button_frame = ctk.CTkFrame(form_frame)
        button_frame.grid(row=3, column=0, columnspan=2, sticky="ew", padx=5, pady=10)

        add_btn = ctk.CTkButton(button_frame, text="Подать заявление", command=self.add_statement)
        add_btn.pack(side="left", padx=5)

        table_frame = ctk.CTkFrame(main_frame)
        table_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.statements_table = ttk.Treeview(table_frame, columns=("ID", "Слушатель", "Курс", "Дата начала"), show="headings")

        for col in self.statements_table["columns"]:
            self.statements_table.heading(col, text=col)
            self.statements_table.column(col, width=100)

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.statements_table.yview)
        self.statements_table.configure(yscrollcommand=scrollbar.set)

        self.statements_table.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def setup_contracts_tab(self):
        main_frame = ctk.CTkFrame(self.contracts_tab)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        button_frame = ctk.CTkFrame(main_frame)
        button_frame.pack(fill="x", padx=10, pady=10)

        generate_btn = ctk.CTkButton(button_frame, text="Сформировать договор", command=self.create_contract)
        generate_btn.pack(side="left", padx=5)

        refresh_btn = ctk.CTkButton(button_frame, text="Обновить данные", command=self.load_contracts, fg_color="green")
        refresh_btn.pack(side="left", padx=5)

        table_frame = ctk.CTkFrame(main_frame)
        table_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.contracts_table = ttk.Treeview(
            table_frame,
            columns=("ID договора", "ID заявления", "Слушатель", "Курс", "Дата договора"),
            show="headings"
        )

        for col in self.contracts_table["columns"]:
            self.contracts_table.heading(col, text=col)
            self.contracts_table.column(col, width=120)

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.contracts_table.yview)
        self.contracts_table.configure(yscrollcommand=scrollbar.set)

        self.contracts_table.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def setup_reports_tab(self):
        main_frame = ctk.CTkFrame(self.reports_tab)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Фрейм для кнопок отчетов
        reports_frame = ctk.CTkFrame(main_frame)
        reports_frame.pack(fill="x", padx=10, pady=10)

        # Прайс-лист
        price_frame = ctk.CTkFrame(reports_frame)
        price_frame.pack(fill="x", padx=5, pady=5)

        ctk.CTkLabel(price_frame, text="Прайс-лист за период:").pack(side="left", padx=5)

        self.price_start_date = DateEntry(
            price_frame,
            width=12,
            background='darkblue',
            foreground='white',
            borderwidth=2,
            date_pattern='yyyy-mm-dd',
            locale='ru_RU'
        )
        self.price_start_date.pack(side="left", padx=5)

        self.price_end_date = DateEntry(
            price_frame,
            width=12,
            background='darkblue',
            foreground='white',
            borderwidth=2,
            date_pattern='yyyy-mm-dd',
            locale='ru_RU'
        )
        self.price_end_date.pack(side="left", padx=5)

        price_btn = ctk.CTkButton(price_frame, text="Сформировать прайс-лист", command=self.generate_price_list)
        price_btn.pack(side="left", padx=5)

        # Кнопка изменения цен
        change_price_btn = ctk.CTkButton(price_frame, text="Изменить цены", command=self.open_change_price_window)
        change_price_btn.pack(side="left", padx=5)

        # Другие отчеты
        other_reports_frame = ctk.CTkFrame(reports_frame)
        other_reports_frame.pack(fill="x", padx=5, pady=5)

        students_btn = ctk.CTkButton(other_reports_frame, text="Состав слушателей по курсам",
                                     command=self.generate_students_report)
        students_btn.pack(side="left", padx=5)

        hours_btn = ctk.CTkButton(other_reports_frame, text="Часы преподавателей",
                                  command=self.generate_teachers_hours_report)
        hours_btn.pack(side="left", padx=5)

        # Таблица для отчетов
        table_frame = ctk.CTkFrame(main_frame)
        table_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.reports_table = ttk.Treeview(table_frame, show="headings")

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.reports_table.yview)
        self.reports_table.configure(yscrollcommand=scrollbar.set)

        self.reports_table.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def open_change_price_window(self):
        # Создаём новое окно для ввода новой цены
        change_window = ctk.CTkToplevel(self)
        change_window.title("Изменить цены")
        change_window.geometry("400x200")
        change_window.resizable(False, False)

        label = ctk.CTkLabel(change_window, text="Введите новую цену для всех курсов:", font=("Arial", 14))
        label.pack(pady=20)

        entry = ctk.CTkEntry(change_window, placeholder_text="Новая цена")
        entry.pack(pady=10)

        def apply_change():
            try:
                new_price = float(entry.get().strip())
                if new_price <= 0:
                    messagebox.showerror("Ошибка", "Цена должна быть положительным числом.")
                    return
            except ValueError:
                messagebox.showerror("Ошибка", "Введите корректное число.")
                return

            # Обновляем цены в базе
            success = self.db.execute_query(
                "UPDATE course SET price = %s",
                (new_price,)
            )

            if success:
                messagebox.showinfo("Успех", f"Цены обновлены на {new_price}")
                change_window.destroy()
            else:
                messagebox.showerror("Ошибка", "Не удалось обновить цены.")

        button = ctk.CTkButton(change_window, text="Применить", command=apply_change)
        button.pack(pady=10)

    def load_teachers(self):
        teachers = self.db.execute_query("SELECT * FROM teacher ORDER BY teacher_id")
        if hasattr(self, 'teachers_table'):
            self.teachers_table.delete(*self.teachers_table.get_children())

        if teachers:
            for teacher in teachers:
                if hasattr(self, 'teachers_table'):
                    self.teachers_table.insert("", "end", values=teacher)

                if hasattr(self, 'course_widgets'):
                    teacher_name = f"{teacher[1]} {teacher[2]}"
                    current_values = list(self.course_widgets["Преподаватель:"].cget("values") or [])
                    if teacher_name not in current_values:
                        current_values.append(teacher_name)
                        self.course_widgets["Преподаватель:"].configure(values=current_values)

    def load_courses(self):
        courses = self.db.execute_query("""
            SELECT c.*, t.surname || ' ' || t.firstname 
            FROM course c 
            JOIN teacher t ON c.teacher_id = t.teacher_id 
            ORDER BY c.course_id
        """)
        if hasattr(self, 'courses_table'):
            self.courses_table.delete(*self.courses_table.get_children())

        if hasattr(self, 'statement_course'):
            self.statement_course.set("")
            self.statement_course.configure(values=[])

        if courses:
            course_names = []
            for course in courses:
                if hasattr(self, 'courses_table'):
                    self.courses_table.insert("", "end", values=course)
                course_names.append(course[1])

            if hasattr(self, 'statement_course'):
                self.statement_course.configure(values=course_names)

    def load_students(self):
        students = self.db.execute_query("SELECT * FROM student ORDER BY student_id")
        if hasattr(self, 'students_table'):
            self.students_table.delete(*self.students_table.get_children())

        if hasattr(self, 'statement_student'):
            self.statement_student.set("")
            self.statement_student.configure(values=[])

        if students:
            student_names = []
            for student in students:
                if hasattr(self, 'students_table'):
                    self.students_table.insert("", "end", values=student)
                student_name = f"{student[1]} {student[2]}"
                student_names.append(student_name)

            if hasattr(self, 'statement_student'):
                self.statement_student.configure(values=student_names)

    def load_statements(self):
        statements = self.db.execute_query("""
            SELECT s.statement_id, st.surname || ' ' || st.firstname, c.name, s.start_date
            FROM statement s
            JOIN student st ON s.student_id = st.student_id
            JOIN course c ON s.course_id = c.course_id
            ORDER BY s.statement_id
        """)
        if hasattr(self, 'statements_table'):
            self.statements_table.delete(*self.statements_table.get_children())

        if statements:
            for stmt in statements:
                if hasattr(self, 'statements_table'):
                    self.statements_table.insert("", "end", values=stmt)

    def load_contracts(self):
        contracts = self.db.execute_query("""
            SELECT co.contract_id, co.statement_id, 
                   st.surname || ' ' || st.firstname, c.name, co.contract_date
            FROM contract co
            JOIN statement s ON co.statement_id = s.statement_id
            JOIN student st ON s.student_id = st.student_id
            JOIN course c ON s.course_id = c.course_id
            ORDER BY co.contract_id
        """)
        if hasattr(self, 'contracts_table'):
            self.contracts_table.delete(*self.contracts_table.get_children())

        if contracts:
            for contract in contracts:
                if hasattr(self, 'contracts_table'):
                    self.contracts_table.insert("", "end", values=contract)

    def add_teacher(self):
        surname = self.teacher_surname.get().strip()
        firstname = self.teacher_firstname.get().strip()
        father = self.teacher_father.get().strip()
        education = self.teacher_education.get().strip()
        category = self.teacher_category.get()

        if not surname or not firstname or not education:
            messagebox.showwarning("Ошибка", "Заполните обязательные поля: Фамилия, Имя, Образование")
            return

        success = self.db.execute_query(
            "INSERT INTO teacher (surname, firstname, father, education, category) VALUES (%s, %s, %s, %s, %s)",
            (surname, firstname, father, education, category)
        )

        if success:
            self.load_teachers()
            self.clear_teacher_form()
            messagebox.showinfo("Успех", "Преподаватель добавлен")
        else:
            messagebox.showerror("Ошибка", "Не удалось добавить преподавателя")

    def add_course(self):
        try:
            name = self.course_widgets["Название:"].get().strip()
            hours = int(self.course_widgets["Часы:"].get())
            price = float(self.course_widgets["Цена:"].get())
            min_students = int(self.course_widgets["Мин. студентов:"].get())
            max_students = int(self.course_widgets["Макс. студентов:"].get())
            start_date = self.course_start_date.get_date().strftime("%Y-%m-%d")
            end_date = self.course_end_date.get_date().strftime("%Y-%m-%d")
            teacher_name = self.course_widgets["Преподаватель:"].get()

            teacher_parts = teacher_name.split()
            if len(teacher_parts) >= 2:
                teacher = self.db.execute_query(
                    "SELECT teacher_id FROM teacher WHERE surname = %s AND firstname = %s",
                    (teacher_parts[0], teacher_parts[1])
                )
                if teacher:
                    teacher_id = teacher[0][0]
                else:
                    messagebox.showerror("Ошибка", "Преподаватель не найден")
                    return
            else:
                messagebox.showerror("Ошибка", "Неверный формат имени преподавателя")
                return

            if not all([name, start_date, end_date]):
                messagebox.showwarning("Ошибка", "Заполните все обязательные поля")
                return

            success = self.db.execute_query(
                """INSERT INTO course (name, hours, price, min_students, max_students, start_date, end_date, teacher_id) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                (name, hours, price, min_students, max_students, start_date, end_date, teacher_id)
            )

            if success:
                self.load_courses()
                self.clear_course_form()
                messagebox.showinfo("Успех", "Курс добавлен")
            else:
                messagebox.showerror("Ошибка", "Не удалось добавить курс")

        except ValueError as e:
            messagebox.showerror("Ошибка", f"Проверьте правильность числовых полей: {e}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Произошла ошибка: {e}")

    def add_student(self):
        surname = self.student_surname.get().strip()
        firstname = self.student_firstname.get().strip()
        father = self.student_father.get().strip()

        if not surname or not firstname:
            messagebox.showwarning("Ошибка", "Заполните Фамилию и Имя")
            return

        success = self.db.execute_query(
            "INSERT INTO student (surname, firstname, father) VALUES (%s, %s, %s)",
            (surname, firstname, father)
        )

        if success:
            self.load_students()
            self.clear_student_form()
            messagebox.showinfo("Успех", "Слушатель добавлен")
        else:
            messagebox.showerror("Ошибка", "Не удалось добавить слушателя")

    def add_statement(self):
        student_name = self.statement_student.get()
        course_name = self.statement_course.get()
        start_date = self.statement_start_date.get_date().strftime("%Y-%m-%d")

        if not student_name or not course_name or not start_date:
            messagebox.showwarning("Ошибка", "Заполните все поля")
            return

        student_parts = student_name.split()
        student = self.db.execute_query(
            "SELECT student_id FROM student WHERE surname = %s AND firstname = %s",
            (student_parts[0], student_parts[1])
        )

        course = self.db.execute_query(
            "SELECT course_id FROM course WHERE name = %s",
            (course_name,)
        )

        if not student or not course:
            messagebox.showerror("Ошибка", "Слушатель или курс не найден")
            return

        student_id = student[0][0]
        course_id = course[0][0]

        success = self.db.execute_query(
            "INSERT INTO statement (student_id, course_id, start_date) VALUES (%s, %s, %s)",
            (student_id, course_id, start_date)
        )

        if success:
            self.load_statements()
            messagebox.showinfo("Успех", "Заявление подано")
        else:
            messagebox.showerror("Ошибка", "Не удалось подать заявление")

    def create_contract(self):
        last_statement = self.db.execute_query(
            "SELECT statement_id FROM statement ORDER BY statement_id DESC LIMIT 1"
        )

        if not last_statement:
            messagebox.showwarning("Ошибка", "Нет заявлений для формирования договора")
            return

        statement_id = last_statement[0][0]

        existing = self.db.execute_query(
            "SELECT contract_id FROM contract WHERE statement_id = %s",
            (statement_id,)
        )

        if existing:
            messagebox.showinfo("Информация", "Договор для последнего заявления уже существует")
            return

        success = self.db.execute_query(
            "INSERT INTO contract (statement_id) VALUES (%s)",
            (statement_id,)
        )

        if success:
            self.load_contracts()
            messagebox.showinfo("Успех", "Договор сформирован")
        else:
            messagebox.showerror("Ошибка", "Не удалось сформировать договор")

    def generate_price_list(self):
        start_date = self.price_start_date.get_date().strftime("%Y-%m-%d")
        end_date = self.price_end_date.get_date().strftime("%Y-%m-%d")

        prices = self.db.execute_query("""
            SELECT name, hours, price 
            FROM course 
            WHERE start_date BETWEEN %s AND %s 
            ORDER BY name
        """, (start_date, end_date))

        self.reports_table.delete(*self.reports_table.get_children())
        self.reports_table["columns"] = ("Название курса", "Часы", "Цена")

        for col in self.reports_table["columns"]:
            self.reports_table.heading(col, text=col)
            self.reports_table.column(col, width=150)

        if prices:
            for price in prices:
                self.reports_table.insert("", "end", values=price)

    def generate_students_report(self):
        year = datetime.now().year
        students = self.db.execute_query("""
            SELECT c.name, st.surname || ' ' || st.firstname
            FROM course c
            JOIN statement stm ON c.course_id = stm.course_id 
                AND EXTRACT(YEAR FROM stm.start_date) = %s
            JOIN student st ON stm.student_id = st.student_id
            ORDER BY c.name, st.surname
        """, (year,))

        self.reports_table.delete(*self.reports_table.get_children())
        self.reports_table["columns"] = ("Курс", "Слушатель")

        for col in self.reports_table["columns"]:
            self.reports_table.heading(col, text=col)
            self.reports_table.column(col, width=200)

        if students:
            for student in students:
                self.reports_table.insert("", "end", values=student)

    def generate_teachers_hours_report(self):
        year = datetime.now().year
        hours = self.db.execute_query("""
            SELECT t.surname || ' ' || t.firstname, c.name, c.hours
            FROM teacher t
            JOIN course c ON t.teacher_id = c.teacher_id
            WHERE EXTRACT(YEAR FROM c.start_date) = %s
            ORDER BY t.surname, c.name
        """, (year,))

        self.reports_table.delete(*self.reports_table.get_children())
        self.reports_table["columns"] = ("Преподаватель", "Курс", "Часы")

        for col in self.reports_table["columns"]:
            self.reports_table.heading(col, text=col)
            self.reports_table.column(col, width=150)

        if hours:
            for hour in hours:
                self.reports_table.insert("", "end", values=hour)

    def clear_teacher_form(self):
        self.teacher_surname.delete(0, 'end')
        self.teacher_firstname.delete(0, 'end')
        self.teacher_father.delete(0, 'end')
        self.teacher_education.delete(0, 'end')
        self.teacher_category.set("первая")

    def clear_course_form(self):
        for widget in self.course_widgets.values():
            if isinstance(widget, ctk.CTkEntry):
                widget.delete(0, 'end')
        today = date.today()
        self.course_start_date.set_date(today)
        self.course_end_date.set_date(today)

    def clear_student_form(self):
        self.student_surname.delete(0, 'end')
        self.student_firstname.delete(0, 'end')
        self.student_father.delete(0, 'end')


def main():
    role_window = RoleSelectionWindow()
    role_window.mainloop()

    if role_window.role is None:
        sys.exit()

    app = CoursesApp(role=role_window.role)
    app.mainloop()


if __name__ == '__main__':
    main()