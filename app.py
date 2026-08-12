import gspread
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials
import streamlit as st

# Configuración de la página
st.set_page_config(
    page_title="Gestión de Inventarios con Google Sheets",
    page_icon="📦",
    layout="wide",
)


# Conexión a Google Sheets usando los secretos de Streamlit
@st.cache_resource
def conectar_google_sheets():
  scope = [
      "https://spreadsheets.google.com/feeds",
      "https://www.googleapis.com/auth/drive",
  ]
  # Cargamos credenciales desde los secretos de Streamlit Cloud
  credentials_dict = dict(st.secrets["gcp_service_account"])
  creds = ServiceAccountCredentials.from_json_keyfile_dict(
      credentials_dict, scope
  )
  client = gspread.authorize(creds)
  # Abre la hoja de cálculo por su nombre exacto en Google Drive
  sheet = client.open("InventarioData").sheet1
  return sheet


def cargar_datos():
  try:
    sheet = conectar_google_sheets()
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    if df.empty:
      df = pd.DataFrame(
          columns=[
              "ID",
              "Producto",
              "Categoría",
              "Cantidad",
              "Precio Unitario ($)",
              "Ubicación",
          ]
      )
    return df
  except Exception as e:
    st.error(f"Error al conectar con Google Sheets: {e}")
    return pd.DataFrame(
        columns=[
            "ID",
            "Producto",
            "Categoría",
            "Cantidad",
            "Precio Unitario ($)",
            "Ubicación",
        ]
    )


def guardar_datos_en_gsheets(df):
  sheet = conectar_google_sheets()
  sheet.clear()  # Limpia la hoja
  sheet.update(
      [df.columns.values.tolist()] + df.values.tolist()
  )  # Actualiza con los nuevos datos


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
  st.title("🔐 Iniciar Sesión - Sistema de Inventarios")
  st.markdown(
      "Por favor, ingresa tus credenciales para acceder al sistema de Área"
      " Técnica Servicios y Soluciones Tecnológicas."
  )

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
      "💡 **Credenciales de prueba:**\n- **Admin:** usuario `admin` / contraseña"
      " `12345`\n- **Empleado:** usuario `empleado` / contraseña `abcde`"
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
        "Ver Inventario",
        "Agregar Producto",
        "Actualizar Stock",
        "Eliminar Producto",
    ]
  else:
    opciones_menu = ["Ver Inventario", "Actualizar Stock"]

  menu = st.sidebar.selectbox("Menú de Navegación", opciones_menu)

  st.title("📦 Sistema de Gestión de Inventarios (Google Sheets)")
  st.markdown(
      "Los datos se guardan de forma permanente y en tiempo real en la nube."
  )

  # 1. VER INVENTARIO
  if menu == "Ver Inventario":
    st.subheader("📋 Inventario Actual")

    if df_inventario.empty:
      st.info(
          "No hay productos registrados en el inventario todavía. Puedes"
          " registrar productos desde el menú de Administrador."
      )
    else:
      busqueda = st.text_input("🔍 Buscar producto por nombre o categoría:")
      if busqueda:
        df_filtrado = df_inventario[
            df_inventario["Producto"]
            .astype(str)
            .str.contains(busqueda, case=False, na=False)
            | df_inventario["Categoría"]
            .astype(str)
            .str.contains(busqueda, case=False, na=False)
        ]
      else:
        df_filtrado = df_inventario

      col1, col2, col3 = st.columns(3)
      col1.metric("Total de Productos Únicos", len(df_inventario))

      try:
        total_unidades = int(df_inventario["Cantidad"].sum())
      except:
        total_unidades = 0
      col2.metric("Unidades Totales en Stock", total_unidades)

      try:
        valor_total = (
            pd.to_numeric(df_inventario["Cantidad"], errors="coerce")
            * pd.to_numeric(df_inventario["Precio Unitario ($)"], errors="coerce")
        ).sum()
      except:
        valor_total = 0.0
      col3.metric("Valor Total del Inventario", f"${valor_total:,.2f}")

      st.dataframe(df_filtrado, use_container_width=True)

  # 2. AGREGAR PRODUCTO
  elif menu == "Agregar Producto":
    st.subheader("➕ Registrar Nuevo Producto")

    with st.form("form_agregar"):
      col1, col2 = st.columns(2)
      with col1:
        prod_id = st.text_input("ID / Código de Barras")
        nombre = st.text_input("Nombre del Producto")
        categoria = st.text_input("Categoría")
      with col2:
        cantidad = st.number_input("Cantidad Inicial", min_value=0, step=1)
        precio = st.number_input(
            "Precio Unitario ($)", min_value=0.0, format="%.2f"
        )
        ubicacion = st.text_input("Ubicación en Almacén")

      submitted = st.form_submit_button("Guardar Producto")

      if submitted:
        if not prod_id or not nombre:
          st.warning(
              "Por favor, completa al menos el ID y el Nombre del producto."
          )
        elif (
            not df_inventario.empty
            and prod_id in df_inventario["ID"].astype(str).values
        ):
          st.error(f"El ID '{prod_id}' ya existe en el inventario.")
        else:
          nuevo_registro = pd.DataFrame({
              "ID": [str(prod_id)],
              "Producto": [str(nombre)],
              "Categoría": [str(categoria)],
              "Cantidad": [int(cantidad)],
              "Precio Unitario ($)": [float(precio)],
              "Ubicación": [str(ubicacion)],
          })
          df_inventario = pd.concat(
              [df_inventario, nuevo_registro], ignore_index=True
          )
          guardar_datos_en_gsheets(df_inventario)
          st.success(
              f"¡Producto '{nombre}' agregado y guardado en Google Sheets"
              " exitosamente!"
          )
          st.rerun()

  # 3. ACTUALIZAR STOCK
  elif menu == "Actualizar Stock":
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

      st.write(f"Stock actual disponible: **{stock_actual} unidades**")

      tipo_movimiento = st.radio(
          "Tipo de Operación",
          ["Entrada (Sumar)", "Salida (Restar)", "Definir Stock Fijo"],
      )
      cantidad_cambio = st.number_input("Cantidad", min_value=1, step=1)

      if st.button("Aplicar Cambios"):
        if tipo_movimiento == "Entrada (Sumar)":
          nuevo_stock = stock_actual + cantidad_cambio
        elif tipo_movimiento == "Salida (Restar)":
          nuevo_stock = max(0, stock_actual - cantidad_cambio)
        else:
          nuevo_stock = cantidad_cambio

        df_inventario.loc[idx, "Cantidad"] = int(nuevo_stock)
        guardar_datos_en_gsheets(df_inventario)
        st.success(
            f"¡Stock actualizado en Google Sheets! El nuevo inventario de"
            f" '{producto_seleccionado}' es {nuevo_stock} unidades."
        )
        st.rerun()

  # 4. ELIMINAR PRODUCTO
  elif menu == "Eliminar Producto":
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
        st.success(
            f"El producto '{producto_a_eliminar}' ha sido eliminado de Google"
            " Sheets."
        )
        st.rerun()
