import bluetooth
import time
import sys
import select
from machine import Pin
from micropython import const

_IRQ_CENTRAL_CONNECT = const(1)
_IRQ_CENTRAL_DISCONNECT = const(2)
_IRQ_GATTS_WRITE = const(3)

_UART_SERVICE_UUID = bluetooth.UUID("6E400001-B5A3-F393-E0A9-E50E24DCCA9E")
_UART_RX_UUID = bluetooth.UUID("6E400002-B5A3-F393-E0A9-E50E24DCCA9E")
_UART_TX_UUID = bluetooth.UUID("6E400003-B5A3-F393-E0A9-E50E24DCCA9E")

_UART_TX = (_UART_TX_UUID, bluetooth.FLAG_NOTIFY)
_UART_RX = (_UART_RX_UUID, bluetooth.FLAG_WRITE | bluetooth.FLAG_WRITE_NO_RESPONSE)
_UART_SERVICE = (_UART_SERVICE_UUID, (_UART_TX, _UART_RX))

NAME = "ESP32-Chat"

led = Pin(2, Pin.OUT)
numero_recibido = None
conectado = False
conn_handle = None

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

def advertising_payload(name):
    payload = bytearray()
    def _append(adv_type, value):
        nonlocal payload
        payload += bytes((len(value) + 1, adv_type)) + value
    _append(0x01, bytes([0x06]))
    _append(0x09, name.encode())
    return payload

def irq(event, data):
    global conectado, conn_handle
    if event == _IRQ_CENTRAL_CONNECT:
        conn_handle, _, _ = data
        conectado = True
        print("\n[Conectado]\n")
    elif event == _IRQ_CENTRAL_DISCONNECT:
        conectado = False
        conn_handle = None
        print("\n[Desconectado, anunciando de nuevo...]")
        ble.gap_advertise(500000, adv_data=payload)
    elif event == _IRQ_GATTS_WRITE:
        conn_h, value_handle = data
        if value_handle == rx_handle:
            mensaje = ble.gatts_read(rx_handle).decode("utf-8").strip()
            procesar_mensaje(mensaje)

ble = bluetooth.BLE()
ble.active(True)
ble.irq(irq)

((tx_handle, rx_handle),) = ble.gatts_register_services((_UART_SERVICE,))
payload = advertising_payload(NAME)
ble.gap_advertise(500000, adv_data=payload)

print(f"PERIFÉRICO listo, anunciándose como '{NAME}'")
print("Escribe texto o un número y presiona Enter para enviarlo.")

poll_teclado = select.poll()
poll_teclado.register(sys.stdin, select.POLLIN)

while True:
    eventos = poll_teclado.poll(50)
    if eventos:
        texto = sys.stdin.readline().strip()
        if texto:
            if conectado:
                ble.gatts_notify(conn_handle, tx_handle, texto + "\r\n")
                print("Yo> ", texto)
            else:
                print("(Aún no conectado, espera...)")
    time.sleep(0.05)