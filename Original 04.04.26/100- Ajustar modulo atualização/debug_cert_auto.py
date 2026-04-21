from pathlib import Path

CERT = Path("certificados.py")
src = CERT.read_text(encoding="utf-8")

# Ver como está o preenchimento do cliente
idx = src.find("_of_data")
print("=== OF DATA ===")
print(repr(src[max(0,idx-100):idx+400]))

# Ver como está a composição química
idx2 = src.find("composicao_quimica")
print("\n=== COMPOSIÇÃO QUÍMICA ===")
print(repr(src[max(0,idx2-100):idx2+400]))
