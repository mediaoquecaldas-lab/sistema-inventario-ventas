import gspread
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials
import streamlit as st
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="App Ventas ¿Media O Que?", page_icon="📦", layout="wide")

# --- CONEXIÓN GOOGLE SHEETS ---
@st.cache_resource
def conectar_google_sheets():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(st.secrets["gcp_service_account"]), scope)
    return gspread.authorize(creds).open("InventarioData")

client = conectar_google_sheets()

# --- CARGAR DATOS ---
def cargar_inventario():
    try:
        data = client.sheet1.get_all_records()
        df = pd.DataFrame(data)
        columnas_necesarias = ["Producto", "Cantidad", "Costo Unitario", "Precio Venta", "Venta Total", "Costo Total", "Ganancia"]
        
        if df.empty or not all(col in df.columns for col in columnas_necesarias):
            return pd.DataFrame(columns=columnas_necesarias)
        
        df["Cantidad"] = pd.to_numeric(df["Cantidad"], errors="coerce").fillna(0).astype(int)
        df["Precio Venta"] = pd.to_numeric(df["Precio Venta"], errors="coerce").fillna(0.0)
        df["Costo Unitario"] = pd.to_numeric(df["Costo Unitario"], errors="coerce").fillna(0.0)
        
        return df
    except Exception:
        return pd.DataFrame(columns=["Producto", "Cantidad", "Costo Unitario", "Precio Venta", "Venta Total", "Costo Total", "Ganancia"])

# --- SIDEBAR Y LOGO ---
try:
    st.sidebar.image("assets/logo.png", use_container_width=True)
except:
    st.sidebar.warning("Logo no encontrado en assets/logo.png")

# --- LOGIN ---
if "autenticado" not in st.session_state: st.session_state.update({"autenticado": False, "nombre": ""})

if not st.session_state["autenticado"]:
    st.title("🔐 Iniciar Sesión - App Ventas ¿Media O Que?")
    with st.form("login"):
        user = st.text_input("Usuario")
        pwd = st.text_input("Contraseña", type="password")
        if st.form_submit_button("Ingresar"):
            if user == "admin" and pwd == "12345":
                st.session_state.update({"autenticado": True, "nombre": "Admin"})
                st.rerun()
            else: st.error("Credenciales incorrectas")
else:
    # --- APP PRINCIPAL ---
    st.title("📦 App Ventas ¿Media O Que?")
    st.markdown("Control financiero y de stock sincronizado en tiempo real.")
    
    menu = st.sidebar.selectbox("Menú de Navegación", ["📊 Dashboard", "🛒 Registrar Venta", "📅 Ventas del Día", "➕ Registrar Producto"])
    df_inventario = cargar_inventario()

    if menu == "📊 Dashboard":
        st.subheader("Resumen General")
        st.dataframe(df_inventario, use_container_width=True)

    elif menu == "🛒 Registrar Venta":
        st.subheader("🛒 Nueva Venta")
        if df_inventario.empty:
            st.warning("No hay productos disponibles.")
        else:
            # 🪑 Selector de Mesa
            mesa_seleccionada = st.selectbox("Seleccionar Mesa", ["Mesa 1", "Mesa 2", "Mesa 3", "Mesa 4", "Mesa 5", "Barra", "Llevar"])
            
            producto = st.selectbox("Producto", df_inventario["Producto"].values)
            info = df_inventario[df_inventario["Producto"] == producto].iloc[0]
            
            precio_unitario = float(info['Precio Venta'])
            st.write(f"Precio Unitario: ${precio_unitario:,.2f}")
            cant = st.number_input("Cantidad", min_value=1, step=1)
            
            if st.button("Confirmar Venta"):
                total = cant * precio_unitario
                # Se agrega la mesa al registro en Google Sheets
                client.worksheet("VentasDiarias").append_row([
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                    mesa_seleccionada, 
                    producto, 
                    int(cant), 
                    float(total)
                ])
                
                # Actualizar stock
                df_inventario.loc[df_inventario["Producto"] == producto, "Cantidad"] -= int(cant)
                
                client.sheet1.clear()
                client.sheet1.update([df_inventario.columns.values.tolist()] + df_inventario.values.tolist())
                st.success(f"¡Venta registrada para la {mesa_seleccionada}!")
                st.rerun()

    elif menu == "📅 Ventas del Día":
        st.subheader("📅 Ventas de Hoy")
        try:
            ws_ventas = client.worksheet("VentasDiarias")
            data_ventas = ws_ventas.get_all_records()
            
            if not data_ventas:
                st.info("La pestaña 'VentasDiarias' existe pero aún no tiene registros.")
            else:
                df_ventas = pd.DataFrame(data_ventas)
                
                # Verificamos que las columnas necesarias existan (incluyendo Mesa)
                cols_requeridas = ['Fecha', 'Mesa', 'Producto', 'Cantidad', 'Total']
                if not all(col in df_ventas.columns for col in cols_requeridas):
                    st.error(f"Error en las columnas de 'VentasDiarias'. Deben ser: {cols_requeridas}. Actualmente detecta: {list(df_ventas.columns)}")
                else:
                    df_ventas['Total'] = pd.to_numeric(df_ventas['Total'], errors='coerce').fillna(0.0)
                    df_ventas['Cantidad'] = pd.to_numeric(df_ventas['Cantidad'], errors='coerce').fillna(0).astype(int)
                    df_ventas['Fecha'] = pd.to_datetime(df_ventas['Fecha'], errors='coerce').dt.strftime("%Y-%m-%d")
                    
                    hoy = datetime.now().strftime("%Y-%m-%d")
                    df_hoy = df_ventas[df_ventas['Fecha'] == hoy]
                    
                    if not df_hoy.empty:
                        total_hoy = df_hoy['Total'].sum()
                        st.write(f"Total acumulado hoy: **${total_hoy:,.2f}**")
                        st.dataframe(df_hoy, use_container_width=True)
                    else:
                        st.info(f"No hay ventas registradas para el día de hoy ({hoy}).")
        except gspread.exceptions.WorksheetNotFound:
            st.error("⚠️ La pestaña 'VentasDiarias' no existe en tu Google Sheet. Por favor, créala.")
        except Exception as e:
            st.error(f"Ocurrió un error al cargar las ventas: {e}")

    elif menu == "➕ Registrar Producto":
        with st.form("nuevo_prod"):
            nombre = st.text_input("Nombre del Producto")
            cant = st.number_input("Cantidad", min_value=0)
            costo = st.number_input("Costo Unitario", min_value=0.0)
            precio = st.number_input("Precio Venta", min_value=0.0)
            if st.form_submit_button("Guardar"):
                client.sheet1.append_row([nombre, int(cant), float(costo), float(precio), float(cant*precio), float(cant*costo), float((cant*precio)-(cant*costo))])
                st.success("¡Producto guardado!")
                st.rerun()
