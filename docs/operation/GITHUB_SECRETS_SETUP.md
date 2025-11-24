# Configuração de Secrets para Deploy via GitHub Actions

Para que o workflow de deploy funcione, você precisa configurar 3 secrets no GitHub:

## 1. Obter os Valores

### VERCEL_TOKEN
1. Acesse: https://vercel.com/account/tokens
2. Clique em "Create Token"
3. Dê um nome (ex: "GitHub Actions Deploy")
4. Selecione o escopo apropriado
5. Copie o token gerado

### VERCEL_ORG_ID e VERCEL_PROJECT_ID

Execute no terminal do projeto:

```bash
# Instalar Vercel CLI (se ainda não tiver)
npm install -g vercel

# Fazer login
vercel login

# Vincular ao projeto
vercel link
```

Após o `vercel link`, será criado o arquivo `.vercel/project.json`:

```bash
# Ver o conteúdo
cat .vercel/project.json
```

O arquivo terá algo como:
```json
{
  "orgId": "flavio-lopes-projects-87104ba4",
  "projectId": "prj_xxxxxxxxxxxxx"
}
```

- `orgId` = **VERCEL_ORG_ID**
- `projectId` = **VERCEL_PROJECT_ID**

## 2. Adicionar os Secrets no GitHub

1. Acesse: https://github.com/ideiasfactory/brazillian_cds_datafeeder_v2/settings/secrets/actions

2. Clique em **"New repository secret"** para cada um:

   - **Nome**: `VERCEL_TOKEN`  
     **Valor**: O token que você criou na Vercel
   
   - **Nome**: `VERCEL_ORG_ID`  
     **Valor**: `flavio-lopes-projects-87104ba4` (do orgId)
   
   - **Nome**: `VERCEL_PROJECT_ID`  
     **Valor**: O projectId do arquivo `.vercel/project.json`

## 3. Desabilitar Deploy Automático na Vercel

Para evitar deploys duplicados:

1. Acesse: https://vercel.com/flavio-lopes-projects-87104ba4/brazillian-cds-datafeeder-v2/settings/git

2. Procure pela opção **"Git Integration"** ou **"Production Branch"**

3. Desabilite o deploy automático:
   - Opção 1: Desconecte completamente a integração Git
   - Opção 2: Configure para não fazer deploy automático no branch `master`

Alternativamente, o `vercel.json` já tem `"github": { "enabled": false }` que deve prevenir deploys automáticos.

## 4. Testar o Fluxo

Após configurar os secrets:

1. Faça um commit e push
2. Verifique em: https://github.com/ideiasfactory/brazillian_cds_datafeeder_v2/actions
3. O workflow "Tests" deve rodar primeiro
4. Se passar, o workflow "Deploy to Vercel" deve iniciar automaticamente
5. Verifique o deploy em: https://vercel.com/flavio-lopes-projects-87104ba4/brazillian-cds-datafeeder-v2

## Fluxo Esperado

```
Push → Tests (GitHub Actions) → ✅ Pass → Deploy (GitHub Actions) → Vercel Production
```

## Troubleshooting

### "Resource not accessible by integration"
- Verifique se os secrets estão configurados corretamente
- Certifique-se de que o VERCEL_TOKEN tem permissões de deploy

### Deploy duplicado
- Desabilite a integração Git na Vercel dashboard
- Ou configure `"github": { "enabled": false }` no vercel.json

### "Project not found"
- Verifique se VERCEL_ORG_ID e VERCEL_PROJECT_ID estão corretos
- Execute `vercel link` novamente para confirmar os IDs
