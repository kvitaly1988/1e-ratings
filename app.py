import streamlit as st
import pandas as pd
from pathlib import Path

# Широкий макет, чтобы таблица была шире
st.set_page_config(page_title="Оценки — личный кабинет", page_icon="📘", layout="wide")

# === Конфигурация ===
# Впишите публичную ссылку Яндекс.Диска на файл с баллами (Excel).
# Оставьте пустым, чтобы читать локальный файл data/Students.xlsx.
STUDENTS_PUBLIC_URL = "https://disk.yandex.ru/i/UuZH50lxCEKh-g"  # например: https://disk.yandex.ru/d/XXXXXXXXXXX

# Пути по умолчанию (локально)
DATA_DIR = Path(__file__).parent / "data"
AUTH_PATH = DATA_DIR / "auth.xlsx"
STUDENTS_PATH = DATA_DIR / "Students.xlsx"

# === Стили: крупные поля ввода и крупный текст таблицы ===
st.markdown(
    """
    <style>
    /* Крупные поля ввода */
    div[data-baseweb="input"] input {
        font-size: 24px !important;
        padding: 16px 14px !important;
    }
    /* Крупные подписи к полям */
    label[class^="css-"], label[class*=" css-"] {
        font-size: 20px !important;
    }
    /* Крупные кнопки */
    button[kind="primary"], button[data-testid="baseButton-secondary"] {
        font-size: 20px !important;
        padding: 12px 20px !important;
    }
    /* Крупный текст в таблице */
    div[data-testid="stDataFrame"] * {
        font-size: 20px !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)



def load_data(students_public_url: str):
    import pandas as pd
    from io import BytesIO
    import requests

    # auth.xlsx — локально
    auth_df = pd.read_excel(AUTH_PATH, dtype=str).fillna("")

    # Students.xlsx — либо с Я.Диска, либо локально
    if students_public_url.strip():
        api_url = "https://cloud-api.yandex.net/v1/disk/public/resources/download"
        resp = requests.get(api_url, params={"public_key": students_public_url}, timeout=20)
        resp.raise_for_status()
        href = resp.json().get("href")
        if not href:
            raise RuntimeError("Яндекс.Диск API не вернул ссылку скачивания (href). Проверьте публичную ссылку.")
        file_resp = requests.get(href, timeout=60)
        file_resp.raise_for_status()
        students_df = pd.read_excel(BytesIO(file_resp.content), dtype=str).fillna("")
    else:
        students_df = pd.read_excel(STUDENTS_PATH, dtype=str).fillna("")

    # Нормализация колонок
    def norm_cols(df):
        mapping = {c: str(c).strip().lower() for c in df.columns}
        return df.rename(columns=mapping)

    return norm_cols(auth_df), norm_cols(students_df)



def find_col(df, candidates):
    cols = list(df.columns)
    for cand in candidates:
        if cand in cols:
            return cand
    # попытка без пробелов
    nospace = {c.replace(" ", ""): c for c in df.columns}
    for cand in candidates:
        if cand.replace(" ", "") in nospace:
            return nospace[cand.replace(" ", "")]
    return None


st.title("Личный кабинет ученика")
st.caption("Введите фамилию и пароль, чтобы увидеть ваши оценки.")

# Загружаем данные (либо локально, либо с Я.Диска — в зависимости от STUDENTS_PUBLIC_URL)
auth_df, students_df = load_data(STUDENTS_PUBLIC_URL)

# Определяем имена колонок
fam_col_auth = find_col(auth_df, ["фамилия", "surname", "last name"])
pwd_col = find_col(auth_df, ["пароль", "password"])
fam_col_students = find_col(students_df, ["фамилия", "surname", "last name"])
name_col_students = find_col(students_df, ["имя", "name", "first name"])

if fam_col_auth is None or pwd_col is None:
    st.error("В файле auth.xlsx должны быть колонки 'Фамилия' и 'Пароль'. Проверьте заголовки.")
    st.stop()

if fam_col_students is None or name_col_students is None:
    st.error("В файле Students.xlsx должны быть колонки 'Фамилия' и 'Имя'. Проверьте заголовки.")
    st.stop()

# --- Форма входа ---
with st.form("login", clear_on_submit=False):
    fam_input = st.text_input("Фамилия")
    pwd_input = st.text_input("Пароль", type="password")
    submitted = st.form_submit_button("Войти")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "current_fam" not in st.session_state:
    st.session_state.current_fam = ""


def try_login(fam, pwd):
    fam = (fam or "").strip()
    pwd = (pwd or "").strip()
    if not fam or not pwd:
        return False, "Введите и фамилию, и пароль."
    matches = auth_df[auth_df[fam_col_auth].str.strip().str.lower() == fam.lower()]
    if matches.empty:
        return False, "Пользователь с такой фамилией не найден."
    if (matches[pwd_col].astype(str).str.strip() == pwd).any():
        return True, ""
    return False, "Неверный пароль."


if submitted:
    ok, msg = try_login(fam_input, pwd_input)
    if ok:
        st.session_state.logged_in = True
        st.session_state.current_fam = fam_input.strip()
        st.success("Успешный вход.")
    else:
        st.session_state.logged_in = False
        st.session_state.current_fam = ""
        st.error(msg)

if st.session_state.logged_in:
    fam = st.session_state.current_fam
    st.divider()

    # Фильтруем строки по фамилии
    user_rows = students_df[students_df[fam_col_students].str.strip().str.lower() == fam.lower()].copy()

    # Заголовок: Ученик: Фамилия, Имя
    if not user_rows.empty and name_col_students in user_rows.columns:
        name_value = user_rows.iloc[0][name_col_students]
        st.subheader(f"Ученик: **{fam}, {name_value}**")
    else:
        st.subheader(f"Ученик: **{fam}**")

    if user_rows.empty:
        st.info("В Students.xlsx не найдено записей с этой фамилией.")
    else:
        # Ставим фамилию и имя первыми колонками
        fixed = [fam_col_students, name_col_students]
        other_cols = [c for c in user_rows.columns if c not in fixed]
        display_df = user_rows[fixed + other_cols]

        # Преобразуем заголовки-даты в формат дд.мм.гг
        new_cols = []
        for c in display_df.columns:
            try:
                parsed = pd.to_datetime(c, errors="raise")
                new_cols.append(parsed.strftime("%d.%m.%y"))
            except Exception:
                new_cols.append(c)
        display_df.columns = new_cols

        # Широкая таблица с крупным шрифтом
        st.dataframe(display_df, use_container_width=True, height=700)

        # Кнопки скачивания (оставила как было)
        csv = display_df.to_csv(index=False).encode("utf-8-sig")
        st.download_button("Скачать как CSV", data=csv, file_name=f"grades_{fam}.csv", mime="text/csv")

        xlsx_buf = pd.ExcelWriter("out.xlsx", engine="openpyxl")
        display_df.to_excel(xlsx_buf, index=False, sheet_name="Оценки")
        xlsx_buf.close()
        with open("out.xlsx", "rb") as f:
            st.download_button(
                "Скачать как Excel",
                data=f.read(),
                file_name=f"grades_{fam}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        Path("out.xlsx").unlink(missing_ok=True)

    with st.expander("Выйти"):
        if st.button("Выйти из аккаунта"):
            st.session_state.logged_in = False
            st.session_state.current_fam = ""
            st.rerun()
else:
    st.info("Пожалуйста, войдите, чтобы увидеть ваши данные.")
