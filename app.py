import streamlit as st
import pandas as pd
import os
import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import uuid

st.set_page_config(page_title="Calculadora de Ayuda", layout="wide")

# --- CONFIGURACIÓN GOOGLE SHEETS ---
SHEET_ID = "1f_s9z21hlyg3puVEpdMYIBow4GQdI8QhG__ABEJAwBI"
HOJA = "Tracker"

# --- FUNCIONES GOOGLE SHEETS ---
def conectar_sheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    client = gspread.authorize(creds)
    return client.open_by_key(SHEET_ID).worksheet(HOJA)

def guardar_o_actualizar_fila(fila, sheet, data, headers):
    try:
        id_index = headers.index("id")
    except ValueError:
        sheet.append_row(list(fila.values()))
        return

    for i, row in enumerate(data[1:], start=2):
        if row[id_index] == fila["id"]:
            valores_ordenados = [fila.get(header, "") for header in headers]
            sheet.update(f"A{i}:{chr(65+len(headers)-1)}{i}", [valores_ordenados])
            return

    # Si no se encuentra el ID, agregar al final
    sheet.append_row(list(fila.values()))

def eliminar_fila_por_id(id_a_eliminar, sheet):
    data = sheet.get_all_values()
    if not data:
        return
    header = data[0]
    if "id" not in header:
        return
    id_index = header.index("id")
    for i, row in enumerate(data[1:], start=2):
        if row[id_index] == id_a_eliminar:
            sheet.delete_rows(i)
            break

def cargar_datos_guardados(sheet):
    try:
        data = sheet.get_all_records(expected_headers=["id", "cartuchos", "yo_ayude", "me_ayudaron", "cct", "fecha", "total", "guardado"])
    except:
        data = []
    return data

# --- CONECTAR UNA SOLA VEZ ---
sheet = conectar_sheet()
sheet_data = sheet.get_all_values()
sheet_headers = sheet_data[0] if sheet_data else []

# --- SESIÓN ---
if "rows" not in st.session_state:
    st.session_state.rows = cargar_datos_guardados(sheet)

if "remove_row" not in st.session_state:
    st.session_state.remove_row = None

if "newly_added" not in st.session_state:
    st.session_state.newly_added = []

# --- OPCIONES ---
cirugias = ["No cirugía", "Manga", "Manga con Biparticion", "Minibypass", "Bypass en Y de Roux"]
valores_cirugia = {
    "No cirugía": 0,
    "Manga": 4000,
    "Manga con Biparticion": 6000,
    "Minibypass": 6000,
    "Bypass en Y de Roux": 6000
}

# --- RESET VISUAL ---
def reset_all():
    st.session_state.rows = []
    st.session_state.remove_row = None
    st.session_state.newly_added = []

st.button("🔄 Resetear Todo (visual)", on_click=reset_all)

# --- AGREGAR FILA ---
if st.button("➕ Agregar Fila"):
    new_id = str(uuid.uuid4())
    nueva_fila = {
        "id": new_id,
        "cartuchos": 0,
        "yo_ayude": "No cirugía",
        "me_ayudaron": "No cirugía",
        "cct": False,
        "fecha": datetime.date.today().isoformat(),
        "total": 0,
        "guardado": False
    }
    st.session_state.rows.append(nueva_fila)
    st.session_state.newly_added.append(new_id)
    st.rerun()

total = 0

# --- MOSTRAR FILAS EN APP ---
for i in range(len(st.session_state.rows)):
    row = st.session_state.rows[i]

    col1, col2, col3, col4, col5 = st.columns([1, 2, 2, 1, 0.5])

    with col1:
        cartuchos = st.selectbox(f"Cartuchos fila {i+1}", list(range(0, 11)), index=row["cartuchos"], key=f"cartuchos_{i}")

    with col2:
        if row["me_ayudaron"] != "No cirugía":
            yo_ayude = "No cirugía"
            st.markdown(f"Yo ayudé: `No cirugía`")
        else:
            yo_ayude = st.selectbox(
                f"Yo ayudé fila {i+1}",
                cirugias,
                index=cirugias.index(row["yo_ayude"]),
                key=f"yo_ayude_{i}"
            )

    with col3:
        if yo_ayude != "No cirugía":
            me_ayudaron = "No cirugía"
            st.markdown(f"Me ayudaron: `No cirugía`")
        else:
            me_ayudaron = st.selectbox(
                f"Me ayudaron fila {i+1}",
                cirugias,
                index=cirugias.index(row["me_ayudaron"]),
                key=f"me_ayudaron_{i}"
            )

    with col4:
        cct = st.toggle("CCT", value=row["cct"], key=f"cct_{i}")

    with col5:
        if st.button("➖", key=f"delete_button_{i}"):
            st.session_state.remove_row = i
            st.rerun()

    # --- CÁLCULO DEL TOTAL POR FILA ---
    subtotal = cartuchos * 1000
    if yo_ayude != "No cirugía":
        subtotal += valores_cirugia[yo_ayude]
        if cct:
            subtotal += 1000
    elif me_ayudaron != "No cirugía":
        subtotal -= valores_cirugia[me_ayudaron]
        if cct:
            subtotal -= 1000

    total += subtotal

    # Actualizar fila en memoria
    st.session_state.rows[i] = {
        "id": row["id"],
        "cartuchos": cartuchos,
        "yo_ayude": yo_ayude,
        "me_ayudaron": me_ayudaron,
        "cct": cct,
        "fecha": row["fecha"],
        "total": subtotal,
        "guardado": True
    }

    # Guardar o actualizar en Sheets (solo una lectura global por ejecución)
    guardar_o_actualizar_fila(st.session_state.rows[i], sheet, sheet_data, sheet_headers)

# --- ELIMINAR FILA DEL HISTORIAL Y VISTA ---
if st.session_state.remove_row is not None:
    index = st.session_state.remove_row
    if 0 <= index < len(st.session_state.rows):
        id_a_eliminar = st.session_state.rows[index]["id"]
        eliminar_fila_por_id(id_a_eliminar, sheet)
        st.session_state.rows.pop(index)
    st.session_state.remove_row = None
    st.rerun()

# --- TOTAL GLOBAL ---
st.markdown("---")
st.subheader(f"💰 Total: ${total:,}")