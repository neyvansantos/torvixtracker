from PIL import Image

# Abre a imagem original
img = Image.open(r"c:\Users\neyva\Documents\Rastreador Ocular\assets\icon.png")

# Calcula as dimensões para o canvas quadrado (usa a maior dimensão)
size = max(img.size)
canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))

# Centraliza a imagem no canvas
offset = ((size - img.width) // 2, (size - img.height) // 2)
canvas.paste(img, offset)

# Salva como ICO com múltiplos tamanhos, mantendo a proporção
canvas.save(r"c:\Users\neyva\Documents\Rastreador Ocular\assets\icon.ico", format="ICO", sizes=[(256, 256), (128, 128), (64, 64), (32, 32), (16, 16)])

print("Icon saved successfully with correct aspect ratio.")
