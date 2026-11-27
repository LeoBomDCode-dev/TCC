"""Popula o banco com dados de exemplo. Rode uma vez: python seed.py"""
import json

from database import get_conn, init_db

CATEGORIAS = [
    ("Processadores", "processadores"),
    ("Placas de vídeo", "placas-de-video"),
    ("Memória RAM", "memoria-ram"),
    ("Placas-mãe", "placas-mae"),
    ("Armazenamento", "armazenamento"),
    ("Fontes", "fontes"),
    ("Periféricos", "perifericos"),
]

# (nome, descricao, categoria_slug, marca, preco, condicao, garantia, testado, specs)
PRODUTOS = [
    ("Ryzen 5 3600", "Processador 6 núcleos, acompanha cooler original.", "processadores", "AMD", 520.00, "excelente", 90, True,
     {"Socket": "AM4", "Núcleos": "6", "Threads": "12", "Clock base": "3.6 GHz"}),
    ("Intel Core i5-10400F", "Sem vídeo integrado, funcionando perfeitamente.", "processadores", "Intel", 480.00, "bom", 90, True,
     {"Socket": "LGA 1200", "Núcleos": "6", "Threads": "12", "Clock base": "2.9 GHz"}),
    ("GeForce GTX 1660 Super 6GB", "Usada em uso leve, sem sinais de mineração.", "placas-de-video", "NVIDIA", 950.00, "bom", 60, True,
     {"Memória": "6 GB GDDR6", "Conexões": "HDMI, DisplayPort", "Consumo": "125 W"}),
    ("Radeon RX 580 8GB", "Pequenas marcas na carcaça, testada em jogos.", "placas-de-video", "AMD", 600.00, "marcas_de_uso", 30, True,
     {"Memória": "8 GB GDDR5", "Conexões": "HDMI, DisplayPort, DVI", "Consumo": "185 W"}),
    ("Kit Memória 16GB (2x8GB) DDR4 3200MHz", "Kit dual channel com dissipador.", "memoria-ram", "Corsair", 220.00, "excelente", 90, True,
     {"Tipo": "DDR4", "Capacidade": "16 GB (2x8)", "Frequência": "3200 MHz"}),
    ("Memória 8GB DDR3 1600MHz", "Módulo único para desktop.", "memoria-ram", "Kingston", 60.00, "bom", 30, True,
     {"Tipo": "DDR3", "Capacidade": "8 GB", "Frequência": "1600 MHz"}),
    ("Placa-mãe B450M Pro", "Acompanha espelho traseiro.", "placas-mae", "Gigabyte", 380.00, "bom", 60, True,
     {"Socket": "AM4", "Chipset": "B450", "Memória": "DDR4", "Formato": "Micro-ATX"}),
    ("SSD 480GB SATA", "Saúde da bateria de escrita em 96%.", "armazenamento", "Kingston", 140.00, "excelente", 90, True,
     {"Capacidade": "480 GB", "Interface": "SATA III", "Leitura": "500 MB/s"}),
    ("Fonte 550W 80 Plus Bronze", "Fonte real, cabos modulares inclusos.", "fontes", "Corsair", 260.00, "bom", 60, True,
     {"Potência": "550 W", "Certificação": "80 Plus Bronze", "Modular": "Não"}),
    ("Teclado Mecânico Redragon Kumara", "Switch blue, algumas teclas com brilho de uso.", "perifericos", "Redragon", 120.00, "marcas_de_uso", 30, True,
     {"Tipo": "Mecânico", "Switch": "Blue", "Layout": "ABNT2"}),
]


def main() -> None:
    init_db()
    conn = get_conn()
    if conn.execute("SELECT COUNT(*) FROM produtos").fetchone()[0] > 0:
        print("Banco já possui produtos; nada a fazer.")
        return

    conn.executemany("INSERT OR IGNORE INTO categorias (nome, slug) VALUES (?, ?)", CATEGORIAS)
    ids = {r["slug"]: r["id"] for r in conn.execute("SELECT id, slug FROM categorias")}

    for nome, desc, slug, marca, preco, cond, garantia, testado, specs in PRODUTOS:
        conn.execute(
            """INSERT INTO produtos (nome, descricao, categoria_id, marca, preco, condicao,
                                     garantia_dias, testado, especificacoes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (nome, desc, ids[slug], marca, preco, cond, garantia, int(testado),
             json.dumps(specs, ensure_ascii=False)),
        )
    conn.commit()
    print(f"{len(CATEGORIAS)} categorias e {len(PRODUTOS)} produtos inseridos.")


if __name__ == "__main__":
    main()