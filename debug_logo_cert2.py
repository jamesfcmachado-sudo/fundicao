from pathlib import Path

CFG = Path("empresa_config.py")
src = CFG.read_text(encoding="utf-8")

# Localiza o fim do bloco de orientacao do certificado
idx = src.find('key="orient_cert_radio"')
fim_bloco = src.find('\n', src.find(')', idx)) + 1
# Pega mais algumas linhas para encontrar o fechamento
fim_bloco2 = src.find('\n\n            # Upload novo template', fim_bloco)

print("Texto apos orient_cert_radio:")
print(repr(src[idx:idx+300]))
