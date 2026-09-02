import bluetooth
import time
import sys
import select
import struct
from machine import Pin
from micropython import const

_IRQ_SCAN_RESULT = const(5)
_IRQ_SCAN_DONE = const(6)
_IRQ_PERIPHERAL_CONNECT = const(7)
_IRQ_PERIPHERAL_DISCONNECT = const(8)
_IRQ_GATTC_SERVICE_RESULT = const(9)
_IRQ_GATTC_CHARACTERISTIC_RESULT = const(11)
_IRQ_GATTC_CHARACTERISTIC_DONE = const(12)
_IRQ_GATTC_NOTIFY = const(18)

_UART_SERVICE_UUID = bluetooth.UUID("6E400001-B5A3-F393-E0A9-E50E24DCCA9E")
_UART_RX_UUID = bluetooth.UUID("6E400002-B5A3-F393-E0A9-E50E24DCCA9E")
_UART_TX_UUID = bluetooth.UUID("6E400003-B5A3-F393-E0A9-E50E24DCCA9E")

NAME = "ESP32-Chat"

led = Pin(2, Pin.OUT)
numero_recibido = None
conectado = False
conn_handle = None
c_tx_handle = None
c_rx_handle = None
addr_type_objetivo = None
addr_objetivo = None

def parpadear(veces):
    for _ in range(veces):
        led.value(1)
        time.sleep(0.3)
        led.value(0)
        time.sleep(0.3)

def procesar_mensaje(mensaje):
    global numero_recibido
    if mensaje.isdigit():
        numero_recibido = int(mensaje)
        print(f"\nOtro> {numero_recibido} (parpadeando LED)")
        parpadear(numero_recibido)
    else:
        print("\nOtro> ", mensaje)

def decode_name(adv_data):
    i = 0
    while i + 1 < len(adv_data):
        length = adv_data[i]
        if length == 0:
            break
        ad_type = adv_data[i + 1]
        if ad_type in (0x08, 0x09):
            return bytes(adv_data[i + 2: i + 1 + length]).decode("utf-8")
        i += 1 + length
    return ""

def irq(event, data):
    global conectado, conn_handle, c_tx_handle, c_rx_handle
    global addr_type_objetivo, addr_objetivo

    if event == _IRQ_SCAN_RESULT:
        addr_type, addr, adv_type, rssi, adv_data = data
        if decode_name(adv_data) == NAME:
            addr_type_objetivo = addr_type
            addr_objetivo = bytes(addr)
            ble.gap_scan(None)

    elif event == _IRQ_SCAN_DONE:
        if addr_objetivo:
            print("Encontrado, conectando...")
            ble.gap_connect(addr_type_objetivo, addr_objetivo)
        else:
            print("No encontrado, reintentando...")
            buscar()

    elif event == _IRQ_PERIPHERAL_CONNECT:
        conn_handle, _, _ = data
        ble.gattc_discover_services(conn_handle)

    elif event == _IRQ_PERIPHERAL_DISCONNECT:
        print("\n[Desconectado, reintentando...]")
        conectado = False
        conn_handle = None
        c_tx_handle = None
        c_rx_handle = None
        buscar()

    elif event == _IRQ_GATTC_SERVICE_RESULT:
        conn_h, start_handle, end_handle, uuid = data
        if uuid == _UART_SERVICE_UUID:
            ble.gattc_discover_characteristics(conn_h, start_handle, end_handle)

    elif event == _IRQ_GATTC_CHARACTERISTIC_RESULT:
        conn_h, def_handle, value_handle, properties, uuid = data
        if uuid == _UART_RX_UUID:
            c_rx_handle = value_handle
        elif uuid == _UART_TX_UUID:
            c_tx_handle = value_handle

    elif event == _IRQ_GATTC_CHARACTERISTIC_DONE:
        if c_tx_handle is not None and c_rx_handle is not None:
            ble.gattc_write(conn_handle, c_tx_handle + 1, struct.pack("<h", 1), 1)
            conectado = True
            print("\n[Conectado]\n")

    elif event == _IRQ_GATTC_NOTIFY:
        conn_h, value_handle, notify_data = data
        if value_handle == c_tx_handle:
            mensaje = bytes(notify_data).decode("utf-8").strip()
            procesar_mensaje(mensaje)

ble = bluetooth.BLE()
ble.active(True)
ble.irq(irq)

def buscar():
    print(f"Buscando '{NAME}'...")
    ble.gap_scan(4000, 30000, 30000)

buscar()

print("CENTRAL listo.")
print("Escribe texto o un número y presiona Enter para enviarlo.")

poll_teclado = select.poll()
poll_teclado.register(sys.stdin, select.POLLIN)

while True:
    eventos = poll_teclado.poll(50)
    if eventos:
        texto = sys.stdin.readline().strip()
        if texto:
            if conectado:
                ble.gattc_write(conn_handle, c_rx_handle, texto + "\r\n", 0)
                print("Yo> ", texto)
            else:
                print("(Aún no conectado, espera...)")
    time.sleep(0.05)