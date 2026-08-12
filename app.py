import gspread
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials
import streamlit as st

# Configuración de la página
st.set_page_config(
    page_title="Gestión de Ventas e Inventario", page_icon="📦", layout="wide"
)

# Columnas requeridas
COLUMNAS_DATA = [
    "Producto",
    "Cantidad",
    "Costo Unitario",
    "Precio Venta",
    "Venta Total",
    "Costo Total",
    "Ganancia",
]


# Conexión a Google Sheets usando los secretos de Streamlit
@st.cache_resource
def conectar_google_sheets():
  scope = [
      "https://spreadsheets.google.com/feeds",
      "https://www.googleapis.com/auth/drive",
  ]
  credentials_dict = dict(st.secrets["gcp_service_account"])
  creds = ServiceAccountCredentials.from_json_keyfile_dict(
      credentials_dict, scope
  )
  client = gspread.authorize(creds)
  sheet = client.open("InventarioData").sheet1
  return sheet


def cargar_datos():
  try:
    sheet = conectar_google_sheets()
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    if df.empty or not all(col in df.columns for col in COLUMNAS_DATA):
      return pd.DataFrame(columns=COLUMNAS_DATA)
    return df
  except Exception as e:
    st.error(f"Error al conectar con Google Sheets: {e}")
    return pd.DataFrame(columns=COLUMNAS_DATA)


def guardar_datos_en_gsheets(df):
  sheet = conectar_google_sheets()
  sheet.clear()
  sheet.update([df.columns.values.tolist()] + df.values.tolist())


# Control de sesión de usuarios local
def verificar_credenciales(usuario, contraseña):
  usuarios_db = {
      "admin": {"password": "12345", "rol": "Administrador", "nombre": "Carlos"},
      "empleado": {
          "password": "abcde",
          "rol": "Empleado",
          "nombre": "Ana Pérez",
      },
  }
  if usuario in usuarios_db and usuarios_db[usuario]["password"] == contraseña:
    return usuarios_db[usuario]
  return None


if "autenticado" not in st.session_state:
  st.session_state["autenticado"] = False
  st.session_state["usuario"] = ""
  st.session_state["rol"] = ""
  st.session_state["nombre"] = ""

# Pantalla de Login
if not st.session_state["autenticado"]:
  st.title("🔐 Iniciar Sesión - Sistema de Ventas e Inventario")
  st.markdown("Por favor, ingresa tus credenciales para acceder al sistema.")

  with st.form("login_form"):
    usuario_input = st.text_input("Usuario")
    password_input = st.text_input("Contraseña", type="password")
    submit_login = st.form_submit_button("Ingresar")

    if submit_login:
      user_data = verificar_credenciales(usuario_input, password_input)
      if user_data:
        st.session_state["autenticado"] = True
        st.session_state["usuario"] = usuario_input
        st.session_state["rol"] = user_data["rol"]
        st.session_state["nombre"] = user_data["nombre"]
        st.success(f"¡Bienvenido/a, {user_data['nombre']}!")
        st.rerun()
      else:
        st.error("Usuario o contraseña incorrectos.")

  st.info(
      "💡 **Credenciales de prueba:**\n"
      "- **Admin:** usuario `admin` / contraseña `12345`\n"
      "- **Empleado:** usuario `empleado` / contraseña `abcde`"
  )

else:
  # APLICACIÓN PRINCIPAL
  df_inventario = cargar_datos()

  st.sidebar.write(f"👤 **Usuario:** {st.session_state['nombre']}")
  st.sidebar.write(f"🛡️ **Rol:** {st.session_state['rol']}")

  if st.sidebar.button("Cerrar Sesión"):
    st.session_state["autenticado"] = False
    st.session_state["usuario"] = ""
    st.session_state["rol"] = ""
    st.session_state["nombre"] = ""
    st.rerun()

  st.sidebar.markdown("---")

  if st.session_state["rol"] == "Administrador":
    opciones_menu = [
        "📊 Dashboard / Resumen",
        "➕ Registrar Producto / Venta",
        "🔄 Actualizar Stock",
        "🗑️ Eliminar Producto",
    ]
  else:
    opciones_menu = ["📊 Dashboard / Resumen", "🔄 Actualizar Stock"]

  menu = st.sidebar.selectbox("Menú de Navegación", opciones_menu)

  st.title("📦 Sistema de Ventas e Inventario en la Nube")
  st.markdown(
      "Control financiero y de stock sincronizado en tiempo real con Google"
      " Sheets."
  )

  # 1. DASHBOARD / RESUMEN
  if menu == "📊 Dashboard / Resumen":
    st.subheader("📋 Resumen General y Financiero")

    if df_inventario.empty:
      st.info(
          "No hay registros todavía. Agrega un producto desde el menú lateral."
      )
    else:
      # Métricas principales
      total_ventas = pd.to_numeric(
          df_inventario["Venta Total"], errors="coerce"
      ).sum()
      total_costos = pd.to_numeric(
          df_inventario["Costo Total"], errors="coerce"
      ).sum()
      total_ganancias = pd.to_numeric(
          df_inventario["Ganancia"], errors="coerce"
      ).sum()

      col1, col2, col3 = st.columns(3)
      col1.metric("Ventas Totales", f"${total_ventas:,.2f}")
      col2.metric("Costos Totales", f"${total_costos:,.2f}")
      col3.metric("Ganancia Neta", f"${total_ganancias:,.2f}")

      st.markdown("---")

      busqueda = st.text_input("🔍 Buscar producto:")
      if busqueda:
        df_filtrado = df_inventario[
            df_inventario["Producto"]
            .astype(str)
            .str.contains(busqueda, case=False, na=False)
        ]
      else:
        df_filtrado = df_inventario

      st.dataframe(df_filtrado, use_container_width=True)

  # 2. REGISTRAR PRODUCTO / VENTA
  elif menu == "➕ Registrar Producto / Venta":
    st.subheader("➕ Registrar Nuevo Producto y Cálculos Financieros")

    with st.form("form_agregar"):
      col1, col2 = st.columns(2)
      with col1:
        producto = st.text_input("Nombre del Producto")
        cantidad = st.number_input("Cantidad", min_value=1, step=1)
        costo_unitario = st.number_input(
            "Costo Unitario ($)", min_value=0.0, format="%.2f"
        )
      with col2:
        precio_venta = st.number_input(
            "Precio Venta ($)", min_value=0.0, format="%.2f"
        )

      submitted = st.form_submit_button("Guardar en Google Sheets")

      if submitted:
        if not producto.strip():
          st.warning("Por favor, ingresa el nombre del producto.")
        else:
          # Cálculos automáticos solicitados
          venta_total = cantidad * precio_venta
          costo_total = cantidad * costo_unitario
          ganancia = venta_total - costo_total

          nuevo_registro = pd.DataFrame([{
              "Producto": str(producto),
              "Cantidad": int(cantidad),
              "Costo Unitario": float(costo_unitario),
              "Precio Venta": float(precio_venta),
              "Venta Total": float(venta_total),
              "Costo Total": float(costo_total),
              "Ganancia": float(ganancia),
          }])

          df_inventario = pd.concat(
              [df_inventario, nuevo_registro], ignore_index=True
          )
          guardar_datos_en_gsheets(df_inventario)
          st.success(
              f"¡Producto '{producto}' guardado exitosamente con sus cálculos!"
          )
          st.rerun()

  # 3. ACTUALIZAR STOCK
  elif menu == "🔄 Actualizar Stock":
    st.subheader("🔄 Actualizar Cantidad de Stock")

    if df_inventario.empty:
      st.info("No hay productos disponibles para actualizar.")
    else:
      producto_seleccionado = st.selectbox(
          "Seleccione el Producto", df_inventario["Producto"].values
      )

      idx = df_inventario[
          df_inventario["Producto"] == producto_seleccionado
      ].index[0]
      stock_actual = int(df_inventario.loc[idx, "Cantidad"])
      costo_u = float(df_inventario.loc[idx, "Costo Unitario"])
      precio_v = float(df_inventario.loc[idx, "Precio Venta"])

      st.write(f"Stock actual disponible: **{stock_actual} unidades**")

      tipo_movimiento = st.radio(
          "Tipo de Operación",
          ["Entrada (Sumar)", "Salida (Restar)", "Definir Stock Fijo"],
      )
      cantidad_cambio = st.number_input("Cantidad", min_value=1, step=1)

      if st.button("Aplicar Cambios y Recalcular"):
        if tipo_movimiento == "Entrada (Sumar)":
          nuevo_stock = stock_actual + cantidad_cambio
        elif tipo_movimiento == "Salida (Restar)":
          nuevo_stock = max(0, stock_actual - cantidad_cambio)
        else:
          nuevo_stock = cantidad_cambio

        # Recálculo automático financiero basado en la nueva cantidad
        nueva_venta_total = nuevo_stock * precio_v
        nuevo_costo_total = nuevo_stock * costo_u
        nueva_ganancia = nueva_venta_total - nuevo_costo_total

        df_inventario.loc[idx, "Cantidad"] = int(nuevo_stock)
        df_inventario.loc[idx, "Venta Total"] = float(nueva_venta_total)
        df_inventario.loc[idx, "Costo Total"] = float(nuevo_costo_total)
        df_inventario.loc[idx, "Ganancia"] = float(nueva_ganancia)

        guardar_datos_en_gsheets(df_inventario)
        st.success(
            f"¡Stock y finanzas actualizadas para '{producto_seleccionado}'!"
        )
        st.rerun()

  # 4. ELIMINAR PRODUCTO
  elif menu == "Eliminar Producto" and st.session_state["rol"] == "Administrador":
    st.subheader("🗑️ Eliminar Producto del Inventario")

    if df_inventario.empty:
      st.info("No hay productos para eliminar.")
    else:
      producto_a_eliminar = st.selectbox(
          "Seleccione el producto a eliminar", df_inventario["Producto"].values
      )

      if st.button("Eliminar Permanentemente", type="primary"):
        df_inventario = df_inventario[
            df_inventario["Producto"] != producto_a_eliminar
        ]
        guardar_datos_en_gsheets(df_inventario)
        st.success(f"El producto '{producto_a_eliminar}' ha sido eliminado.")
        st.rerun()