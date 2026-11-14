from __future__ import annotations

import base64
from io import BytesIO
import logging
import os
from typing import Any
from urllib.parse import urlparse

from flask import Flask, flash, redirect, render_template, request, url_for
from PIL import Image

from DirectorioTelefonico import add_user, load_users, update_user


app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY") or os.urandom(32)
logging.basicConfig(level=logging.INFO)

CONTACT_FIELDS = ("nombre", "apellido", "telefono", "email", "role")


def image_src(contact: dict[str, Any]) -> str | None:
    source = contact.get("EnlaceImagen")
    if isinstance(source, bytes):
        try:
            image_format = Image.open(BytesIO(source)).format
            mime_type = Image.MIME.get(image_format or "", "image/jpeg")
        except (OSError, ValueError):
            return None
        return f"data:{mime_type};base64," + base64.b64encode(source).decode("ascii")
    if source:
        parsed = urlparse(str(source).strip())
        if parsed.scheme in {"http", "https"} and parsed.netloc:
            return str(source).strip()
    return None


app.jinja_env.globals["image_src"] = image_src


@app.route("/", methods=["GET"])
def index():
    search = request.args.get("q", "").strip()
    selected_id = request.args.get("contact", type=int)
    try:
        contacts = load_users()
    except Exception:
        logging.exception("No se pudieron cargar los contactos")
        flash("No se pudo conectar con el directorio. Revisa la configuración de MySQL.", "error")
        contacts = []

    matches = [
        contact
        for contact in contacts
        if not search
        or search.casefold()
        in " ".join(
            str(value or "")
            for key, value in contact.items()
            if key != "EnlaceImagen" and not isinstance(value, bytes)
        ).casefold()
    ]
    selected = next(
        (contact for contact in matches if contact.get("usuario_id") == selected_id),
        matches[0] if matches else None,
    )
    return render_template(
        "index.html",
        contacts=matches,
        selected=selected,
        search=search,
        total_contacts=len(contacts),
    )


def read_contact_form() -> dict[str, str] | None:
    values = {field: request.form.get(field, "").strip() for field in CONTACT_FIELDS}
    if not values["nombre"] or not values["apellido"]:
        flash("El nombre y el apellido son obligatorios.", "error")
        return None
    return values


@app.route("/contactos", methods=["POST"])
def create_contact():
    values = read_contact_form()
    if values is not None:
        try:
            add_user(values)
            flash("El contacto se agregó correctamente.", "success")
        except Exception:
            logging.exception("No se pudo guardar un contacto")
            flash("No se pudo guardar el contacto. Inténtalo de nuevo.", "error")
    return redirect(url_for("index"))


@app.route("/contactos/<int:contact_id>", methods=["POST"])
def edit_contact(contact_id: int):
    values = read_contact_form()
    if values is not None:
        try:
            update_user(contact_id, values)
            flash("Los cambios se guardaron correctamente.", "success")
        except LookupError:
            flash("No se encontró el contacto que intentas editar.", "error")
        except Exception:
            logging.exception("No se pudo actualizar el contacto")
            flash("No se pudieron guardar los cambios. Inténtalo de nuevo.", "error")
    return redirect(url_for("index", contact=contact_id))


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.getenv("PORT", "5000")), debug=False)
