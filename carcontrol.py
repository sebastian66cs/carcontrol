import serial
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import threading
import platform

INPUTS_AVAILABLE = False
try:
    from inputs import get_gamepad, UnpluggedError
    INPUTS_AVAILABLE = True
except ImportError:
    pass

# ----- CONFIGURACIÓN SERIAL -----
PORT = "COM11"
BAUD = 9600
ser = None

# Variables globales
keys_pressed = set()
is_moving = False
command_count = 0
controller_thread = None
controller_running = False
dpad_state = {"x": 0, "y": 0}

# ====== FUNCIONES ======

def init_controller():
    global controller_thread, controller_running
    
    if not INPUTS_AVAILABLE:
        controller_status.config(text="● NO DISPONIBLE", foreground="#FF8800")
        controller_name.config(text="Librería 'inputs' no instalada")
        log_message("○ Control Xbox no disponible")
        return
    
    def detect_controller():
        global controller_running, controller_thread
        try:
            get_gamepad() # Test rápido
            root.after(0, lambda: controller_status.config(text="● CONECTADO", foreground="#00FF88"))
            root.after(0, lambda: controller_name.config(text="Control Xbox detectado"))
            root.after(0, lambda: log_message("✓ Control Xbox conectado"))
            
            controller_running = True
            controller_thread = threading.Thread(target=read_controller, daemon=True)
            controller_thread.start()
            
        except:
            root.after(0, lambda: controller_status.config(text="● NO DETECTADO", foreground="#FF4444"))
            root.after(0, lambda: controller_name.config(text="Conecta un control de Xbox"))
    
    threading.Thread(target=detect_controller, daemon=True).start()

def read_controller():
    global dpad_state, controller_running
    while controller_running:
        try:
            events = get_gamepad()
            for event in events:
                if event.code == 'ABS_HAT0X': dpad_state["x"] = event.state 
                elif event.code == 'ABS_HAT0Y': dpad_state["y"] = event.state
                elif event.code == 'BTN_SOUTH' and event.state == 1:
                    root.after(0, lambda: send("S")); root.after(0, unhighlight_all_buttons)
            process_dpad()
        except:
            controller_running = False
            break

def process_dpad():
    x, y = dpad_state["x"], dpad_state["y"]
    cmd = None
    if y == -1: cmd = "F"; root.after(0, lambda: highlight_button(btn_up))
    elif y == 1: cmd = "B"; root.after(0, lambda: highlight_button(btn_down))
    elif x == -1: cmd = "L"; root.after(0, lambda: highlight_button(btn_left))
    elif x == 1: cmd = "R"; root.after(0, lambda: highlight_button(btn_right))
    else: cmd = "S"; root.after(0, unhighlight_all_buttons)
    
    if cmd: root.after(0, lambda c=cmd: send(c))

def connect():
    global ser
    try:
        ser = serial.Serial(PORT, BAUD, timeout=1)
        status_label.config(text="● CONECTADO", foreground="#00FF88")
        status_detail.config(text=f"{PORT} @ {BAUD}")
        connect_btn.config(state="disabled")
        disconnect_btn.config(state="normal")
        log_message("✓ Conectado")
        root.after(500, update_speed_a)
        root.after(600, update_speed_b)
    except Exception as e:
        messagebox.showerror("Error", str(e))
        log_message("✗ Error conexión")

def disconnect():
    global ser
    if ser and ser.is_open: ser.close()
    status_label.config(text="● DESCONECTADO", foreground="#FF4444")
    status_detail.config(text="Sin conexión")
    connect_btn.config(state="normal")
    disconnect_btn.config(state="disabled")
    log_message("○ Desconectado")

def send(cmd):
    global command_count
    if ser and ser.is_open:
        try:
            ser.write(cmd.encode())
            command_count += 1
            update_stats()
            if cmd[0] not in ['X', 'Y']: log_message(f"→ {cmd}")
        except: pass

def update_speed_a(event=None):
    if ser and ser.is_open:
        val = int(slider_a.get())
        send(f"X{val}")
        val_label_a.config(text=f"{val}")

def update_speed_b(event=None):
    if ser and ser.is_open:
        val = int(slider_b.get())
        send(f"Y{val}")
        val_label_b.config(text=f"{val}")

def log_message(msg):
    timestamp = datetime.now().strftime("%H:%M:%S")
    log_text.config(state="normal")
    log_text.insert("1.0", f"[{timestamp}] {msg}\n")
    log_text.config(state="disabled")
    log_text.see("end") # Auto-scroll al final del log

def update_stats():
    commands_label.config(text=str(command_count))

def on_key_press(event):
    global is_moving
    key = event.keysym.lower()
    if key in ["w", "a", "s", "d", "space"] and key not in keys_pressed:
        keys_pressed.add(key)
        if not is_moving:
            is_moving = True
            if key == "w": send("F"); highlight_button(btn_up)
            elif key == "s": send("B"); highlight_button(btn_down)
            elif key == "a": send("L"); highlight_button(btn_left)
            elif key == "d": send("R"); highlight_button(btn_right)
            elif key == "space": send("S"); highlight_button(btn_stop)

def on_key_release(event):
    global is_moving
    key = event.keysym.lower()
    if key in keys_pressed:
        keys_pressed.discard(key)
        if key in ["w", "a", "s", "d"]:
            is_moving = False
            send("S")
            unhighlight_all_buttons()

def highlight_button(button):
    unhighlight_all_buttons()
    button.config(bg="#00AAFF", fg="white")

def unhighlight_all_buttons():
    for btn in [btn_up, btn_down, btn_left, btn_right, btn_stop]:
        btn.config(bg="#2D2D2D", fg="white")

def button_press(cmd, button):
    send(cmd)
    highlight_button(button)

def button_release():
    send("S")
    unhighlight_all_buttons()
 
def _on_mousewheel(event):
    # Scroll con rueda del ratón
    if platform.system() == 'Windows':
        canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    elif platform.system() == 'Darwin': # macOS
        canvas.yview_scroll(int(-1*event.delta), "units")
    else: # Linux
        if event.num == 4: canvas.yview_scroll(-1, "units")
        elif event.num == 5: canvas.yview_scroll(1, "units")

# ====== GUI SETUP ======
root = tk.Tk()
root.title("Car Controller Pro - Scrollable")
root.geometry("1100x700")
root.configure(bg="#0D0D0D")

root.bind("<KeyPress>", on_key_press)
root.bind("<KeyRelease>", on_key_release)

# 1. BARRA SUPERIOR (FIJA)
top_bar = tk.Frame(root, bg="#1A1A1A", height=60)
top_bar.pack(fill="x", side="top")
top_bar.pack_propagate(False)

tk.Label(top_bar, text="CAR CONTROLLER", font=("Segoe UI", 18, "bold"), bg="#1A1A1A", fg="#00AAFF").pack(side="left", padx=20)
tk.Label(top_bar, text="v1.0", font=("Segoe UI", 9), bg="#1A1A1A", fg="#666666").pack(side="left")

# 2. CONTENEDOR PARA SCROLL (Canvas + Scrollbar)
scroll_container = tk.Frame(root, bg="#0D0D0D")
scroll_container.pack(fill="both", expand=True)

canvas = tk.Canvas(scroll_container, bg="#0D0D0D", highlightthickness=0)
scrollbar = ttk.Scrollbar(scroll_container, orient="vertical", command=canvas.yview)

# Frame INTERNO que se moverá (aquí va todo el contenido)
scrollable_frame = tk.Frame(canvas, bg="#0D0D0D")

# Configuración del scroll
scrollable_frame.bind(
    "<Configure>",
    lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
)
# ¡IMPORTANTE! Forzar que el frame interno tenga el mismo ancho que el canvas
canvas.bind(
    "<Configure>",
    lambda e: canvas.itemconfig(window_id, width=e.width)
)

window_id = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
canvas.configure(yscrollcommand=scrollbar.set)

# Empaquetado del scroll
canvas.pack(side="left", fill="both", expand=True)
scrollbar.pack(side="right", fill="y")

# Bindings para la rueda del ratón
canvas.bind_all("<MouseWheel>", _on_mousewheel) # Windows
canvas.bind_all("<Button-4>", _on_mousewheel)   # Linux up
canvas.bind_all("<Button-5>", _on_mousewheel)   # Linux down

# ============ CONTENIDO PRINCIPAL (Dentro del scrollable_frame) ============
# Usamos un frame wrapper para dar márgenes
main_wrapper = tk.Frame(scrollable_frame, bg="#0D0D0D")
main_wrapper.pack(fill="both", expand=True, padx=20, pady=10)

# CONFIGURACIÓN DE GRID (ESTO FALTABA PARA EL RESCALADO CORRECTO)
main_wrapper.columnconfigure(0, weight=1) # Columna izquierda (Controles) se expande
main_wrapper.columnconfigure(1, weight=0) # Columna derecha (Log) tamaño fijo

# Layout de dos columnas
left_panel = tk.Frame(main_wrapper, bg="#0D0D0D")
left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

right_panel = tk.Frame(main_wrapper, bg="#0D0D0D", width=350)
right_panel.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

# --- STATUS CARD ---
status_card = tk.Frame(left_panel, bg="#1A1A1A")
status_card.pack(fill="x", pady=(0, 15))

status_header = tk.Frame(status_card, bg="#1A1A1A")
status_header.pack(fill="x", padx=20, pady=10)
tk.Label(status_header, text="ESTADO DE CONEXIÓN", font=("Segoe UI", 11, "bold"), bg="#1A1A1A", fg="white").pack(side="left")

# Status content grid
status_content = tk.Frame(status_card, bg="#1A1A1A")
status_content.pack(fill="x", padx=20, pady=(0, 15))

status_label = tk.Label(status_content, text="● DESCONECTADO", font=("Segoe UI", 12, "bold"), bg="#1A1A1A", fg="#FF4444")
status_label.pack(anchor="w")
status_detail = tk.Label(status_content, text="Sin conexión", font=("Segoe UI", 9), bg="#1A1A1A", fg="#888888")
status_detail.pack(anchor="w")

# Botones de conexión
btn_frame = tk.Frame(status_content, bg="#1A1A1A")
btn_frame.pack(fill="x", pady=(10, 0))
connect_btn = tk.Button(btn_frame, text="CONECTAR", command=connect, bg="#00AA44", fg="white", font=("Segoe UI", 10, "bold"), relief="flat", padx=20, pady=8, cursor="hand2")
connect_btn.pack(side="left", padx=(0, 10))
disconnect_btn = tk.Button(btn_frame, text="DESCONECTAR", command=disconnect, bg="#CC3333", fg="white", font=("Segoe UI", 10, "bold"), relief="flat", state="disabled", padx=20, pady=8, cursor="hand2")
disconnect_btn.pack(side="left")

# Status Xbox
controller_frame = tk.Frame(status_content, bg="#1A1A1A")
controller_frame.pack(fill="x", pady=(15, 0))
controller_status = tk.Label(controller_frame, text="● CONTROL NO DETECTADO", font=("Segoe UI", 9, "bold"), bg="#1A1A1A", fg="#FF4444")
controller_status.pack(anchor="w")
controller_name = tk.Label(controller_frame, text="Conecta un control de Xbox para usarlo", font=("Segoe UI", 8), bg="#1A1A1A", fg="#666666")
controller_name.pack(anchor="w")

# --- CONTROLS CARD ---
controls_card = tk.Frame(left_panel, bg="#1A1A1A")
controls_card.pack(fill="both", expand=True, pady=(0, 15)) # Expand=True para que ocupe espacio vertical

tk.Label(controls_card, text="CONTROLES DE DIRECCIÓN", font=("Segoe UI", 11, "bold"), bg="#1A1A1A", fg="white").pack(anchor="w", padx=20, pady=15)

controls_grid = tk.Frame(controls_card, bg="#1A1A1A")
controls_grid.pack(expand=True, pady=30) # Más padding vertical para centrarlo visualmente
btn_style = {"font": ("Segoe UI", 20, "bold"), "width": 6, "height": 2, "bg": "#2D2D2D", "fg": "white", "relief": "flat", "cursor": "hand2"}

btn_up = tk.Button(controls_grid, text="▲", **btn_style)
btn_up.grid(row=0, column=1, pady=10)
btn_left = tk.Button(controls_grid, text="◄", **btn_style)
btn_left.grid(row=1, column=0, padx=10)
btn_stop = tk.Button(controls_grid, text="■", **btn_style)
btn_stop.grid(row=1, column=1, padx=10)
btn_right = tk.Button(controls_grid, text="►", **btn_style)
btn_right.grid(row=1, column=2, padx=10)
btn_down = tk.Button(controls_grid, text="▼", **btn_style)
btn_down.grid(row=2, column=1, pady=10)

# Bindings botones
for btn, cmd in [(btn_up, "F"), (btn_down, "B"), (btn_left, "L"), (btn_right, "R"), (btn_stop, "S")]:
    btn.bind("<ButtonPress>", lambda e, c=cmd, b=btn: button_press(c, b))
    btn.bind("<ButtonRelease>", lambda e: button_release())

# --- SPEED CONTROL CARD ---
speed_card = tk.Frame(left_panel, bg="#1A1A1A")
speed_card.pack(fill="x", pady=(0, 15))

tk.Label(speed_card, text="CONTROL DE VELOCIDAD (PWM)", font=("Segoe UI", 11, "bold"), bg="#1A1A1A", fg="white").pack(anchor="w", padx=20, pady=15)

# Slider A
frame_a = tk.Frame(speed_card, bg="#1A1A1A")
frame_a.pack(fill="x", padx=20, pady=5)
tk.Label(frame_a, text="Motor Izquierdo (A)", bg="#1A1A1A", fg="#AAAAAA").pack(side="left")
val_label_a = tk.Label(frame_a, text="255", bg="#1A1A1A", fg="#00AAFF", font=("Segoe UI", 10, "bold"))
val_label_a.pack(side="right")
slider_a = ttk.Scale(speed_card, from_=0, to=255, orient="horizontal", command=lambda v: val_label_a.config(text=str(int(float(v)))))
slider_a.set(255)
slider_a.pack(fill="x", padx=20, pady=(0, 15))
slider_a.bind("<ButtonRelease-1>", update_speed_a)

# Slider B
frame_b = tk.Frame(speed_card, bg="#1A1A1A")
frame_b.pack(fill="x", padx=20, pady=5)
tk.Label(frame_b, text="Motor Derecho (B)", bg="#1A1A1A", fg="#AAAAAA").pack(side="left")
val_label_b = tk.Label(frame_b, text="255", bg="#1A1A1A", fg="#00AAFF", font=("Segoe UI", 10, "bold"))
val_label_b.pack(side="right")
slider_b = ttk.Scale(speed_card, from_=0, to=255, orient="horizontal", command=lambda v: val_label_b.config(text=str(int(float(v)))))
slider_b.set(255)
slider_b.pack(fill="x", padx=20, pady=(0, 20))
slider_b.bind("<ButtonRelease-1>", update_speed_b)

# --- RIGHT PANEL (LOG) ---
stats_card = tk.Frame(right_panel, bg="#1A1A1A")
stats_card.pack(fill="x", pady=(0, 15))
tk.Label(stats_card, text="ESTADÍSTICAS", font=("Segoe UI", 11, "bold"), bg="#1A1A1A", fg="white").pack(anchor="w", padx=20, pady=10)
commands_label = tk.Label(stats_card, text="0", font=("Segoe UI", 24, "bold"), bg="#1A1A1A", fg="#00AAFF")
commands_label.pack(pady=5)
tk.Label(stats_card, text="Comandos enviados", bg="#1A1A1A", fg="#888888").pack(pady=(0, 15))

log_card = tk.Frame(right_panel, bg="#1A1A1A")
log_card.pack(fill="both", expand=True) # El log se expande verticalmente
log_header = tk.Frame(log_card, bg="#1A1A1A")
log_header.pack(fill="x", padx=20, pady=10)
tk.Label(log_header, text="REGISTRO DE ACTIVIDAD", font=("Segoe UI", 11, "bold"), bg="#1A1A1A", fg="white").pack(side="left")
clear_log_btn = tk.Button(log_header, text="✕ Limpiar", command=lambda: (log_text.config(state="normal"), log_text.delete("1.0", "end"), log_text.config(state="disabled")), font=("Segoe UI", 8), bg="#CC3333", fg="white", activebackground="#EE4444", relief="flat", bd=0, cursor="hand2", padx=10, pady=2)
clear_log_btn.pack(side="right")

log_text = tk.Text(log_card, font=("Consolas", 9), bg="#0D0D0D", fg="#00FF88", relief="flat", height=25) # Altura inicial mayor
log_text.pack(fill="both", expand=True, padx=10, pady=(0, 10))

log_message("GUI v1.0 Iniciada")
init_controller()

root.mainloop()