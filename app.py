from datetime import datetime
import os
import pandas as pd
import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials

st.set_page_config(
    page_title="Área Técnica - Inventario y Ventas", page_icon="📊", layout="wide"
)


# Configuración de la conexión a Google Sheets
@st.cache_resource
def init_connection():
  scope = [
      "https://spreadsheets.google.com/feeds",
      "https://www.googleapis.com/auth/drive",
  ]
  # Lee las credenciales desde los secretos de Streamlit (secrets.toml)
  creds_dict = dict(st.secrets["gcp_service_account"])
  creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
  client = gspread.authorize(creds)
  return client


try:
  client = init_connection()
  # Asegúrate de configurar tu 'sheet_key' en el archivo .streamlit/secrets.toml
  spreadsheet = client.open_by_key(st.secrets["sheet"]["sheet_key"])
except Exception as e:
  st.error(f"Error crítico al conectar con Google Sheets: {e}")
  st.stop()

st.title("📊 Área Técnica - Servicios y Soluciones Tecnológicas")
st.subheader("Sistema de Registro de Ventas e Inventario")

# Menú de navegación lateral
menu = st.sidebar.selectbox("Navegación", ["Registrar Venta", "Ver Inventario"])

if menu == "Registrar Venta":
  st.header("🛒 Registrar Nueva Venta")

  with st.form("form_venta"):
    producto = st.text_input("Nombre del Producto / Servicio")
    cantidad = st.number_input("Cantidad", min_value=1, value=1, step=1)
    precio_unitario = st.number_input(
        "Precio Venta Unitario", min_value=0.0, value=0.0, step=500.0
    )

    submitted = st.form_submit_button("Guardar en Google Sheets")

    if submitted:
      if producto.strip() != "":
        try:
          # Selecciona la pestaña 'VentasDiarias' de tu Google Sheet
          worksheet = spreadsheet.worksheet("VentasDiarias")

          fecha_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
          total = cantidad * precio_unitario

          # Añade la fila asegurando el orden de tus columnas
          worksheet.append_row([fecha_hora, producto, cantidad, precio_unitario, total])

          st.success("¡Venta registrada y sincronizada con éxito!")
        except Exception as e:
          st.error(f"No se pudo guardar la venta en la hoja de cálculo: {e}")
      else:
        st.warning("Por favor, ingresa el nombre del producto.")

elif menu == "Ver Inventario":
  st.header("📦 Inventario Actual")
  try:
    # Selecciona la pestaña de inventario (ajusta el nombre si es diferente)
    worksheet_inv = spreadsheet.worksheet("Inventario")
    rows = worksheet_inv.get_all_records()
    df = pd.DataFrame(rows)

    if not df.empty:
      st.dataframe(df, use_container_width=True)
    else:
      st.info("La hoja de inventario se encuentra vacía.")
  except Exception as e:
    st.warning(f"No se pudo cargar la pestaña de inventario: {e}")
