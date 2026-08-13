import gspread
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials
import streamlit as st
from datetime import datetime

# Configuración
st.set_page_config(page_title="App Ventas ¿Media O Que?", page_icon="📦", layout="wide")

# Conexión
@st.cache_resource
def conectar_google_sheets():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(st.secrets["gcp_service_account"]), scope)
    return gspread.authorize(creds).open("InventarioData")

client = conectar_google_sheets()

def cargar_inventario():
    try:
        data = client.sheet1.get_all_records()
        df = pd.DataFrame(data)
        columnas_necesarias = ["Producto", "Cantidad", "Costo Unitario", "Precio Venta", "Venta Total", "Costo Total", "Ganancia"]
        if df.empty or not all(col in df.columns for col in columnas_necesarias):
            return pd.DataFrame(columns=columnas_necesarias)
        return df
    except Exception:
        return pd.DataFrame(columns=["Producto", "Cantidad", "Costo Unitario", "Precio Venta", "Venta Total", "Costo Total", "Ganancia"])

# --- LOGIN ---
if "autenticado" not in st.session_state: st.session_state.update({"autenticado": False, "nombre": ""})

if not st.session_state["autenticado"]:
    st.title("🔐 Iniciar Sesión - App Ventas ¿Media O Que?")
    with st.form("login"):
        user = st.text_input("Usuario")
        pwd = st.text_input("Contraseña", type="password")
        if st.form_submit_button("Ingresar"):
            if user == "admin" and pwd == "12345":
                st.session_state.update({"autenticado": True, "nombre": "Carlos", "rol": "Administrador"})
                st.rerun()
            else: st.error("Credenciales incorrectas")
else:
    # --- APP PRINCIPAL ---
    st.title("📦 App Ventas ¿Media O Que?")
    st.markdown("Control financiero y de stock sincronizado en tiempo real con Google Sheets.")
    
    menu = st.sidebar.selectbox("Menú de Navegación", ["📊 Dashboard", "🛒 Registrar Venta", "📅 Ventas del Día", "➕ Registrar Producto"])
    
    df_inventario = cargar_inventario()

    if menu == "📊 Dashboard":
        st.subheader("Resumen General")
        if df_inventario.empty:
            st.info("No hay productos registrados todavía. Agrega uno desde el menú lateral.")
        else:
            st.dataframe(df_inventario, use_container_width=True)

    elif menu == "🛒 Registrar Venta":
        st.subheader("🛒 Nueva Venta")
        if df_inventario.empty:
            st.warning("No hay productos disponibles en el inventario.")
        else:
            producto = st.selectbox("Producto", df_inventario["Producto"].values)
            info = df_inventario[df_inventario["Producto"] == producto].iloc[0]
            elif menu == "🛒 Registrar Venta":
        st.subheader("🛒 Nueva Venta")
        if df_inventario.empty:
            st.warning("No hay productos disponibles en el inventario.")
        else:
            producto = st.selectbox("Producto", df_inventario["Producto"].values)
            info = df_inventario[df_inventario["Producto"] == producto].iloc[0]
            
            # Conversión segura a número para evitar el ValueError
            try:
                precio_unitario = float(info['Precio Venta'])
            except (ValueError, TypeError):
                precio_unitario = 0.0
                
            st.write(f"Precio: ${precio_unitario:,.2f}")
            
            cant = st.number_input("Cantidad", min_value=1, step=1)
            if st.button("Confirmar Venta"):
                total = cant * precio_unitario
                client.worksheet("VentasDiarias").append_row([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), producto, int(cant), float(total)])
                
                # Descontar stock
                df_inventario.loc[df_inventario["Producto"] == producto, "Cantidad"] -= cant
                client.sheet1.clear()
                client.sheet1.update([df_inventario.columns.values.tolist()] + df_inventario.values.tolist())
                st.success("¡Venta realizada con éxito!")
                st.rerun()
            
            cant = st.number_input("Cantidad", min_value=1, step=1)
            if st.button("Confirmar Venta"):
                total = cant * info['Precio Venta']
                client.worksheet("VentasDiarias").append_row([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), producto, int(cant), float(total)])
                
                # Descontar stock
                df_inventario.loc[df_inventario["Producto"] == producto, "Cantidad"] -= cant
                client.sheet1.clear()
                client.sheet1.update([df_inventario.columns.values.tolist()] + df_inventario.values.tolist())
                st.success("¡Venta realizada con éxito!")
                st.rerun()

    elif menu == "📅 Ventas del Día":
        st.subheader("📅 Ventas de Hoy")
        try:
            df_ventas = pd.DataFrame(client.worksheet("VentasDiarias").get_all_records())
            if not df_ventas.empty and "Fecha" in df_ventas.columns:
                df_ventas['Fecha'] = pd.to_datetime(df_ventas['Fecha']).dt.strftime("%Y-%m-%d")
                df_hoy = df_ventas[df_ventas['Fecha'] == datetime.now().strftime("%Y-%m-%d")]
                if not df_hoy.empty:
                    st.write(f"Total hoy: **${df_hoy['Total'].sum():,.2f}**")
                    st.dataframe(df_hoy, use_container_width=True)
                else:
                    st.info("No hay ventas registradas el día de hoy.")
            else:
                st.info("No hay registros de ventas todavía.")
        except Exception:
            st.info("La pestaña 'VentasDiarias' está vacía o no configurada.")

    elif menu == "➕ Registrar Producto":
        with st.form("nuevo_prod"):
            nombre = st.text_input("Nombre del Producto")
            cant = st.number_input("Cantidad", min_value=0, step=1)
            costo = st.number_input("Costo Unitario", min_value=0.0, format="%.2f")
            precio = st.number_input("Precio Venta", min_value=0.0, format="%.2f")
            if st.form_submit_button("Guardar Producto"):
                if nombre.strip():
                    v_total = cant * precio
                    c_total = cant * costo
                    ganancia = v_total - c_total
                    client.sheet1.append_row([nombre, int(cant), float(costo), float(precio), float(v_total), float(c_total), float(ganancia)])
                    st.success(f"¡Producto '{nombre}' guardado exitosamente!")
                    st.rerun()
                else:
                    st.warning("Escribe el nombre del producto.")
