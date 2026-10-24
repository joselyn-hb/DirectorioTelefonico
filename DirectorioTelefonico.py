# Este archivo contiene la interfaz gráfica del directorio telefónico.
# Aquí se crean las ventanas y se muestran, buscan y editan los contactos.

# Permite usar anotaciones de tipos modernas sin evaluarlas inmediatamente.
from __future__ import annotations

# Importaciones de librerías del sistema y de terceros.
# Cada una sirve para una tarea específica dentro de la app.
import os
import threading
from io import BytesIO
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from urllib.request import urlopen

# customtkinter: librería para crear la interfaz gráfica con ventanas, botones y etiquetas.
import customtkinter as ctk
import mysql.connector

# PIL: maneja imágenes, redimensionado y renderizado para mostrarlas en la app.
from PIL import Image, ImageDraw, ImageTk
from dotenv import load_dotenv


# Ruta base del proyecto: carpeta donde está este archivo.
# Así la app sabe dónde encontrar recursos como imágenes o el archivo .env.
BASE_DIR = Path(__file__).resolve().parent

# Icono de la aplicación y una imagen por defecto cuando no hay foto disponible.
APP_ICON = BASE_DIR / "static" / "imagen" / "logo.ico"
PLACEHOLDER_IMAGE = Image.new("RGB", (360, 260), "#263238")


# Convierte valores de la base de datos a texto legible para mostrarlos en pantalla.
def value_as_text(value: Any) -> str:
    """
    Si el valor es nulo, devuelve un texto amigable.
    Si es una imagen guardada en la base de datos, lo indica.
    """
    if value is None:
        return "No disponible"
    if isinstance(value, bytes):
        return "[imagen almacenada en la base de datos]"
    return str(value)


# Busca el campo de una fila que podría contener una imagen.
# Esto sirve porque la imagen puede venir con distintos nombres en la base de datos.
def image_value(user: dict[str, Any]) -> Any:
    """
    Recorre varias opciones de nombres para encontrar una foto o URL.

    Algunos proyectos usan 'foto', otros 'imagen' o 'enlace', etc.
    """
    preferred = (
        "imagen",
        "imagen_url",
        "enlace_imagen",
        "enlace",
        "foto",
        "fotografia",
        "avatar",
        "image",
        "image_url",
        "url_imagen",
        "url",
        "enlaceimagen",
    )
    normalized = {str(key).lower(): value for key, value in user.items()}
    for name in preferred:
        if name in normalized and normalized[name]:
            return normalized[name]
    for key, value in normalized.items():
        if value and ("image" in key or "imagen" in key or "foto" in key):
            return value
    return None


# Carga una imagen desde varias fuentes.
# Puede venir en bytes, como una URL, como un archivo local o entonces usa una imagen por defecto.
def load_image(source: Any, size: tuple[int, int]) -> Image.Image:
    """
    Abre la imagen desde distintos tipos de origen:
    - bytes de la base de datos
    - URL en internet
    - ruta local del disco
    - imágenes por defecto si no hay fuente
    """
    if isinstance(source, bytes):
        image = Image.open(BytesIO(source))
    elif source:
        source_text = str(source).strip()
        parsed = urlparse(source_text)
        if parsed.scheme in {"http", "https"}:
            with urlopen(source_text, timeout=8) as response:
                image = Image.open(BytesIO(response.read()))
        else:
            image = Image.open(Path(source_text))
    else:
        image = PLACEHOLDER_IMAGE.copy()
    return image.convert("RGB")


# Redondea los bordes de una imagen para que se vea mejor en una tarjeta.
def rounded_image(image: Image.Image, radius: int = 24) -> Image.Image:
    """
    Crea una máscara con esquinas redondeadas para que la imagen tenga bordes suaves.
    """
    rounded = image.convert("RGBA")
    mask = Image.new("L", rounded.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        (0, 0, rounded.width - 1, rounded.height - 1),
        radius=radius,
        fill=255,
    )
    rounded.putalpha(mask)
    return rounded


# Esta clase representa la ventana principal de la aplicación.
# Es la pantalla del directorio telefónico que el usuario ve.
class DirectorioTelefonico(ctk.CTk):
    def __init__(self) -> None:
        """
        Constructor de la ventana principal.

        Aquí se configura el tamaño, el tema, los elementos de la interfaz y el estado inicial.
        """
        super().__init__()

        # Nombre de la ventana
        self.title("Directorio telefónico")

        # Calcula el tamaño ideal de la ventana según el monitor del usuario.
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        window_width = max(900, int(screen_width * 0.90))
        window_height = max(580, int(screen_height * 0.85))
        position_x = max(0, (screen_width - window_width) // 2)
        position_y = max(0, (screen_height - window_height) // 2)
        self.geometry(
            f"{window_width}x{window_height}+{position_x}+{position_y}"
        )
        self.minsize(900, 580)

        # Cuando el usuario cierre la ventana, se destruye la app.
        self.protocol("WM_DELETE_WINDOW", self.destroy)

        # Si existe un ícono en la carpeta static, lo usa como logo de la ventana.
        if APP_ICON.exists():
            try:
                self.iconbitmap(str(APP_ICON))
            except Exception:
                try:
                    self.wm_iconbitmap(str(APP_ICON))
                except Exception:
                    pass

        # Cambia el estilo visual a oscuro y usa un tema azul por defecto.
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Variables internas de la app.
        self.users: list[dict[str, Any]] = []
        self.image_references: list[ImageTk.PhotoImage] = []
        self.search_text = ctk.StringVar()

        # Se crea la interfaz y luego se cargan los contactos.
        self._build_layout()
        self.search_text.trace_add("write", self.filter_users)
        self.after(100, self.refresh_users)

    def _build_layout(self) -> None:
        """
        Construye la parte visual de la aplicación: encabezado, lista de contactos y panel de detalle.
        """
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Encabezado con el título y el botón para actualizar.
        header = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        header.grid(row=0, column=0, columnspan=2, sticky="ew", padx=28, pady=(24, 12))
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            header,
            text="Directorio telefónico",
            font=ctk.CTkFont(size=28, weight="bold"),
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            header,
            text="Selecciona un registro para consultar sus datos",
            text_color=("gray35", "gray70"),
        ).grid(row=1, column=0, sticky="w", pady=(3, 0))

        ctk.CTkButton(
            header, text="Agregar", width=110, command=self.open_add_contact_window
        ).grid(row=0, column=2, rowspan=2, padx=(16, 0))
        ctk.CTkButton(
            header, text="Actualizar", width=110, command=self.refresh_users
        ).grid(row=0, column=1, rowspan=2, padx=(16, 0))


        # Panel izquierdo: lista de contactos.
        list_panel = ctk.CTkFrame(self, corner_radius=12)
        list_panel.grid(row=1, column=0, sticky="nsew", padx=(28, 4), pady=(0, 28))
        list_panel.grid_rowconfigure(2, weight=1)
        list_panel.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            list_panel, text="Contactos", font=ctk.CTkFont(size=18, weight="bold")
        ).grid(row=0, column=0, sticky="w", padx=18, pady=(18, 10))
        ctk.CTkEntry(
            list_panel,
            textvariable=self.search_text,
            placeholder_text="Buscar en los registros...",
        ).grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 12))
        self.contact_list = ctk.CTkScrollableFrame(list_panel, label_text="")
        self.contact_list.grid(row=2, column=0, sticky="nsew", padx=10, pady=(0, 10))

        # Panel derecho: tarjeta de detalle del contacto.
        self.detail_card = ctk.CTkFrame(self, corner_radius=12)
        self.detail_card.grid(row=1, column=1, sticky="nsew", padx=(4, 28), pady=(0, 28))
        self.detail_card.grid_columnconfigure(0, weight=1)
        self.detail_card.grid_rowconfigure(1, weight=0)
        self.detail_card.grid_rowconfigure(2, weight=0)
        self.detail_title = ctk.CTkLabel(
            self.detail_card,
            text="Detalle del contacto",
            font=ctk.CTkFont(size=20, weight="bold"),
        )
        self.detail_title.grid(row=0, column=0, sticky="w", padx=24, pady=(22, 6))
        self.image_label = ctk.CTkLabel(
            self.detail_card,
            text="",
            width=360,
            height=260,
            corner_radius=0,
            border_width=0,
            fg_color="transparent",
        )
        self.image_label.grid(row=1, column=0, padx=24, pady=(4, 0))
        self.details = ctk.CTkFrame(
            self.detail_card,
            width=360,
            fg_color="transparent",
        )
        self.details.grid(
            row=2,
            column=0,
            sticky="n",
            padx=24,
            pady=(0, 4),
        )
        self.details.grid_propagate(False)
        self.details.grid_columnconfigure(0, weight=1)

        # Mensaje inicial cuando todavía no se seleccionó ningún contacto.
        self.show_message("Selecciona un contacto para ver su información.")

    def open_add_contact_window(self) -> None:
        ventana = ctk.CTkToplevel(self)
        ventana.title("Agregar contacto")
        ventana.geometry("420x430")
        ventana.resizable(False, False)
        ventana.transient(self)
        ventana.grab_set()
        ventana.grid_columnconfigure(1, weight=1)

        fields = (
            ("nombre", "Nombre *"),
            ("apellido", "Apellido *"),
            ("telefono", "Teléfono"),
            ("email", "Correo"),
            ("role", "Cargo"),
        )
        entradas: dict[str, ctk.CTkEntry] = {}

        for fila, (clave, etiqueta) in enumerate(fields):
            ctk.CTkLabel(ventana, text=etiqueta).grid(
                row=fila, column=0, padx=(20, 12), pady=10, sticky="w"
            )
            entrada = ctk.CTkEntry(ventana, width=250)
            entrada.grid(row=fila, column=1, padx=(0, 20), pady=10, sticky="ew")
            entradas[clave] = entrada

        estado = ctk.CTkLabel(ventana, text="", wraplength=370)
        estado.grid(
            row=len(fields), column=0, columnspan=2, padx=20, pady=(8, 0)
        )
        guardar = ctk.CTkButton(
            ventana,
            text="Guardar contacto",
            command=lambda: self.save_new_contact(
                entradas, ventana, estado, guardar
            ),
        )
        guardar.grid(row=len(fields) + 1, column=0, columnspan=2, pady=20)

    def save_new_contact(
        self,
        entradas: dict[str, ctk.CTkEntry],
        ventana: ctk.CTkToplevel,
        estado: ctk.CTkLabel,
        guardar: ctk.CTkButton,
    ) -> None:
        values = {
            key: entry.get().strip()
            for key, entry in entradas.items()
        }
        if not values["nombre"] or not values["apellido"]:
            estado.configure(
                text="El nombre y el apellido son obligatorios.",
                text_color="#ff6b6b",
            )
            return

        estado.configure(text="Guardando contacto...", text_color=("gray20", "gray80"))
        guardar.configure(state="disabled")
        ventana.protocol("WM_DELETE_WINDOW", lambda: None)
        threading.Thread(
            target=self._save_new_contact_worker,
            args=(values, ventana, estado, guardar),
            daemon=True,
        ).start()

    def _save_new_contact_worker(
        self,
        values: dict[str, str],
        ventana: ctk.CTkToplevel,
        estado: ctk.CTkLabel,
        guardar: ctk.CTkButton,
    ) -> None:
        try:
            add_user(values)
        except Exception as error:
            message = f"No se pudo guardar el contacto:\n{error}"
            self.after(
                0,
                lambda message=message: self._show_contact_save_error(
                    ventana, estado, guardar, message
                ),
            )
            return

        self.after(0, lambda: self._contact_saved(ventana))

    def _show_contact_save_error(
        self,
        ventana: ctk.CTkToplevel,
        estado: ctk.CTkLabel,
        guardar: ctk.CTkButton,
        message: str,
    ) -> None:
        estado.configure(text=message, text_color="#ff6b6b")
        guardar.configure(state="normal")
        ventana.protocol("WM_DELETE_WINDOW", ventana.destroy)

    def _contact_saved(self, ventana: ctk.CTkToplevel) -> None:
        ventana.destroy()
        self.refresh_users()

    def _contact_updated(
        self, ventana: ctk.CTkToplevel, user_id: int
    ) -> None:
        ventana.destroy()
        self.refresh_users(selected_user_id=user_id)



























































    def refresh_users(self, selected_user_id: int | None = None) -> None:
        """
        Actualiza la lista de contactos desde la base de datos.

        Se ejecuta en un hilo separado para que la interfaz no se congele mientras llega la información.
        """
        self.show_message("Cargando contactos...")
        threading.Thread(
            target=self._load_users_worker,
            args=(selected_user_id,),
            daemon=True,
        ).start()



    def _load_users_worker(self, selected_user_id: int | None = None) -> None:
        """
        Consulta los usuarios en segundo plano y luego devuelve el resultado a la interfaz principal.
        """
        try:
            users = load_users()
        except Exception as error:
            message = f"No se pudo cargar la información:\n{error}"
            self.after(0, lambda message=message: self.show_message(message))
            return
        self.after(0, lambda: self._set_users(users, selected_user_id))

    def _set_users(
        self, users: list[dict[str, Any]], selected_user_id: int | None = None
    ) -> None:
        """
        Recibe los contactos y los guarda en la app para mostrarlos en la lista.
        """
        self.users = users
        self.filter_users()

        if users:
            selected_user = next(
                (
                    user
                    for user in users
                    if user.get("usuario_id") == selected_user_id
                ),
                users[0],
            )
            self.show_user(selected_user)
        else:
            self.show_message("La tabla usuarios no contiene registros.")

    def filter_users(self, *_args: Any) -> None:
        """
        Busca entre los contactos según el texto ingresado por el usuario.
        """
        query = self.search_text.get().strip().lower()

        # Limpia la lista visible antes de volver a dibujarla.
        for child in self.contact_list.winfo_children():
            child.destroy()

        matches = [
            user
            for user in self.users
            if not query
            or query in " ".join(value_as_text(value).lower() for value in user.values())
        ]

        for user in matches:
            self.create_contact_button(user)

        if not matches:
            ctk.CTkLabel(self.contact_list, text="No hay coincidencias.").pack(
                padx=12, pady=20
            )

    def create_contact_button(self, user: dict[str, Any]) -> None:
        """
        Crea una tarjeta clickeable para cada contacto encontrado.
        """
        title = value_as_text(user.get("NombreCompleto"))
        subtitle = value_as_text(user.get("role"))
        contact = ctk.CTkFrame(
            self.contact_list,
            corner_radius=8,
            cursor="hand2",
            height=58,
        )
        contact.pack(fill="x", padx=4, pady=4)
        contact.pack_propagate(False)

        # Avatar del contacto (solo inicial)
        avatar_frame = ctk.CTkFrame(contact, width=40, height=40, corner_radius=20)
        avatar_frame.pack(side="left", padx=8, pady=8)
        avatar_frame.pack_propagate(False)

        inicial = title[0].upper() if title else "?"
        avatar_label = ctk.CTkLabel(
            avatar_frame,
            text=inicial,
            font=ctk.CTkFont(size=18, weight="bold"),
            anchor="center",
        )
        avatar_label.pack(expand=True, fill="both")



        name_label = ctk.CTkLabel(
            contact,
            text=title,
            anchor="w",
            justify="left",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        name_label.pack(fill="x", padx=12, pady=(8, 0))

        role_label = ctk.CTkLabel(
            contact,
            text=subtitle,
            anchor="w",
            justify="left",
            text_color=("gray35", "gray70"),
        )
        role_label.pack(fill="x", padx=12, pady=(0, 6))

        # Al hacer clic en la tarjeta, se abre el detalle de ese usuario.
        for widget in (contact, name_label, role_label):
            widget.bind(
                "<Button-1>",
                lambda _event, selected=user: self.show_user(selected),
            )

    def show_user(self, user: dict[str, Any]) -> None:
        """
        Muestra la tarjeta de detalle del contacto seleccionado con su imagen y datos.
        """
        self.detail_title.configure(text="Detalle del contacto")

        # Borra cualquier contenido anterior del panel derecho.
        for child in self.details.winfo_children():
            child.destroy()


        source = image_value(user)
        try:
            image = load_image(source, (360, 260))
            image.thumbnail((360, 260), Image.Resampling.LANCZOS)
        except Exception:
            image = PLACEHOLDER_IMAGE.copy()

        image = rounded_image(image)
        display_image = ImageTk.PhotoImage(image=image, master=self)

        # Guarda la referencia para que la imagen no desaparezca de la memoria.
        self.image_references.append(display_image)
        self.image_label.configure(image=display_image, text="")

        # Campos visibles en la tarjeta de detalle.
        visible_fields = (
            ("Nombre Completo", "NombreCompleto"),
            ("Telefono", "telefono"),
            ("Email", "email"),
            ("Role", "role"),
        )

        for label, key in visible_fields:
            value = user.get(key)
            row = ctk.CTkFrame(self.details, fg_color="transparent")
            row.pack(fill="x", pady=2)
            row.grid_columnconfigure(1, weight=1)
            ctk.CTkLabel(
                row,
                text=f"{label}:",
                width=130,
                anchor="w",
                font=ctk.CTkFont(weight="bold"),
            ).grid(row=0, column=0, sticky="nw", padx=(0, 10))
            ctk.CTkLabel(
                row,
                text=value_as_text(value),
                anchor="w",
                justify="left",
                wraplength=210,
            ).grid(row=0, column=1, sticky="ew")

        ctk.CTkButton(
            self.details,
            text="Editar contacto",
            command=lambda selected=user: self.open_edit_contact_window(selected),
        ).pack(pady=(12, 4))

    def open_edit_contact_window(self, user: dict[str, Any]) -> None:
        ventana = ctk.CTkToplevel(self)
        ventana.title("Editar contacto")
        ventana.geometry("420x430")
        ventana.resizable(False, False)
        ventana.transient(self)
        ventana.grab_set()
        ventana.grid_columnconfigure(1, weight=1)

        fields = (
            ("nombre", "Nombre *"),
            ("apellido", "Apellido *"),
            ("telefono", "Teléfono"),
            ("email", "Correo"),
            ("role", "Cargo"),
        )
        entradas: dict[str, ctk.CTkEntry] = {}

        for fila, (clave, etiqueta) in enumerate(fields):
            ctk.CTkLabel(ventana, text=etiqueta).grid(
                row=fila, column=0, padx=(20, 12), pady=10, sticky="w"
            )
            entrada = ctk.CTkEntry(ventana, width=250)
            entrada.grid(row=fila, column=1, padx=(0, 20), pady=10, sticky="ew")
            entrada.insert(0, str(user.get(clave) or ""))
            entradas[clave] = entrada

        estado = ctk.CTkLabel(ventana, text="", wraplength=370)
        estado.grid(
            row=len(fields), column=0, columnspan=2, padx=20, pady=(8, 0)
        )
        guardar = ctk.CTkButton(
            ventana,
            text="Guardar cambios",
            command=lambda: self.save_contact_changes(
                user, entradas, ventana, estado, guardar
            ),
        )
        guardar.grid(row=len(fields) + 1, column=0, columnspan=2, pady=20)

    def save_contact_changes(
        self,
        user: dict[str, Any],
        entradas: dict[str, ctk.CTkEntry],
        ventana: ctk.CTkToplevel,
        estado: ctk.CTkLabel,
        guardar: ctk.CTkButton,
    ) -> None:
        values = {key: entry.get().strip() for key, entry in entradas.items()}
        if not values["nombre"] or not values["apellido"]:
            estado.configure(
                text="El nombre y el apellido son obligatorios.",
                text_color="#ff6b6b",
            )
            return

        estado.configure(text="Guardando cambios...", text_color=("gray20", "gray80"))
        guardar.configure(state="disabled")
        ventana.protocol("WM_DELETE_WINDOW", lambda: None)
        threading.Thread(
            target=self._save_contact_changes_worker,
            args=(user["usuario_id"], values, ventana, estado, guardar),
            daemon=True,
        ).start()

    def _save_contact_changes_worker(
        self,
        user_id: int,
        values: dict[str, str],
        ventana: ctk.CTkToplevel,
        estado: ctk.CTkLabel,
        guardar: ctk.CTkButton,
    ) -> None:
        try:
            update_user(user_id, values)
        except Exception as error:
            message = f"No se pudieron guardar los cambios:\n{error}"
            self.after(
                0,
                lambda message=message: self._show_contact_save_error(
                    ventana, estado, guardar, message
                ),
            )
            return

        self.after(0, lambda: self._contact_updated(ventana, user_id))

    def show_message(self, message: str) -> None:
        """
        Muestra un texto de estado en vez de los datos del contacto.
        """
        self.image_label.configure(text="")
        self.detail_title.configure(text=message)

        for child in self.details.winfo_children():
            child.destroy()


# ========================= BACKEND =========================
# Configuración de conexión y operaciones de persistencia en MySQL.

load_dotenv(BASE_DIR / ".env")


def database_config() -> dict[str, Any]:
    """Lee la configuración de conexión desde el archivo .env."""
    required = ("DB_HOST", "DB_USER", "DB_PASSWORD")
    missing = [key for key in required if os.getenv(key) is None]

    if missing:
        raise RuntimeError("Faltan variables en .env: " + ", ".join(missing))

    return {
        "host": os.getenv("DB_HOST"),
        "port": int(os.getenv("DB_PORT", "3306")),
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD"),
        "database": os.getenv("DB_NAME", "administracion"),
    }


def load_users() -> list[dict[str, Any]]:
    """Consulta y devuelve todos los contactos de la tabla usuarios."""
    connection = mysql.connector.connect(**database_config())
    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT
                usuario_id,
                nombre,
                apellido,
                CONCAT(nombre, ' ', apellido) AS NombreCompleto,
                telefono,
                email,
                role,
                EnlaceImagen
            FROM usuarios
            """
        )
        return [dict(row) for row in cursor.fetchall()]
    finally:
        if cursor is not None:
            cursor.close()
        connection.close()


def add_user(values: dict[str, str]) -> None:
    """Guarda un contacto nuevo en la base de datos."""
    connection = mysql.connector.connect(**database_config())
    cursor = None
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO usuarios (nombre, apellido, telefono, email, role)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                values["nombre"],
                values["apellido"],
                values["telefono"] or None,
                values["email"] or None,
                values["role"] or None,
            ),
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        if cursor is not None:
            cursor.close()
        connection.close()


def update_user(user_id: int, values: dict[str, str]) -> None:
    """Actualiza un contacto existente mediante su identificador único."""
    connection = mysql.connector.connect(**database_config())
    cursor = None
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            UPDATE usuarios
            SET nombre = %s, apellido = %s, telefono = %s, email = %s, role = %s
            WHERE usuario_id = %s
            """,
            (
                values["nombre"],
                values["apellido"],
                values["telefono"] or None,
                values["email"] or None,
                values["role"] or None,
                user_id,
            ),
        )
        if cursor.rowcount == 0:
            cursor.execute(
                "SELECT 1 FROM usuarios WHERE usuario_id = %s",
                (user_id,),
            )
            if cursor.fetchone() is None:
                raise LookupError("No se encontró el contacto para actualizar.")
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        if cursor is not None:
            cursor.close()
        connection.close()


if __name__ == "__main__":
    app = DirectorioTelefonico()
    app.mainloop()
