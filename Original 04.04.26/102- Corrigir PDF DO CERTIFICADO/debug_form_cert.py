from pathlib import Path

CERT = Path("certificados.py")
src = CERT.read_text(encoding="utf-8")

# Ver como o numero do certificado e gerado
idx = src.find("numero_cert")
print("=== numero_cert ===")
print(repr(src[max(0,idx-50):idx+200]))

# Ver como o cliente e definido no formulario
idx2 = src.find("cert_cliente")
print("\n=== cert_cliente ===")
print(repr(src[max(0,idx2-100):idx2+200]))

# Ver como OF e definida
idx3 = src.find("_of_cert")
print("\n=== _of_cert ===")
print(repr(src[idx3:idx3+200]))
