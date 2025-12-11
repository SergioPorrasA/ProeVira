import pdfplumber
import os

# Ruta al PDF problemático (2009)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROEVIRA_DIR = os.path.dirname(SCRIPT_DIR) # .../ProeVira
UPDATE_DIR = os.path.dirname(PROEVIRA_DIR) # .../Proevira_Update
PDF_PATH = os.path.join(UPDATE_DIR, 'Conversor_PDF_CSV', 'pdfs', 'dengue_2009.pdf')

print(f"Propiedades de texto para: {PDF_PATH}")

with pdfplumber.open(PDF_PATH) as pdf:
    page = pdf.pages[0]
    
    # Extraer palabras con sus coordenadas
    words = page.extract_words(x_tolerance=3, keep_blank_chars=True)
    
    # Filtrar solo palabras que parecen ser parte de la fila de Hidalgo (donde vimos el error)
    # Hidalgo estaba en la fila 14 aprox del CSV original
    
    print("\n--- Palabras en la zona de 'Hidalgo' ---")
    hidalgo_words = [w for w in words if "Hidalgo" in w['text'] or (w['top'] > 200 and w['top'] < 300)]
    
    # Imprimir algunas para ver la separación horizontal (x0, x1)
    # Buscamos saltos de línea visual (top similar)
    
    # Agrupar por línea (top similar)
    rows = {}
    for w in words:
        top_int = int(w['top'] / 5) * 5 # Agrupar con tolerancia vertical de 5
        if top_int not in rows: rows[top_int] = []
        rows[top_int].append(w)
        
    # Imprimir las filas que contienen datos numéricos densos
    count = 0
    for top, row_words in sorted(rows.items()):
        # Check if row looks like the Hidalgo row
        text_line = " ".join([w['text'] for w in row_words])
        if "Hidalgo" in text_line or "Aguascalientes" in text_line:
            print(f"\nROW (top ~{top*5}): {text_line}")
            print("  Coords (text, x0, x1, gap_to_next):")
            row_words.sort(key=lambda x: x['x0'])
            for i, w in enumerate(row_words):
                gap = 0
                if i < len(row_words) - 1:
                    gap = row_words[i+1]['x0'] - w['x1']
                print(f"    '{w['text']}' : x0={w['x0']:.2f}, x1={w['x1']:.2f}, gap={gap:.2f}")
