from machine import UART, Pin
import time
import sys
import select

# UART2 hacia el otro ESP32: 9600 baudios, 8N1, sin control de flujo
uart = UART(2, baudrate=9600, bits=8, parity=None, stop=1, tx=17, rx=16)

# Para leer del teclado (consola de Thonny) sin bloquear el programa
poll_teclado = select.poll()
poll_teclado.register(sys.stdin, select.POLLIN)

print("Chat iniciado. Escribe un mensaje y presiona Enter para enviarlo.")

while True:
    # 1) Revisar si llegó algo por UART (del otro ESP32)
    if uart.any():
        mensaje = uart.read()
        try:
            print("\nOtro> ", mensaje.decode('utf-8').strip())
        except UnicodeError:
            print("\nOtro (bytes crudos):", mensaje)

    # 2) Revisar si el usuario escribió algo en la consola
    eventos = poll_teclado.poll(50)  # espera hasta 50 ms
    if eventos:
        texto = sys.stdin.readline().strip()
        if texto:
            uart.write(texto + "\r\n")
            print("Yo> ", texto)

    time.sleep(0.05)