# tray-icons-flat

Herramienta universal de Linux y servicio para detectar, adaptar y corregir iconos rotos o discordantes en la bandeja del sistema (system tray). 

Convierte iconos opacos, con fondos cuadrados o colores saturados en iconos planos, sobrios, con transparencia y formato monocromático/simbólico estándar (compatible con **KDE Plasma**, **GNOME**, **XFCE**, etc.).

---

## Características

- 🔍 **Escaneo Inteligente (`scan`)**: Detecta aplicaciones instaladas y reporta si sus iconos de bandeja están en estado original/roto (`Broken/Stock`) o corregidos (`Fixed`).
- 🎨 **Estrategias Universales**:
  - **Sobrescritura limpia de temas XDG (`icon_theme`)**: Inyecta iconos vectoriales con soporte de `ColorScheme-Text` (`currentColor`) en `~/.local/share/icons/` (Papirus, Breeze, hicolor) sin alterar archivos de sistema ni requerir `sudo`.
  - **Parcheador ASAR seguro para Electron (`electron_asar`)**: Permite sustituir recursos de bandeja dentro de paquetes Electron (como Antigravity), preservando siempre un backup prístino (`.stock`).
- 🖼️ **Conversor de Imágenes Integrado (`convert`)**:
  - Remoción automática de fondos sólidos (cajas negras o blancas).
  - Conversión a monocromo sobrio (`#dfdfdf` o configurable) con canal alfa suave.
  - Preservación selectiva de puntos de acento o notificación (puntos rojos, azules, etc.).
  - Ajuste automático al tamaño de bandeja (22x22, 24x24 px) con margen y centrado.
  - Soporte tanto para archivos raster (PNG, JPEG) como vectoriales (SVG).
- 🔄 **Persistencia ante Actualizaciones (`service`)**:
  - Servicio systemd de usuario (`systemd --user`) y entrada de autostart para verificar y reaplicar arreglos automáticamente tras actualizaciones de paquetes o al iniciar sesión.
- 📚 **Biblioteca de Recetas Modular (`recipes/`)**:
  - Formato declarativo YAML para agregar nuevas aplicaciones fácilmente.
  - Asistente interactivo `tray-icons-flat add` para crear nuevas recetas en segundos.

---

## Aplicaciones Incluidas Inicialmente

| Aplicación | ID | Tipo / Estrategia | Descripción del Arreglo |
| :--- | :--- | :--- | :--- |
| **ASUS ROG Control Center** | `asus-rog` | `icon_theme` | Reemplaza el ojo ROG rojo saturado por un icono plano simbólico vectorial transparente (`asus_notif_*`). |
| **Camera Controls** | `cameractrls` | `icon_theme` | Reemplaza el cuadrado negro con lente fotográfica por una apertura de cámara limpia y transparente. |
| **Antigravity IDE** | `antigravity` | `electron_asar` | Parchea `app.asar` para usar el isotipo plano y transparente en vez de la caja blanca con arcoíris. |

---

## Instalación

```bash
git clone https://github.com/locoxella/tray-icons-flat.git
cd tray-icons-flat
pip install --user -e .
```

Asegúrate de que `~/.local/bin` esté en tu `$PATH`.

---

## Uso

### 1. Escaneo del Estado de los Iconos

```bash
tray-icons-flat scan
```

Muestra una tabla con las aplicaciones detectadas y su estado actual.

### 2. Aplicar Arreglos

Corregir todas las aplicaciones detectadas:
```bash
tray-icons-flat fix --all
```

O corregir una aplicación específica:
```bash
tray-icons-flat fix asus-rog
```

> **Nota**: Para ver el cambio en aplicaciones que ya se encuentran en ejecución, reinicia la aplicación correspondiente.

### 3. Revertir al Estado Original (Stock)

```bash
tray-icons-flat revert --all
# o para una app específica:
tray-icons-flat revert antigravity
```

### 4. Activar Servicio de Persistencia (Systemd)

Para que las aplicaciones sigan arregladas aun cuando se actualicen:

```bash
# Instalar y activar el servicio de usuario
tray-icons-flat service install

# Ver el estado
tray-icons-flat service status

# Desinstalar el servicio
tray-icons-flat service uninstall
```

### 5. Conversor de Imágenes a Iconos de Bandeja

Convierte cualquier imagen (PNG, SVG, etc.) a un icono plano listo para el tray:

```bash
# Conversión básica a 22x22 con fondo transparente y monocromo
tray-icons-flat convert /ruta/a/icono.png -o /tmp/icono_plano.png

# Mantener puntos de alerta/notificación (ej. badge rojo)
tray-icons-flat convert /ruta/a/icono.png -o /tmp/icono_plano.png --padding 2

# Ajustar color frontal (por ejemplo blanco puro)
tray-icons-flat convert /ruta/a/icono.png -o /tmp/icono_plano.png --color "#ffffff"
```

### 6. Agregar una Nueva Aplicación a la Biblioteca

Usa el asistente interactivo:
```bash
tray-icons-flat add
```
O crea manualmente una carpeta en `recipes/<nombre-app>/` o en `~/.config/tray-icons-flat/recipes/<nombre-app>/` con un archivo `recipe.yaml` y sus assets.

---

## Estructura de una Receta (`recipe.yaml`)

### Para aplicaciones basadas en Temas de Iconos (XDG / DBus StatusNotifierItem)

```yaml
id: mi-app
name: Mi Aplicación
description: Arreglo de icono para Mi Aplicación
strategy: icon_theme
detector:
  binary: mi-app-bin
  desktop: mi-app.desktop
  # o para Flatpak:
  # flatpak_id: com.ejemplo.MiApp
icons:
  - name: mi-app-tray
    source: assets/mi-app-tray.svg
```

### Para aplicaciones Electron con paquete ASAR

```yaml
id: app-electron
name: Aplicación Electron
strategy: electron_asar
detector:
  path: ~/apps/MiApp/resources/app.asar
asar_path: ~/apps/MiApp/resources/app.asar
replacements:
  icon.png: assets/icon_flat.png
```

---

## Licencia

MIT License.
