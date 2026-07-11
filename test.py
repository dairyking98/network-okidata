import socket

def is_printer_ready(printer_ip, printer_port):
    """
    Attempts to query the printer status by sending an inquiry command.
    This example sends an ENQ (ASCII 5) command and waits for a response.
    
    Returns:
        (bool, bytes or str): A tuple where the first element indicates if the printer is ready,
                              and the second element contains the raw response or error message.
    """
    # The ENQ command (0x05) is a common inquiry code, but may not be supported by your printer.
    STATUS_QUERY = b'\x05'
    
    try:
        # Create a socket connection to the printer.
        with socket.create_connection((printer_ip, printer_port), timeout=5) as s:
            # Send the inquiry command.
            s.sendall(STATUS_QUERY)
            # Try to read a response (adjust the buffer size as needed).
            response = s.recv(1024)
            if response:
                return True, response
            else:
                return False, b"No response received."
    except Exception as e:
        return False, str(e)

# Example usage:
if __name__ == '__main__':
    printer_ip = "192.168.4.28"  # Replace with your printer's IP.
    printer_port = 9100           # Replace with your printer's port.
    
    ready, info = is_printer_ready(printer_ip, printer_port)
    if ready:
        print("Printer is ready. Response:", info)
    else:
        print("Printer is not ready. Error/Info:", info)
