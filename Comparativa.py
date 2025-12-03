import matplotlib.pyplot as plt

# DADOS DAS DUAS INSTÂNCIAS

melhoras_inst1 = [230.0, 210.5, 185.3, 170.2, 140.55]
melhoras_inst2 = [240.0, 205.0, 190.0, 175.5, 165.2]

x = list(range(1, len(melhoras_inst1) + 1))

# GRÁFICO COM DUAS LINHAS

plt.figure(figsize=(10, 6))

# Instância 1
plt.plot(x, melhoras_inst1, marker='o', linewidth=2, label='Instância 1')

# Instância 2
plt.plot(x, melhoras_inst2, marker='s', linewidth=2, label='Instância 2')

plt.title("Comparativo de Melhorias entre Duas Instâncias", fontsize=14)
plt.xlabel("Iterações / Melhorias", fontsize=12)
plt.ylabel("Distância Total", fontsize=12)

plt.grid(True, linestyle='--', alpha=0.4)
plt.legend()

plt.tight_layout()
plt.show()
