import erp_integration

print("Testando motor determinístico de ERP...")

# Teste com uma string comum que deve estar no banco ou apenas falhar graciosamente (ValueError) e não com AttributeError
try:
    cod, cnpj = erp_integration.validar_fornecedor("alfa")
    print(f"Sucesso! Fornecedor Alfa encontrado: Codigo={cod}, CNPJ={cnpj}")
except ValueError as e:
    print(f"Validacao funcionou mas fornecedor nao existe: {e}")
except Exception as e:
    print(f"ERRO INESPERADO no Fornecedor: {type(e).__name__} - {e}")

try:
    cod_loja = erp_integration.validar_loja("matriz")
    print(f"Sucesso! Loja encontrada: {cod_loja}")
except ValueError as e:
    print(f"Validacao funcionou mas loja nao existe: {e}")
except Exception as e:
    print(f"ERRO INESPERADO na Loja: {type(e).__name__} - {e}")

print("Fim do teste.")
