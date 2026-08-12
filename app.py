import gspread
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials
import streamlit as st
from datetime import datetime

# Configuración
st.set_page_config(page_title="Sistema de Ventas", page_icon="📦", layout="wide")

# Conexión
@st.cache_resource
def conectar_google_sheets():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(st.secrets["gcp_service_account"]), scope)
    return gspread.authorize(creds).open("InventarioData")

client = conectar_google_sheets()

def cargar_inventario():
    data = client.sheet1.get_all_records()
    return pd.DataFrame(data)

# --- LOGIN ---
if "autenticado" not in st.session_state: st.session_state.update({"autenticado": False, "nombre": ""})

if not st.session_state["autenticado"]:
    st.title("🔐 Iniciar Sesión")
    with st.form("login"):
        user = st.text_input("Usuario")
        pwd = st.text_input("Contraseña", type="password")
        if st.form_submit_button("Ingresar"):
            if user == "admin" and pwd == "12345":
                st.session_state.update({"autenticado": True, "nombre": "Carlos", "rol": "Administrador"})
                st.rerun()
            else: st.error("Credenciales incorrectas")
else:
    # ... dentro del bloque "else" de la autenticación
    st.title("📦 App Ventas ¿Media O Que?")
    st.markdown("Control financiero y de stock sincronizado en tiempo real con Google Sheets.")    
    
    # --- APP PRINCIPAL ---
    menu = st.sidebar.selectbox("Menú", ["📊 Dashboard", "🛒 Registrar Venta", "📅 Ventas del Día", "➕ Registrar Producto"])
    
    df_inventario = cargar_inventario()

    if menu == "📊 Dashboard":
        st.subheader("Resumen General")
        st.dataframe(df_inventario, use_container_width=True)

    elif menu == "🛒 Registrar Venta":
        st.subheader("🛒 Nueva Venta")
        producto = st.selectbox("Producto", df_inventario["Producto"].values)
        info = df_inventario[df_inventario["Producto"] == producto].iloc[0]
        st.write(f"Precio: ${info['Precio Venta']:,.2f}")
        
        cant = st.number_input("Cantidad", min_value=1, step=1)
        if st.button("Confirmar Venta"):
            # 1. Registrar en hoja VentasDiarias
            total = cant * info['Precio Venta']
            client.worksheet("VentasDiarias").append_row([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), producto, cant, total])
            # 2. Descontar stock
            df_inventario.loc[df_inventario["Producto"] == producto, "Cantidad"] -= cant
            client.sheet1.clear()
            client.sheet1.update([df_inventario.columns.values.tolist()] + df_inventario.values.tolist())
            st.success("¡Venta realizada!")

    elif menu == "📅 Ventas del Día":
        st.subheader("📅 Ventas de Hoy")
        df_ventas = pd.DataFrame(client.worksheet("VentasDiarias").get_all_records())
        if not df_ventas.empty:
            df_ventas['Fecha'] = pd.to_datetime(df_ventas['Fecha']).dt.strftime("%Y-%m-%d")
            df_hoy = df_ventas[df_ventas['Fecha'] == datetime.now().strftime("%Y-%m-%d")]
            st.write(f"Total hoy: ${df_hoy['Total'].sum():,.2f}")
            st.dataframe(df_hoy)
        else: st.info("No hay ventas hoy.")

    elif menu == "➕ Registrar Producto":
        with st.form("nuevo_prod"):
            nombre = st.text_input("Producto")
            cant = st.number_input("Cantidad", 0)
            precio = st.number_input("Precio Venta", 0.0)
            if st.form_submit_button("Guardar"):
                client.sheet1.append_row([nombre, cant, 0, precio, 0, 0, 0])
                st.success("Producto guardado")
