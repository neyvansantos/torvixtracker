---
description: Comando de automação de release para o Torvix Tracker. Realiza verificações, atualiza versões, gera build e sincroniza com GitHub.
---

# /lancar - Release Automation

## Propósito

Este comando automatiza o ciclo de vida de uma nova versão do Torvix Tracker, garantindo que o código esteja saudável antes de empacotar e distribuir.

---

## Fluxo de Execução

O comando `/lancar` segue estas fases obrigatórias:

### 1. Fase de Validação (Obrigatória)
Antes de qualquer alteração, o assistente deve rodar o checklist de saúde do projeto:
`python .agent/scripts/checklist.py .`

- **Se falhar (P0/P1):** Parar imediatamente e mostrar os erros ao usuário.
- **Se passar:** Prosseguir para a coleta de dados.

### 2. Coleta de Informações
O assistente deve perguntar ao usuário:
1. **Nova Versão:** (Ex: 0.1.5)
2. **O que mudou (Changelog):** (Ex: "Melhoria na sensibilidade da cabeça")

### 3. Execução do Script de Release
Com os dados em mãos, o assistente executa o script principal:
`python release.py <versao> "<changelog>"`

Este script fará:
- Update em `eye_drive_tracker/__init__.py`
- Update em `version.json`
- Execução de `build_exe.py` (Geração do .exe)
- Git add, commit e push.

### 4. Conclusão e Relatório
Ao final, o assistente deve apresentar um resumo:
- Status da Versão
- Link/Caminho do executável gerado
- Confirmação de sincronização com GitHub

---

## Como usar

```
/lancar
```

O assistente iniciará o processo interativo guiado.
